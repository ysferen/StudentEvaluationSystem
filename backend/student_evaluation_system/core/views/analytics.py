from rest_framework import serializers as drf_serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Avg, Count, F, OuterRef, Subquery, IntegerField, FloatField
from drf_spectacular.utils import extend_schema

from core.permissions import IsAdminOrProgramHead
from core.models import Program, StudentLearningOutcomeScore, StudentProgramOutcomeScore, Course, ProgramOutcome, Term
from evaluation.models import CourseEnrollment, StudentGrade


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


class GpaByYearSerializer(drf_serializers.Serializer):
    year = drf_serializers.IntegerField()
    student_count = drf_serializers.IntegerField()
    gpa = drf_serializers.FloatField(allow_null=True)


class ProgramStatsResponseSerializer(drf_serializers.Serializer):
    programs = ProgramStatSerializer(many=True)
    year_level_breakdown = YearLevelBreakdownSerializer(many=True)
    gpa_by_year = GpaByYearSerializer(many=True)


def _calculate_year_level_breakdown(prog_course_ids, po_ids, duration_years):
    """Calculate year-level breakdown for a program's enrolled students."""
    active_term = Term.objects.filter(is_active=True).first()
    year_level_breakdown = []

    if not active_term or not active_term.academic_year:
        for year_num in range(1, duration_years + 1):
            year_level_breakdown.append({"year": year_num, "student_count": 0, "avg_score": None})
        return year_level_breakdown

    # .order_by() clears the model Meta.ordering so that .distinct() only
    # considers the columns in .values(), preventing overcounting when a
    # student is enrolled in multiple courses.
    enrolled_students = list(
        CourseEnrollment.objects.filter(course_id__in=prog_course_ids, status="active")
        .order_by()
        .values("student_id", "student__student_profile__enrollment_term__academic_year")
        .distinct()
    )

    year_buckets = {year_num: {"student_count": 0} for year_num in range(1, duration_years + 1)}
    students_by_year = {year_num: [] for year_num in range(1, duration_years + 1)}

    for enrollment in enrolled_students:
        enrollment_ay = enrollment.get("student__student_profile__enrollment_term__academic_year")
        if enrollment_ay is None:
            continue
        year_level = active_term.academic_year - enrollment_ay + 1
        if 1 <= year_level <= duration_years:
            year_buckets[year_level]["student_count"] += 1
            students_by_year[year_level].append(enrollment["student_id"])

    for year_num in range(1, duration_years + 1):
        avg_score = None
        if students_by_year[year_num] and po_ids:
            avg = StudentProgramOutcomeScore.objects.filter(
                program_outcome_id__in=po_ids,
                student_id__in=students_by_year[year_num],
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


_TURKISH_GRADE_SCALE = [
    (90, 4.00),
    (85, 3.50),
    (80, 3.00),
    (70, 2.50),
    (60, 2.00),
    (55, 1.50),
    (50, 1.00),
    (0, 0.00),
]


def _percentage_to_gpa(percentage):
    """Convert a percentage score to GPA on 4.0 scale using Turkish letter grade system."""
    for threshold, gpa in _TURKISH_GRADE_SCALE:
        if percentage >= threshold:
            return gpa
    return 0.00


def _get_enrolled_students_by_year(prog_course_ids, duration_years, active_term):
    enrolled_students = list(
        CourseEnrollment.objects.filter(course_id__in=prog_course_ids, status="active")
        .order_by()
        .values("student_id", "student__student_profile__enrollment_term__academic_year")
        .distinct()
    )

    students_by_year = {year_num: [] for year_num in range(1, duration_years + 1)}

    for enrollment in enrolled_students:
        enrollment_ay = enrollment.get("student__student_profile__enrollment_term__academic_year")
        if enrollment_ay is None:
            continue
        year_level = active_term.academic_year - enrollment_ay + 1
        if 1 <= year_level <= duration_years:
            students_by_year[year_level].append(enrollment["student_id"])

    return students_by_year


def _get_student_course_grade_map(all_student_ids, prog_course_ids):
    all_grades = list(
        StudentGrade.objects.filter(
            student_id__in=all_student_ids,
            assessment__course_id__in=prog_course_ids,
        )
        .select_related("assessment", "assessment__course")
        .annotate(
            percentage=F("score") * 100.0 / F("assessment__total_score"),
        )
        .values("student_id", "assessment__course_id", "assessment__course__credits", "percentage", "assessment__weight")
    )

    student_course_grade = {}
    for g in all_grades:
        sid = g["student_id"]
        cid = g["assessment__course_id"]
        credits = g["assessment__course__credits"] or 0
        w = g["assessment__weight"] or 0
        if w > 0:
            key = (sid, cid)
            if key not in student_course_grade:
                student_course_grade[key] = [0, 0, credits]
            student_course_grade[key][0] += g["percentage"] * w
            student_course_grade[key][1] += w

    return student_course_grade


def _get_student_gpa_by_id(student_course_grade):
    student_cumulative = {}
    for (sid, cid), (weighted_sum, total_weight, credits) in student_course_grade.items():
        if total_weight > 0 and credits > 0:
            course_pct = weighted_sum / total_weight
            course_gpa = _percentage_to_gpa(course_pct)
            if sid not in student_cumulative:
                student_cumulative[sid] = [0, 0]
            student_cumulative[sid][0] += course_gpa * credits
            student_cumulative[sid][1] += credits

    student_gpa = {}
    for sid, (gpa_sum, total_credits) in student_cumulative.items():
        if total_credits > 0:
            student_gpa[sid] = round(gpa_sum / total_credits, 2)

    return student_gpa


def _build_gpa_by_year_response(students_by_year, student_gpa, duration_years):
    gpa_by_year = []

    for year_num in range(1, duration_years + 1):
        student_ids = students_by_year[year_num]
        student_count = len(student_ids)
        gpas = [student_gpa[sid] for sid in student_ids if sid in student_gpa]
        gpa = round(sum(gpas) / len(gpas), 2) if gpas else None

        gpa_by_year.append(
            {
                "year": year_num,
                "student_count": student_count,
                "gpa": gpa,
            }
        )

    return gpa_by_year


def _calculate_gpa_by_year(prog_course_ids, duration_years):
    """
    Calculate GPA per year level using Turkish letter grade scale.

    For each student:
      1. Calculate per-course weighted percentage from assessment grades.
      2. Convert to letter-grade GPA using the Turkish scale.
      3. Compute credit-weighted cumulative GPA across all courses.
    Then average cumulative GPAs by year level.
    """
    active_term = Term.objects.filter(is_active=True).first()

    if not active_term or not active_term.academic_year or not prog_course_ids:
        gpa_by_year = []
        for year_num in range(1, duration_years + 1):
            gpa_by_year.append({"year": year_num, "student_count": 0, "gpa": None})
        return gpa_by_year

    students_by_year = _get_enrolled_students_by_year(prog_course_ids, duration_years, active_term)

    all_student_ids = []
    for sids in students_by_year.values():
        all_student_ids.extend(sids)

    if not all_student_ids:
        gpa_by_year = []
        for year_num in range(1, duration_years + 1):
            gpa_by_year.append({"year": year_num, "student_count": 0, "gpa": None})
        return gpa_by_year

    student_course_grade = _get_student_course_grade_map(all_student_ids, prog_course_ids)
    student_gpa = _get_student_gpa_by_id(student_course_grade)

    return _build_gpa_by_year_response(students_by_year, student_gpa, duration_years)


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

        # Single annotated queryset replaces N+1 per-program queries
        program_stats_qs = programs.annotate(
            total_students=Count("courses__enrollments__student_id", distinct=True),
            total_courses=Count("courses", distinct=True),
            po_avg=Subquery(
                StudentProgramOutcomeScore.objects.filter(program_outcome__program=OuterRef("pk"))
                .values("program_outcome__program")
                .annotate(avg=Avg("score"))
                .values("avg")[:1],
                output_field=FloatField(),
            ),
            lo_count=Subquery(
                StudentLearningOutcomeScore.objects.filter(learning_outcome__course__program=OuterRef("pk"))
                .values("learning_outcome__course__program")
                .annotate(cnt=Count("*"))
                .values("cnt")[:1],
                output_field=IntegerField(),
            ),
            po_count=Count("program_outcomes__student_scores", distinct=True),
        )

        # Batch collect course/PO IDs (2 queries instead of N)
        all_course_ids = list(Course.objects.filter(program__in=programs).values_list("id", flat=True))
        all_po_ids = list(ProgramOutcome.objects.filter(program__in=programs).values_list("id", flat=True))

        # Build response list from annotated queryset
        max_duration_years = 4
        result_list = []
        for p in program_stats_qs:
            result_list.append(
                {
                    "id": p.id,
                    "code": p.code,
                    "name": p.name,
                    "total_students": p.total_students,
                    "total_courses": p.total_courses,
                    "avg_score": round(p.po_avg, 2) if p.po_avg is not None else None,
                    "lo_count": p.lo_count or 0,
                    "po_count": p.po_count,
                }
            )
            max_duration_years = max(max_duration_years, p.duration_years)
        program_stats = result_list

        year_level_breakdown = _calculate_year_level_breakdown(all_course_ids, all_po_ids, max_duration_years)

        gpa_by_year = _calculate_gpa_by_year(all_course_ids, max_duration_years)

        return Response(
            {
                "programs": program_stats,
                "year_level_breakdown": year_level_breakdown,
                "gpa_by_year": gpa_by_year,
            }
        )
