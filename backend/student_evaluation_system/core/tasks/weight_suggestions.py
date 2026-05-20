"""
Celery tasks for core app.

Tasks run inside the Celery worker process. The worker loads the
SentenceTransformer model once at startup via worker_process_init,
so subsequent invocations are instant (no 8s reload).
"""

import logging
import os
import time
import threading

from celery import shared_task
from celery.signals import worker_ready
from django.utils import timezone
from core.services.sse import publish_progress

# Ensure submodule tasks are auto-discovered by Celery
from core.tasks.term_transition import clone_templates_for_term_task  # noqa: F401

logger = logging.getLogger(__name__)

# Module-level suggester --- loaded once per worker process
_suggester = None
_suggester_lock = threading.Lock()


def get_weight_suggester():
    """Lazy loader for the ML model."""
    global _suggester
    if _suggester is None:
        with _suggester_lock:
            if _suggester is None:
                logger.info("Loading SentenceTransformer model into memory...")
                from sentence_transformers import SentenceTransformer
                from core.services.weight_suggestion import WeightSuggester

                model_name = os.getenv("SENTENCE_TRANSFORMER_MODEL", "all-MiniLM-L6-v2")
                model = SentenceTransformer(model_name)
                _suggester = WeightSuggester(encoder=model)
    return _suggester


@worker_ready.connect
def bootstrap_model(sender, **kwargs):
    """
    Signal triggered when the Celery worker is ready to accept tasks.
    This ensures the model is loaded into RAM *before* the first task arrives.
    """
    # Check if we are in the ML worker by looking at the queue or an env var
    # This prevents the default worker from accidentally loading the model
    if os.getenv("IS_ML_WORKER") == "true":
        get_weight_suggester()


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def suggest_assessment_lo_weights_task(
    self,
    course_id: int,
    job_id: int | None = None,
    include_raw_embeddings: bool = False,
) -> dict:
    """
    Suggest assessment-to-LO weight mappings for a course.

    Fetches learning outcomes and assessments from the database,
    then uses a pre-loaded SentenceTransformer model to compute
    similarity-based weight mappings.

    Args:
        course_id: ID of the Course to suggest weights for.
        job_id: Optional WeightSuggestionJob ID for status tracking.
        include_raw_embeddings: Include embedding vectors, cosine
            similarities, and normalization values in the returned result.

    Returns:
        dict with shape: {"assessment_lo": {assessment_name: {LO_key: weight}}}
    """
    from core.models import Course, ProgramOutcome, WeightSuggestionJob

    logger.info(f"TASK STARTED AT: {time.time()}")
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
        assessment_names = [a.name for a in assessments]
        assessment_texts = [
            f"{a.name}: {a.description}" if a.description else f"{a.name}: {a.get_assessment_type_display()}"
            for a in assessments
        ]
        _suggester = get_weight_suggester()
        if _suggester is None:
            raise RuntimeError("Weight suggester not initialized — model failed to load")

        result = _suggester.suggest_assessment_lo(
            course_name=course.name,
            los=los,
            assessments=assessment_texts,
            assessment_keys=assessment_names,
            include_raw_embeddings=include_raw_embeddings,
        )

        pos = list(ProgramOutcome.objects.filter(term=course.term).values_list("description", flat=True))
        if pos:
            lo_po_result = _suggester.suggest_lo_po(
                course_name=course.name,
                los=los,
                pos=pos,
                include_raw_embeddings=include_raw_embeddings,
            )
            result["lo_po"] = lo_po_result["lo_po"]
            if include_raw_embeddings:
                result.setdefault("debug", {})["lo_po"] = lo_po_result.get("debug", {}).get("lo_po", {})

    except Exception as exc:
        if job_id:
            WeightSuggestionJob.objects.filter(id=job_id).update(
                status=WeightSuggestionJob.STATUS_FAILED,
                finished_at=timezone.now(),
                error=str(exc),
            )
            publish_progress(
                f"jobs.{job_id}",
                {
                    "type": "complete",
                    "job_id": job_id,
                    "status": "failed",
                    "error": str(exc),
                },
            )
        raise

    if job_id:
        WeightSuggestionJob.objects.filter(id=job_id).update(
            status=WeightSuggestionJob.STATUS_SUCCESS,
            finished_at=timezone.now(),
            result=result,
        )
        publish_progress(
            f"jobs.{job_id}",
            {
                "type": "complete",
                "job_id": job_id,
                "status": "success",
            },
        )

    logger.info(f"TASK SENT AT: {time.time()}")
    return result
