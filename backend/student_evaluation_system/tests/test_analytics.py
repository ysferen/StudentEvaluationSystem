"""
Unit tests for GPA calculation functions in core.views.analytics.
"""

import pytest

from core.views.analytics import (
    _percentage_to_gpa,
    _get_student_course_grade_map,
    _get_student_gpa_by_id,
    _calculate_gpa_by_year,
)
from core.models import Term
from evaluation.models import StudentGrade


class TestPercentageToGpa:
    """Test the _percentage_to_gpa pure function."""

    def test_returns_4_00_for_90_and_above(self):
        assert _percentage_to_gpa(100) == 4.00
        assert _percentage_to_gpa(95) == 4.00
        assert _percentage_to_gpa(90) == 4.00

    def test_returns_3_50_for_85_to_89(self):
        assert _percentage_to_gpa(89.99) == 3.50
        assert _percentage_to_gpa(87) == 3.50
        assert _percentage_to_gpa(85) == 3.50

    def test_returns_3_00_for_80_to_84(self):
        assert _percentage_to_gpa(84.99) == 3.00
        assert _percentage_to_gpa(82) == 3.00
        assert _percentage_to_gpa(80) == 3.00

    def test_returns_2_50_for_70_to_79(self):
        assert _percentage_to_gpa(79.99) == 2.50
        assert _percentage_to_gpa(75) == 2.50
        assert _percentage_to_gpa(70) == 2.50

    def test_returns_2_00_for_60_to_69(self):
        assert _percentage_to_gpa(69.99) == 2.00
        assert _percentage_to_gpa(65) == 2.00
        assert _percentage_to_gpa(60) == 2.00

    def test_returns_1_50_for_55_to_59(self):
        assert _percentage_to_gpa(59.99) == 1.50
        assert _percentage_to_gpa(57) == 1.50
        assert _percentage_to_gpa(55) == 1.50

    def test_returns_1_00_for_50_to_54(self):
        assert _percentage_to_gpa(54.99) == 1.00
        assert _percentage_to_gpa(52) == 1.00
        assert _percentage_to_gpa(50) == 1.00

    def test_returns_0_00_below_50(self):
        assert _percentage_to_gpa(49.99) == 0.00
        assert _percentage_to_gpa(25) == 0.00
        assert _percentage_to_gpa(0) == 0.00

    def test_handles_negative_values(self):
        assert _percentage_to_gpa(-10) == 0.00


class TestGetStudentGpaById:
    """Test the _get_student_gpa_by_id pure function."""

    def test_single_course_correct_gpa(self):
        grade_map = {
            (1, 101): [85.0, 1.0, 3],
        }
        result = _get_student_gpa_by_id(grade_map)
        assert result == {1: 3.50}

    def test_multiple_courses_credit_weighted_average(self):
        grade_map = {
            (1, 101): [95.0, 1.0, 3],
            (1, 102): [65.0, 1.0, 4],
        }
        result = _get_student_gpa_by_id(grade_map)
        expected = round((4.00 * 3 + 2.00 * 4) / 7, 2)
        assert result == {1: expected}

    def test_multiple_students_multiple_courses(self):
        grade_map = {
            (1, 101): [90.0, 1.0, 3],
            (2, 101): [70.0, 1.0, 4],
        }
        result = _get_student_gpa_by_id(grade_map)
        assert result == {1: 4.00, 2: 2.50}

    def test_zero_weight_skipped(self):
        grade_map = {
            (1, 101): [80.0, 0.0, 3],
        }
        result = _get_student_gpa_by_id(grade_map)
        assert result == {}

    def test_zero_credits_skipped(self):
        grade_map = {
            (1, 101): [80.0, 1.0, 0],
        }
        result = _get_student_gpa_by_id(grade_map)
        assert result == {}

    def test_empty_grade_map_returns_empty_dict(self):
        result = _get_student_gpa_by_id({})
        assert result == {}

    def test_rounds_to_2_decimal_places(self):
        grade_map = {
            (1, 101): [85.5, 1.0, 3],
        }
        result = _get_student_gpa_by_id(grade_map)
        assert result[1] == 3.50
        assert isinstance(result[1], float)

    def test_cumulative_over_three_courses(self):
        grade_map = {
            (1, 101): [92.0, 1.0, 3],
            (1, 102): [78.0, 1.0, 3],
            (1, 103): [55.0, 1.0, 2],
        }
        result = _get_student_gpa_by_id(grade_map)
        expected = round((4.00 * 3 + 2.50 * 3 + 1.50 * 2) / 8, 2)
        assert result == {1: expected}


@pytest.mark.django_db
class TestGetStudentCourseGradeMap:
    """Test the _get_student_course_grade_map DB-dependent function."""

    def test_single_grade_maps_correctly(
        self, student_user_factory, course_factory, assessment_factory, course_enrollment_factory, student_grade_factory
    ):
        course = course_factory(credits=3)
        student = student_user_factory()
        course_enrollment_factory(student=student, course=course)
        assessment = assessment_factory(course=course, total_score=100, weight=0.5)
        student_grade_factory(student=student, assessment=assessment, score=80.0)

        result = _get_student_course_grade_map([student.id], [course.id])

        assert (student.id, course.id) in result
        weighted_sum, total_weight, credits = result[(student.id, course.id)]
        assert weighted_sum == pytest.approx(80.0 * 0.5, rel=1e-2)
        assert total_weight == 0.5
        assert credits == 3

    def test_multiple_assessments_weighted_correctly(
        self, student_user_factory, course_factory, assessment_factory, course_enrollment_factory
    ):
        course = course_factory(credits=4)
        student = student_user_factory()
        course_enrollment_factory(student=student, course=course)

        ass1 = assessment_factory(course=course, total_score=100, weight=0.3)
        ass2 = assessment_factory(course=course, total_score=100, weight=0.7)

        StudentGrade.objects.create(student=student, assessment=ass1, score=90.0)
        StudentGrade.objects.create(student=student, assessment=ass2, score=70.0)

        result = _get_student_course_grade_map([student.id], [course.id])

        weighted_sum, total_weight, credits = result[(student.id, course.id)]
        assert weighted_sum == pytest.approx(90.0 * 0.3 + 70.0 * 0.7, rel=1e-2)
        assert total_weight == 1.0
        assert credits == 4

    def test_zero_weight_assessment_ignored(
        self, student_user_factory, course_factory, assessment_factory, course_enrollment_factory
    ):
        course = course_factory(credits=3)
        student = student_user_factory()
        course_enrollment_factory(student=student, course=course)

        ass_zero = assessment_factory(course=course, total_score=100, weight=0.0)
        ass_valid = assessment_factory(course=course, total_score=100, weight=0.8)

        StudentGrade.objects.create(student=student, assessment=ass_zero, score=100.0)
        StudentGrade.objects.create(student=student, assessment=ass_valid, score=80.0)

        result = _get_student_course_grade_map([student.id], [course.id])

        weighted_sum, total_weight, credits = result[(student.id, course.id)]
        assert weighted_sum == pytest.approx(80.0 * 0.8, rel=1e-2)
        assert total_weight == 0.8
        assert credits == 3

    def test_multiple_courses_for_same_student(
        self, student_user_factory, course_factory, assessment_factory, course_enrollment_factory
    ):
        course1 = course_factory(credits=3)
        course2 = course_factory(credits=4)
        student = student_user_factory()
        course_enrollment_factory(student=student, course=course1)
        course_enrollment_factory(student=student, course=course2)

        ass1 = assessment_factory(course=course1, total_score=100, weight=1.0)
        ass2 = assessment_factory(course=course2, total_score=100, weight=1.0)

        StudentGrade.objects.create(student=student, assessment=ass1, score=85.0)
        StudentGrade.objects.create(student=student, assessment=ass2, score=75.0)

        result = _get_student_course_grade_map([student.id], [course1.id, course2.id])

        assert len(result) == 2
        assert result[(student.id, course1.id)] == [85.0, 1.0, 3]
        assert result[(student.id, course2.id)] == [75.0, 1.0, 4]

    def test_empty_student_ids_returns_empty_dict(self, course_factory):
        course = course_factory()
        result = _get_student_course_grade_map([], [course.id])
        assert result == {}

    def test_empty_course_ids_returns_empty_dict(self, student_user_factory):
        student = student_user_factory()
        result = _get_student_course_grade_map([student.id], [])
        assert result == {}


@pytest.mark.django_db
class TestCalculateGpaByYear:
    """Test the _calculate_gpa_by_year orchestrator function."""

    @pytest.fixture
    def _active_term(self):
        return Term.objects.create(name="Active Term", is_active=True, academic_year=2025)

    def test_no_active_term_returns_null_gpas(self, program_factory):
        program = program_factory(duration_years=4)
        course_ids = list(program.courses.values_list("id", flat=True))

        result = _calculate_gpa_by_year(course_ids, program.duration_years)

        assert len(result) == 4
        for item in result:
            assert item["gpa"] is None

    def test_active_term_without_academic_year_returns_null_gpas(self, program_factory):
        Term.objects.create(name="No AY Term", is_active=True, academic_year=None)
        program = program_factory(duration_years=4)
        course_ids = list(program.courses.values_list("id", flat=True))

        result = _calculate_gpa_by_year(course_ids, program.duration_years)

        assert len(result) == 4
        for item in result:
            assert item["gpa"] is None

    def test_empty_course_ids_returns_empty_year_buckets(self):
        Term.objects.create(name="Active", is_active=True, academic_year=2025)

        result = _calculate_gpa_by_year([], 4)

        assert len(result) == 4
        for item in result:
            assert item["student_count"] == 0
            assert item["gpa"] is None

    def test_no_students_returns_year_buckets_with_null(self):
        Term.objects.create(name="Active", is_active=True, academic_year=2025)
        result = _calculate_gpa_by_year([999], 3)

        assert len(result) == 3
        for item in result:
            assert item["student_count"] == 0
            assert item["gpa"] is None

    def test_single_student_gpa_calculated_correctly(
        self, student_user_factory, course_factory, assessment_factory, course_enrollment_factory, _active_term
    ):
        program = _active_term.courses.first().program if _active_term.courses.exists() else None
        from core.models import Program
        from factories import DegreeLevelFactory, DepartmentFactory

        dept = DepartmentFactory()
        deg = DegreeLevelFactory()
        program = Program.objects.create(
            code="TESTGP", name="GPA Test Program", degree_level=deg, department=dept, duration_years=4
        )
        course = course_factory(credits=3, program=program, term=_active_term)
        student = student_user_factory()
        student.student_profile.enrollment_term = _active_term
        student.student_profile.enrollment_term.academic_year = 2025  # year 1
        student.student_profile.enrollment_term.save()
        student.student_profile.save()

        course_enrollment_factory(student=student, course=course, status="active")
        assessment = assessment_factory(course=course, total_score=100, weight=1.0)
        StudentGrade.objects.create(student=student, assessment=assessment, score=85.0)

        result = _calculate_gpa_by_year([course.id], program.duration_years)

        assert result[0]["year"] == 1
        assert result[0]["student_count"] == 1
        assert result[0]["gpa"] == 3.50
        assert result[1]["gpa"] is None

    def test_students_across_multiple_year_levels(
        self, course_factory, assessment_factory, course_enrollment_factory, _active_term
    ):
        from core.models import Program
        from factories import DegreeLevelFactory, DepartmentFactory

        dept = DepartmentFactory()
        deg = DegreeLevelFactory()
        program = Program.objects.create(
            code="TESTG2", name="Multi-Year GPA Test", degree_level=deg, department=dept, duration_years=4
        )
        course = course_factory(credits=3, program=program, term=_active_term)
        assessment = assessment_factory(course=course, total_score=100, weight=1.0)

        enrollment_term_y1 = Term.objects.create(name="Fall 2025", is_active=False, academic_year=2025)
        enrollment_term_y2 = Term.objects.create(name="Fall 2024", is_active=False, academic_year=2024)

        from tests.factories import StudentUserFactory

        student1 = StudentUserFactory()
        student1.student_profile.enrollment_term = enrollment_term_y1
        student1.student_profile.save()
        course_enrollment_factory(student=student1, course=course, status="active")
        StudentGrade.objects.create(student=student1, assessment=assessment, score=85.0)

        student2 = StudentUserFactory()
        student2.student_profile.enrollment_term = enrollment_term_y2
        student2.student_profile.save()
        course_enrollment_factory(student=student2, course=course, status="active")
        StudentGrade.objects.create(student=student2, assessment=assessment, score=75.0)

        result = _calculate_gpa_by_year([course.id], program.duration_years)

        assert result[0]["year"] == 1
        assert result[0]["student_count"] == 1
        assert result[0]["gpa"] == 3.50

        assert result[1]["year"] == 2
        assert result[1]["student_count"] == 1
        assert result[1]["gpa"] == 2.50

        assert result[2]["gpa"] is None
        assert result[3]["gpa"] is None

    def test_student_with_enrollment_term_missing_academic_year_skipped(
        self, student_user_factory, course_factory, assessment_factory, course_enrollment_factory, _active_term
    ):
        from core.models import Program
        from factories import DegreeLevelFactory, DepartmentFactory

        dept = DepartmentFactory()
        deg = DegreeLevelFactory()
        program = Program.objects.create(
            code="TESTG3", name="Skip Test Program", degree_level=deg, department=dept, duration_years=4
        )
        course = course_factory(credits=3, program=program, term=_active_term)
        student = student_user_factory()
        student.student_profile.enrollment_term.academic_year = None
        student.student_profile.enrollment_term.save()

        course_enrollment_factory(student=student, course=course, status="active")
        assessment = assessment_factory(course=course, total_score=100, weight=1.0)
        StudentGrade.objects.create(student=student, assessment=assessment, score=85.0)

        result = _calculate_gpa_by_year([course.id], program.duration_years)

        for item in result:
            assert item["student_count"] == 0
            assert item["gpa"] is None
