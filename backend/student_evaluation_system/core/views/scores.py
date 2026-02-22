"""
Student Score ViewSets.

Contains ViewSets for viewing student scores:
- StudentLearningOutcomeScore (read-only)
- StudentProgramOutcomeScore (read-only)
"""

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db.models import Avg

from ..models import (
    StudentLearningOutcomeScore,
    StudentProgramOutcomeScore,
)
from ..serializers import (
    StudentLearningOutcomeScoreSerializer,
    StudentProgramOutcomeScoreSerializer,
)


class StudentLearningOutcomeScoreViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for student learning outcome scores.

    Permissions:
    - Students: View own scores only
    - Instructors: View scores for students in their courses
    - Admins: View all scores
    """

    queryset = StudentLearningOutcomeScore.objects.select_related(
        "student", "learning_outcome", "learning_outcome__course"
    ).all()
    serializer_class = StudentLearningOutcomeScoreSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """
        Filter scores based on user role:
        - Students: only their own scores
        - Instructors: scores for students in their courses
        - Admins: all scores
        """
        user = self.request.user
        queryset = super().get_queryset()

        if hasattr(user, "is_student") and user.is_student:
            queryset = queryset.filter(student=user)
        elif hasattr(user, "is_instructor") and user.is_instructor and not getattr(user, "is_admin_user", False):
            queryset = queryset.filter(learning_outcome__course__instructors=user)

        # Apply filters
        course_id = self.request.query_params.get("course", None)
        student_id = self.request.query_params.get("student", None)

        if course_id:
            queryset = queryset.filter(learning_outcome__course_id=course_id)
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        return queryset

    @action(detail=False, methods=["get"], url_path="course_averages")
    def course_averages(self, request):
        """Return average LO scores grouped by course."""
        course_id = request.query_params.get("course")
        student_id = request.query_params.get("student")

        if not course_id and not student_id:
            return Response({"error": "course or student parameter is required"}, status=400)

        qs = self.get_queryset()
        if course_id:
            qs = qs.filter(learning_outcome__course_id=course_id)
        if student_id:
            qs = qs.filter(student_id=student_id)

        data = (
            qs.values("learning_outcome__course_id")
            .annotate(weighted_average=Avg("score"))
            .values("learning_outcome__course_id", "weighted_average")
        )

        results = [
            {
                "course_id": item["learning_outcome__course_id"],
                "weighted_average": item["weighted_average"],
            }
            for item in data
        ]

        return Response(results)

    @action(detail=False, methods=["get"], url_path="lo_averages")
    def lo_averages(self, request):
        """Return average LO scores grouped by learning outcome."""
        course_id = request.query_params.get("course")
        student_id = request.query_params.get("student")

        if not course_id and not student_id:
            return Response({"error": "course or student parameter is required"}, status=400)

        qs = self.get_queryset()
        if course_id:
            qs = qs.filter(learning_outcome__course_id=course_id)
        if student_id:
            qs = qs.filter(student_id=student_id)

        data = (
            qs.values("learning_outcome_id", "learning_outcome__code", "learning_outcome__description")
            .annotate(avg_score=Avg("score"))
            .values("learning_outcome__code", "learning_outcome__description", "avg_score")
        )

        results = [
            {
                "lo_code": item["learning_outcome__code"],
                "lo_description": item["learning_outcome__description"],
                "avg_score": item["avg_score"],
            }
            for item in data
        ]

        return Response(results)


class StudentProgramOutcomeScoreViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for student program outcome scores.

    Permissions:
    - Students: View own scores only
    - Instructors: View scores for students in their courses
    - Admins: View all scores
    """

    queryset = StudentProgramOutcomeScore.objects.select_related(
        "student", "program_outcome", "program_outcome__program", "term"
    ).all()
    serializer_class = StudentProgramOutcomeScoreSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """
        Filter scores based on user role:
        - Students: only their own scores
        - Instructors: scores for students in their courses
        - Admins: all scores
        """
        user = self.request.user
        queryset = super().get_queryset()

        if hasattr(user, "is_student") and user.is_student:
            queryset = queryset.filter(student=user)
        elif hasattr(user, "is_instructor") and user.is_instructor and not getattr(user, "is_admin_user", False):
            queryset = queryset.filter(program_outcome__program__courses__instructors=user)

        # Apply filters
        program_id = self.request.query_params.get("program", None)
        student_id = self.request.query_params.get("student", None)

        if program_id:
            queryset = queryset.filter(program_outcome__program_id=program_id)
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        return queryset
