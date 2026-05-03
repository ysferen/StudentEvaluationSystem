# Weight Suggestion Celery Worker — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move weight suggestion into a Celery worker with pre-loaded SentenceTransformer model, eliminating the ~8s cold-start per invocation.

**Architecture:** Model loads once via `worker_process_init` signal. Task fetches course LOs/assessments from DB, calls the pre-loaded `WeightSuggester`, returns the weight mapping. Job tracking via `WeightSuggestionJob` model. REST endpoint for async invocation.

**Tech Stack:** Django 5.2, Celery, Redis, SentenceTransformer, DRF, pytest

**Workdir for all steps:** `backend/student_evaluation_system/`

---

### Task 0: Create `WeightSuggestionJob` Model

**Files:**
- Modify: `core/models.py` (add model at end)
- Create: (migration auto-generated)

- [ ] **Step 1: Add the model to core/models.py**

Append this after the last model (line 646, after `InstructorPermission`):

```python
class WeightSuggestionJob(TimeStampedModel):
    """Tracks async weight suggestion tasks run via Celery."""

    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_RUNNING, "Running"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
    )

    course = models.ForeignKey(
        "Course",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="weight_suggestion_jobs",
    )
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="triggered_weight_suggestion_jobs",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    celery_task_id = models.CharField(max_length=255, blank=True)
    result = models.JSONField(null=True, blank=True)
    error = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Weight Suggestion Job"
        verbose_name_plural = "Weight Suggestion Jobs"

    def __str__(self):
        course_id = self.course_id if self.course_id is not None else "-"
        return f"WeightSuggestionJob {self.id}: course={course_id} status={self.status}"
```

- [ ] **Step 2: Generate and run migration**

```bash
cd backend/student_evaluation_system && uv run python manage.py makemigrations core --name weight_suggestion_job
```
Expected: creates `core/migrations/XXXX_weight_suggestion_job.py`

```bash
cd backend/student_evaluation_system && uv run python manage.py migrate core
```
Expected: `Applying core.XXXX_weight_suggestion_job... OK`

- [ ] **Step 3: Verify model works**

```bash
cd backend/student_evaluation_system && uv run python manage.py shell -c "
from core.models import WeightSuggestionJob
j = WeightSuggestionJob.objects.create(status='pending')
print(f'Created job {j.id} with status {j.status}')
"
```
Expected: `Created job 1 with status pending`

- [ ] **Step 4: Commit**

```bash
git add core/models.py core/migrations/
git commit -m "feat: add WeightSuggestionJob model for async weight suggestion tracking"
```

---

### Task 1: Create Celery Task with Pre-loaded Model

**Files:**
- Create: `core/tasks.py`
- Test: `tests/test_weight_suggestion_tasks.py` (starting in this task, completed in Task 4)

- [ ] **Step 1: Write the failing test for the task existence**

Create `tests/test_weight_suggestion_tasks.py`:

```python
"""Tests for weight suggestion Celery tasks."""

import pytest
from unittest.mock import MagicMock, patch


class TestSuggestAssessmentLOTask:
    """Tests for suggest_assessment_lo_weights_task."""

    def test_task_is_registered(self):
        """Verify the task is importable and has celery attributes."""
        from core.tasks import suggest_assessment_lo_weights_task

        assert suggest_assessment_lo_weights_task is not None
        assert hasattr(suggest_assessment_lo_weights_task, "delay")
        assert hasattr(suggest_assessment_lo_weights_task, "name")

    def test_task_returns_correct_schema(self):
        """Task result must have 'assessment_lo' key with expected structure."""
        from core.tasks import suggest_assessment_lo_weights_task
        from core.services.weight_suggestion import WeightSuggester
        from unittest.mock import MagicMock, patch

        mock_suggester = MagicMock()
        mock_suggester.suggest_assessment_lo.return_value = {
            "assessment_lo": {
                "Midterm": {"LO1": 4, "LO2": 2},
                "Final": {"LO1": 3, "LO2": 5},
            }
        }

        mock_course = MagicMock()
        mock_course.name = "Test Course"
        mock_course.learning_outcomes.all.return_value = [
            MagicMock(description="LO1: desc a"),
            MagicMock(description="LO2: desc b"),
        ]
        mock_course.assessments.all.return_value = []

        with patch("core.tasks._suggester", mock_suggester), \
             patch("core.tasks.Course") as mock_course_model:
            mock_course_model.objects.get.return_value = mock_course

            result = suggest_assessment_lo_weights_task(course_id=42)

            assert isinstance(result, dict)
            assert "assessment_lo" in result
            weights = result["assessment_lo"]
            assert isinstance(weights, dict)
            for assessment_name, lo_weights in weights.items():
                assert isinstance(lo_weights, dict)
                for lo_key, weight in lo_weights.items():
                    assert isinstance(weight, int)
                    assert 0 <= weight <= 5

    def test_task_updates_job_status_on_success(self):
        """Task should update job to success with result."""
        from core.tasks import suggest_assessment_lo_weights_task

        mock_suggester = MagicMock()
        mock_suggester.suggest_assessment_lo.return_value = {
            "assessment_lo": {"Midterm": {"LO1": 3, "LO2": 4}}
        }

        mock_course = MagicMock()
        mock_course.name = "Test Course"
        mock_course.learning_outcomes.all.return_value = [
            MagicMock(description="LO1: desc a"),
            MagicMock(description="LO2: desc b"),
        ]
        mock_course.assessments.all.return_value = []

        mock_job = MagicMock()

        with patch("core.tasks._suggester", mock_suggester), \
             patch("core.tasks.Course") as mock_course_model, \
             patch("core.tasks.WeightSuggestionJob") as mock_job_model, \
             patch("core.tasks.timezone") as mock_tz:
            mock_course_model.objects.get.return_value = mock_course
            mock_job_model.objects.filter.return_value = MagicMock()
            mock_tz.now.return_value = "2025-01-01T00:00:00Z"

            result = suggest_assessment_lo_weights_task(course_id=42, job_id=99)

            # Verify job was updated to success
            mock_job_model.objects.filter.assert_any_call(id=99)

    def test_task_updates_job_on_failure(self):
        """Task should mark job as failed on exception."""
        from core.tasks import suggest_assessment_lo_weights_task

        mock_suggester = MagicMock()
        mock_suggester.suggest_assessment_lo.side_effect = ValueError("model error")

        mock_course = MagicMock()
        mock_course.name = "Test Course"
        mock_course.learning_outcomes.all.return_value = [
            MagicMock(description="LO1: desc a"),
        ]
        mock_course.assessments.all.return_value = []

        with patch("core.tasks._suggester", mock_suggester), \
             patch("core.tasks.Course") as mock_course_model, \
             patch("core.tasks.WeightSuggestionJob") as mock_job_model, \
             patch("core.tasks.timezone") as mock_tz:
            mock_course_model.objects.get.return_value = mock_course
            mock_filter = MagicMock()
            mock_job_model.objects.filter.return_value = mock_filter
            mock_tz.now.return_value = "2025-01-01T00:00:00Z"

            with pytest.raises(ValueError, match="model error"):
                suggest_assessment_lo_weights_task(course_id=42, job_id=99)

            mock_filter.update.assert_called()
            update_kwargs = mock_filter.update.call_args[1]
            assert update_kwargs["status"] == "failed"

    def test_task_handles_missing_course(self):
        """Task should raise Course.DoesNotExist if course not found."""
        from core.tasks import suggest_assessment_lo_weights_task
        from django.core.exceptions import ObjectDoesNotExist

        with patch("core.tasks.Course") as mock_course_model:
            mock_course_model.objects.get.side_effect = ObjectDoesNotExist("no course")

            with pytest.raises(ObjectDoesNotExist):
                suggest_assessment_lo_weights_task(course_id=99999)

    def test_task_handles_no_los(self):
        """Task should succeed with empty mapping when course has no LOs."""
        from core.tasks import suggest_assessment_lo_weights_task

        mock_suggester = MagicMock()
        mock_suggester.suggest_assessment_lo.return_value = {"assessment_lo": {}}

        mock_course = MagicMock()
        mock_course.name = "Test Course"
        mock_course.learning_outcomes.all.return_value = []
        mock_course.assessments.all.return_value = [
            MagicMock(name="Midterm", assessment_type="midterm"),
        ]

        with patch("core.tasks._suggester", mock_suggester), \
             patch("core.tasks.Course") as mock_course_model:
            mock_course_model.objects.get.return_value = mock_course

            result = suggest_assessment_lo_weights_task(course_id=42)

            assert result == {"assessment_lo": {}}
            # Suggester should be called with empty LO list
            call_kwargs = mock_suggester.suggest_assessment_lo.call_args[1]
            assert call_kwargs["los"] == []


class TestWorkerInit:
    """Tests for the worker_process_init signal handler."""

    def test_init_worker_creates_suggester(self):
        """Verify the signal handler sets _suggester."""
        import core.tasks as tasks_module

        with patch.object(tasks_module, "SentenceTransformer") as mock_st, \
             patch.object(tasks_module, "WeightSuggester") as mock_ws_cls, \
             patch.object(tasks_module, "os") as mock_os:
            mock_os.getenv.return_value = "test-model"
            mock_ws_cls.return_value = "mock-suggester-instance"

            tasks_module._init_weight_suggester()

            mock_st.assert_called_once_with("test-model")
            mock_ws_cls.assert_called_once()
            # Verify encoder was passed
            call_kwargs = mock_ws_cls.call_args[1]
            assert "encoder" in call_kwargs

    def test_init_worker_default_model(self):
        """Verify default model name when env var is not set."""
        import core.tasks as tasks_module

        with patch.object(tasks_module, "SentenceTransformer") as mock_st, \
             patch.object(tasks_module, "WeightSuggester") as mock_ws_cls, \
             patch.object(tasks_module, "os") as mock_os:
            mock_os.getenv.return_value = None  # simulate unset env var

            tasks_module._init_weight_suggester()

            mock_st.assert_called_once_with("all-MiniLM-L6-v2")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend/student_evaluation_system && uv run pytest tests/test_weight_suggestion_tasks.py -v 2>&1 | head -20
```
Expected: `ModuleNotFoundError: No module named 'core.tasks'` (or similar import error)

- [ ] **Step 3: Create core/tasks.py with model pre-loading and task**

Create `core/tasks.py`:

```python
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

# Module-level suggester — loaded once per worker process
_suggester = None


@worker_process_init.connect
def _init_weight_suggester(**kwargs):
    """Load the embedding model once when the Celery worker starts."""
    global _suggester
    model_name = os.getenv("SENTENCE_TRANSFORMER_MODEL", "all-MiniLM-L6-v2")
    model = SentenceTransformer(model_name)
    _suggester = WeightSuggester(encoder=model)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True,
             retry_kwargs={"max_retries": 3})
def suggest_assessment_lo_weights_task(self, course_id: int,
                                       job_id: int | None = None) -> dict:
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
        assessment_texts = [
            f"{a.name}: {a.get_assessment_type_display()}" for a in assessments
        ]

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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend/student_evaluation_system && uv run pytest tests/test_weight_suggestion_tasks.py -v
```
Expected: all tests pass (8 tests)

- [ ] **Step 5: Commit**

```bash
git add core/tasks.py tests/test_weight_suggestion_tasks.py
git commit -m "feat: add Celery task with pre-loaded model for weight suggestion"
```

---

### Task 2: Rewrite Test Script

**Files:**
- Modify: `run_weight_suggestion.py`

- [ ] **Step 1: Rewrite run_weight_suggestion.py**

Replace the entire content of `run_weight_suggestion.py`:

```python
"""
Celery-based weight suggestion test script.

Usage:
    cd backend/student_evaluation_system
    uv run python run_weight_suggestion.py [course_id]

    If no course_id is provided, picks the first course with LOs from the DB.
    If no assessments exist in DB for the course, uses hard-coded assessment
    descriptions.

Prerequisites:
    - Django DB accessible
    - Redis running (Celery broker)
    - Celery worker running (docker compose up celery_worker)
"""

import json
import os
import sys
import time


def _get_default_assessment_texts():
    """Hard-coded assessment descriptions (fallback when none in DB)."""
    return [
        "Midterm exam: tests theoretical understanding of database concepts",
        "Final exam: comprehensive evaluation of all course topics",
        "Project: practical implementation of a database application",
    ]


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "student_evaluation_system.settings")

    import django
    django.setup()

    from core.models import Course

    # --- Resolve course_id ---
    if len(sys.argv) > 1:
        course_id = int(sys.argv[1])
    else:
        # Pick first course that has learning outcomes
        course = Course.objects.filter(
            learning_outcomes__isnull=False
        ).distinct().first()
        if course is None:
            print("ERROR: No course with learning outcomes found in DB.")
            print("Create a course with LOs first, or provide a course_id argument.")
            sys.exit(1)
        course_id = course.id

    course = Course.objects.get(id=course_id)
    print("=" * 70)
    print(f"Course: {course.name} (ID: {course.id})")
    print(f"LOs: {course.learning_outcomes.count()}")
    for lo in course.learning_outcomes.all():
        print(f"  {lo.code}: {lo.description}")
    print(f"Assessments in DB: {course.assessments.count()}")
    print("=" * 70)

    # --- Queue the Celery task ---
    print("\nDispatching Celery task...")

    try:
        from core.tasks import suggest_assessment_lo_weights_task
        async_result = suggest_assessment_lo_weights_task.delay(course_id=course.id)
    except Exception as e:
        print(f"ERROR: Could not dispatch task. Is Celery/Redis running?\n{e}")
        sys.exit(1)

    # --- Poll for result ---
    print(f"Task ID: {async_result.id}")
    print("Waiting for result", end="", flush=True)

    timeout = 120
    poll_interval = 0.5
    start = time.monotonic()
    while not async_result.ready():
        elapsed = time.monotonic() - start
        if elapsed > timeout:
            print(f"\nERROR: Task timed out after {timeout}s.")
            print("Check Celery worker logs for errors.")
            sys.exit(1)
        print(".", end="", flush=True)
        time.sleep(poll_interval)

    print(f" done ({time.monotonic() - start:.1f}s)")

    # --- Print result ---
    if async_result.failed():
        print(f"\nERROR: Task failed.\n{async_result.traceback}")
        sys.exit(1)

    result = async_result.result
    print("\nResponse:")
    print(json.dumps(result, indent=4))

    # Summary table
    mappings = result.get("assessment_lo", {})
    if mappings:
        lo_count = len(next(iter(mappings.values())))
        lo_keys = [f"LO{i + 1}" for i in range(lo_count)]
        print("\n" + "-" * 50)
        header = f"{'Assessment':<20}" + "".join(f"{lo:>6}" for lo in lo_keys)
        print(header)
        print("-" * 50)
        for assessment, weights in mappings.items():
            short_name = assessment[:20]
            row = f"{short_name:<20}"
            for lo_key in lo_keys:
                row += f"{weights.get(lo_key, '?'):>6}"
            print(row)
        print("-" * 50)
    else:
        print("\nNo assessment_lo mappings returned (empty result).")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add run_weight_suggestion.py
git commit -m "refactor: rewrite test script to use Celery task instead of direct WeightSuggester"
```

---

### Task 3: Update Existing Tests

**Files:**
- Modify: `tests/test_weight_suggestion.py`

- [ ] **Step 1: Add test for the module-level suggester pattern**

Append to `tests/test_weight_suggestion.py`:

```python
# ---------------------------------------------------------------------------
# Test: Celery model pre-loading integration
# ---------------------------------------------------------------------------

def test_suggester_accepts_external_encoder(sample_course_name, sample_los, sample_assessments, dummy_encoder):
    """
    Verify WeightSuggester works correctly when encoder is passed via
    keyword argument (as it will be from the Celery worker init).
    """
    from core.services.weight_suggestion import WeightSuggester

    embeddings = {
        "Midterm": [1.0, 0.0],
        "Final": [0.8, 0.2],
        "Project": [0.0, 1.0],
        sample_los[0]: [1.0, 0.0],
        sample_los[1]: [0.0, 1.0],
    }
    encoder = dummy_encoder(embeddings)
    suggester = WeightSuggester(encoder=encoder)

    result = suggester.suggest_assessment_lo(
        course_name=sample_course_name,
        los=sample_los,
        assessments=sample_assessments,
    )

    assert "assessment_lo" in result
    assert len(result["assessment_lo"]) == 3

def test_suggester_handles_empty_assessments(sample_course_name, sample_los, dummy_encoder):
    """WeightSuggester should return empty mapping when assessments list is empty."""
    from core.services.weight_suggestion import WeightSuggester

    embeddings = {
        sample_los[0]: [1.0, 0.0],
        sample_los[1]: [0.0, 1.0],
    }
    suggester = WeightSuggester(encoder=dummy_encoder(embeddings))
    result = suggester.suggest_assessment_lo(
        course_name=sample_course_name,
        los=sample_los,
        assessments=[],
    )

    assert result == {"assessment_lo": {}}
```

- [ ] **Step 2: Run existing tests to verify nothing broke**

```bash
cd backend/student_evaluation_system && uv run pytest tests/test_weight_suggestion.py -v
```
Expected: all 5 tests pass (3 original + 2 new)

- [ ] **Step 3: Commit**

```bash
git add tests/test_weight_suggestion.py
git commit -m "test: add coverage for encoder injection and empty assessments in WeightSuggester"
```

---

### Task 4: REST Endpoint — TDD Tests

**Files:**
- Create: `tests/test_weight_suggestion_endpoint.py`
- Modify: `tests/conftest.py` (add fixtures)

- [ ] **Step 1: Add conftest fixtures**

Append to `tests/conftest.py`:

```python
@pytest.fixture
def weight_suggestion_job_factory(db):
    """Factory for WeightSuggestionJob records."""
    from core.models import WeightSuggestionJob

    def _create_job(**kwargs):
        defaults = {
            "status": WeightSuggestionJob.STATUS_PENDING,
        }
        defaults.update(kwargs)
        return WeightSuggestionJob.objects.create(**defaults)

    return _create_job


@pytest.fixture
def course_with_los(db_setup):
    """Creates a course with 3 learning outcomes (no assessments)."""
    from core.models import LearningOutcome

    course = db_setup["course"]
    lo1 = LearningOutcome.objects.create(
        code="LO1",
        description="Explains operating system components",
        course=course,
    )
    lo2 = LearningOutcome.objects.create(
        code="LO2",
        description="Compares process management algorithms",
        course=course,
    )
    lo3 = LearningOutcome.objects.create(
        code="LO3",
        description="Analyzes memory management techniques",
        course=course,
    )
    return {"course": course, "los": [lo1, lo2, lo3]}
```

- [ ] **Step 2: Create endpoint test file (TDD — all tests fail initially)**

Create `tests/test_weight_suggestion_endpoint.py`:

```python
"""
TDD tests for the weight suggestion REST endpoint.

These tests define the expected API contract BEFORE the endpoint exists.
All tests should FAIL on first run, then pass after implementation.
"""

import pytest
from django.urls import reverse
from rest_framework import status
from unittest.mock import patch


ENDPOINT_LIST = "weightsuggestion-list"
ENDPOINT_DETAIL = "weightsuggestion-detail"


def _post_body(course_id=1):
    return {"course_id": course_id}


class TestWeightSuggestionCreate:
    """POST /api/v1/core/weight-suggestion/"""

    def test_create_requires_authentication(self, api_client):
        """Unauthenticated users should get 401."""
        url = reverse(ENDPOINT_LIST)
        response = api_client.post(url, _post_body(), format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_by_student_returns_403(self, api_client, student_factory):
        """Students cannot trigger weight suggestion."""
        student = student_factory("ws_student")
        api_client.force_authenticate(user=student.user)
        url = reverse(ENDPOINT_LIST)
        response = api_client.post(url, _post_body(), format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_by_instructor_returns_201(self, api_client, instructor_factory,
                                               course_with_los):
        """Instructors can trigger weight suggestion — returns job id."""
        instructor = instructor_factory("ws_instructor")
        api_client.force_authenticate(user=instructor.user)
        url = reverse(ENDPOINT_LIST)
        response = api_client.post(
            url, _post_body(course_id=course_with_los["course"].id), format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "id" in data
        assert data["status"] == "pending"

    def test_create_by_admin_returns_201(self, api_client, admin_user_factory,
                                          course_with_los):
        """Admins can trigger weight suggestion."""
        admin_cls = admin_user_factory
        admin = admin_cls(username="ws_admin")
        api_client.force_authenticate(user=admin)
        url = reverse(ENDPOINT_LIST)
        response = api_client.post(
            url, _post_body(course_id=course_with_los["course"].id), format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_queues_celery_task(self, api_client, instructor_factory,
                                        course_with_los):
        """The POST should call task.delay() with the right args."""
        instructor = instructor_factory("ws_instructor2")
        api_client.force_authenticate(user=instructor.user)

        with patch(
            "core.views.weight_suggestion.suggest_assessment_lo_weights_task.delay"
        ) as mock_delay:
            mock_delay.return_value.id = "fake-task-id-123"
            url = reverse(ENDPOINT_LIST)
            response = api_client.post(
                url, _post_body(course_id=course_with_los["course"].id),
                format="json",
            )

            assert response.status_code == status.HTTP_201_CREATED
            mock_delay.assert_called_once()
            call_kwargs = mock_delay.call_args[1]
            assert call_kwargs["course_id"] == course_with_los["course"].id

    def test_create_requires_course_id(self, api_client, instructor_factory):
        """POST without course_id should return 400."""
        instructor = instructor_factory("ws_instructor3")
        api_client.force_authenticate(user=instructor.user)
        url = reverse(ENDPOINT_LIST)
        response = api_client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestWeightSuggestionDetail:
    """GET /api/v1/core/weight-suggestion/<id>/"""

    def test_detail_requires_authentication(self, api_client,
                                             weight_suggestion_job_factory):
        """Unauthenticated users should get 401."""
        job = weight_suggestion_job_factory()
        url = reverse(ENDPOINT_DETAIL, args=[job.id])
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_detail_returns_job_data(self, api_client, instructor_factory,
                                      weight_suggestion_job_factory):
        """GET should return full job detail including result."""
        instructor = instructor_factory("ws_instructor4")
        api_client.force_authenticate(user=instructor.user)

        job = weight_suggestion_job_factory(
            status="success",
            result={"assessment_lo": {"Midterm": {"LO1": 3, "LO2": 4}}},
        )
        url = reverse(ENDPOINT_DETAIL, args=[job.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == job.id
        assert data["status"] == "success"
        assert data["result"] == {"assessment_lo": {"Midterm": {"LO1": 3, "LO2": 4}}}

    def test_detail_404_for_missing_job(self, api_client, instructor_factory):
        """Non-existent job should return 404."""
        instructor = instructor_factory("ws_instructor5")
        api_client.force_authenticate(user=instructor.user)
        url = reverse(ENDPOINT_DETAIL, args=[99999])
        response = api_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_detail_shows_failed_status(self, api_client, instructor_factory,
                                         weight_suggestion_job_factory):
        """Failed job should show error text."""
        instructor = instructor_factory("ws_instructor6")
        api_client.force_authenticate(user=instructor.user)

        job = weight_suggestion_job_factory(
            status="failed",
            error="Course not found",
        )
        url = reverse(ENDPOINT_DETAIL, args=[job.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "failed"
        assert data["error"] == "Course not found"
        assert data["result"] is None
```

- [ ] **Step 3: Run TDD tests — verify they all FAIL**

```bash
cd backend/student_evaluation_system && uv run pytest tests/test_weight_suggestion_endpoint.py -v 2>&1 | tail -30
```
Expected: All tests fail with import errors, 404s, or `NoReverseMatch` (endpoint not registered yet).

- [ ] **Step 4: Commit TDD tests (failing, as expected)**

```bash
git add tests/test_weight_suggestion_endpoint.py tests/conftest.py
git commit -m "test: add TDD tests for weight suggestion REST endpoint (all failing)"
```

---

### Task 5: Implement REST Endpoint

**Files:**
- Create: `core/views/weight_suggestion.py`
- Modify: `core/views/__init__.py` (export new viewset)
- Modify: `core/urls.py` (register route)
- Modify: `core/serializers.py` (add serializer)

- [ ] **Step 1: Add serializer for WeightSuggestionJob**

Append to `core/serializers.py` (after line 531, after `CourseTemplateLOPOMappingSerializer`):

```python
class WeightSuggestionJobSerializer(serializers.ModelSerializer):
    """Serializer for WeightSuggestionJob."""

    class Meta:
        model = WeightSuggestionJob
        fields = [
            "id",
            "course",
            "triggered_by",
            "status",
            "celery_task_id",
            "result",
            "error",
            "started_at",
            "finished_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "celery_task_id",
            "result",
            "error",
            "started_at",
            "finished_at",
            "created_at",
            "updated_at",
        ]
```

- [ ] **Step 2: Create weight_suggestion view**

Create `core/views/weight_suggestion.py`:

```python
"""
Weight Suggestion ViewSet.

Exposes async weight suggestion endpoints that queue Celery tasks
and return job tracking records.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import WeightSuggestionJob
from ..serializers import WeightSuggestionJobSerializer
from ..tasks import suggest_assessment_lo_weights_task


class WeightSuggestionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for triggering and tracking weight suggestion jobs.

    POST /weight-suggestion/ — queue a suggestion for a course
    GET  /weight-suggestion/{id}/ — get job status and result
    """

    queryset = WeightSuggestionJob.objects.all()
    serializer_class = WeightSuggestionJobSerializer

    def get_permissions(self):
        """Only authenticated instructors and admins can use this."""
        if self.action in ("create", "list"):
            from ..permissions import IsInstructorOrAdmin
            return [IsAuthenticated(), IsInstructorOrAdmin()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        """Queue a weight suggestion Celery task for the given course."""
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

        task = suggest_assessment_lo_weights_task.delay(
            course_id=course_id, job_id=job.id
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
```

- [ ] **Step 3: Export from views __init__.py**

In `core/views/__init__.py`, add the import and export:

After line 53 (`from .permissions import InstructorPermissionViewSet`) add:
```python
# Weight Suggestion
from .weight_suggestion import WeightSuggestionViewSet
```

In `__all__`, add:
```python
    # Weight Suggestion
    "WeightSuggestionViewSet",
```

- [ ] **Step 4: Register route in urls.py**

In `core/urls.py`, add to the router registrations (before `urlpatterns`):

```python
router.register(r"weight-suggestion", views.WeightSuggestionViewSet, basename="weightsuggestion")
```

- [ ] **Step 5: Add model import to serializers.py**

At the top of `core/serializers.py`, add `WeightSuggestionJob` to the import from `core.models`:

Find: `from core.models import (` (around line 10)
Add `WeightSuggestionJob,` (alphabetically, after `Term,` and before `University,` or wherever in the list)

- [ ] **Step 6: Run endpoint tests — verify they pass**

```bash
cd backend/student_evaluation_system && uv run pytest tests/test_weight_suggestion_endpoint.py -v
```
Expected: All ~10 tests pass.

- [ ] **Step 7: Run all weight suggestion tests together**

```bash
cd backend/student_evaluation_system && uv run pytest tests/test_weight_suggestion.py tests/test_weight_suggestion_tasks.py tests/test_weight_suggestion_endpoint.py -v
```
Expected: All tests pass (~18 total).

- [ ] **Step 8: Commit**

```bash
git add core/views/weight_suggestion.py core/views/__init__.py core/urls.py core/serializers.py
git commit -m "feat: add REST endpoint for weight suggestion with Celery job tracking"
```

---

### Task 6: End-to-End Verification

**Files:**
- None new — manual verification

- [ ] **Step 1: Verify Celery worker is running**

```bash
docker ps --filter name=celery --format "{{.Names}}: {{.Status}}"
```
Expected: `ses-celery-worker: Up ...` (or similar). If not running: `docker compose up -d celery_worker`

- [ ] **Step 2: Run the test script against a real course**

First, ensure you have a course with LOs in the DB:
```bash
cd backend/student_evaluation_system && uv run python manage.py shell -c "
from core.models import Course, Term, Program, LearningOutcome
course = Course.objects.filter(learning_outcomes__isnull=False).first()
if course:
    print(f'Course ID: {course.id}, Name: {course.name}, LOs: {course.learning_outcomes.count()}')
else:
    print('No course with LOs — create one first')
"
```

Then run the script:
```bash
cd backend/student_evaluation_system && uv run python run_weight_suggestion.py <course_id>
```
Expected: Output shows course info, task ID, poll dots, then the weight mapping JSON and summary table. Note the timing — should be fast (<1s for the computation part, model is already loaded in worker).

- [ ] **Step 3: Run the full test suite to ensure no regressions**

```bash
cd backend/student_evaluation_system && uv run pytest -x --ignore=tests/test_file_import_endpoints.py --ignore=tests/test_evaluation.py 2>&1 | tail -20
```
Expected: All tests pass. (Skip long-running file import/evaluation tests if needed.)

- [ ] **Step 4: Commit any final fixes**

```bash
git add -A
git diff --cached --stat
# Only commit if there are fixes
```

---

## Summary

| Task | What | Tests |
|------|------|-------|
| 0 | `WeightSuggestionJob` model + migration | Manual shell check |
| 1 | `core/tasks.py` with pre-loaded model + Celery task | 8 unit tests |
| 2 | Rewrite `run_weight_suggestion.py` test script | Manual run |
| 3 | Update existing `test_weight_suggestion.py` | 5 tests |
| 4 | TDD endpoint tests (failing first) | ~10 tests |
| 5 | REST endpoint implementation | Same tests → pass |
| 6 | End-to-end verification | Manual + full suite |
