"""
Weight Suggestion ViewSet.

Exposes async weight suggestion endpoints that queue Celery tasks
and return job tracking records.
"""

from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import WeightSuggestionJob
from ..serializers import WeightSuggestionJobSerializer
from ..tasks.weight_suggestions import suggest_assessment_lo_weights_task


class WeightSuggestionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for triggering and tracking weight suggestion jobs.

    POST /weight-suggestion/ -- queue a suggestion for a course
    GET  /weight-suggestion/{id}/ -- get job status and result
    Supports both assessment-to-LO and LO-to-PO weight suggestions.
    """

    queryset = WeightSuggestionJob.objects.all()
    serializer_class = WeightSuggestionJobSerializer

    def get_permissions(self):
        """Only authenticated instructors and admins can create."""
        if self.action == "create":
            from ..permissions import IsInstructorOrAdmin

            return [IsAuthenticated(), IsInstructorOrAdmin()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        """Queue a weight suggestion Celery task for the given course.

        Returns job tracking record. Result will contain both assessment_lo
        and lo_po weight mappings when the job completes successfully.
        """
        course_id = request.data.get("course_id")
        if not course_id:
            return Response(
                {"error": "course_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        job = WeightSuggestionJob.objects.create(
            course_id=course_id,
            triggered_by=request.user,
            status=WeightSuggestionJob.STATUS_PENDING,
        )

        task = suggest_assessment_lo_weights_task.apply_async(
            kwargs={"course_id": course_id, "job_id": job.id}, queue="ml_queue"
        )
        job.celery_task_id = task.id
        job.save(update_fields=["celery_task_id"])

        serializer = self.get_serializer(job)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        """List weight suggestion jobs."""
        queryset = self.get_queryset().order_by("-created_at")
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """Get a single job's status and result."""
        return super().retrieve(request, *args, **kwargs)
