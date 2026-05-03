"""
Celery tasks for core app.

Tasks run inside the Celery worker process. The worker loads the
SentenceTransformer model once at startup via worker_process_init,
so subsequent invocations are instant (no 8s reload).
"""

import os

from celery import shared_task
from celery.signals import worker_process_init
from django.utils import timezone
from sentence_transformers import SentenceTransformer

from core.services.weight_suggestion import WeightSuggester

# Module-level suggester --- loaded once per worker process
_suggester = None


@worker_process_init.connect
def _init_weight_suggester(**kwargs):
    """Load the embedding model once when the Celery worker starts."""
    global _suggester
    model_name = os.getenv("SENTENCE_TRANSFORMER_MODEL", "all-MiniLM-L6-v2")
    model = SentenceTransformer(model_name)
    _suggester = WeightSuggester(encoder=model)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def suggest_assessment_lo_weights_task(self, course_id: int, job_id: int | None = None) -> dict:
    """
    Suggest assessment-to-LO weight mappings for a course.

    Fetches learning outcomes and assessments from the database,
    then uses a pre-loaded SentenceTransformer model to compute
    similarity-based weight mappings.

    Args:
        course_id: ID of the Course to suggest weights for.
        job_id: Optional WeightSuggestionJob ID for status tracking.

    Returns:
        dict with shape: {"assessment_lo": {assessment_name: {LO_key: weight}}}
    """
    from core.models import Course, WeightSuggestionJob

    # Update job status to running
    if job_id:
        WeightSuggestionJob.objects.filter(id=job_id).update(
            status=WeightSuggestionJob.STATUS_RUNNING,
            started_at=timezone.now(),
            celery_task_id=self.request.id,
            error="",
        )

    try:
        course = Course.objects.get(id=course_id)

        los = list(course.learning_outcomes.values_list("description", flat=True))
        assessments = course.assessments.all()
        assessment_texts = [f"{a.name}: {a.get_assessment_type_display()}" for a in assessments]

        result = _suggester.suggest_assessment_lo(
            course_name=course.name,
            los=los,
            assessments=assessment_texts,
        )

    except Exception as exc:
        if job_id:
            WeightSuggestionJob.objects.filter(id=job_id).update(
                status=WeightSuggestionJob.STATUS_FAILED,
                finished_at=timezone.now(),
                error=str(exc),
            )
        raise

    if job_id:
        WeightSuggestionJob.objects.filter(id=job_id).update(
            status=WeightSuggestionJob.STATUS_SUCCESS,
            finished_at=timezone.now(),
            result=result,
        )

    return result
