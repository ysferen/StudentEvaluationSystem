from rest_framework import serializers as drf_serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Avg
from drf_spectacular.utils import extend_schema

from core.permissions import IsAdminOrProgramHead
from core.models import Program, StudentLearningOutcomeScore, StudentProgramOutcomeScore, Course, ProgramOutcome, Term
from evaluation.models import CourseEnrollment
from users.models import InstructorProfile


class EnrollmentTrendSerializer(drf_serializers.Serializer):
    term = drf_serializers.CharField()
    student_count = drf_serializers.IntegerField()


class ProgramStatSerializer(drf_serializers.Serializer):
    id = drf_serializers.IntegerField()
    code = drf_serializers.CharField()
    name = drf_serializers.CharField()
    total_students = drf_serializers.IntegerField()
    total_faculty = drf_serializers.IntegerField()
    avg_score = drf_serializers.FloatField(allow_null=True)
    lo_count = drf_serializers.IntegerField()
    po_count = drf_serializers.IntegerField()


class ProgramStatsResponseSerializer(drf_serializers.Serializer):
    programs = ProgramStatSerializer(many=True)
    enrollment_trends = EnrollmentTrendSerializer(many=True)


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
        for program in programs:
            prog_courses = Course.objects.filter(program=program)
            prog_course_ids = list(prog_courses.values_list("id", flat=True))

            total_students = (
                CourseEnrollment.objects.filter(course_id__in=prog_course_ids).values("student_id").distinct().count()
            )

            total_faculty = InstructorProfile.objects.filter(user__taught_courses__in=prog_courses).distinct().count()

            po_ids = ProgramOutcome.objects.filter(program=program).values_list("id", flat=True)
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
                    "total_faculty": total_faculty,
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

        return Response(
            {
                "programs": program_stats,
                "enrollment_trends": enrollment_trends,
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

        return Response(
            {
                "programs": program_stats,
                "enrollment_trends": enrollment_trends,
            }
        )
