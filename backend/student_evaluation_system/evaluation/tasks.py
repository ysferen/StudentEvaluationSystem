from celery import shared_task
from django.utils import timezone

from core.services.sse import publish_progress
from .models import ScoreRecomputeJob
from .services import calculate_course_scores


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def recompute_course_scores_task(self, course_id: int, job_id: int | None = None) -> dict:
    if job_id:
        ScoreRecomputeJob.objects.filter(id=job_id).update(
            status=ScoreRecomputeJob.STATUS_RUNNING,
            started_at=timezone.now(),
            celery_task_id=self.request.id,
            error="",
        )

    try:
        summary = calculate_course_scores(course_id)
    except Exception as exc:
        if job_id:
            ScoreRecomputeJob.objects.filter(id=job_id).update(
                status=ScoreRecomputeJob.STATUS_FAILED,
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
        ScoreRecomputeJob.objects.filter(id=job_id).update(
            status=ScoreRecomputeJob.STATUS_SUCCESS,
            finished_at=timezone.now(),
        )
        publish_progress(
            f"jobs.{job_id}",
            {
                "type": "complete",
                "job_id": job_id,
                "status": "success",
            },
        )

    return {
        "course_id": course_id,
        "job_id": job_id,
        "summary": summary,
    }
