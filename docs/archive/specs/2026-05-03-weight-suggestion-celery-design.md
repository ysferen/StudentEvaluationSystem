# Weight Suggestion Celery Worker — Design Spec

**Date:** 2026-05-03
**Status:** Draft

## Problem

The `WeightSuggester` service loads a SentenceTransformer model on each instantiation (~8s).
Running `run_weight_suggestion.py` creates a fresh Python process each time, paying the load cost every invocation.

## Goal

Move the weight suggestion flow into a Celery worker where the embedding model is pre-loaded once at worker startup.
Subsequent task invocations reuse the loaded model, eliminating the 8s cold-start penalty.

## Scope

- **In:** assessment-to-LO weight suggestion only (LO-to-PO deferred)
- **In:** Celery task + pre-loaded model
- **In:** Test script that calls the task with an arbitrary course from DB
- **In:** Unit tests for the task + TDD tests for the REST endpoint
- **Out:** LO-to-PO suggestions (future work)
- **Out:** Frontend changes


## Architecture

```
                  ┌──────────────────────────────┐
                  │    Celery Worker (Docker)      │
                  │                               │
  test script ──► │  core/tasks.py                 │
  OR              │  ┌───────────────────────────┐ │
  REST endpoint ─► │  │ suggest_assessment_lo...  │ │
                  │  │  - fetch LOs from DB       │ │
                  │  │  - call _suggester         │──┼──► WeightSuggester
                  │  └───────────────────────────┘ │       (pre-loaded model via
                  │                               │        worker_process_init)
                  └──────────────────────────────┘
```

## Components

### 1. Model Pre-loading

**File:** `core/tasks.py` (new, or added to existing)

Module-level variable `_suggester: WeightSuggester | None = None`.

Celery `worker_process_init` signal handler loads the SentenceTransformer model
and creates a `WeightSuggester` instance once per worker process.

```python
from celery.signals import worker_process_init
from sentence_transformers import SentenceTransformer
from core.services.weight_suggestion import WeightSuggester

_suggester = None

@worker_process_init.connect
def _init_weight_suggester(**kwargs):
    global _suggester
    model = SentenceTransformer(os.getenv("SENTENCE_TRANSFORMER_MODEL", "all-MiniLM-L6-v2"))
    _suggester = WeightSuggester(encoder=model)
```

### 2. Celery Task

**File:** `core/tasks.py`

```python
@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True,
             retry_kwargs={"max_retries": 3})
def suggest_assessment_lo_weights_task(self, course_id: int, job_id: int | None = None) -> dict:
    """
    Fetch LOs and assessments for a course, compute weight suggestions.
    """
```

Behavior:
1. If `job_id` given, mark `WeightSuggestionJob` as `running`
2. Fetch course from DB, extract LO descriptions and assessment (name + type) texts
3. Call `_suggester.suggest_assessment_lo(course_name, los, assessments)`
4. If `job_id` given, update job with `result` (JSON) and mark `success`
5. On exception, mark job `failed` with error text, then re-raise for Celery retry

### 3. WeightSuggestionJob Model

**File:** `core/models.py` (new model)

Fields:
| Field | Type | Notes |
|-------|------|-------|
| `course` | FK → Course | The course to suggest weights for |
| `triggered_by` | FK → User | Who initiated the suggestion |
| `status` | CharField | pending / running / success / failed |
| `celery_task_id` | CharField | Celery task UUID |
| `result` | JSONField | The weight mapping dict (null until success) |
| `error` | TextField | Error message if failed |
| `started_at` | DateTimeField | When task began |
| `finished_at` | DateTimeField | When task completed |
| `created_at` / `updated_at` | — | Inherited from `TimeStampedModel` |

### 4. REST Endpoint (TDD now, implementation follows)

**File:** `core/views.py` — new `WeightSuggestionViewSet`

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/core/weight-suggestion/` | Queue a suggestion for a course |
| `GET` | `/api/v1/core/weight-suggestion/{id}/` | Get job status + result |

**POST body:** `{"course_id": <int>}`
**POST response (201):** `{"id": <job_id>, "status": "pending"}`
**GET response (200):** `{"id", "course_id", "status", "result", "error", "created_at", "started_at", "finished_at"}`

Authorization: authenticated users with instructor or program_head role.

### 5. Test Script

**File:** `run_weight_suggestion.py` (rewritten)

- Accepts optional course ID argument
- If no ID, picks the first course with LOs from DB
- Calls `suggest_assessment_lo_weights_task.delay(course_id)`
- Uses hard-coded assessment descriptions from the current script as fallback when no assessments exist in DB
- Polls `AsyncResult.get(timeout=60)` and prints the weight mapping
- Clear error message if Celery worker is unreachable

### 6. Tests

| File | Purpose |
|------|---------|
| `tests/test_weight_suggestion.py` | Keep existing unit tests (schema conformance, similarity ranking with DummyEncoder). Add test verifying `_init_weight_suggester` signal creates the suggester. |
| `tests/test_weight_suggestion_tasks.py` (NEW) | Test `suggest_assessment_lo_weights_task`: mock DB course with LOs, mock `_suggester`, verify correct args passed to `suggest_assessment_lo()`, verify result schema. Test job status transitions. |
| `tests/test_weight_suggestion_endpoint.py` (NEW) | TDD endpoint tests: POST creates job + queues task, GET returns job detail, auth required, 404 for missing job, 403 for wrong role. |

New conftest fixtures:
- `course_with_los_factory` — creates a course with 3 LOs in DB
- `weight_suggestion_job_factory` — creates a `WeightSuggestionJob` record


## Data Flow

```
POST /weight-suggestion/ {"course_id": 42}
  → WeightSuggestionJob.objects.create(status=pending)
  → suggest_assessment_lo_weights_task.delay(course_id=42, job_id=job.pk)
    → Course.objects.get(id=42)
    → course.learning_outcomes.all()
    → course.assessments.all()
    → _suggester.suggest_assessment_lo(course_name, lo_descriptions, assessment_texts)
    → job.result = {...}, job.status = success
  → Client polls GET /weight-suggestion/<job_id>/
```

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Course not found | Task raises, job → `failed`, error = "Course not found" |
| No LOs on course | Return empty mapping (valid result) |
| Model encoding error | Task retries (max 3), then job → `failed` |
| Celery worker unreachable | Script shows clear "Worker unavailable — is Celery running?" |
| Unauthenticated request | 401 |
| Wrong role (student) | 403 |


## Implementation Order

1. Create `WeightSuggestionJob` model + migration
2. Create `core/tasks.py` with model pre-loading + Celery task
3. Rewrite `run_weight_suggestion.py` test script
4. Update existing `test_weight_suggestion.py`
5. Create `test_weight_suggestion_tasks.py` (mock-based, no real model)
6. Create `test_weight_suggestion_endpoint.py` (TDD for REST)
7. Implement REST endpoint (`views.py`, `urls.py`, serializer)

## Dependencies

- SentenceTransformer already installed
- Celery + Redis already configured and running
- Django 5.2, DRF, pytest
- No new packages required
