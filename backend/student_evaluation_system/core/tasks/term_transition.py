from celery import shared_task
from django.utils import timezone
from core.models import Term, CourseTemplate, TermTransitionJob
from core.services.sse import publish_progress
from core.services.course_template import clone_course_from_template


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def clone_templates_for_term_task(self, template_ids: list[int], term_id: int, job_id: int):
    """Clone selected course templates for a given term. Publishes progress via SSE."""
    job = TermTransitionJob.objects.get(id=job_id)
    job.status = "running"
    job.started_at = timezone.now()
    job.save()

    term = Term.objects.get(id=term_id)
    templates = CourseTemplate.objects.filter(id__in=template_ids).select_related("program")
    total = len(templates)
    created = 0

    for i, template in enumerate(templates, start=1):
        try:
            clone_course_from_template(template, term)
            created += 1
        except Exception as e:
            # Log error but continue — one bad template shouldn't fail all
            accumulated = job.error or ""
            job.error = accumulated + f"Template {template.id} ({template.code}): {e}\n"
            job.save(update_fields=["error"])

        publish_progress(
            f"jobs.{job_id}",
            {
                "type": "progress",
                "job_id": job_id,
                "status": "running",
                "current": i,
                "total": total,
                "created": created,
            },
        )

    job.status = "success" if created == total else "failed"
    job.courses_created = created
    job.finished_at = timezone.now()
    job.save()

    publish_progress(
        f"jobs.{job_id}",
        {
            "type": "complete",
            "job_id": job_id,
            "status": job.status,
            "courses_created": created,
            "total_templates": total,
        },
    )

    return {"courses_created": created}
