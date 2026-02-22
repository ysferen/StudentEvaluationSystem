# evaluation/services.py
"""
Score calculation services for the Student Evaluation System.

This module contains business logic for calculating student scores at both
the Learning Outcome (LO) and Program Outcome (PO) levels. Calculations
aggregate assessment grades using weighted mappings.
"""

from django.db import transaction
from django.contrib.auth import get_user_model
from typing import Dict, Any

from .models import Assessment, AssessmentLearningOutcomeMapping, StudentGrade, CourseEnrollment
from core.models import (
    Course,
    LearningOutcome,
    StudentLearningOutcomeScore,
    StudentProgramOutcomeScore,
    LearningOutcomeProgramOutcomeMapping,
    ProgramOutcome,
)

User = get_user_model()


def calculate_course_scores(course_id: int) -> Dict[str, Any]:
    """
    Calculate Learning Outcome scores for all students in a course.

    This function performs the following steps:
    1. Fetches all grades for the course with optimized queries
    2. Calculates LO scores for every student enrolled in the course
    3. Triggers program-level PO score calculation for affected students
    4. Stores scores in the database (replacing old LO values for this course)

    The calculation uses weighted aggregation where:
    - Each assessment has a weight (e.g., Midterm 30%, Final 40%)
    - Each assessment-LO mapping has a weight (contribution to that LO)
    - Final LO score = Σ(assessment_score × assessment_weight × mapping_weight) / Σ(weights)

    Args:
        course_id (int): ID of the course to calculate scores for.

    Returns:
        Dict[str, Any]: Summary containing:
            - students_processed (int): Number of students whose scores were calculated
            - lo_scores_created (int): Number of LO score records created

    Raises:
        Course.DoesNotExist: If the specified course does not exist.

    Optimization Notes:
        - Uses select_related for foreign keys (course, program, term, student)
        - Uses prefetch_related for reverse relationships
        - Caches query results in dictionaries to avoid N+1 queries
        - Uses bulk_create for efficient database writes
    """

    # 1. Setup: Fetch necessary data efficiently with minimal queries
    course = Course.objects.select_related("program", "term").get(id=course_id)

    # Fetch enrollments with student data in one query
    enrollments = CourseEnrollment.objects.filter(course=course).select_related("student")

    # Fetch all learning outcomes for this course
    learning_outcomes = list(LearningOutcome.objects.filter(course=course))

    # Fetch all assessments for this course once (not in loop)
    assessments = list(Assessment.objects.filter(course=course))

    # Get all weights for this course in one go
    # Dict format: {(assessment_id, lo_id): weight}
    matrix_map = {}
    for item in AssessmentLearningOutcomeMapping.objects.filter(assessment__course=course).select_related(
        "assessment", "learning_outcome"
    ):
        matrix_map[(item.assessment_id, item.learning_outcome_id)] = item.weight

    # Get all grades for this course in one query
    # Dict format: {(student_id, assessment_id): score}
    grade_map = {}
    for grade in StudentGrade.objects.filter(assessment__course=course).select_related("assessment"):
        grade_map[(grade.student_id, grade.assessment_id)] = grade.score

    # Prepare list for bulk creation
    lo_score_objects = []
    affected_students = set()

    with transaction.atomic():
        # Step 2: Delete old LO calculations for this course
        StudentLearningOutcomeScore.objects.filter(learning_outcome__course=course).delete()

        # Step 3: Loop through Students and Learning Outcomes
        for enrollment in enrollments:
            student = enrollment.student
            affected_students.add(student.id)

            # --- Calculate LO Scores ---
            for lo in learning_outcomes:
                total_score = 0
                total_weight = 0

                # Use pre-fetched assessments instead of querying in loop
                for assessment in assessments:
                    # Effective weight combines assessment weight and mapping weight
                    mapping_weight = matrix_map.get((assessment.id, lo.id), 0) or 0
                    weight = (assessment.weight or 0) * mapping_weight
                    if weight > 0:
                        score = grade_map.get((student.id, assessment.id), 0) or 0
                        total_score += score * weight
                        total_weight += weight

                # Avoid division by zero
                final_lo_score = (total_score / total_weight) if total_weight > 0 else 0

                # Prepare object
                lo_score_objects.append(
                    StudentLearningOutcomeScore(student=student, learning_outcome=lo, score=final_lo_score)
                )

        # Step 4: Bulk Save LO Scores (single query)
        if lo_score_objects:
            StudentLearningOutcomeScore.objects.bulk_create(lo_score_objects, batch_size=1000)

    # Step 5: Recalculate PO scores for all affected students
    for student_id in affected_students:
        calculate_student_po_scores(student_id, course.program.id, course.term.id)

    # Return a simple summary so callers/tests have a non-None result
    return {
        "students_processed": len(affected_students),
        "lo_scores_created": len(lo_score_objects),
    }


def calculate_student_po_scores(student_id: int, program_id: int, term_id: int) -> None:
    """
    Calculate Program Outcome scores for a student across all courses in their program.

    This aggregates Learning Outcome scores from all courses the student is enrolled
    in for the specified term, weighted by LO-PO mappings.

    The calculation uses weighted aggregation where:
    - Each LO score contributes to POs based on LO-PO mapping weights
    - Final PO score = Σ(lo_score × lo_po_weight) / Σ(lo_po_weights)

    Args:
        student_id (int): ID of the student to calculate scores for.
        program_id (int): ID of the program (defines which POs to calculate).
        term_id (int): ID of the academic term.

    Returns:
        None: Scores are saved directly to the database.

    Raises:
        User.DoesNotExist: If the specified student does not exist.
        ProgramOutcome.DoesNotExist: If no program outcomes exist for the program/term.

    Optimization Notes:
        - Uses select_related for student profile data
        - Pre-fetches all LO scores in a single query
        - Uses dictionary mapping for O(1) LO score lookups
        - Uses bulk_create for efficient database writes
        - Deletes old scores in a single query before creating new ones
    """
    from users.models import CustomUser

    # Fetch student with related data
    student = CustomUser.objects.select_related("student_profile").get(id=student_id)

    # Get all courses in this program for this term that the student is enrolled in
    enrolled_courses = Course.objects.filter(program_id=program_id, term_id=term_id, enrollments__student=student)

    # Get all program outcomes for this program and term
    program_outcomes = list(ProgramOutcome.objects.filter(program_id=program_id, term_id=term_id))

    # Pre-fetch all LO scores for this student in one query
    # Dict format: {learning_outcome_id: score}
    lo_scores_map = {
        score.learning_outcome_id: score.score
        for score in StudentLearningOutcomeScore.objects.filter(
            student=student, learning_outcome__course__in=enrolled_courses
        ).select_related("learning_outcome")
    }

    po_score_objects = []

    with transaction.atomic():
        # Delete old PO scores for this student in this program/term
        StudentProgramOutcomeScore.objects.filter(
            student=student, program_outcome__program_id=program_id, term_id=term_id
        ).delete()

        # For each PO, aggregate across all courses
        for po in program_outcomes:
            total_weighted_score = 0
            total_weight = 0

            # Find all LO->PO mappings for this PO across all enrolled courses
            mappings = LearningOutcomeProgramOutcomeMapping.objects.filter(
                program_outcome=po, course__in=enrolled_courses
            ).select_related("learning_outcome")

            for mapping in mappings:
                # Get the student's LO score from pre-fetched map (no query)
                lo_score = lo_scores_map.get(mapping.learning_outcome_id, 0)
                weight = mapping.weight or 0

                # Weighted contribution to PO
                total_weighted_score += lo_score * weight
                total_weight += weight

            # Calculate final PO score
            final_po_score = (total_weighted_score / total_weight) if total_weight > 0 else 0

            po_score_objects.append(
                StudentProgramOutcomeScore(student=student, program_outcome=po, term_id=term_id, score=final_po_score)
            )

        # Bulk save PO scores (single query)
        if po_score_objects:
            StudentProgramOutcomeScore.objects.bulk_create(po_score_objects, batch_size=1000)
