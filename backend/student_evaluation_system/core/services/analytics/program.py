from django.db.models import Avg, Count, F

from core.models import Course, LearningOutcome, Program, ProgramOutcome, StudentProgramOutcomeScore, Term
from evaluation.models import CourseEnrollment, StudentGrade


def get_academic_cycle_start_year(term_or_academic_year, semester=None):
    """
    Return the academic-year start for a term.

    The app stores Güz 2025-2026 as academic_year=2025 and Bahar
    2025-2026 as academic_year=2026. For cohort/year-level math those
    are the same academic cycle, so both must normalize to 2025.
    """
    if hasattr(term_or_academic_year, "academic_year"):
        academic_year = term_or_academic_year.academic_year
        semester = term_or_academic_year.semester
    else:
        academic_year = term_or_academic_year

    if academic_year is None:
        return None

    return academic_year - 1 if semester in {"spring", "summer"} else academic_year


def calculate_student_year_level(active_term, enrollment_academic_year, enrollment_semester, duration_years):
    active_cycle = get_academic_cycle_start_year(active_term)
    enrollment_cycle = get_academic_cycle_start_year(enrollment_academic_year, enrollment_semester)
    if active_cycle is None or enrollment_cycle is None:
        return None

    year_level = active_cycle - enrollment_cycle + 1
    if 1 <= year_level <= duration_years:
        return year_level
    return None


def calculate_year_level_breakdown(prog_course_ids, po_ids, duration_years, active_term=None):
    """Calculate year-level breakdown for a program's enrolled students."""
    active_term = active_term or get_active_term()
    year_level_breakdown = []

    if not active_term or not active_term.academic_year:
        for year_num in range(1, duration_years + 1):
            year_level_breakdown.append({"year": year_num, "student_count": 0, "avg_score": None})
        return year_level_breakdown

    enrolled_students = list(
        CourseEnrollment.objects.filter(course_id__in=prog_course_ids, status="active")
        .order_by()
        .values(
            "student_id",
            "student__student_profile__enrollment_term__academic_year",
            "student__student_profile__enrollment_term__semester",
        )
        .distinct()
    )

    year_buckets = {year_num: {"student_count": 0} for year_num in range(1, duration_years + 1)}
    students_by_year = {year_num: [] for year_num in range(1, duration_years + 1)}

    for enrollment in enrolled_students:
        enrollment_ay = enrollment.get("student__student_profile__enrollment_term__academic_year")
        enrollment_semester = enrollment.get("student__student_profile__enrollment_term__semester")
        year_level = calculate_student_year_level(active_term, enrollment_ay, enrollment_semester, duration_years)
        if year_level is None:
            continue
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


def percentage_to_gpa(percentage):
    """Convert a percentage score to GPA on 4.0 scale using Turkish letter grade system."""
    for threshold, gpa in _TURKISH_GRADE_SCALE:
        if percentage >= threshold:
            return gpa
    return 0.00


def get_enrolled_students_by_year(prog_course_ids, duration_years, active_term):
    enrolled_students = list(
        CourseEnrollment.objects.filter(course_id__in=prog_course_ids, status="active")
        .order_by()
        .values(
            "student_id",
            "student__student_profile__enrollment_term__academic_year",
            "student__student_profile__enrollment_term__semester",
        )
        .distinct()
    )

    students_by_year = {year_num: [] for year_num in range(1, duration_years + 1)}

    for enrollment in enrolled_students:
        enrollment_ay = enrollment.get("student__student_profile__enrollment_term__academic_year")
        enrollment_semester = enrollment.get("student__student_profile__enrollment_term__semester")
        year_level = calculate_student_year_level(active_term, enrollment_ay, enrollment_semester, duration_years)
        if year_level is None:
            continue
        students_by_year[year_level].append(enrollment["student_id"])

    return students_by_year


def get_student_course_grade_map(all_student_ids, prog_course_ids):
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
    for grade in all_grades:
        sid = grade["student_id"]
        cid = grade["assessment__course_id"]
        credits = grade["assessment__course__credits"] or 0
        weight = grade["assessment__weight"] or 0
        if weight > 0:
            key = (sid, cid)
            if key not in student_course_grade:
                student_course_grade[key] = [0, 0, credits]
            student_course_grade[key][0] += grade["percentage"] * weight
            student_course_grade[key][1] += weight

    return student_course_grade


def get_student_gpa_by_id(student_course_grade):
    student_cumulative = {}
    for (sid, _cid), (weighted_sum, total_weight, credits) in student_course_grade.items():
        if total_weight > 0 and credits > 0:
            course_pct = weighted_sum / total_weight
            course_gpa = percentage_to_gpa(course_pct)
            if sid not in student_cumulative:
                student_cumulative[sid] = [0, 0]
            student_cumulative[sid][0] += course_gpa * credits
            student_cumulative[sid][1] += credits

    student_gpa = {}
    for sid, (gpa_sum, total_credits) in student_cumulative.items():
        if total_credits > 0:
            student_gpa[sid] = round(gpa_sum / total_credits, 2)

    return student_gpa


def build_gpa_by_year_response(students_by_year, student_gpa, duration_years):
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


def calculate_gpa_by_year(prog_course_ids, duration_years, active_term=None):
    """
    Calculate GPA per year level using Turkish letter grade scale.

    For each student:
      1. Calculate per-course weighted percentage from assessment grades.
      2. Convert to letter-grade GPA using the Turkish scale.
      3. Compute credit-weighted cumulative GPA across all courses.
    Then average cumulative GPAs by year level.
    """
    active_term = active_term or get_active_term()

    if not active_term or not active_term.academic_year or not prog_course_ids:
        return [{"year": year_num, "student_count": 0, "gpa": None} for year_num in range(1, duration_years + 1)]

    students_by_year = get_enrolled_students_by_year(prog_course_ids, duration_years, active_term)

    all_student_ids = []
    for sids in students_by_year.values():
        all_student_ids.extend(sids)

    if not all_student_ids:
        return [{"year": year_num, "student_count": 0, "gpa": None} for year_num in range(1, duration_years + 1)]

    student_course_grade = get_student_course_grade_map(all_student_ids, prog_course_ids)
    student_gpa = get_student_gpa_by_id(student_course_grade)

    return build_gpa_by_year_response(students_by_year, student_gpa, duration_years)


def get_active_term():
    return Term.objects.filter(is_active=True).first()


def get_programs_for_user(user):
    """Return the programs visible to an admin or program head."""
    if user.is_admin_user:
        return Program.objects.select_related("department", "degree_level").all()

    head_profile = getattr(user, "program_head_profile", None)
    if head_profile is None:
        return None
    return Program.objects.filter(pk=head_profile.program_id).select_related("department", "degree_level")


def get_term_course_ids(program_ids, term):
    if not term:
        return []
    return list(Course.objects.filter(program__in=program_ids, term=term).values_list("id", flat=True))


def get_term_po_ids(program_ids, term):
    if not term:
        return []
    return list(ProgramOutcome.objects.filter(program__in=program_ids, term=term).values_list("id", flat=True))


def get_term_course_counts_by_program(program_ids, term):
    if not term:
        return {program_id: 0 for program_id in program_ids}

    counts = (
        Course.objects.filter(program__in=program_ids, term=term)
        .values("program")
        .annotate(total=Count("id"))
        .values_list("program", "total")
    )
    return {**{program_id: 0 for program_id in program_ids}, **dict(counts)}


def get_active_term_student_counts_by_program(program_ids, active_term):
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


def get_term_po_score_stats_by_program(program_ids, term):
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


def get_term_po_counts_by_program(program_ids, term):
    if not term:
        return {program_id: 0 for program_id in program_ids}

    counts = (
        ProgramOutcome.objects.filter(program__in=program_ids, term=term)
        .values("program")
        .annotate(total=Count("id"))
        .values_list("program", "total")
    )
    return {**{program_id: 0 for program_id in program_ids}, **dict(counts)}


def get_term_lo_counts_by_program(program_ids, term):
    if not term:
        return {program_id: 0 for program_id in program_ids}

    counts = (
        LearningOutcome.objects.filter(course__program__in=program_ids, course__term=term)
        .values("course__program")
        .annotate(total=Count("id"))
        .values_list("course__program", "total")
    )
    return {**{program_id: 0 for program_id in program_ids}, **dict(counts)}


def build_program_stats(program_list, students_map, courses_map, po_score_map, po_count_map, lo_map):
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
