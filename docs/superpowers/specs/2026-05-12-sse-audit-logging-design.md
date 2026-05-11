# SSE (Server-Sent Events) + Audit Logging Design

**Date:** 2026-05-12
**Status:** Design

## Overview

Two infrastructure additions that complete the Semester 2 pipeline:

1. **SSE (Server-Sent Events):** Replace 1-second polling with push-based job progress updates. Used by Term Transition, Score Recompute, and Weight Suggestion jobs.
2. **Audit Logging:** Comprehensive audit trail for grade changes, file imports, LO-PO mapping changes, weight suggestion approvals, term transitions, and permission modifications.

---

# Part 1 — SSE (Server-Sent Events)

## Why SSE over WebSocket?

- Django 5.2 supports `StreamingHttpResponse` natively — no new dependencies.
- SSE is one-directional (server → client), which matches our use case (job progress, notifications).
- `EventSource` API in browsers has built-in reconnection.
- No need for `channels` + `daphne` + `CHANNEL_LAYERS` + `ASGI_APPLICATION` rewrite.
- Redis pub/sub is already available (the Celery broker) — acts as the message bus.

## Architecture

```
┌──────────────┐     publish      ┌──────────┐     subscribe      ┌─────────────────┐
│ Celery Task  │ ───────────────▶ │  Redis   │ ◀───────────────── │ Django SSE View │
│              │                  │ Pub/Sub  │                    │ (async)         │
└──────────────┘                  └──────────┘                    └────────┬────────┘
                                                                          │
                                                                  StreamingHttpResponse
                                                                  text/event-stream
                                                                          │
                                                                          ▼
                                                                  ┌──────────────┐
                                                                  │   Browser    │
                                                                  │  EventSource │
                                                                  └──────────────┘
```

## Backend

### SSE Publish Helper

```python
# backend/student_evaluation_system/core/services/sse.py
import json
import redis

def get_redis_client() -> redis.Redis:
    from django.conf import settings
    return redis.Redis.from_url(settings.CELERY_BROKER_URL)

def publish_progress(channel: str, data: dict):
    """Publish a progress event to a Redis pub/sub channel."""
    client = get_redis_client()
    client.publish(channel, json.dumps(data))
```

Channel naming convention: `jobs.{job_id}` for job-specific streams, `notifications.{user_id}` for user notifications.

### SSE Endpoint

```
GET /api/core/events/?channels=jobs.42
GET /api/core/events/?channels=jobs.42,notifications.5
```

```python
# backend/student_evaluation_system/core/views/sse.py
import json
import asyncio
from django.http import StreamingHttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from core.services.sse import get_redis_client

@api_view(["GET"])
@permission_classes([IsAuthenticated])
async def event_stream(request):
    channels = request.query_params.get("channels", "")
    if not channels:
        return Response({"error": "channels query parameter required"}, status=400)

    channel_list = [c.strip() for c in channels.split(",") if c.strip()]

    # Validate: user can only subscribe to their own notification channels
    for ch in channel_list:
        if ch.startswith("notifications."):
            user_id = ch.split(".", 1)[1]
            if str(user_id) != str(request.user.id):
                return Response({"error": "Cannot subscribe to another user's notifications"}, status=403)

    async def event_generator():
        client = get_redis_client()
        pubsub = client.pubsub()
        pubsub.subscribe(*channel_list)

        try:
            while True:
                message = pubsub.get_message(ignore_subscribe_messages=True, timeout=30.0)
                if message and message["type"] == "message":
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    yield f"data: {data}\n\n"
                else:
                    # Heartbeat to keep connection alive
                    yield ": heartbeat\n\n"
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
        finally:
            pubsub.unsubscribe(*channel_list)

    return StreamingHttpResponse(
        event_generator(),
        content_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
```

### Register URL

```python
# In core/urls.py
from core.views.sse import event_stream

urlpatterns = [
    path("events/", event_stream, name="event-stream"),
    # ... other routes
]
```

## Frontend

### SSE Hook

```typescript
// frontend/src/shared/hooks/useJobStream.ts
import { useEffect, useState } from 'react'

interface JobProgress {
  type: 'progress' | 'complete'
  job_id: number
  status: 'running' | 'success' | 'failed'
  current?: number
  total?: number
  created?: number
  courses_created?: number
  error?: string
}

export function useJobStream(jobId: number | null) {
  const [progress, setProgress] = useState<JobProgress | null>(null)
  const [isComplete, setIsComplete] = useState(false)

  useEffect(() => {
    if (!jobId) return

    const baseUrl = import.meta.env.VITE_API_URL || ''
    const url = `${baseUrl}/api/core/events/?channels=jobs.${jobId}`
    const eventSource = new EventSource(url, { withCredentials: true })

    eventSource.onmessage = (event) => {
      try {
        const data: JobProgress = JSON.parse(event.data)
        setProgress(data)
        if (data.type === 'complete') {
          setIsComplete(true)
          eventSource.close()
        }
      } catch {
        // Ignore heartbeat messages (lines starting with ":")
      }
    }

    eventSource.onerror = () => {
      // EventSource auto-reconnects by default
      // On reconnect, fetch current job status to catch up
    }

    return () => {
      eventSource.close()
    }
  }, [jobId])

  return { progress, isComplete }
}
```

### JobProgressBar Component

```tsx
// frontend/src/shared/components/JobProgressBar.tsx
import { useJobStream } from '@/shared/hooks/useJobStream'

interface Props {
  jobId: number | null
  onComplete?: () => void
}

export const JobProgressBar: React.FC<Props> = ({ jobId, onComplete }) => {
  const { progress, isComplete } = useJobStream(jobId)

  useEffect(() => {
    if (isComplete) onComplete?.()
  }, [isComplete, onComplete])

  if (!progress) return null

  if (progress.type === 'complete') {
    return (
      <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
        <p className="text-emerald-800 font-medium">
          Complete: {progress.courses_created ?? progress.created ?? 0} items processed
        </p>
      </div>
    )
  }

  const pct = progress.total ? Math.round((progress.current! / progress.total) * 100) : 0

  return (
    <div className="bg-primary-50 border border-primary-200 rounded-xl p-4">
      <p className="text-sm text-primary-700 mb-2">
        Processing... {progress.current}/{progress.total}
      </p>
      <div className="w-full bg-primary-200 rounded-full h-2">
        <div
          className="bg-primary-600 h-2 rounded-full transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
```

### Replace Polling in RecomputeJobsContext

Current 1-second polling in `RecomputeJobsContext.tsx`:

```typescript
// BEFORE: setInterval(poll, 1000)
const interval = window.setInterval(() => {
  void poll()
}, 1000)

// AFTER: SSE subscription per pending job
useEffect(() => {
  const pendingJobs = jobs.filter(j => j.status === 'pending' || j.status === 'running')
  const eventSources: EventSource[] = []

  pendingJobs.forEach(job => {
    const es = new EventSource(`${baseUrl}/api/core/events/?channels=jobs.${job.id}`, { withCredentials: true })
    es.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'complete') {
        queryClient.invalidateQueries({ queryKey: ['score-recompute-jobs'] })
        es.close()
      }
    }
    eventSources.push(es)
  })

  return () => eventSources.forEach(es => es.close())
}, [jobs, queryClient])
```

---

# Part 2 — Audit Logging

## Data Model

```python
# backend/student_evaluation_system/core/models.py (addition)

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DELETE", "Delete"),
        ("TRANSITION", "Term Transition"),
        ("IMPORT", "File Import"),
        ("APPROVE", "Approval"),
    ]

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="audit_logs")
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, db_index=True)
    model_name = models.CharField(max_length=100)  # e.g., "StudentGrade", "Term"
    object_id = models.PositiveIntegerField(null=True, blank=True)
    before_snapshot = models.JSONField(null=True, blank=True)
    after_snapshot = models.JSONField(null=True, blank=True)
    metadata = models.JSONField(default=dict)  # Extra context: file name, row count, etc.
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["model_name", "object_id"]),
            models.Index(fields=["user", "-timestamp"]),
            models.Index(fields=["action", "-timestamp"]),
        ]
```

## Tracking Mechanism

### Approach: Django Signals + Explicit Calls

Use `post_save` / `post_delete` signals for model-level tracking, and explicit `audit()` calls in view actions for complex operations (imports, transitions, approvals).

### Request Context Middleware

```python
# backend/student_evaluation_system/core/middleware.py (addition)

from core.services.audit import set_audit_request

def audit_context_middleware(get_response):
    def middleware(request):
        request.audit_context = {
            "ip_address": request.META.get("REMOTE_ADDR"),
            "user_agent": request.META.get("HTTP_USER_AGENT", ""),
        }
        set_audit_request(request)
        return get_response(request)
    return middleware
```

Register in `settings.py`:
```python
MIDDLEWARE = [
    # ... existing middleware ...
    "core.middleware.audit_context_middleware",
]
```

### Audit Service

```python
# backend/student_evaluation_system/core/services/audit.py

import threading
from core.models import AuditLog

_audit_request_store = threading.local()

def set_audit_request(request):
    """Store the current request for audit context (called by middleware)."""
    _audit_request_store.request = request

def get_audit_request():
    return getattr(_audit_request_store, 'request', None)

def log_audit(user, action, model_name, object_id=None, before=None, after=None, metadata=None):
    request = get_audit_request()
    ip = request.audit_context["ip_address"] if request else None
    ua = request.audit_context["user_agent"] if request else ""

    AuditLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=object_id,
        before_snapshot=before,
        after_snapshot=after,
        metadata=metadata or {},
        ip_address=ip,
        user_agent=ua,
    )

def set_grade_user(grade_instance, user):
    """Attach user to grade instance for signal-based audit capture."""
    grade_instance._audit_user = user
```

### Tracked Actions

| Action | Trigger | model_name | before_snapshot | after_snapshot | metadata |
|--------|---------|------------|-----------------|----------------|----------|
| Grade change | `post_save` on `StudentGrade` | `StudentGrade` | Old score dict (on update) | New score dict | `{assessment_id, student_id}` |
| Grade deletion | `post_delete` on `StudentGrade` | `StudentGrade` | Full grade dict | `null` | — |
| File import | View action after import | `StudentGrade` | `null` | `{rows_imported: N, errors: M}` | `{file_name, total_rows}` |
| LO-PO mapping change | View action after bulk save | `LOPOMapping` | Old mappings list | New mappings list | `{course_id}` |
| Assessment-LO mapping change | View action after bulk save | `AssessmentLOMapping` | Old mappings list | New mappings list | `{assessment_id, course_id}` |
| Weight suggestion approval | View action on acceptance | `AssessmentLOMapping` | Old weights | Approved weights | `{course_id, job_id}` |
| Term transition | View action on next-term | `Term` | `{old_term_id, old_term_name}` | `{new_term_id, new_term_name}` | `{template_ids, courses_created}` |
| Permission change | `post_save` on `User` (role field) | `User` | Old role | New role | — |
| Course enrollment | `post_save` on `CourseEnrollment` | `CourseEnrollment` | — | Enrollment dict | — |

### Signal Handlers

```python
# backend/student_evaluation_system/core/signals.py (new file)

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from evaluation.models import StudentGrade
from users.models import CustomUser
from core.services.audit import log_audit

@receiver(post_save, sender=StudentGrade)
def audit_grade_save(sender, instance, created, **kwargs):
    user = getattr(instance, '_audit_user', None)  # Set by view/import service
    if not user:
        return

    after = {
        "score": instance.score,
        "total_score": instance.assessment.total_score,
        "assessment_id": instance.assessment_id,
        "student_id": instance.student_id,
    }

    if created:
        log_audit(user, "CREATE", "StudentGrade", instance.id, before=None, after=after)
    else:
        # post_save doesn't have the old value — handle UPDATE in view layer
        pass


@receiver(post_delete, sender=StudentGrade)
def audit_grade_delete(sender, instance, **kwargs):
    user = getattr(instance, '_audit_user', None)
    if not user:
        return

    before = {
        "score": instance.score,
        "total_score": instance.assessment.total_score,
        "assessment_id": instance.assessment_id,
        "student_id": instance.student_id,
    }
    log_audit(user, "DELETE", "StudentGrade", instance.id, before=before, after=None)

# Auto-connect signals in core/apps.py ready() method
```

### Signal Registration in AppConfig

```python
# backend/student_evaluation_system/core/apps.py
from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        import core.signals  # noqa: F401 — connect audit signal handlers
```

### View-Layer Audit for Updates

For UPDATE actions where `post_save` cannot capture the "before" state, audit explicitly in the view:

```python
# In view handling grade update:
old_grade = StudentGrade.objects.get(id=grade_id)
old_snapshot = {"score": old_grade.score}
# ... save new grade ...
log_audit(request.user, "UPDATE", "StudentGrade", grade_id,
          before=old_snapshot,
          after={"score": new_score})
```

### View-Layer Audit for Complex Actions

```python
# In TermViewSet.next_term:
log_audit(
    request.user,
    "TRANSITION",
    "Term",
    new_term.id,
    before={"id": old_term.id, "name": str(old_term)},
    after={"id": new_term.id, "name": str(new_term)},
    metadata={"template_ids": template_ids, "courses_created": result["courses_created"]},
)

# In file import view:
log_audit(
    request.user,
    "IMPORT",
    "StudentGrade",
    object_id=None,
    before=None,
    after=None,
    metadata={
        "file_name": file.name,
        "total_rows": summary["total_rows"],
        "imported": summary["imported"],
        "errors": summary["errors"],
    },
)
```

---

## Performance Considerations

- Audit writes are fire-and-forget via `AuditLog.objects.create()` — no impact on primary operation latency.
- JSON fields store snapshots; large snapshots (bulk mapping changes) use summarized lists, not full dumps.
- `db_index` on `timestamp`, `action`, `model_name+object_id`, and `user+timestamp` for efficient querying.
- No audit on reads — only on mutating operations.
- Retention: audit logs are never automatically deleted. A future cleanup job can archive logs older than X years.

---

## API Endpoints (Read-Only, Admin Only)

| Route | Purpose |
|-------|---------|
| `GET /api/core/audit-logs/?model_name=StudentGrade&object_id=123` | Filter audit trail |
| `GET /api/core/audit-logs/?user=5&action=IMPORT` | User activity feed |
| `GET /api/core/audit-logs/?action=TRANSITION` | All term transitions |
| `GET /api/core/audit-logs/?from=2026-01-01&to=2026-06-01` | Date range |

### AuditLogViewSet

Standard read-only `ModelViewSet` with `DjangoFilterBackend` for filtering. Admin-only access.

---

## Verification Checklist

### SSE
- [ ] `GET /api/core/events/?channels=jobs.1` returns `text/event-stream` with 200
- [ ] Heartbeat messages sent every 30s to keep connection alive
- [ ] Publishing to Redis channel `jobs.42` streams to connected SSE client
- [ ] Client disconnection cleans up Redis subscription
- [ ] Multiple clients can subscribe to same channel
- [ ] User cannot subscribe to another user's `notifications.*` channel
- [ ] `useJobStream` hook receives `EventSource` messages correctly
- [ ] `JobProgressBar` renders progress percentage and completion state
- [ ] `RecomputeJobsContext` replaces polling with SSE (no more `setInterval`)
- [ ] SSE auto-reconnects after connection loss

### Audit Logging
- [ ] `pytest backend/tests/test_audit.py` — new test file
- [ ] Grade save creates audit record with correct before/after
- [ ] Grade delete creates audit record
- [ ] File import creates audit record with metadata
- [ ] Term transition creates audit record
- [ ] Weight suggestion approval creates audit record
- [ ] Bulk mapping save creates audit record
- [ ] `GET /api/core/audit-logs/` returns filtered results
- [ ] Admin-only access to audit endpoints
- [ ] `ip_address` and `user_agent` populated from request context
