# Next Term Feature Design

**Date:** 2026-05-12
**Status:** Design

## Overview

Add a "Next Term" button allowing admins and program heads to transition the academic term: suspend the current term, create a new term, and instantiate courses from selected templates. The transition runs asynchronously via Celery with SSE-based progress streaming.

---

## Domain Rules

- **Academic year starts with Fall and ends with Spring.** Auto-calculation: Fall 2025 → Spring 2026 → Fall 2026 → Spring 2027.
- **Summer is a manual option.** Not part of auto-cycle, but user can select it.
- **Course data is preserved as-is.** Term inactivation (`is_active=False`) is sufficient — no new status fields on Course, Assessment, or Enrollment models.
- **Related objects stay unchanged.** Only the term's `is_active` toggles; all courses, grades, and scores remain affiliated with their historical term.

---

## User Flow

```
1. Admin/Program Head navigates to HeadCourses or HeadDashboard
2. "Next Term" button is visible (only when a term is active)
3. Click → Modal opens
4. Modal shows:
   - Current active term name
   - New term: auto-calculated semester + year (editable)
   - Semester dropdown: Fall, Spring, Summer
   - Academic year field (numeric, editable)
   - Checkbox list of available course templates (program-scoped)
   - "Select All" / "Deselect All" toggles
   - Cancel / Start New Term buttons
5. On confirm → POST request dispatched
6. Progress bar appears via SSE stream
7. On completion: toast notification, page refreshes
```

---

## Frontend

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `NextTermButton` | `features/head/components/` | Button visible when active term exists |
| `NextTermModal` | `features/head/components/` | Modal with form + template selection |
| `JobProgressBar` | `shared/components/` | Reusable progress bar powered by SSE hook |

### NextTermModal Fields

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `semester` | select (fall/spring/summer) | Auto-calculated from current term | Summer requires manual selection |
| `academic_year` | number | Current year (or year+1 if spring→fall) | Editable |
| `template_ids` | checkbox list | None pre-selected | Scoped to user's program. Sorted by code. |

### API Calls

| Call | Usage |
|------|-------|
| `useCoreTermsActiveRetrieve()` | Check if a term is already active; get current term data |
| `useCoreCourseTemplatesList({ program: programId })` | Fetch templates for modal checkbox list |
| `coreTermsNextTermCreate(body)` | POST to trigger transition |
| `useJobStream(jobId)` | SSE subscription for progress (from Spec C) |

### State: NextTermButton visibility

```typescript
const { data: activeTerm } = useCoreTermsActiveRetrieve()
// Button shown when activeTerm exists
```

---

## Backend

### API Endpoint

```
POST /api/core/terms/next-term/
```

**Request body:**

```json
{
  "semester": "spring",
  "academic_year": 2026,
  "template_ids": [1, 2, 5]
}
```

**Validation:**

- Reject if another term is currently active and user isn't transitioning from it
- `semester` must be one of: `fall`, `spring`, `summer`
- `academic_year` must be positive integer
- `template_ids` must be valid IDs belonging to the user's program(s) (program heads) or any program (admins)
- Require authenticated user with admin or program head role

**Response: 202 Accepted**

```json
{
  "job_id": 42,
  "old_term_id": 3,
  "new_term_id": 4,
  "new_term_name": "Spring 2026",
  "template_count": 3,
  "message": "Term transition started. Courses are being created from templates."
}
```

### View Implementation

New `@action` on `TermViewSet`:

```python
class TermViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny, IsAdminOrProgramHeadOrReadOnly]

    @action(detail=False, methods=["post"], url_path="next-term")
    def next_term(self, request):
        serializer = NextTermSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        old_term = Term.objects.get(is_active=True)
        new_term = serializer.save(old_term=old_term, created_by=request.user)

        job = TermTransitionJob.objects.create(
            old_term=old_term,
            new_term=new_term,
            triggered_by=request.user,
            template_ids=serializer.validated_data["template_ids"],
            status="pending",
        )

        task = clone_templates_for_term_task.delay(
            template_ids=serializer.validated_data["template_ids"],
            term_id=new_term.id,
            job_id=job.id,
        )
        job.celery_task_id = task.id
        job.save()

        return Response(
            {
                "job_id": job.id,
                "old_term_id": old_term.id,
                "new_term_id": new_term.id,
                "new_term_name": str(new_term),
                "template_count": len(serializer.validated_data["template_ids"]),
                "message": "Term transition started. Courses are being created from templates.",
            },
            status=status.HTTP_202_ACCEPTED,
        )
```

### NextTermSerializer

```python
class NextTermSerializer(serializers.Serializer):
    semester = serializers.ChoiceField(choices=["fall", "spring", "summer"])
    academic_year = serializers.IntegerField(min_value=2000, max_value=2100)
    template_ids = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=True, min_length=0
    )

    def validate_template_ids(self, value):
        user = self.context["request"].user
        if user.is_admin_user:
            templates = CourseTemplate.objects.filter(id__in=value)
        else:
            profile = user.program_head_profile
            templates = CourseTemplate.objects.filter(
                id__in=value, program_id=profile.program_id
            )
        if len(templates) != len(set(value)):
            raise ValidationError("One or more template IDs are invalid or not accessible.")
        return value

    def create(self, validated_data):
        from django.db import transaction

        old_term = validated_data.pop("old_term")
        created_by = validated_data.pop("created_by")

        with transaction.atomic():
            # Suspend current term
            old_term.is_active = False
            old_term.save()

            # Create new term
            new_term = Term.objects.create(
                semester=validated_data["semester"],
                academic_year=validated_data["academic_year"],
                name=f"{validated_data['semester'].capitalize()} {validated_data['academic_year']}",
                is_active=True,
            )

        return new_term
```

### Model: TermTransitionJob

```python
class TermTransitionJob(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    old_term = models.ForeignKey(Term, on_delete=models.PROTECT, related_name="transitions_from")
    new_term = models.ForeignKey(Term, on_delete=models.PROTECT, related_name="transitions_to")
    triggered_by = models.ForeignKey(User, on_delete=models.PROTECT)
    template_ids = models.JSONField(default=list)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True)
    courses_created = models.PositiveIntegerField(default=0)
    celery_task_id = models.CharField(max_length=255, blank=True, null=True)
    error = models.TextField(blank=True, null=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
```

### Celery Task

```python
@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 2})
def clone_templates_for_term_task(self, template_ids: list[int], term_id: int, job_id: int):
    from core.services.course_template import clone_course_from_template
    from core.models import CourseTemplate, Term
    from core.services.sse import publish_progress
    import redis

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
            # Log but continue — don't fail all for one bad template
            job.error = f"Template {template.id} ({template.code}): {e}"
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

    job.status = "success"
    job.courses_created = created
    job.finished_at = timezone.now()
    job.save()

    publish_progress(
        f"jobs.{job_id}",
        {
            "type": "complete",
            "job_id": job_id,
            "status": "success",
            "courses_created": created,
            "total_templates": total,
        },
    )

    return {"courses_created": created}
```

---

## Permissions

| Action | Who can do it |
|--------|---------------|
| See "Next Term" button | Admin or Program Head with an active term |
| Open Next Term modal | Admin or Program Head |
| Select templates | Admins see all templates; program heads see only their program's templates |
| Submit transition | Admin or Program Head |
| View job progress/result | The user who triggered it, or any admin |

---

## API Schema Changes

| Route | Method | Purpose |
|-------|--------|---------|
| `/api/core/terms/next-term/` | POST | Trigger term transition |
| `/api/core/term-transition-jobs/` | GET | List transition jobs (admin/program head scoped) |
| `/api/core/term-transition-jobs/{id}/` | GET | Retrieve job status |
| `/api/core/events/?channels=jobs.{job_id}` | GET | SSE stream for job progress (from Spec C) |

New OpenAPI schema regeneration required after implementation.

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| No active term | "Next Term" button hidden; endpoint returns 400 |
| Template clone fails on one course | Logged in job error field; task continues with remaining templates |
| Celery worker down | `task.delay()` falls back with try/except; job marked as failed |
| User loses connection during SSE | SSE auto-reconnects via `EventSource`; on reconnection, polls job status once to catch up |
| Duplicate submission | `Term.save()` ensures only one active term. Second submission fails validation (no active term to transition from) |
| User not authorized | 403 response; template list filtered to user's program |

---

## Verification Checklist

- [ ] `pytest backend/tests/test_term_transition.py` — new test file
- [ ] Test: transition with 0 templates (empty `template_ids` list) succeeds
- [ ] Test: transition with valid templates creates correct number of courses
- [ ] Test: transition marks old term inactive, new term active
- [ ] Test: program head can only select own program's templates
- [ ] Test: admin can select any templates
- [ ] Test: Celery task publishes progress to Redis pub/sub
- [ ] Test: SSE endpoint streams correct events
- [ ] Frontend: modal renders with correct template list
- [ ] Frontend: progress bar updates during transition
- [ ] Frontend: toast notification on completion
- [ ] Frontend: page refresh after success shows new active term
