from rest_framework import generics, viewsets, status
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django.db.models import Avg, Count, F, Sum, FloatField
from django.db import transaction
from django.utils import timezone

from .models import Assessment, AssessmentLearningOutcomeMapping, StudentGrade, CourseEnrollment, ScoreRecomputeJob
from .serializers import (
    AssessmentSerializer,
    AssessmentCreateSerializer,
    AssessmentLearningOutcomeMappingSerializer,
    BulkAssessmentLOMappingSerializer,
    BulkAssessmentDescriptionUpdateSerializer,
    StudentGradeSerializer,
    StudentGradeCreateSerializer,
    CourseEnrollmentSerializer,
    ScoreRecomputeJobSerializer,
)
from .services import calculate_course_scores, calculate_student_po_scores
from core.models import LearningOutcome, StudentLearningOutcomeScore
from core.permissions import (
    IsInstructorOfCourse,
    IsOwnerOrInstructorOrAdmin,
    IsEnrolledStudentOrInstructorOrAdmin,
    InstructorPermissionMixin,
)

import logging

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                name="course",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter assessments by course ID",
            ),
            OpenApiParameter(
                name="type",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter assessments by type (midterm, final, homework, project, quiz, attendance, other)",
            ),
        ]
    )
)
class AssessmentViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for assessments.

    Permissions:
    - Read: Instructors and Admins
    - Write: Instructors (own courses) and Admins
    """

    queryset = Assessment.objects.select_related("course", "created_by").all()
    permission_classes = [IsAuthenticated, IsInstructorOfCourse, InstructorPermissionMixin]
    resource_area = "assessments"

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return AssessmentCreateSerializer
        return AssessmentSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        course_id = self.request.query_params.get("course", None)
        assessment_type = self.request.query_params.get("type", None)

        if course_id:
            queryset = queryset.filter(course_id=course_id)
        if assessment_type:
            queryset = queryset.filter(assessment_type=assessment_type)

        return queryset

    def perform_update(self, serializer):
        """After updating an assessment, recalculate if weight changed."""
        old_weight = self.get_object().weight
        assessment = serializer.save()

        # Only recalculate if weight changed (expensive operation)
        if old_weight != assessment.weight:
            calculate_course_scores(assessment.course_id)

    def perform_destroy(self, instance):
        """After deleting an assessment, recalculate scores."""
        course_id = instance.course_id
        instance.delete()
        calculate_course_scores(course_id)

    @action(detail=True, methods=["get"])
    def grades(self, request, pk=None):
        """Get all grades for this assessment."""
        assessment = self.get_object()
        grades = assessment.student_grades.select_related("student")
        serializer = StudentGradeSerializer(grades, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def statistics(self, request, pk=None):
        """Get statistics for this assessment."""
        assessment = self.get_object()
        grades = assessment.student_grades.all()

        if not grades.exists():
            return Response({"detail": "No grades yet."})

        stats = grades.aggregate(average=Avg("score"), count=Count("id"))

        return Response(
            {
                "assessment": assessment.name,
                "total_students": stats["count"],
                "average_score": stats["average"],
                "max_score": assessment.total_score,
            }
        )

    @extend_schema(
        request=BulkAssessmentDescriptionUpdateSerializer,
        responses={200: {"type": "object", "properties": {"updated_count": {"type": "integer"}}}},
        description="Bulk update assessment descriptions. Used to set descriptions before AI weight suggestion.",
    )
    @action(detail=False, methods=["post"])
    def bulk_descriptions(self, request):
        """Bulk update assessment descriptions in a single transaction."""
        serializer = BulkAssessmentDescriptionUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        updated_count = 0
        with transaction.atomic():
            for item in data["assessments"]:
                Assessment.objects.filter(id=item["id"]).update(description=item["description"])
                updated_count += 1

        return Response({"updated_count": updated_count})


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                name="assessment",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter mappings by assessment ID",
            ),
        ]
    )
)
class AssessmentLearningOutcomeMappingViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for assessment-LO mappings.

    Permissions:
    - Read: Instructors and Admins
    - Write: Instructors (own courses) and Admins
    """

    queryset = AssessmentLearningOutcomeMapping.objects.select_related(
        "assessment", "assessment__course", "learning_outcome"
    ).all()
    serializer_class = AssessmentLearningOutcomeMappingSerializer
    permission_classes = [IsAuthenticated, IsInstructorOfCourse]

    def get_queryset(self):
        queryset = super().get_queryset()
        assessment_id = self.request.query_params.get("assessment", None)
        course_id = self.request.query_params.get("course", None)

        if assessment_id:
            queryset = queryset.filter(assessment_id=assessment_id)
        if course_id:
            queryset = queryset.filter(assessment__course_id=course_id)

        return queryset

    def perform_create(self, serializer):
        """After creating LO mapping, recalculate scores."""
        mapping = serializer.save()
        calculate_course_scores(mapping.assessment.course_id)

    def perform_update(self, serializer):
        """After updating LO mapping, recalculate scores."""
        old_weight = self.get_object().weight
        mapping = serializer.save()

        # Only recalculate if weight changed
        if old_weight != mapping.weight:
            calculate_course_scores(mapping.assessment.course_id)

    def perform_destroy(self, instance):
        """After deleting LO mapping, recalculate scores."""
        course_id = instance.assessment.course_id
        instance.delete()
        calculate_course_scores(course_id)

    @extend_schema(request=BulkAssessmentLOMappingSerializer)
    @action(detail=False, methods=["post"])
    def bulk_sync(self, request):
        """Apply assessment-LO mapping changes in bulk and trigger async score recompute."""
        serializer = BulkAssessmentLOMappingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        created = []
        updated = []
        deleted_ids = []
        affected_course_ids = set()

        with transaction.atomic():
            # Deletes
            for mapping_id in data.get("deletes", []):
                mapping = get_object_or_404(AssessmentLearningOutcomeMapping, pk=mapping_id)
                course_id = mapping.assessment.course_id
                affected_course_ids.add(course_id)
                mapping.delete()
                deleted_ids.append(mapping_id)

            # Updates
            for item in data.get("updates", []):
                mapping = get_object_or_404(AssessmentLearningOutcomeMapping, pk=item["id"])
                if "weight" in item:
                    mapping.weight = item["weight"]
                    mapping.save(update_fields=["weight"])
                    affected_course_ids.add(mapping.assessment.course_id)
                updated.append(AssessmentLearningOutcomeMappingSerializer(mapping).data)

            # Creates
            for item in data.get("creates", []):
                assessment = get_object_or_404(Assessment, pk=item["assessment_id"])
                learning_outcome = get_object_or_404(LearningOutcome, pk=item["learning_outcome_id"])
                mapping = AssessmentLearningOutcomeMapping.objects.create(
                    assessment=assessment,
                    learning_outcome=learning_outcome,
                    weight=item["weight"],
                )
                affected_course_ids.add(assessment.course_id)
                result = AssessmentLearningOutcomeMappingSerializer(mapping).data
                result["temp_id"] = item.get("temp_id")
                created.append(result)

        # Dispatch async score recompute (non-blocking) or fall back to sync
        job_ids = []
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


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                name="student",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter grades by student ID",
            ),
            OpenApiParameter(
                name="assessment",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter grades by assessment ID",
            ),
            OpenApiParameter(
                name="course", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, description="Filter grades by course ID"
            ),
        ]
    ),
    course_averages=extend_schema(
        parameters=[
            OpenApiParameter(
                name="student",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Get weighted averages for specific student across all their courses",
            ),
            OpenApiParameter(
                name="course",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Get weighted average for specific course (class average or per-student)",
            ),
            OpenApiParameter(
                name="per_student",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="When used with course parameter, returns individual student averages for grade distribution",
            ),
        ],
        description="Calculate weighted course averages. Either student or course parameter is required.",
    ),
)
class StudentGradeViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for student grades.

    Permissions:
    - Read: Students (own grades), Instructors (their students), Admins (all)
    - Write: Instructors (their courses) and Admins
    """

    queryset = StudentGrade.objects.select_related("student", "assessment", "assessment__course").all()
    permission_classes = [IsAuthenticated, IsOwnerOrInstructorOrAdmin]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return StudentGradeCreateSerializer
        return StudentGradeSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        student_id = self.request.query_params.get("student", None)
        assessment_id = self.request.query_params.get("assessment", None)
        course_id = self.request.query_params.get("course", None)

        if student_id:
            queryset = queryset.filter(student_id=student_id)
        if assessment_id:
            queryset = queryset.filter(assessment_id=assessment_id)
        if course_id:
            queryset = queryset.filter(assessment__course_id=course_id)

        return queryset

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        course_id = request.query_params.get("course")
        if course_id:
            assessments = Assessment.objects.filter(course_id=course_id).values(
                "id", "name", "assessment_type", "total_score", "weight", "date", "description"
            )
            response.data["assignments"] = list(assessments)
        return response

    def perform_create(self, serializer):
        """After creating a grade, recalculate scores."""
        grade = serializer.save()
        calculate_course_scores(grade.assessment.course_id)

    def perform_update(self, serializer):
        """After updating a grade, recalculate scores."""
        grade = serializer.save()
        calculate_course_scores(grade.assessment.course_id)

    def perform_destroy(self, instance):
        """After deleting a grade, recalculate scores."""
        course_id = instance.assessment.course_id
        instance.delete()
        calculate_course_scores(course_id)

    @action(detail=False, methods=["get"])
    def course_averages(self, request):
        """
        Calculate weighted course averages based on assessment grades and weights.
        This is used for lecturer analytics and charts.

        Query Parameters:
        - student: Student ID (optional) - for specific student
        - course: Course ID (optional) - for specific course
        - per_student: Boolean (optional) - if true with course, returns per-student averages

        Returns:
        - If student specified: List of courses with weighted average for that student
        - If course specified without student: Aggregated average for the course
        - If course + per_student=true: List of all students with their weighted averages (for distribution)

        Example: /api/evaluation/grades/course_averages/?student=1
        Example: /api/evaluation/grades/course_averages/?course=5
        Example: /api/evaluation/grades/course_averages/?course=5&per_student=true (for grade distribution)
        """
        student_id = request.query_params.get("student")
        course_id = request.query_params.get("course")
        per_student = request.query_params.get("per_student", "false").lower() == "true"

        if not student_id and not course_id:
            return Response(
                {"error": "Either student or course query parameter is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Special case: per-student averages for grade distribution
        if course_id and per_student and not student_id:
            return self._calculate_per_student_averages(course_id)

        # Determine which courses to calculate averages for
        if course_id and not student_id:
            # Direct course query - return class average for this course
            course_ids = [int(course_id)]
        elif student_id:
            # Get all courses this student is enrolled in
            enrollments_query = CourseEnrollment.objects.filter(student_id=student_id)
            if course_id:
                enrollments_query = enrollments_query.filter(course_id=course_id)
            course_ids = list(enrollments_query.values_list("course_id", flat=True).distinct())
        else:
            course_ids = []

        # Calculate weighted average for each course
        course_averages = []

        for cid in course_ids:
            # Base query for grades in this course
            grades_query = StudentGrade.objects.filter(assessment__course_id=cid)

            # Filter by student if provided
            if student_id:
                grades_query = grades_query.filter(student_id=student_id)

            # Get all grades with assessment details and calculate percentage
            grades = grades_query.select_related("assessment").annotate(
                # Calculate percentage for each grade
                percentage=F("score") * 100.0 / F("assessment__total_score"),
                # Get the weight from assessment
                weight=F("assessment__weight"),
            )

            if grades.exists():
                # Calculate weighted sum and total weight using aggregation
                aggregated = grades.aggregate(
                    weighted_sum=Sum(F("percentage") * F("weight"), output_field=FloatField()), total_weight=Sum("weight")
                )

                weighted_sum = aggregated["weighted_sum"] or 0
                total_weight = aggregated["total_weight"] or 0

                # Calculate final weighted average
                if total_weight > 0:
                    weighted_average = weighted_sum / total_weight
                else:
                    weighted_average = None
            else:
                weighted_average = None

            course_averages.append(
                {"course_id": cid, "weighted_average": round(weighted_average, 2) if weighted_average is not None else None}
            )

        return Response(course_averages)

    def _calculate_per_student_averages(self, course_id):
        """
        Calculate weighted average for each student in a course.
        Used for grade distribution analytics.

        Returns: List of students with their weighted averages
        """
        # Get all students enrolled in this course
        enrollments = CourseEnrollment.objects.filter(course_id=course_id).select_related("student")

        student_averages = []

        for enrollment in enrollments:
            student_id = enrollment.student_id

            # Get all grades for this student in this course
            grades = (
                StudentGrade.objects.filter(student_id=student_id, assessment__course_id=course_id)
                .select_related("assessment")
                .annotate(percentage=F("score") * 100.0 / F("assessment__total_score"), weight=F("assessment__weight"))
            )

            if grades.exists():
                # Calculate weighted average for this student
                aggregated = grades.aggregate(
                    weighted_sum=Sum(F("percentage") * F("weight"), output_field=FloatField()), total_weight=Sum("weight")
                )

                weighted_sum = aggregated["weighted_sum"] or 0
                total_weight = aggregated["total_weight"] or 0

                if total_weight > 0:
                    weighted_average = weighted_sum / total_weight
                else:
                    weighted_average = None
            else:
                weighted_average = None

            student_averages.append(
                {
                    "student_id": student_id,
                    "weighted_average": round(weighted_average, 2) if weighted_average is not None else None,
                }
            )

        return Response(student_averages)


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                name="student",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter enrollments by student ID",
            ),
            OpenApiParameter(
                name="course",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter enrollments by course ID",
            ),
        ]
    )
)
class CourseEnrollmentViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for course enrollments.

    Permissions:
    - Read: Instructors and Admins
    - Write: Instructors (own courses) and Admins
    """

    queryset = CourseEnrollment.objects.select_related("student", "course").all()
    serializer_class = CourseEnrollmentSerializer
    permission_classes = [
        IsAuthenticated,
        IsEnrolledStudentOrInstructorOrAdmin,
    ]

    def get_queryset(self):
        queryset = super().get_queryset()
        student_id = self.request.query_params.get("student", None)
        course_id = self.request.query_params.get("course", None)

        if student_id:
            queryset = queryset.filter(student_id=student_id)
        if course_id:
            queryset = queryset.filter(course_id=course_id)

        return queryset

    def perform_create(self, serializer):
        """After enrolling a student, calculate their scores."""
        enrollment = serializer.save()
        calculate_course_scores(enrollment.course_id)

    def perform_destroy(self, instance):
        """After unenrolling, remove student's scores for this course."""
        course_id = instance.course_id
        student_id = instance.student_id
        program_id = instance.course.program_id
        term_id = instance.course.term_id

        with transaction.atomic():
            # Delete LO scores for this student in this course
            StudentLearningOutcomeScore.objects.filter(student_id=student_id, learning_outcome__course_id=course_id).delete()

            # Delete the enrollment
            instance.delete()

            # Recalculate PO scores (since removing course affects program-level scores)
            calculate_student_po_scores(student_id, program_id, term_id)

    @action(detail=False, methods=["post"])
    def bulk_enroll(self, request):
        """Enroll multiple students in a course."""
        course_id = request.data.get("course_id")
        student_ids = request.data.get("student_ids", [])

        if not course_id or not student_ids:
            return Response({"detail": "course_id and student_ids are required."}, status=status.HTTP_400_BAD_REQUEST)

        enrollments = []
        newly_enrolled = False

        with transaction.atomic():
            for student_id in student_ids:
                enrollment, created = CourseEnrollment.objects.get_or_create(student_id=student_id, course_id=course_id)
                if created:
                    enrollments.append(enrollment)
                    newly_enrolled = True

            # Recalculate scores for all newly enrolled students
            if newly_enrolled:
                calculate_course_scores(course_id)

        serializer = self.get_serializer(enrollments, many=True)
        return Response({"enrolled_count": len(enrollments), "enrollments": serializer.data})


# Legacy views for backward compatibility
class EvaluationListView(generics.ListAPIView):
    """List all student grades (evaluations)."""

    queryset = StudentGrade.objects.select_related("student", "assessment", "assessment__course").all()
    serializer_class = StudentGradeSerializer


class EvaluationDetailView(generics.RetrieveAPIView):
    """Retrieve a single student grade by PK."""

    queryset = StudentGrade.objects.select_related("student", "assessment", "assessment__course").all()
    serializer_class = StudentGradeSerializer


class EvaluationCreateView(generics.CreateAPIView):
    """Create a student grade (evaluation)."""

    queryset = StudentGrade.objects.all()
    serializer_class = StudentGradeCreateSerializer


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                name="course",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter jobs by course ID",
            ),
            OpenApiParameter(
                name="status",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter jobs by status (pending, running, success, failed)",
            ),
        ]
    )
)
class ScoreRecomputeJobViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only endpoint for score recompute job status tracking."""

    queryset = ScoreRecomputeJob.objects.select_related("course", "triggered_by").all()
    serializer_class = ScoreRecomputeJobSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        course_id = self.request.query_params.get("course")
        status_value = self.request.query_params.get("status")

        if course_id:
            queryset = queryset.filter(course_id=course_id)
        if status_value:
            queryset = queryset.filter(status=status_value)

        return queryset
