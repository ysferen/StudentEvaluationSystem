# SSE + Audit Logging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Server-Sent Events infrastructure for push-based job progress and a comprehensive audit logging system tracking all mutating operations.

**Architecture:** SSE uses Django 5.2's StreamingHttpResponse with Redis pub/sub (already configured) — no new dependencies. Audit logging uses Django signals for model changes and explicit calls in views for complex operations, stored in a new AuditLog model with JSON snapshots.

**Tech Stack:** Django 5.2, Redis pub/sub, EventSource API, threading.local for request context

---

## File Structure

| Action | File | Purpose |
|--------|------|---------|
| CREATE | `backend/student_evaluation_system/core/services/sse.py` | Redis pub/sub publish helper |
| CREATE | `backend/student_evaluation_system/core/views/sse.py` | Async SSE endpoint |
| CREATE | `backend/student_evaluation_system/core/services/audit.py` | Audit logging service + request context |
| CREATE | `backend/student_evaluation_system/core/middleware.py` | Audit context middleware (or extend existing) |
| CREATE | `backend/student_evaluation_system/core/signals.py` | Audit signal handlers |
| MODIFY | `backend/student_evaluation_system/core/models.py` | Add AuditLog model |
| MODIFY | `backend/student_evaluation_system/core/apps.py` | Register signals in ready() |
| MODIFY | `backend/student_evaluation_system/core/urls.py` | Register SSE route |
| MODIFY | `backend/student_evaluation_system/student_evaluation_system/settings.py` | Register middleware |
| MODIFY | `backend/student_evaluation_system/core/admin.py` | Register AuditLog admin |
| CREATE | `backend/student_evaluation_system/tests/test_sse.py` | SSE endpoint tests |
| CREATE | `backend/student_evaluation_system/tests/test_audit.py` | Audit logging tests |
| CREATE | `frontend/src/shared/hooks/useJobStream.ts` | SSE hook |
| CREATE | `frontend/src/shared/components/JobProgressBar.tsx` | Progress bar component |
| MODIFY | `frontend/src/shared/contexts/RecomputeJobsContext.tsx` | Replace polling with SSE |
| CREATE | `frontend/src/shared/hooks/__tests__/useJobStream.test.ts` | SSE hook tests |
| CREATE | `frontend/src/shared/components/__tests__/JobProgressBar.test.tsx` | Progress bar tests |

---

### Task 1: AuditLog Model + Migration

**Files:**
- Modify: `backend/student_evaluation_system/core/models.py` — append AuditLog model
- Create: migration file (auto-generated)

- [ ] **Step 1: Add AuditLog model to core/models.py**

```python
# Append to end of backend/student_evaluation_system/core/models.py

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DELETE", "Delete"),
        ("TRANSITION", "Term Transition"),
        ("IMPORT", "File Import"),
        ("APPROVE", "Approval"),
    ]

    user = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.PROTECT,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, db_index=True)
    model_name = models.CharField(max_length=100)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    before_snapshot = models.JSONField(null=True, blank=True)
    after_snapshot = models.JSONField(null=True, blank=True)
    metadata = models.JSONField(default=dict)
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
        verbose_name = "Audit Log Entry"
        verbose_name_plural = "Audit Log Entries"

    def __str__(self):
        return f"{self.action} {self.model_name}#{self.object_id} by {self.user} at {self.timestamp}"
```

- [ ] **Step 2: Generate migration and verify**

Run: `cd backend/student_evaluation_system && uv run python manage.py makemigrations core`
Expected: Creates migration file `core/migrations/XXXX_auditlog.py`

Run: `cd backend/student_evaluation_system && uv run python manage.py migrate`
Expected: "Applying core.XXXX_auditlog... OK"

- [ ] **Step 3: Add AuditLog to Django admin**

```python
# Create: backend/student_evaluation_system/core/admin.py (if not exists, else append)

from django.contrib import admin
from core.models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["timestamp", "user", "action", "model_name", "object_id"]
    list_filter = ["action", "model_name", "timestamp"]
    search_fields = ["user__username", "model_name", "metadata"]
    readonly_fields = [
        "user", "action", "model_name", "object_id",
        "before_snapshot", "after_snapshot", "metadata",
        "ip_address", "user_agent", "timestamp",
    ]
    ordering = ["-timestamp"]

    def has_add_permission(self, request):
        return False  # Audit logs are created by the system, not manually

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
```

- [ ] **Step 4: Write model test**

```python
# Create: backend/student_evaluation_system/tests/test_audit.py

import pytest
from core.models import AuditLog

@pytest.mark.django_db
class TestAuditLogModel:

    def test_create_audit_log_entry(self, student_user):
        """Audit log entry can be created with all fields."""
        entry = AuditLog.objects.create(
            user=student_user,
            action="CREATE",
            model_name="StudentGrade",
            object_id=42,
            before_snapshot=None,
            after_snapshot={"score": 85, "total_score": 100},
            metadata={"assessment_id": 7},
            ip_address="127.0.0.1",
            user_agent="pytest",
        )
        assert entry.id is not None
        assert entry.user == student_user
        assert entry.action == "CREATE"
        assert entry.timestamp is not None

    def test_audit_log_str(self, student_user):
        entry = AuditLog.objects.create(
            user=student_user, action="DELETE", model_name="Term", object_id=1
        )
        assert "DELETE" in str(entry)
        assert "Term#1" in str(entry)

    def test_ordering_newest_first(self, student_user):
        older = AuditLog.objects.create(user=student_user, action="CREATE", model_name="X", object_id=1)
        newer = AuditLog.objects.create(user=student_user, action="UPDATE", model_name="X", object_id=2)
        entries = list(AuditLog.objects.all())
        assert entries[0] == newer
        assert entries[1] == older
```

- [ ] **Step 5: Run tests**

Run: `cd backend/student_evaluation_system && uv run pytest tests/test_audit.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add backend/student_evaluation_system/core/models.py backend/student_evaluation_system/core/migrations/ backend/student_evaluation_system/core/admin.py backend/student_evaluation_system/tests/test_audit.py
git commit -m "feat: add AuditLog model with admin registration"
```

---

### Task 2: Audit Context Middleware

**Files:**
- Create: `backend/student_evaluation_system/core/services/audit.py`
- Create: `backend/student_evaluation_system/core/middleware.py`
- Modify: `backend/student_evaluation_system/student_evaluation_system/settings.py`

- [ ] **Step 1: Create audit service with request context**

```python
# Create: backend/student_evaluation_system/core/services/audit.py

import threading
from core.models import AuditLog

_audit_request_store = threading.local()


def set_audit_request(request):
    """Store the current request for audit context (called by middleware)."""
    _audit_request_store.request = request


def get_audit_request():
    """Retrieve the current request from thread-local storage."""
    return getattr(_audit_request_store, "request", None)


def log_audit(user, action, model_name, object_id=None, before=None, after=None, metadata=None):
    """Create an audit log entry. Safe to call from views, signals, or tasks."""
    request = get_audit_request()
    ip = request.audit_context["ip_address"] if (request and hasattr(request, "audit_context")) else None
    ua = request.audit_context["user_agent"] if (request and hasattr(request, "audit_context")) else ""

    return AuditLog.objects.create(
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
    """Attach user to a grade instance for signal-based audit capture."""
    grade_instance._audit_user = user
```

- [ ] **Step 2: Write test for audit service**

```python
# Append to: backend/student_evaluation_system/tests/test_audit.py

from core.services.audit import log_audit, set_audit_request, get_audit_request, set_grade_user
from evaluation.models import StudentGrade

@pytest.mark.django_db
class TestAuditService:

    def test_log_audit_creates_entry(self, student_user):
        entry = log_audit(
            student_user, "CREATE", "TestModel", object_id=1,
            after={"key": "value"}, metadata={"extra": "data"}
        )
        assert entry.id is not None
        assert entry.after_snapshot == {"key": "value"}
        assert entry.metadata == {"extra": "data"}

    def test_log_audit_without_request(self, student_user):
        """log_audit works even when no request is in thread-local (e.g., from tests)."""
        entry = log_audit(student_user, "DELETE", "TestModel", object_id=99)
        assert entry.ip_address is None
        assert entry.user_agent == ""

    def test_set_grade_user_attaches_attribute(self, student_user, student_grade):
        set_grade_user(student_grade, student_user)
        assert getattr(student_grade, "_audit_user", None) == student_user

    def test_request_context_isolation(self, rf, student_user):
        """Thread-local storage isolates requests correctly."""
        request = rf.get("/")
        request.audit_context = {"ip_address": "10.0.0.1", "user_agent": "test-agent"}
        set_audit_request(request)

        entry = log_audit(student_user, "CREATE", "X", object_id=1)
        assert entry.ip_address == "10.0.0.1"
        assert entry.user_agent == "test-agent"
```

- [ ] **Step 3: Run tests**

Run: `cd backend/student_evaluation_system && uv run pytest tests/test_audit.py -v`
Expected: 7 passed

- [ ] **Step 4: Create middleware**

```python
# Create: backend/student_evaluation_system/core/middleware.py

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

- [ ] **Step 5: Register middleware in settings.py**

Open `backend/student_evaluation_system/student_evaluation_system/settings.py`. Add after the existing middleware list (preserving order, add after `django.contrib.sessions.middleware.SessionMiddleware`):

```python
MIDDLEWARE = [
    # ... existing entries ...
    "core.middleware.audit_context_middleware",  # Must be after SessionMiddleware
    # ... rest of existing entries ...
]
```

- [ ] **Step 6: Write middleware test**

```python
# Append to: backend/student_evaluation_system/tests/test_audit.py

from core.middleware import audit_context_middleware

class TestAuditMiddleware:

    def test_middleware_sets_audit_context(self, rf, student_user):
        request = rf.get("/some-path/")
        request.user = student_user

        middleware = audit_context_middleware(lambda r: None)
        middleware(request)

        assert hasattr(request, "audit_context")
        assert "ip_address" in request.audit_context
        assert "user_agent" in request.audit_context
```

- [ ] **Step 7: Run all audit tests**

Run: `cd backend/student_evaluation_system && uv run pytest tests/test_audit.py -v`
Expected: 8 passed

- [ ] **Step 8: Commit**

```bash
git add backend/student_evaluation_system/core/services/audit.py backend/student_evaluation_system/core/middleware.py backend/student_evaluation_system/student_evaluation_system/settings.py backend/student_evaluation_system/tests/test_audit.py
git commit -m "feat: add audit context middleware and audit service"
```

---

### Task 3: Audit Signal Handlers for StudentGrade

**Files:**
- Create: `backend/student_evaluation_system/core/signals.py`
- Modify: `backend/student_evaluation_system/core/apps.py`

- [ ] **Step 1: Create signal handlers**

```python
# Create: backend/student_evaluation_system/core/signals.py

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from evaluation.models import StudentGrade
from core.services.audit import log_audit


@receiver(post_save, sender=StudentGrade)
def audit_grade_save(sender, instance, created, **kwargs):
    user = getattr(instance, "_audit_user", None)
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
    # Updates are handled explicitly in the view layer (post_save can't capture before state)


@receiver(post_delete, sender=StudentGrade)
def audit_grade_delete(sender, instance, **kwargs):
    user = getattr(instance, "_audit_user", None)
    if not user:
        return

    before = {
        "score": instance.score,
        "total_score": instance.assessment.total_score,
        "assessment_id": instance.assessment_id,
        "student_id": instance.student_id,
    }
    log_audit(user, "DELETE", "StudentGrade", instance.id, before=before, after=None)
```

- [ ] **Step 2: Register signals in AppConfig**

Open `backend/student_evaluation_system/core/apps.py`. If it exists, modify `ready()`. If not, create it:

```python
# Modify or create: backend/student_evaluation_system/core/apps.py

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        import core.signals  # noqa: F401
```

Ensure `__init__.py` doesn't already define `default_app_config`. If it does, update it.

- [ ] **Step 3: Write signal test**

```python
# Append to: backend/student_evaluation_system/tests/test_audit.py

from core.models import AuditLog
from core.services.audit import set_grade_user
from evaluation.models import StudentGrade

@pytest.mark.django_db
class TestGradeAuditSignals:

    def test_grade_create_triggers_audit(self, student_user, student_grade):
        """Creating a grade with _audit_user set triggers audit log."""
        # Reset any existing entries
        AuditLog.objects.all().delete()
        set_grade_user(student_grade, student_user)
        student_grade.save()

        logs = AuditLog.objects.filter(action="CREATE", model_name="StudentGrade")
        assert logs.count() >= 1
        entry = logs.first()
        assert entry.user == student_user
        assert entry.after_snapshot["score"] == student_grade.score

    def test_grade_delete_triggers_audit(self, student_user, student_grade):
        """Deleting a grade with _audit_user set triggers audit log."""
        AuditLog.objects.all().delete()
        existing_score = student_grade.score
        set_grade_user(student_grade, student_user)
        student_grade.delete()

        logs = AuditLog.objects.filter(action="DELETE", model_name="StudentGrade")
        assert logs.count() >= 1
        assert logs.first().before_snapshot["score"] == existing_score

    def test_grade_save_without_user_does_not_audit(self, student_grade):
        """Grades without _audit_user do not trigger audit logs."""
        AuditLog.objects.all().delete()
        # _audit_user is NOT set
        student_grade.score = student_grade.score + 1
        student_grade.save()

        logs = AuditLog.objects.filter(model_name="StudentGrade")
        assert logs.count() == 0
```

- [ ] **Step 4: Run tests**

Run: `cd backend/student_evaluation_system && uv run pytest tests/test_audit.py -v`
Expected: 11 passed

- [ ] **Step 5: Commit**

```bash
git add backend/student_evaluation_system/core/signals.py backend/student_evaluation_system/core/apps.py backend/student_evaluation_system/tests/test_audit.py
git commit -m "feat: add audit signal handlers for StudentGrade create/delete"
```

---

### Task 4: SSE Publish Helper + Endpoint

**Files:**
- Create: `backend/student_evaluation_system/core/services/sse.py`
- Create: `backend/student_evaluation_system/core/views/sse.py`
- Modify: `backend/student_evaluation_system/core/urls.py`
- Create: `backend/student_evaluation_system/tests/test_sse.py`

- [ ] **Step 1: Create SSE publish helper**

```python
# Create: backend/student_evaluation_system/core/services/sse.py

import json
import redis as redis_lib
from django.conf import settings


def get_redis_client():
    return redis_lib.Redis.from_url(settings.CELERY_BROKER_URL)


def publish_progress(channel: str, data: dict):
    """Publish progress data to a Redis pub/sub channel.

    Channel naming: 'jobs.{job_id}' for job streams, 'notifications.{user_id}' for user alerts.
    """
    client = get_redis_client()
    client.publish(channel, json.dumps(data))
```

- [ ] **Step 2: Write publish test**

```python
# Create: backend/student_evaluation_system/tests/test_sse.py

import json
from unittest.mock import patch, MagicMock
from core.services.sse import publish_progress, get_redis_client


class TestSsePublish:

    @patch("core.services.sse.redis_lib.Redis.from_url")
    def test_publish_progress_sends_json(self, mock_from_url):
        mock_client = MagicMock()
        mock_from_url.return_value = mock_client

        publish_progress("jobs.42", {"type": "progress", "current": 3, "total": 10})

        mock_client.publish.assert_called_once()
        call_args = mock_client.publish.call_args[0]
        assert call_args[0] == "jobs.42"
        parsed = json.loads(call_args[1])
        assert parsed["type"] == "progress"
        assert parsed["current"] == 3
        assert parsed["total"] == 10
```

- [ ] **Step 3: Run SSE publish test**

Run: `cd backend/student_evaluation_system && uv run pytest tests/test_sse.py -v`
Expected: 1 passed

- [ ] **Step 4: Create SSE async view**

```python
# Create: backend/student_evaluation_system/core/views/sse.py

import json
import asyncio
from django.http import StreamingHttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from core.services.sse import get_redis_client


@api_view(["GET"])
@permission_classes([IsAuthenticated])
async def event_stream(request):
    """SSE endpoint. Subscribe via ?channels=jobs.42,notifications.5"""
    channels = request.GET.get("channels", "")
    if not channels:
        return Response({"error": "channels query parameter required"}, status=400)

    channel_list = [c.strip() for c in channels.split(",") if c.strip()]

    # Security: users can only subscribe to their own notification channel
    for ch in channel_list:
        if ch.startswith("notifications."):
            user_id = ch.split(".", 1)[1]
            if str(user_id) != str(request.user.id):
                return Response(
                    {"error": "Cannot subscribe to another user's notification channel"},
                    status=403,
                )

    async def event_generator():
        client = get_redis_client()
        pubsub = client.pubsub()
        try:
            pubsub.subscribe(*channel_list)
        except Exception:
            return

        try:
            while True:
                message = pubsub.get_message(ignore_subscribe_messages=True, timeout=30.0)
                if message and message.get("type") == "message":
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    yield f"data: {data}\n\n"
                else:
                    yield ": heartbeat\n\n"
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
        finally:
            try:
                pubsub.unsubscribe(*channel_list)
            except Exception:
                pass

    response = StreamingHttpResponse(
        event_generator(),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    response["Connection"] = "keep-alive"
    return response
```

- [ ] **Step 5: Register SSE route**

Open `backend/student_evaluation_system/core/urls.py`. Add above the router registration:

```python
from core.views.sse import event_stream

urlpatterns = [
    path("events/", event_stream, name="event-stream"),
]
```

The existing `urlpatterns` list already exists — add this entry to it. You may need to import `path` from `django.urls` if not already imported.

- [ ] **Step 6: Write SSE view tests**

```python
# Append to: backend/student_evaluation_system/tests/test_sse.py

import pytest
from unittest.mock import patch, MagicMock
from django.test import override_settings


@pytest.mark.django_db
class TestEventStreamView:

    def test_missing_channels_returns_400(self, authenticated_api_client):
        response = authenticated_api_client.get("/api/core/events/")
        assert response.status_code == 400
        assert "channels" in response.json()["error"]

    def test_unauthorized_notification_channel(self, authenticated_api_client, student_user):
        """User cannot subscribe to another user's notification channel."""
        other_user_id = student_user.id + 999
        response = authenticated_api_client.get(
            f"/api/core/events/?channels=notifications.{other_user_id}"
        )
        assert response.status_code == 403

    @patch("core.views.sse.get_redis_client")
    def test_valid_channel_returns_sse_stream(self, mock_get_redis, authenticated_api_client):
        mock_pubsub = MagicMock()
        mock_pubsub.get_message.return_value = None  # No messages, just heartbeats
        mock_client = MagicMock()
        mock_client.pubsub.return_value = mock_pubsub
        mock_get_redis.return_value = mock_client

        response = authenticated_api_client.get("/api/core/events/?channels=jobs.1")

        assert response.status_code == 200
        assert response["Content-Type"] == "text/event-stream"
        assert response["Cache-Control"] == "no-cache"

    @patch("core.views.sse.get_redis_client")
    def test_stream_receives_published_message(self, mock_get_redis, authenticated_api_client):
        import json

        mock_pubsub = MagicMock()
        # Simulate one message then timeout
        mock_pubsub.get_message.side_effect = [
            {"type": "message", "data": json.dumps({"type": "progress", "current": 1, "total": 5}).encode()},
            None,  # next call returns None (heartbeat)
        ]
        mock_client = MagicMock()
        mock_client.pubsub.return_value = mock_pubsub
        mock_get_redis.return_value = mock_client

        response = authenticated_api_client.get("/api/core/events/?channels=jobs.1")
        content = b"".join(response.streaming_content)

        assert b"data:" in content
        assert b"progress" in content
```

- [ ] **Step 7: Run all SSE tests**

Run: `cd backend/student_evaluation_system && uv run pytest tests/test_sse.py -v`
Expected: 5 passed

- [ ] **Step 8: Commit**

```bash
git add backend/student_evaluation_system/core/services/sse.py backend/student_evaluation_system/core/views/sse.py backend/student_evaluation_system/core/urls.py backend/student_evaluation_system/tests/test_sse.py
git commit -m "feat: add SSE endpoint with Redis pub/sub streaming"
```

---

### Task 5: Frontend SSE Hook + JobProgressBar

**Files:**
- Create: `frontend/src/shared/hooks/useJobStream.ts`
- Create: `frontend/src/shared/components/JobProgressBar.tsx`
- Create: `frontend/src/shared/hooks/__tests__/useJobStream.test.ts`
- Create: `frontend/src/shared/components/__tests__/JobProgressBar.test.tsx`

- [ ] **Step 1: Create useJobStream hook**

```typescript
// Create: frontend/src/shared/hooks/useJobStream.ts

import { useEffect, useState, useCallback } from 'react'

export interface JobProgress {
  type: 'progress' | 'complete'
  job_id: number
  status: 'running' | 'success' | 'failed'
  current?: number
  total?: number
  created?: number
  courses_created?: number
  error?: string
}

interface UseJobStreamResult {
  progress: JobProgress | null
  isComplete: boolean
  error: string | null
  reconnect: () => void
}

export function useJobStream(jobId: number | null): UseJobStreamResult {
  const [progress, setProgress] = useState<JobProgress | null>(null)
  const [isComplete, setIsComplete] = useState(false)
  const [streamError, setStreamError] = useState<string | null>(null)
  const [retryCount, setRetryCount] = useState(0)

  const connect = useCallback(() => {
    if (!jobId) return () => {}

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
        // Heartbeat messages (lines starting with ":") are not valid JSON — ignore
      }
    }

    eventSource.onerror = () => {
      setStreamError('Connection lost. Retrying...')
      // EventSource auto-reconnects by default
    }

    return () => {
      eventSource.close()
    }
  }, [jobId, retryCount])

  useEffect(() => {
    const cleanup = connect()
    return cleanup
  }, [connect])

  const reconnect = useCallback(() => {
    setIsComplete(false)
    setStreamError(null)
    setRetryCount((prev) => prev + 1)
  }, [])

  return { progress, isComplete, error: streamError, reconnect }
}
```

- [ ] **Step 2: Write hook test**

```typescript
// Create: frontend/src/shared/hooks/__tests__/useJobStream.test.ts

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useJobStream } from '../useJobStream'

describe('useJobStream', () => {
  let mockEventSource: any
  let eventSourceInstances: any[]

  beforeEach(() => {
    eventSourceInstances = []
    mockEventSource = vi.fn().mockImplementation((url: string, config?: any) => {
      const instance = {
        url,
        config,
        onmessage: null as any,
        onerror: null as any,
        close: vi.fn(),
      }
      eventSourceInstances.push(instance)
      return instance
    })
    vi.stubGlobal('EventSource', mockEventSource)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('returns null progress when jobId is null', () => {
    const { result } = renderHook(() => useJobStream(null))
    expect(result.current.progress).toBeNull()
    expect(result.current.isComplete).toBe(false)
  })

  it('creates EventSource with correct URL when jobId is provided', () => {
    renderHook(() => useJobStream(42))

    expect(mockEventSource).toHaveBeenCalled()
    const url = mockEventSource.mock.calls[0][0] as string
    expect(url).toContain('channels=jobs.42')
    expect(url).toContain('/api/core/events/')
  })

  it('sets isComplete when complete event received', () => {
    const { result } = renderHook(() => useJobStream(42))

    act(() => {
      const instance = eventSourceInstances[0]
      instance.onmessage({
        data: JSON.stringify({
          type: 'complete',
          job_id: 42,
          status: 'success',
          courses_created: 5,
        }),
      })
    })

    expect(result.current.isComplete).toBe(true)
    expect(result.current.progress?.courses_created).toBe(5)
    expect(eventSourceInstances[0].close).toHaveBeenCalled()
  })

  it('does not set isComplete for progress events', () => {
    const { result } = renderHook(() => useJobStream(42))

    act(() => {
      const instance = eventSourceInstances[0]
      instance.onmessage({
        data: JSON.stringify({
          type: 'progress',
          job_id: 42,
          status: 'running',
          current: 3,
          total: 10,
        }),
      })
    })

    expect(result.current.isComplete).toBe(false)
    expect(result.current.progress?.current).toBe(3)
    expect(result.current.progress?.total).toBe(10)
  })

  it('ignores heartbeat messages (non-JSON)', () => {
    const { result } = renderHook(() => useJobStream(42))

    act(() => {
      const instance = eventSourceInstances[0]
      instance.onmessage({ data: ': heartbeat' })
    })

    // Progress should remain null (heartbeat ignored)
    expect(result.current.progress).toBeNull()
  })

  it('closes EventSource on unmount', () => {
    const { unmount } = renderHook(() => useJobStream(42))
    unmount()
    expect(eventSourceInstances[0].close).toHaveBeenCalled()
  })
})
```

- [ ] **Step 3: Run hook tests**

Run: `cd frontend && npx vitest run src/shared/hooks/__tests__/useJobStream.test.ts`
Expected: 6 passed

- [ ] **Step 4: Create JobProgressBar component**

```tsx
// Create: frontend/src/shared/components/JobProgressBar.tsx

import React, { useEffect } from 'react'
import { useJobStream } from '@/shared/hooks/useJobStream'

interface JobProgressBarProps {
  jobId: number | null
  onComplete?: () => void
  label?: string
}

export const JobProgressBar: React.FC<JobProgressBarProps> = ({
  jobId,
  onComplete,
  label = 'Processing...',
}) => {
  const { progress, isComplete, error, reconnect } = useJobStream(jobId)

  useEffect(() => {
    if (isComplete && onComplete) {
      onComplete()
    }
  }, [isComplete, onComplete])

  if (!jobId || !progress) {
    return null
  }

  if (progress.type === 'complete') {
    return (
      <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
        <p className="text-emerald-800 font-medium">
          Complete: {progress.courses_created ?? progress.created ?? 0} items processed
        </p>
      </div>
    )
  }

  if (progress.status === 'failed') {
    return (
      <div className="bg-danger-50 border border-danger-200 rounded-xl p-4">
        <p className="text-danger-800 font-medium mb-2">Job failed</p>
        {progress.error && (
          <p className="text-danger-600 text-sm">{progress.error}</p>
        )}
        <button
          onClick={reconnect}
          className="mt-2 px-3 py-1 bg-danger-600 text-white text-sm rounded-lg"
        >
          Retry
        </button>
      </div>
    )
  }

  const pct = progress.total && progress.total > 0
    ? Math.round(((progress.current ?? 0) / progress.total) * 100)
    : 0

  return (
    <div className="bg-primary-50 border border-primary-200 rounded-xl p-4">
      <p className="text-sm text-primary-700 mb-2">
        {label} {progress.current}/{progress.total}
      </p>
      <div className="w-full bg-primary-200 rounded-full h-2">
        <div
          className="bg-primary-600 h-2 rounded-full transition-all duration-300"
          style={{ width: `${pct}%` }}
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
      {error && (
        <p className="text-warning-600 text-xs mt-1">{error}</p>
      )}
    </div>
  )
}
```

- [ ] **Step 5: Write component tests**

```typescript
// Create: frontend/src/shared/components/__tests__/JobProgressBar.test.tsx

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { JobProgressBar } from '../JobProgressBar'

// Mock the hook
vi.mock('@/shared/hooks/useJobStream', () => ({
  useJobStream: vi.fn(),
}))

import { useJobStream } from '@/shared/hooks/useJobStream'

describe('JobProgressBar', () => {
  beforeEach(() => {
    vi.mocked(useJobStream).mockReturnValue({
      progress: null,
      isComplete: false,
      error: null,
      reconnect: vi.fn(),
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('renders nothing when jobId is null', () => {
    const { container } = render(<JobProgressBar jobId={null} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders nothing when no progress yet', () => {
    const { container } = render(<JobProgressBar jobId={42} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders progress bar with percentage', () => {
    vi.mocked(useJobStream).mockReturnValue({
      progress: {
        type: 'progress',
        job_id: 42,
        status: 'running',
        current: 5,
        total: 10,
      },
      isComplete: false,
      error: null,
      reconnect: vi.fn(),
    })

    render(<JobProgressBar jobId={42} label="Creating courses..." />)
    expect(screen.getByText('Creating courses... 5/10')).toBeDefined()
    expect(screen.getByRole('progressbar')).toBeDefined()
  })

  it('renders complete state', () => {
    vi.mocked(useJobStream).mockReturnValue({
      progress: {
        type: 'complete',
        job_id: 42,
        status: 'success',
        courses_created: 8,
      },
      isComplete: true,
      error: null,
      reconnect: vi.fn(),
    })

    render(<JobProgressBar jobId={42} />)
    expect(screen.getByText('Complete: 8 items processed')).toBeDefined()
  })

  it('calls onComplete when job finishes', () => {
    const onComplete = vi.fn()
    vi.mocked(useJobStream).mockReturnValue({
      progress: {
        type: 'complete',
        job_id: 42,
        status: 'success',
        courses_created: 1,
      },
      isComplete: true,
      error: null,
      reconnect: vi.fn(),
    })

    render(<JobProgressBar jobId={42} onComplete={onComplete} />)
    expect(onComplete).toHaveBeenCalledTimes(1)
  })

  it('renders error state with retry button', () => {
    const reconnect = vi.fn()
    vi.mocked(useJobStream).mockReturnValue({
      progress: {
        type: 'complete',  // failure is determined by status, not type
        job_id: 42,
        status: 'failed',
        error: 'Template 3 failed to clone',
      },
      isComplete: true,
      error: null,
      reconnect,
    })

    // Fix: the component checks status BEFORE type for failure
    // Actually it checks progress.status === 'failed' before type
    // Our mock has type 'complete' and status 'failed' which triggers the failed branch
    render(<JobProgressBar jobId={42} />)
    expect(screen.getByText('Job failed')).toBeDefined()
    expect(screen.getByText('Template 3 failed to clone')).toBeDefined()
  })
})
```

- [ ] **Step 6: Run component tests**

Run: `cd frontend && npx vitest run src/shared/components/__tests__/JobProgressBar.test.tsx`
Expected: 6 passed

- [ ] **Step 7: Commit**

```bash
git add frontend/src/shared/hooks/useJobStream.ts frontend/src/shared/components/JobProgressBar.tsx frontend/src/shared/hooks/__tests__/useJobStream.test.ts frontend/src/shared/components/__tests__/JobProgressBar.test.tsx
git commit -m "feat: add useJobStream SSE hook and JobProgressBar component"
```

---

### Task 6: Replace Polling with SSE in RecomputeJobsContext

**Files:**
- Modify: `frontend/src/shared/contexts/RecomputeJobsContext.tsx`

- [ ] **Step 1: Read current file**

Read `frontend/src/shared/contexts/RecomputeJobsContext.tsx` to understand the current polling logic at lines 110-151.

- [ ] **Step 2: Replace polling with SSE subscriptions**

Replace the entire polling `useEffect` (lines 110-151 approximately) with SSE-based subscriptions:

```typescript
// REPLACE the polling useEffect in RecomputeJobsContext.tsx
// The existing code has: setInterval(() => { void poll() }, 1000)

import { useRef } from 'react'

// Inside the component, replace the polling useEffect:
useEffect(() => {
  const cancelled = false
  const pendingJobs = jobs.filter(
    (job) => job.status === 'pending' || job.status === 'running'
  )

  if (pendingJobs.length === 0) return

  const baseUrl = import.meta.env.VITE_API_URL || ''
  const eventSources: EventSource[] = []

  pendingJobs.forEach((job) => {
    const url = `${baseUrl}/api/core/events/?channels=jobs.${job.id}`
    const es = new EventSource(url, { withCredentials: true })

    es.onmessage = (event) => {
      if (cancelled) {
        es.close()
        return
      }
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'complete') {
          // Invalidate and refetch jobs from the API
          queryClient.invalidateQueries({ queryKey: ['score-recompute-jobs'] })
          es.close()
        }
      } catch {
        // Heartbeat — ignore
      }
    }

    es.onerror = () => {
      // EventSource auto-reconnects by default
    }

    eventSources.push(es)
  })

  return () => {
    // cancelled = true — not needed for closure since we use the array
    eventSources.forEach((es) => es.close())
  }
}, [jobs, queryClient])
```

Note: Remove the old `poll` function and the `window.setInterval` / `window.setTimeout` calls for polling. Keep the notification timeout logic (lines 156-162) unchanged — those handle notification dismissal, not data fetching.

- [ ] **Step 3: Verify build**

Run: `cd frontend && npx tsc --noEmit`
Expected: No TypeScript errors

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 4: Commit**

```bash
git add frontend/src/shared/contexts/RecomputeJobsContext.tsx
git commit -m "refactor: replace 1-second polling with SSE in RecomputeJobsContext"
```

---

### Task 7: Final Integration Verification

**Files:** None — verification only.

- [ ] **Step 1: Run all backend tests**

Run: `cd backend/student_evaluation_system && uv run pytest -v`
Expected: All tests pass (existing + new audit/sse tests)

- [ ] **Step 2: Run all frontend tests**

Run: `cd frontend && npx vitest run`
Expected: All tests pass

- [ ] **Step 3: Run backend lint**

Run: `cd backend/student_evaluation_system && uv run ruff check .`
Expected: No errors

- [ ] **Step 4: Run frontend lint**

Run: `cd frontend && npm run lint`
Expected: No errors

- [ ] **Step 5: Commit final state if any cleanups needed**

```bash
git add -A
git diff --cached --stat
git commit -m "chore: final integration verification for SSE + audit logging"
```
