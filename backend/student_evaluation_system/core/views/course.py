"""
Course and Outcome ViewSets.

Contains ViewSets for managing:
- Courses
- ProgramOutcomes
- LearningOutcomes
- LearningOutcomeProgramOutcomeMappings
"""

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from ..models import (
    Course,
    ProgramOutcome,
    LearningOutcome,
    LearningOutcomeProgramOutcomeMapping,
)
from ..serializers import (
    CourseSerializer,
    ProgramOutcomeSerializer,
    CoreLearningOutcomeSerializer,
    LearningOutcomeProgramOutcomeMappingSerializer,
)
from ..permissions import IsInstructorOrAdmin


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                name='department',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter courses by department ID'
            ),
            OpenApiParameter(
                name='term',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter courses by term ID'
            ),
            OpenApiParameter(
                name='instructor',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter courses by instructor ID'
            ),
        ]
    )
)
class CourseViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for courses.

    Permissions:
    - Read: Instructors and Admins
    - Write: Instructors (own courses) and Admins
    """
    queryset = Course.objects.select_related('program', 'term').prefetch_related('instructors').all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated, IsInstructorOrAdmin]

    def get_queryset(self):
        """
        Filter courses based on user role:
        - Instructors: only courses they teach
        - Admins: all courses
        """
        user = self.request.user
        queryset = super().get_queryset()

        # Instructors only see their own courses
        if user.is_instructor and not user.is_admin_user:
            queryset = queryset.filter(instructors=user)

        # Apply query filters
        department_id = self.request.query_params.get('department', None)
        term_id = self.request.query_params.get('term', None)
        instructor_id = self.request.query_params.get('instructor', None)

        if department_id:
            queryset = queryset.filter(department_id=department_id)
        if term_id:
            queryset = queryset.filter(term_id=term_id)
        if instructor_id:
            queryset = queryset.filter(instructors__id=instructor_id)

        return queryset

    @action(detail=True, methods=['get'])
    def learning_outcomes(self, request, pk=None):
        """Get all learning outcomes for this course."""
        course = self.get_object()
        outcomes = course.learning_outcomes.all()
        serializer = CoreLearningOutcomeSerializer(outcomes, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        tags=['Outcomes'],
        parameters=[
            OpenApiParameter(
                name='department',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter program outcomes by department ID'
            ),
            OpenApiParameter(
                name='term',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter program outcomes by term ID'
            ),
        ]
    ),
    retrieve=extend_schema(tags=['Outcomes']),
    create=extend_schema(tags=['Outcomes']),
    update=extend_schema(tags=['Outcomes']),
    partial_update=extend_schema(tags=['Outcomes']),
    destroy=extend_schema(tags=['Outcomes']),
)
class ProgramOutcomeViewSet(viewsets.ModelViewSet):
    """CRUD operations for program outcomes."""
    queryset = ProgramOutcome.objects.select_related('program', 'term', 'created_by').all()
    serializer_class = ProgramOutcomeSerializer
    permission_classes = [IsAuthenticated, IsInstructorOrAdmin]

    def get_queryset(self):
        queryset = super().get_queryset()
        program_id = self.request.query_params.get('program', None)
        term_id = self.request.query_params.get('term', None)

        if program_id:
            queryset = queryset.filter(program_id=program_id)
        if term_id:
            queryset = queryset.filter(term_id=term_id)

        return queryset


@extend_schema_view(
    list=extend_schema(tags=['Outcomes']),
    retrieve=extend_schema(tags=['Outcomes']),
    create=extend_schema(tags=['Outcomes']),
    update=extend_schema(tags=['Outcomes']),
    partial_update=extend_schema(tags=['Outcomes']),
    destroy=extend_schema(tags=['Outcomes']),
)
class LearningOutcomeViewSet(viewsets.ModelViewSet):
    """CRUD operations for learning outcomes."""
    queryset = LearningOutcome.objects.select_related('course', 'created_by').all()
    serializer_class = CoreLearningOutcomeSerializer
    permission_classes = [IsAuthenticated, IsInstructorOrAdmin]

    def get_queryset(self):
        queryset = super().get_queryset()
        course_id = self.request.query_params.get('course', None)

        if course_id:
            queryset = queryset.filter(course_id=course_id)

        return queryset


class LearningOutcomeProgramOutcomeMappingViewSet(viewsets.ModelViewSet):
    """CRUD operations for LO-PO mappings."""
    queryset = LearningOutcomeProgramOutcomeMapping.objects.select_related(
        'learning_outcome', 'program_outcome', 'course'
    ).all()
    serializer_class = LearningOutcomeProgramOutcomeMappingSerializer
    permission_classes = [IsAuthenticated, IsInstructorOrAdmin]
