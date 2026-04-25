from rest_framework import serializers as drf_serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Avg
from drf_spectacular.utils import extend_schema

from core.permissions import IsAdminOrProgramHead
from core.models import Program, StudentLearningOutcomeScore, StudentProgramOutcomeScore, Course, ProgramOutcome, Term
from evaluation.models import CourseEnrollment


class EnrollmentTrendSerializer(drf_serializers.Serializer):
    term = drf_serializers.CharField()
    student_count = drf_serializers.IntegerField()


class ProgramStatSerializer(drf_serializers.Serializer):
    id = drf_serializers.IntegerField()
    code = drf_serializers.CharField()
    name = drf_serializers.CharField()
    total_students = drf_serializers.IntegerField()
    total_courses = drf_serializers.IntegerField()
    avg_score = drf_serializers.FloatField(allow_null=True)
    lo_count = drf_serializers.IntegerField()
    po_count = drf_serializers.IntegerField()


class YearLevelBreakdownSerializer(drf_serializers.Serializer):
    year = drf_serializers.IntegerField()
    student_count = drf_serializers.IntegerField()
    avg_score = drf_serializers.FloatField(allow_null=True)


class ProgramStatsResponseSerializer(drf_serializers.Serializer):
    programs = ProgramStatSerializer(many=True)
    enrollment_trends = EnrollmentTrendSerializer(many=True)
    year_level_breakdown = YearLevelBreakdownSerializer(many=True)


def _calculate_year_level_breakdown(prog_course_ids, po_ids, duration_years):
    """Calculate year-level breakdown for a program's enrolled students."""
    active_term = Term.objects.filter(is_active=True).first()
    year_level_breakdown = []

    if not active_term or not active_term.academic_year:
        for year_num in range(1, duration_years + 1):
            year_level_breakdown.append({"year": year_num, "student_count": 0, "avg_score": None})
        return year_level_breakdown

    enrolled_students = (
        CourseEnrollment.objects.filter(course_id__in=prog_course_ids, status="active")
        .select_related("student__student_profile__enrollment_term")
        .values("student_id", "student__student_profile__enrollment_term__academic_year")
        .distinct()
    )

    year_buckets = {year_num: {"student_count": 0} for year_num in range(1, duration_years + 1)}

    for enrollment in enrolled_students:
        enrollment_ay = enrollment.get("student__student_profile__enrollment_term__academic_year")
        if enrollment_ay is None:
            continue
        year_level = active_term.academic_year - enrollment_ay + 1
        if 1 <= year_level <= duration_years:
            year_buckets[year_level]["student_count"] += 1

    for year_num in range(1, duration_years + 1):
        students_in_year = [
            enrollment["student_id"]
            for enrollment in enrolled_students
            if enrollment.get("student__student_profile__enrollment_term__academic_year") is not None
            and active_term.academic_year - enrollment["student__student_profile__enrollment_term__academic_year"] + 1
            == year_num
        ]
        avg_score = None
        if students_in_year and po_ids:
            avg = StudentProgramOutcomeScore.objects.filter(
                program_outcome_id__in=po_ids,
                student_id__in=students_in_year,
            ).aggregate(avg_score=Avg("score"))["avg_score"]
            avg_score = round(avg, 2) if avg is not None else None

        year_level_breakdown.append(
            {
                "year": year_num,
                "student_count": year_buckets[year_num]["student_count"],
                "avg_score": avg_score,
            }
        )

    return year_level_breakdown


@extend_schema(
    responses=ProgramStatsResponseSerializer,
    tags=["Analytics"],
)
class ProgramStatsView(APIView):
    """Analytics endpoint for program heads and admins."""

    permission_classes = [IsAuthenticated, IsAdminOrProgramHead]

    def get(self, request):
        """
        Return aggregated statistics scoped to the user's programs.

        Admins see all programs. Program heads see only their program.
        """
        user = request.user

        if user.is_admin_user:
            programs = Program.objects.select_related("department", "degree_level").all()
        else:
            head_profile = getattr(user, "program_head_profile", None)
            if head_profile is None:
                return Response({"detail": "No program head profile found."}, status=403)
            programs = Program.objects.filter(pk=head_profile.program_id).select_related("department", "degree_level")

        program_ids = list(programs.values_list("id", flat=True))

        program_stats = []
        po_ids = []
        prog_course_ids = []
        for program in programs:
            prog_courses = Course.objects.filter(program=program)
            prog_course_ids = list(prog_courses.values_list("id", flat=True))

            total_students = (
                CourseEnrollment.objects.filter(course_id__in=prog_course_ids).values("student_id").distinct().count()
            )

            total_courses = Course.objects.filter(program=program).count()

            po_ids = list(ProgramOutcome.objects.filter(program=program).values_list("id", flat=True))
            po_avg = StudentProgramOutcomeScore.objects.filter(program_outcome_id__in=po_ids).aggregate(
                avg_score=Avg("score")
            )["avg_score"]

            lo_count = StudentLearningOutcomeScore.objects.filter(learning_outcome__course_id__in=prog_course_ids).count()

            po_count = StudentProgramOutcomeScore.objects.filter(program_outcome_id__in=po_ids).count()

            program_stats.append(
                {
                    "id": program.id,
                    "code": program.code,
                    "name": program.name,
                    "total_students": total_students,
                    "total_courses": total_courses,
                    "avg_score": round(po_avg, 2) if po_avg is not None else None,
                    "lo_count": lo_count,
                    "po_count": po_count,
                }
            )

        terms = Term.objects.all().order_by("-name")[:5]
        enrollment_trends = []
        for term in terms:
            count = (
                CourseEnrollment.objects.filter(
                    course__program_id__in=program_ids,
                    course__term=term,
                )
                .values("student_id")
                .distinct()
                .count()
            )
            enrollment_trends.append(
                {
                    "term": term.name,
                    "student_count": count,
                }
            )

        duration_years = program.duration_years if hasattr(program, "duration_years") else 4
        year_level_breakdown = _calculate_year_level_breakdown(prog_course_ids, po_ids, duration_years)

        return Response(
            {
                "programs": program_stats,
                "enrollment_trends": enrollment_trends,
                "year_level_breakdown": year_level_breakdown,
            }
        )
