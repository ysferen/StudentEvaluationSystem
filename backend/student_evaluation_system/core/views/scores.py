"""
Student Score ViewSets.

Contains ViewSets for viewing student scores:
- StudentLearningOutcomeScore (read-only)
- StudentProgramOutcomeScore (read-only)
"""

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from ..models import (
    StudentLearningOutcomeScore,
    StudentProgramOutcomeScore,
)
from ..serializers import (
    StudentLearningOutcomeScoreSerializer,
    StudentProgramOutcomeScoreSerializer,
)
from ..permissions import IsOwnerOrInstructorOrAdmin


class StudentLearningOutcomeScoreViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for student learning outcome scores.

    Permissions:
    - Students: View own scores only
    - Instructors: View scores for students in their courses
    - Admins: View all scores
    """
    queryset = StudentLearningOutcomeScore.objects.select_related(
        'student', 'learning_outcome', 'course'
    ).all()
    serializer_class = StudentLearningOutcomeScoreSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrInstructorOrAdmin]

    def get_queryset(self):
        """
        Filter scores based on user role:
        - Students: only their own scores
        - Instructors: scores for students in their courses
        - Admins: all scores
        """
        user = self.request.user
        queryset = super().get_queryset()

        if user.is_student:
            # Students only see their own scores
            queryset = queryset.filter(student=user)
        elif user.is_instructor and not user.is_admin_user:
            # Instructors see scores for their courses
            queryset = queryset.filter(course__instructors=user)

        # Apply filters
        course_id = self.request.query_params.get('course', None)
        student_id = self.request.query_params.get('student', None)

        if course_id:
            queryset = queryset.filter(course_id=course_id)
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        return queryset


class StudentProgramOutcomeScoreViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for student program outcome scores.

    Permissions:
    - Students: View own scores only
    - Instructors: View scores for students in their courses
    - Admins: View all scores
    """
    queryset = StudentProgramOutcomeScore.objects.select_related(
        'student', 'program_outcome', 'program'
    ).all()
    serializer_class = StudentProgramOutcomeScoreSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrInstructorOrAdmin]

    def get_queryset(self):
        """
        Filter scores based on user role:
        - Students: only their own scores
        - Instructors: scores for students in their courses
        - Admins: all scores
        """
        user = self.request.user
        queryset = super().get_queryset()

        if user.is_student:
            queryset = queryset.filter(student=user)
        elif user.is_instructor and not user.is_admin_user:
            queryset = queryset.filter(program__courses__instructors=user)

        # Apply filters
        program_id = self.request.query_params.get('program', None)
        student_id = self.request.query_params.get('student', None)

        if program_id:
            queryset = queryset.filter(program_id=program_id)
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        return queryset
