from celery import shared_task
from django.utils import timezone
from core.models import Term, CourseTemplate, TermTransitionJob, Program
from core.services.sse import publish_progress
from core.services.course_template import clone_course_from_template, clone_program_outcomes_for_term


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

    # Clone program outcomes from old term to new term for each program used by templates
    old_term = job.old_term
    program_ids = set(t.program_id for t in templates if t.program_id)
    po_map: dict[int, int] = {}
    for pid in program_ids:
        program = Program.objects.get(id=pid)
        program_po_map = clone_program_outcomes_for_term(old_term, term, program, user=job.triggered_by)
        po_map.update(program_po_map)

    for i, template in enumerate(templates, start=1):
        try:
            clone_course_from_template(template, term, po_map=po_map)
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
