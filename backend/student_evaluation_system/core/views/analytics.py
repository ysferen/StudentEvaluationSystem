from rest_framework import serializers as drf_serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Avg, Count, F
from drf_spectacular.utils import extend_schema

from core.permissions import IsAdminOrProgramHead
from core.models import Program, StudentProgramOutcomeScore, Course, ProgramOutcome, Term, LearningOutcome
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


def _calculate_year_level_breakdown(prog_course_ids, po_ids, duration_years, active_term=None):
    """Calculate year-level breakdown for a program's enrolled students."""
    active_term = active_term or Term.objects.filter(is_active=True).first()
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


def _calculate_gpa_by_year(prog_course_ids, duration_years, active_term=None):
    """
    Calculate GPA per year level using Turkish letter grade scale.

    For each student:
      1. Calculate per-course weighted percentage from assessment grades.
      2. Convert to letter-grade GPA using the Turkish scale.
      3. Compute credit-weighted cumulative GPA across all courses.
    Then average cumulative GPAs by year level.
    """
    active_term = active_term or Term.objects.filter(is_active=True).first()

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


def _get_active_term_student_counts_by_program(program_ids, active_term):
    """Count distinct students with active enrollments in active-term courses."""
    if not active_term:
        return {program_id: 0 for program_id in program_ids}

    counts = (
        CourseEnrollment.objects.filter(
            course__program__in=program_ids,
            course__term=active_term,
            status="active",
        )
        .values("course__program")
        .annotate(total=Count("student_id", distinct=True))
        .values_list("course__program", "total")
    )
    return {**{program_id: 0 for program_id in program_ids}, **dict(counts)}


def _get_programs_for_user(user):
    """Return the programs visible to an admin or program head."""
    if user.is_admin_user:
        return Program.objects.select_related("department", "degree_level").all()

    head_profile = getattr(user, "program_head_profile", None)
    if head_profile is None:
        return None
    return Program.objects.filter(pk=head_profile.program_id).select_related("department", "degree_level")


def _get_active_term():
    return Term.objects.filter(is_active=True).first()


def _get_term_course_ids(program_ids, term):
    if not term:
        return []
    return list(Course.objects.filter(program__in=program_ids, term=term).values_list("id", flat=True))


def _get_term_po_ids(program_ids, term):
    if not term:
        return []
    return list(ProgramOutcome.objects.filter(program__in=program_ids, term=term).values_list("id", flat=True))


def _get_term_course_counts_by_program(program_ids, term):
    if not term:
        return {program_id: 0 for program_id in program_ids}

    counts = (
        Course.objects.filter(program__in=program_ids, term=term)
        .values("program")
        .annotate(total=Count("id"))
        .values_list("program", "total")
    )
    return {**{program_id: 0 for program_id in program_ids}, **dict(counts)}


def _get_term_po_score_stats_by_program(program_ids, term):
    defaults = {program_id: {"avg": None, "count": 0} for program_id in program_ids}
    if not term:
        return defaults

    stats = (
        StudentProgramOutcomeScore.objects.filter(program_outcome__program__in=program_ids, term=term)
        .values("program_outcome__program")
        .annotate(avg_score=Avg("score"), total_count=Count("id"))
        .values_list("program_outcome__program", "avg_score", "total_count")
    )
    return {**defaults, **{row[0]: {"avg": row[1], "count": row[2]} for row in stats}}


def _get_term_po_counts_by_program(program_ids, term):
    if not term:
        return {program_id: 0 for program_id in program_ids}

    counts = (
        ProgramOutcome.objects.filter(program__in=program_ids, term=term)
        .values("program")
        .annotate(total=Count("id"))
        .values_list("program", "total")
    )
    return {**{program_id: 0 for program_id in program_ids}, **dict(counts)}


def _get_term_lo_counts_by_program(program_ids, term):
    if not term:
        return {program_id: 0 for program_id in program_ids}

    counts = (
        LearningOutcome.objects.filter(course__program__in=program_ids, course__term=term)
        .values("course__program")
        .annotate(total=Count("id"))
        .values_list("course__program", "total")
    )
    return {**{program_id: 0 for program_id in program_ids}, **dict(counts)}


def _build_program_stats(program_list, students_map, courses_map, po_score_map, po_count_map, lo_map):
    program_stats = []
    max_duration_years = 4

    for program in program_list:
        po_data = po_score_map.get(program.id, {"avg": None, "count": 0})
        avg_score = round(po_data["avg"], 2) if po_data["avg"] is not None else None

        program_stats.append(
            {
                "id": program.id,
                "code": program.code,
                "name": program.name,
                "total_students": students_map.get(program.id, 0),
                "total_courses": courses_map.get(program.id, 0),
                "avg_score": avg_score,
                "lo_count": lo_map.get(program.id, 0),
                "po_count": po_count_map.get(program.id, 0),
            }
        )
        max_duration_years = max(max_duration_years, program.duration_years)

    return program_stats, max_duration_years


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

        programs = _get_programs_for_user(user)
        if programs is None:
            return Response({"detail": "No program head profile found."}, status=403)

        program_list = list(programs)
        program_ids = [p.id for p in program_list]

        active_term = _get_active_term()
        courses_map = _get_term_course_counts_by_program(program_ids, active_term)
        students_map = _get_active_term_student_counts_by_program(program_ids, active_term)
        po_score_map = _get_term_po_score_stats_by_program(program_ids, active_term)
        po_count_map = _get_term_po_counts_by_program(program_ids, active_term)
        lo_map = _get_term_lo_counts_by_program(program_ids, active_term)
        active_course_ids = _get_term_course_ids(program_ids, active_term)
        active_po_ids = _get_term_po_ids(program_ids, active_term)
        program_stats, max_duration_years = _build_program_stats(
            program_list,
            students_map,
            courses_map,
            po_score_map,
            po_count_map,
            lo_map,
        )

        year_level_breakdown = _calculate_year_level_breakdown(
            active_course_ids,
            active_po_ids,
            max_duration_years,
            active_term=active_term,
        )

        gpa_by_year = _calculate_gpa_by_year(active_course_ids, max_duration_years, active_term=active_term)

        return Response(
            {
                "programs": program_stats,
                "year_level_breakdown": year_level_breakdown,
                "gpa_by_year": gpa_by_year,
            }
        )
