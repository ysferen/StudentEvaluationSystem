"""
Course Template ViewSets.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from core.models import (
    Term,
    CourseTemplate,
    CourseTemplateAssessmentLOMapping,
    CourseTemplateLOPOMapping,
)
from core.serializers import (
    CourseSerializer,
    CourseTemplateSerializer,
    CourseTemplateLearningOutcomeSerializer,
    CourseTemplateAssessmentSerializer,
    CourseTemplateAssessmentLOMappingSerializer,
    CourseTemplateLOPOMappingSerializer,
)
from core.permissions import InstructorPermissionMixin
from core.services.course_template import clone_course_from_template


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                name="program",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter templates by program ID",
            ),
        ]
    ),
)
class CourseTemplateViewSet(viewsets.ModelViewSet):
    """CRUD operations for course templates, plus instantiate action."""

    queryset = CourseTemplate.objects.select_related("program").prefetch_related("learning_outcomes", "assessments").all()
    serializer_class = CourseTemplateSerializer
    permission_classes = [AllowAny, InstructorPermissionMixin]
    resource_area = "course_templates"

    def get_queryset(self):
        queryset = super().get_queryset()
        program_id = self.request.query_params.get("program")
        if program_id:
            queryset = queryset.filter(program_id=program_id)
        return queryset

    @extend_schema(
        description="Create a new Course by cloning all template data into the given term.",
        request={"type": "object", "properties": {"term_id": {"type": "integer"}}, "required": ["term_id"]},
        responses={201: CourseSerializer},
    )
    @action(detail=True, methods=["post"])
    def instantiate(self, request, pk=None):
        """
        POST /api/core/course-templates/{id}/instantiate/
        Body: {"term_id": 1}

        Creates a new Course by cloning all template data into the given term.
        """
        template = self.get_object()

        term_id = request.data.get("term_id")
        if not term_id:
            return Response({"error": "term_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            term = Term.objects.get(pk=term_id)
        except Term.DoesNotExist:
            return Response(
                {"error": f"Term with id {term_id} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            course = clone_course_from_template(template, term, user=request.user)
        except Exception as exc:
            return Response(
                {"error": f"Failed to instantiate course: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        serializer = CourseSerializer(course)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"], url_path="learning-outcomes")
    def template_learning_outcomes(self, request, pk=None):
        """
        GET/POST learning outcomes for this template.
        """
        template = self.get_object()

        if request.method == "GET":
            outcomes = template.learning_outcomes.all()
            serializer = CourseTemplateLearningOutcomeSerializer(outcomes, many=True)
            return Response(serializer.data)

        # POST
        serializer = CourseTemplateLearningOutcomeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(course_template=template)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"], url_path="assessments")
    def template_assessments(self, request, pk=None):
        """
        GET/POST assessments for this template.
        """
        template = self.get_object()

        if request.method == "GET":
            assessments = template.assessments.all()
            serializer = CourseTemplateAssessmentSerializer(assessments, many=True)
            return Response(serializer.data)

        # POST
        serializer = CourseTemplateAssessmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(course_template=template)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CourseTemplateAssessmentLOMappingViewSet(viewsets.ModelViewSet):
    """CRUD for template assessment-to-LO mappings."""

    queryset = CourseTemplateAssessmentLOMapping.objects.all()
    serializer_class = CourseTemplateAssessmentLOMappingSerializer
    permission_classes = [AllowAny, InstructorPermissionMixin]
    resource_area = "course_templates"

    def get_queryset(self):
        queryset = super().get_queryset()
        template_assessment_id = self.request.query_params.get("template_assessment")
        template_lo_id = self.request.query_params.get("template_learning_outcome")

        if template_assessment_id:
            queryset = queryset.filter(template_assessment_id=template_assessment_id)
        if template_lo_id:
            queryset = queryset.filter(template_learning_outcome_id=template_lo_id)

        return queryset


class CourseTemplateLOPOMappingViewSet(viewsets.ModelViewSet):
    """CRUD for template LO-to-PO mappings."""

    queryset = CourseTemplateLOPOMapping.objects.all()
    serializer_class = CourseTemplateLOPOMappingSerializer
    permission_classes = [AllowAny, InstructorPermissionMixin]
    resource_area = "course_templates"

    def get_queryset(self):
        queryset = super().get_queryset()
        template_lo_id = self.request.query_params.get("template_learning_outcome")

        if template_lo_id:
            queryset = queryset.filter(template_learning_outcome_id=template_lo_id)

        return queryset
