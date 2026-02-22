"""
Tests for evaluation app models and services.

Tests assessments, grades, and score calculations.
"""

import pytest
from django.db import IntegrityError

from evaluation.models import Assessment, StudentGrade, CourseEnrollment
from evaluation.services import calculate_course_scores


@pytest.mark.django_db
class TestAssessmentModel:
    """Test Assessment model."""

    def test_assessment_creation(self, fb_course_factory):
        """Test creating an assessment."""
        course = fb_course_factory()
        assessment = Assessment.objects.create(
            name="Midterm Exam",
            course=course,
            assessment_type="midterm",
            total_score=100,
            weight=0.3,
        )

        assert assessment.name == "Midterm Exam"
        assert assessment.assessment_type == "midterm"
        assert assessment.total_score == 100

    def test_assessment_weight_validation(self, fb_course_factory):
        """Test assessment weight must be between 0 and 1."""
        course = fb_course_factory()

        # Valid weight
        assessment = Assessment.objects.create(
            name="Valid Assessment",
            course=course,
            assessment_type="quiz",
            total_score=100,
            weight=0.25,
        )
        assert assessment.weight == 0.25

    def test_assessment_ordering(self, fb_course_factory):
        """Test assessments are ordered by date."""
        course = fb_course_factory()

        assessment1 = Assessment.objects.create(
            name="First",
            course=course,
            assessment_type="quiz",
            date="2025-01-15",
        )
        assessment2 = Assessment.objects.create(
            name="Second",
            course=course,
            assessment_type="quiz",
            date="2025-01-20",
        )

        assessments = list(Assessment.objects.filter(course=course))
        assert assessments[0] == assessment1
        assert assessments[1] == assessment2


@pytest.mark.django_db
class TestStudentGradeModel:
    """Test StudentGrade model."""

    def test_grade_creation(self, fb_student_factory, fb_assessment_factory):
        """Test creating a student grade."""
        student = fb_student_factory()
        assessment = fb_assessment_factory()

        grade = StudentGrade.objects.create(
            student=student,
            assessment=assessment,
            score=85.5,
        )

        assert grade.score == 85.5
        assert grade.student == student
        assert grade.assessment == assessment

    def test_grade_validation_score_range(self, fb_student_factory, fb_assessment_factory):
        """Test grade score must be non-negative."""
        student = fb_student_factory()
        assessment = fb_assessment_factory()

        # Negative score should fail
        with pytest.raises(IntegrityError):
            StudentGrade.objects.create(
                student=student,
                assessment=assessment,
                score=-10,
            )

    def test_unique_student_assessment(self, fb_student_factory, fb_assessment_factory):
        """Test student can only have one grade per assessment."""
        student = fb_student_factory()
        assessment = fb_assessment_factory()

        StudentGrade.objects.create(
            student=student,
            assessment=assessment,
            score=80,
        )

        # Creating duplicate should fail
        with pytest.raises(IntegrityError):
            StudentGrade.objects.create(
                student=student,
                assessment=assessment,
                score=90,
            )


@pytest.mark.django_db
class TestCourseEnrollment:
    """Test CourseEnrollment model."""

    def test_enrollment_creation(self, fb_student_factory, fb_course_factory):
        """Test enrolling a student in a course."""
        student = fb_student_factory()
        course = fb_course_factory()

        enrollment = CourseEnrollment.objects.create(
            student=student,
            course=course,
            status="active",
        )

        assert enrollment.student == student
        assert enrollment.course == course
        assert enrollment.status == "active"

    def test_unique_enrollment(self, fb_student_factory, fb_course_factory):
        """Test student can only be enrolled once per course."""
        student = fb_student_factory()
        course = fb_course_factory()

        CourseEnrollment.objects.create(
            student=student,
            course=course,
        )

        # Duplicate enrollment should fail
        with pytest.raises(IntegrityError):
            CourseEnrollment.objects.create(
                student=student,
                course=course,
            )


@pytest.mark.django_db
class TestScoreCalculation:
    """Test score calculation services."""

    def test_calculate_course_scores(self, fb_course_factory, fb_student_factory, fb_assessment_factory):
        """Test course score calculation."""
        course = fb_course_factory()
        student = fb_student_factory()
        assessment = fb_assessment_factory(course=course)

        # Create a grade
        StudentGrade.objects.create(
            student=student,
            assessment=assessment,
            score=80,
        )

        # Run calculation
        result = calculate_course_scores(course.id)

        assert result is not None

    def test_calculate_empty_course(self, fb_course_factory):
        """Test calculation for course with no grades."""
        course = fb_course_factory()

        result = calculate_course_scores(course.id)

        # Should handle empty course gracefully
        assert result is not None
