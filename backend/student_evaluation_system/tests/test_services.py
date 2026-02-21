"""
Unit tests for service functions (score calculation, file import).

These tests verify the business logic without hitting the database
or making HTTP requests.
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from django.db import transaction

from evaluation.services import calculate_course_scores, calculate_student_po_scores
from core.models import StudentLearningOutcomeScore, StudentProgramOutcomeScore


@pytest.mark.django_db
class TestCalculateCourseScores:
    """Test the calculate_course_scores function."""

    def test_calculates_lo_scores_for_all_enrolled_students(
        self, course_with_data_factory
    ):
        """Test that LO scores are calculated for all enrolled students."""
        # Create a course with complete data
        course = course_with_data_factory()

        # Verify initial state - should have no LO scores
        initial_score_count = StudentLearningOutcomeScore.objects.filter(
            learning_outcome__course=course
        ).count()
        assert initial_score_count == 0

        # Calculate scores
        calculate_course_scores(course.id)

        # Verify scores were created
        scores = StudentLearningOutcomeScore.objects.filter(
            learning_outcome__course=course
        )

        # Each enrolled student should have LO scores
        enrollment_count = course.enrollments.count()
        lo_count = course.learning_outcomes.count()

        assert scores.count() == enrollment_count * lo_count

    def test_score_calculation_with_weights(
        self, course_factory, assessment_factory, student_user_factory,
        learning_outcome_factory, course_enrollment_factory,
        student_grade_factory
    ):
        """Test that scores are correctly calculated using assessment weights."""
        # Create course with known data
        course = course_factory()

        # Create learning outcome
        lo = learning_outcome_factory(course=course)

        # Create student and enroll
        student = student_user_factory()
        course_enrollment_factory(student=student, course=course)

        # Create assessment with weight
        assessment = assessment_factory(
            course=course,
            total_score=100,
            weight=0.5
        )

        # Create LO mapping with weight
        from evaluation.models import AssessmentLearningOutcomeMapping
        AssessmentLearningOutcomeMapping.objects.create(
            assessment=assessment,
            learning_outcome=lo,
            weight=1.0  # 100% of this assessment counts toward LO
        )

        # Student gets 80/100 on assessment
        student_grade_factory(
            student=student,
            assessment=assessment,
            score=80.0
        )

        # Calculate scores
        calculate_course_scores(course.id)

        # Verify calculated score
        score = StudentLearningOutcomeScore.objects.get(
            student=student,
            learning_outcome=lo
        )

        # Score should be 80 (80% of 100 * weight 1.0 / total weight 1.0)
        assert score.score == pytest.approx(80.0, rel=1e-2)

    def test_replaces_old_scores_on_recalculation(
        self, course_with_data_factory
    ):
        """Test that old scores are deleted before new ones are created."""
        course = course_with_data_factory()

        # First calculation
        calculate_course_scores(course.id)

        first_score_ids = set(
            StudentLearningOutcomeScore.objects.filter(
                learning_outcome__course=course
            ).values_list('id', flat=True)
        )

        # Second calculation
        calculate_course_scores(course.id)

        second_score_ids = set(
            StudentLearningOutcomeScore.objects.filter(
                learning_outcome__course=course
            ).values_list('id', flat=True)
        )

        # No IDs should be the same (old scores deleted, new ones created)
        assert not first_score_ids.intersection(second_score_ids)

    def test_handles_no_enrollments(self, course_factory):
        """Test calculation when course has no enrolled students."""
        course = course_factory()

        # Should not raise exception
        calculate_course_scores(course.id)

        # No scores should be created
        assert StudentLearningOutcomeScore.objects.filter(
            learning_outcome__course=course
        ).count() == 0

    def test_handles_no_assessments(self, course_factory, student_user_factory,
                                     course_enrollment_factory):
        """Test calculation when course has no assessments."""
        course = course_factory()

        # Enroll student but don't create assessments
        student = student_user_factory()
        course_enrollment_factory(student=student, course=course)

        # Should not raise exception
        calculate_course_scores(course.id)

        # All LO scores should be 0
        scores = StudentLearningOutcomeScore.objects.filter(student=student)
        for score in scores:
            assert score.score == 0.0


@pytest.mark.django_db
class TestCalculateStudentPOScores:
    """Test the calculate_student_po_scores function."""

    def test_calculates_po_scores_from_lo_scores(
        self, course_with_data_factory, program_outcome_factory,
        learning_outcome_program_outcome_mapping_factory
    ):
        """Test that PO scores are calculated from LO scores."""
        course = course_with_data_factory()
        program = course.program
        term = course.term

        # Create program outcome
        po = program_outcome_factory(program=program, term=term)

        # Get a learning outcome and set its score
        lo = course.learning_outcomes.first()
        student = course.enrollments.first().student

        # Set LO score to 80 (create row if missing)
        StudentLearningOutcomeScore.objects.update_or_create(
            student=student,
            learning_outcome=lo,
            defaults={'score': 80.0}
        )

        # Create LO-PO mapping with weight 1.0
        from core.models import LearningOutcomeProgramOutcomeMapping
        LearningOutcomeProgramOutcomeMapping.objects.create(
            course=course,
            learning_outcome=lo,
            program_outcome=po,
            weight=1.0
        )

        # Calculate PO scores
        calculate_student_po_scores(student.id, program.id, term.id)

        # Verify PO score was created
        po_score = StudentProgramOutcomeScore.objects.get(
            student=student,
            program_outcome=po
        )

        # PO score should be 80 (LO score * weight / total weight)
        assert po_score.score == pytest.approx(80.0, rel=1e-2)

    def test_handles_missing_lo_scores(self, course_with_data_factory,
                                        program_outcome_factory):
        """Test calculation when some LO scores are missing."""
        course = course_with_data_factory()
        program = course.program
        term = course.term

        po = program_outcome_factory(program=program, term=term)
        lo = course.learning_outcomes.first()
        student = course.enrollments.first().student

        # Delete LO scores
        StudentLearningOutcomeScore.objects.filter(
            student=student,
            learning_outcome__course=course
        ).delete()

        # Create mapping
        from core.models import LearningOutcomeProgramOutcomeMapping
        LearningOutcomeProgramOutcomeMapping.objects.create(
            course=course,
            learning_outcome=lo,
            program_outcome=po,
            weight=1.0
        )

        # Should not raise exception
        calculate_student_po_scores(student.id, program.id, term.id)

        # PO score should be 0 (missing LO treated as 0)
        po_score = StudentProgramOutcomeScore.objects.get(
            student=student,
            program_outcome=po
        )
        assert po_score.score == 0.0

    def test_replaces_old_po_scores(self, course_with_data_factory,
                                     program_outcome_factory):
        """Test that old PO scores are deleted before new ones are created."""
        course = course_with_data_factory()
        program = course.program
        term = course.term

        po = program_outcome_factory(program=program, term=term)
        student = course.enrollments.first().student

        # Create initial PO score
        StudentProgramOutcomeScore.objects.create(
            student=student,
            program_outcome=po,
            term=term,
            score=50.0
        )

        # Calculate again
        calculate_student_po_scores(student.id, program.id, term.id)

        # Should have exactly one score
        scores = StudentProgramOutcomeScore.objects.filter(
            student=student,
            program_outcome=po
        )
        assert scores.count() == 1


@pytest.mark.django_db
class TestScoreCalculationEdgeCases:
    """Test edge cases for score calculations."""

    def test_zero_weight_assessments_ignored(
        self, course_factory, assessment_factory, student_user_factory,
        learning_outcome_factory, course_enrollment_factory
    ):
        """Test that assessments with 0 weight don't affect scores."""
        course = course_factory()
        lo = learning_outcome_factory(course=course)
        student = student_user_factory()
        course_enrollment_factory(student=student, course=course)

        # Create assessment with 0 weight
        assessment = assessment_factory(
            course=course,
            weight=0.0
        )

        # Create mapping
        from evaluation.models import AssessmentLearningOutcomeMapping
        AssessmentLearningOutcomeMapping.objects.create(
            assessment=assessment,
            learning_outcome=lo,
            weight=1.0
        )

        # Student gets 100
        from evaluation.models import StudentGrade
        StudentGrade.objects.create(
            student=student,
            assessment=assessment,
            score=100.0
        )

        calculate_course_scores(course.id)

        # Score should be 0 (no weight means no contribution)
        score = StudentLearningOutcomeScore.objects.get(
            student=student,
            learning_outcome=lo
        )
        assert score.score == 0.0

    def test_multiple_assessments_weighted_average(
        self, course_factory, assessment_factory, student_user_factory,
        learning_outcome_factory, course_enrollment_factory
    ):
        """Test calculation with multiple assessments."""
        course = course_factory()
        lo = learning_outcome_factory(course=course)
        student = student_user_factory()
        course_enrollment_factory(student=student, course=course)

        # Create two assessments
        from evaluation.models import AssessmentLearningOutcomeMapping, StudentGrade

        ass1 = assessment_factory(course=course, weight=0.3, total_score=100)
        ass2 = assessment_factory(course=course, weight=0.7, total_score=100)

        AssessmentLearningOutcomeMapping.objects.create(
            assessment=ass1, learning_outcome=lo, weight=1.0
        )
        AssessmentLearningOutcomeMapping.objects.create(
            assessment=ass2, learning_outcome=lo, weight=1.0
        )

        # Scores: 80 and 100
        StudentGrade.objects.create(student=student, assessment=ass1, score=80.0)
        StudentGrade.objects.create(student=student, assessment=ass2, score=100.0)

        calculate_course_scores(course.id)

        score = StudentLearningOutcomeScore.objects.get(
            student=student,
            learning_outcome=lo
        )

        # Weighted average: (80*0.3 + 100*0.7) / (0.3 + 0.7) = 94
        assert score.score == pytest.approx(94.0, rel=1e-2)
