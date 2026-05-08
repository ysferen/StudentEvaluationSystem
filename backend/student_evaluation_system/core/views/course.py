"""
Course and Outcome ViewSets.

Contains ViewSets for managing:
- Courses
- ProgramOutcomes
- LearningOutcomes
- LearningOutcomeProgramOutcomeMappings
"""

from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from ..models import (
    Course,
    Program,
    ProgramOutcome,
    LearningOutcome,
    LearningOutcomeProgramOutcomeMapping,
    Term,
)
from ..serializers import (
    CourseSerializer,
    ProgramOutcomeSerializer,
    CoreLearningOutcomeSerializer,
    LearningOutcomeProgramOutcomeMappingSerializer,
    BulkLOPOMappingSerializer,
)
from ..permissions import InstructorPermissionMixin


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                name="department",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter courses by department ID",
            ),
            OpenApiParameter(
                name="term", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, description="Filter courses by term ID"
            ),
            OpenApiParameter(
                name="instructor",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter courses by instructor ID",
            ),
            OpenApiParameter(
                name="program",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter courses by program ID",
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

    queryset = Course.objects.select_related("program", "term").prefetch_related("instructors").all()
    serializer_class = CourseSerializer
    permission_classes = [AllowAny, InstructorPermissionMixin]
    resource_area = "courses"

    def get_permissions(self):
        """
        Keep backward compatibility for non-versioned endpoints while
        requiring authentication on versioned v1 course read endpoints.
        """
        if self.request.path.startswith("/api/v1/") and self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated()]
        return [permission() for permission in self.permission_classes]

    def _apply_role_filters(self, queryset, user):
        """Scope courses by user role. Instructors see only their courses, etc."""
        if not getattr(user, "is_authenticated", False):
            return queryset
        if getattr(user, "is_admin_user", False):
            return queryset
        if getattr(user, "is_instructor", False):
            return queryset.filter(instructors=user)
        if getattr(user, "is_student", False):
            from evaluation.models import CourseEnrollment

            enrolled_course_ids = CourseEnrollment.objects.filter(student=user).values_list("course_id", flat=True)
            return queryset.filter(id__in=enrolled_course_ids)
        if hasattr(user, "program_head_profile"):
            programs = Program.objects.filter(pk=user.program_head_profile.program_id)
            return queryset.filter(program__in=programs)
        return queryset.none()

    def get_queryset(self):
        """
        Filter courses based on user role:
        - Instructors: only courses they teach (auto-scoped to active term)
        - Admins: all courses
        """
        user = self.request.user
        queryset = super().get_queryset()
        queryset = self._apply_role_filters(queryset, user)

        # Apply query params
        department_id = self.request.query_params.get("department", None)
        term_id = self.request.query_params.get("term", None)
        instructor_id = self.request.query_params.get("instructor", None)
        program_id = self.request.query_params.get("program", None)

        if department_id:
            queryset = queryset.filter(program__department_id=department_id)
        if term_id:
            queryset = queryset.filter(term_id=term_id)
        if instructor_id:
            queryset = queryset.filter(instructors__id=instructor_id)
        if program_id:
            queryset = queryset.filter(program_id=program_id)

        # Auto-scope instructors and program heads to the active term unless
        # they explicitly filter by a specific term (so the dashboard shows
        # current courses by default, but the courses page can look at history).
        # We only apply this default scope on list views, not retrieve/detail views,
        # so that users can still view older courses via direct links (like CourseDetail).
        if (
            self.action == "list"
            and getattr(user, "is_authenticated", False)
            and (getattr(user, "is_instructor", False) or hasattr(user, "program_head_profile"))
            and not term_id
        ):
            active_term = Term.objects.filter(is_active=True).first()
            if active_term:
                queryset = queryset.filter(term=active_term)

        return queryset.distinct()

    @action(detail=True, methods=["get"])
    def learning_outcomes(self, request, pk=None):
        """Get all learning outcomes for this course."""
        course = self.get_object()
        outcomes = course.learning_outcomes.all()
        serializer = CoreLearningOutcomeSerializer(outcomes, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        tags=["Outcomes"],
        parameters=[
            OpenApiParameter(
                name="department",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter program outcomes by department ID",
            ),
            OpenApiParameter(
                name="term",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter program outcomes by term ID",
            ),
        ],
    ),
    retrieve=extend_schema(tags=["Outcomes"]),
    create=extend_schema(tags=["Outcomes"]),
    update=extend_schema(tags=["Outcomes"]),
    partial_update=extend_schema(tags=["Outcomes"]),
    destroy=extend_schema(tags=["Outcomes"]),
)
class ProgramOutcomeViewSet(viewsets.ModelViewSet):
    """CRUD operations for program outcomes."""

    queryset = ProgramOutcome.objects.select_related("program", "term", "created_by").all()
    serializer_class = ProgramOutcomeSerializer
    permission_classes = [AllowAny, InstructorPermissionMixin]
    resource_area = "program_outcomes"

    def get_queryset(self):
        queryset = super().get_queryset()
        program_id = self.request.query_params.get("program", None)
        term_id = self.request.query_params.get("term", None)

        if program_id:
            queryset = queryset.filter(program_id=program_id)
        if term_id:
            queryset = queryset.filter(term_id=term_id)

        return queryset


@extend_schema_view(
    list=extend_schema(
        tags=["Outcomes"],
        parameters=[
            OpenApiParameter(
                name="course", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, description="Filter by course ID"
            ),
        ],
    ),
    retrieve=extend_schema(tags=["Outcomes"]),
    create=extend_schema(tags=["Outcomes"]),
    update=extend_schema(tags=["Outcomes"]),
    partial_update=extend_schema(tags=["Outcomes"]),
    destroy=extend_schema(tags=["Outcomes"]),
)
class LearningOutcomeViewSet(viewsets.ModelViewSet):
    """CRUD operations for learning outcomes."""

    queryset = LearningOutcome.objects.select_related("course", "created_by").all()
    serializer_class = CoreLearningOutcomeSerializer
    permission_classes = [AllowAny, InstructorPermissionMixin]
    resource_area = "learning_outcomes"

    def get_queryset(self):
        queryset = super().get_queryset()
        course_id = self.request.query_params.get("course", None)

        if course_id:
            queryset = queryset.filter(course_id=course_id)

        return queryset


class LearningOutcomeProgramOutcomeMappingViewSet(viewsets.ModelViewSet):
    """CRUD operations for LO-PO mappings."""

    queryset = LearningOutcomeProgramOutcomeMapping.objects.select_related(
        "learning_outcome", "program_outcome", "course"
    ).all()
    serializer_class = LearningOutcomeProgramOutcomeMappingSerializer
    permission_classes = [AllowAny, InstructorPermissionMixin]
    resource_area = "lo_po_weights"

    @extend_schema(request=BulkLOPOMappingSerializer)
    @action(detail=False, methods=["post"])
    def bulk_sync(self, request):
        """Apply LO-PO mapping changes in bulk and trigger async PO score recompute."""
        from django.shortcuts import get_object_or_404

        serializer = BulkLOPOMappingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        created = []
        updated = []
        deleted_ids = []
        affected_course_ids = set()

        with transaction.atomic():
            # Deletes
            for mapping_id in data.get("deletes", []):
                mapping = get_object_or_404(LearningOutcomeProgramOutcomeMapping, pk=mapping_id)
                affected_course_ids.add(mapping.course_id)
                mapping.delete()
                deleted_ids.append(mapping_id)

            # Updates
            for item in data.get("updates", []):
                mapping = get_object_or_404(LearningOutcomeProgramOutcomeMapping, pk=item["id"])
                if "weight" in item:
                    mapping.weight = item["weight"]
                    mapping.save(update_fields=["weight"])
                    affected_course_ids.add(mapping.course_id)
                updated.append(LearningOutcomeProgramOutcomeMappingSerializer(mapping).data)

            # Creates
            for item in data.get("creates", []):
                learning_outcome = get_object_or_404(LearningOutcome, pk=item["learning_outcome_id"])
                program_outcome = get_object_or_404(ProgramOutcome, pk=item["program_outcome_id"])
                course = get_object_or_404(Course, pk=data["course_id"])
                mapping = LearningOutcomeProgramOutcomeMapping.objects.create(
                    learning_outcome=learning_outcome,
                    program_outcome=program_outcome,
                    course=course,
                    weight=item["weight"],
                )
                affected_course_ids.add(course.id)
                result = LearningOutcomeProgramOutcomeMappingSerializer(mapping).data
                result["temp_id"] = item.get("temp_id")
                created.append(result)

        # Dispatch async score recompute (non-blocking) or fall back to sync
        job_ids = []
        from evaluation.models import ScoreRecomputeJob

        for course_id in affected_course_ids:
            job = ScoreRecomputeJob.objects.create(
                task_type=ScoreRecomputeJob.TASK_TYPE_COURSE_RECOMPUTE,
                status=ScoreRecomputeJob.STATUS_PENDING,
                course_id=course_id,
                triggered_by=request.user,
            )
            try:
                from evaluation.tasks import recompute_course_scores_task

                async_result = recompute_course_scores_task.delay(course_id, job.pk)
                job.celery_task_id = async_result.id
                job.save(update_fields=["celery_task_id"])
            except Exception:
                # Celery unavailable — fall back to synchronous calculation
                from evaluation.services import calculate_course_scores

                calculate_course_scores(course_id)
                job.status = ScoreRecomputeJob.STATUS_SUCCESS
                job.finished_at = timezone.now()
                job.save(update_fields=["status", "finished_at"])
            job_ids.append(job.pk)

        return Response(
            {
                "created": created,
                "updated": updated,
                "deleted": deleted_ids,
                "recompute_job_ids": job_ids,
            }
        )
