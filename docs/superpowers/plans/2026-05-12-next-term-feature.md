# Next Term Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Next Term" button allowing admins and program heads to transition the academic term — suspend current term, create a new one, and instantiate courses from selected templates via Celery background task.

**Architecture:** Frontend modal calls `POST /api/core/terms/next-term/`, which creates a `TermTransitionJob`, dispatches a Celery task to clone templates, and streams progress via SSE (see Plan C). The Celery task reuses the existing `clone_course_from_template()` service.

**Tech Stack:** Django REST Framework, Celery, React/TypeScript, React Query, SSE (EventSource), Tailwind

**Pre-requisite:** Plan C (SSE + Audit Logging) must be implemented first for SSE progress streaming and audit tracking of the term transition.

---

## File Structure

| Action | File | Purpose |
|--------|------|---------|
| CREATE | `backend/student_evaluation_system/core/models.py` | `TermTransitionJob` model (append) |
| MODIFY | `backend/student_evaluation_system/core/serializers.py` | `NextTermSerializer` |
| MODIFY | `backend/student_evaluation_system/core/views/academic_structure.py` | `next_term` action on TermViewSet |
| CREATE | `backend/student_evaluation_system/core/tasks/term_transition.py` | Celery task for cloning templates |
| MODIFY | `backend/student_evaluation_system/core/views/__init__.py` | Export new ViewSet additions |
| CREATE | `backend/student_evaluation_system/tests/test_term_transition.py` | Backend tests |
| CREATE | `frontend/src/features/head/components/NextTermModal.tsx` | Modal component |
| MODIFY | `frontend/src/features/courses/pages/HeadCourses.tsx` | Add "Next Term" button |
| CREATE | `frontend/src/features/head/components/__tests__/NextTermModal.test.tsx` | Modal tests |
| CREATE | `frontend/src/features/courses/pages/__tests__/HeadCourses.nextterm.test.tsx` | Integration tests |

---

### Task 1: TermTransitionJob Model

**Files:**
- Modify: `backend/student_evaluation_system/core/models.py` — append TermTransitionJob

- [ ] **Step 1: Add TermTransitionJob model**

```python
# Append to end of backend/student_evaluation_system/core/models.py

class TermTransitionJob(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    old_term = models.ForeignKey(
        Term, on_delete=models.PROTECT, related_name="transitions_from"
    )
    new_term = models.ForeignKey(
        Term, on_delete=models.PROTECT, related_name="transitions_to"
    )
    triggered_by = models.ForeignKey(
        "users.CustomUser", on_delete=models.PROTECT, related_name="term_transitions"
    )
    template_ids = models.JSONField(default=list)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True
    )
    courses_created = models.PositiveIntegerField(default=0)
    celery_task_id = models.CharField(max_length=255, blank=True, null=True)
    error = models.TextField(blank=True, null=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Term Transition Job"
        verbose_name_plural = "Term Transition Jobs"

    def __str__(self):
        return f"TermTransition {self.old_term} -> {self.new_term} ({self.status})"
```

- [ ] **Step 2: Generate and run migration**

Run: `cd backend/student_evaluation_system && uv run python manage.py makemigrations core`
Expected: Creates migration file

Run: `cd backend/student_evaluation_system && uv run python manage.py migrate`
Expected: "Applying core.XXXX_termtransitionjob... OK"

- [ ] **Step 3: Write model test**

```python
# Create: backend/student_evaluation_system/tests/test_term_transition.py

import pytest
from core.models import TermTransitionJob


@pytest.mark.django_db
class TestTermTransitionJobModel:

    def test_create_transition_job(self, active_term, student_user):
        second_term = active_term  # fixture provides active term
        # Create another term to transition to
        from core.models import Term
        new_term = Term.objects.create(name="Spring 2026", semester="spring", academic_year=2026, is_active=False)

        job = TermTransitionJob.objects.create(
            old_term=second_term,
            new_term=new_term,
            triggered_by=student_user,
            template_ids=[1, 2, 3],
            status="pending",
        )
        assert job.id is not None
        assert job.status == "pending"
        assert job.courses_created == 0
        assert job.template_ids == [1, 2, 3]
        assert str(job).startswith("TermTransition")

    def test_job_status_transitions(self, active_term, student_user):
        from core.models import Term
        new_term = Term.objects.create(name="Spring 2026", semester="spring", academic_year=2026, is_active=False)

        job = TermTransitionJob.objects.create(
            old_term=active_term,
            new_term=new_term,
            triggered_by=student_user,
            status="pending",
        )

        job.status = "running"
        job.save()
        job.refresh_from_db()
        assert job.status == "running"

        job.status = "success"
        job.courses_created = 5
        job.save()
        job.refresh_from_db()
        assert job.status == "success"
        assert job.courses_created == 5
```

- [ ] **Step 4: Run model tests**

Run: `cd backend/student_evaluation_system && uv run pytest tests/test_term_transition.py::TestTermTransitionJobModel -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add backend/student_evaluation_system/core/models.py backend/student_evaluation_system/core/migrations/ backend/student_evaluation_system/tests/test_term_transition.py
git commit -m "feat: add TermTransitionJob model"
```

---

### Task 2: NextTermSerializer + View Action

**Files:**
- Modify: `backend/student_evaluation_system/core/serializers.py` — append NextTermSerializer
- Modify: `backend/student_evaluation_system/core/views/academic_structure.py` — add next_term action
- Modify: `backend/student_evaluation_system/tests/test_term_transition.py` — add endpoint tests

- [ ] **Step 1: Write failing serializer test**

```python
# Append to: backend/student_evaluation_system/tests/test_term_transition.py

import json


@pytest.mark.django_db
class TestNextTermEndpoint:

    def test_next_term_requires_auth(self, api_client):
        response = api_client.post("/api/core/terms/next-term/", {}, format="json")
        assert response.status_code == 401

    def test_next_term_creates_new_term(self, authenticated_api_client, active_term, program, course_template):
        """Happy path: transition from active term to new term with one template."""
        data = {
            "semester": "spring",
            "academic_year": 2026,
            "template_ids": [course_template.id],
        }
        response = authenticated_api_client.post("/api/core/terms/next-term/", data, format="json")
        assert response.status_code == 202
        result = response.json()
        assert "job_id" in result
        assert result["new_term_name"] == "Spring 2026"
        assert result["template_count"] == 1

        # Old term should now be inactive
        active_term.refresh_from_db()
        assert active_term.is_active is False

    def test_next_term_rejects_invalid_semester(self, authenticated_api_client, active_term):
        data = {"semester": "winter", "academic_year": 2026, "template_ids": []}
        response = authenticated_api_client.post("/api/core/terms/next-term/", data, format="json")
        assert response.status_code == 400
        assert "semester" in response.json()

    def test_next_term_rejects_negative_academic_year(self, authenticated_api_client, active_term):
        data = {"semester": "fall", "academic_year": -1, "template_ids": []}
        response = authenticated_api_client.post("/api/core/terms/next-term/", data, format="json")
        assert response.status_code == 400

    def test_next_term_empty_templates_succeeds(self, authenticated_api_client, active_term):
        """Transition with no templates is valid (just create new term)."""
        data = {"semester": "spring", "academic_year": 2026, "template_ids": []}
        response = authenticated_api_client.post("/api/core/terms/next-term/", data, format="json")
        assert response.status_code == 202
        assert response.json()["template_count"] == 0

    def test_program_head_can_only_select_own_templates(self, auth_client_program_head, active_term, course_template, program):
        """Program head should not be able to select templates from another program."""
        # Create a template in a different program
        from core.models import Program, CourseTemplate
        other_program = Program.objects.create(name="Other", code="OTH", duration_years=4)
        other_template = CourseTemplate.objects.create(
            name="Other Course", code="OTH101", credits=3, program=other_program
        )

        data = {
            "semester": "spring",
            "academic_year": 2026,
            "template_ids": [other_template.id],
        }
        response = auth_client_program_head.post("/api/core/terms/next-term/", data, format="json")
        assert response.status_code == 400
        assert "template" in str(response.json()).lower()
```

- [ ] **Step 2: Run tests (should fail)**

Run: `cd backend/student_evaluation_system && uv run pytest tests/test_term_transition.py::TestNextTermEndpoint -v`
Expected: All FAIL — view doesn't exist yet

- [ ] **Step 3: Create NextTermSerializer**

```python
# Append to: backend/student_evaluation_system/core/serializers.py

class NextTermSerializer(serializers.Serializer):
    semester = serializers.ChoiceField(choices=["fall", "spring", "summer"])
    academic_year = serializers.IntegerField(min_value=2000, max_value=2100)
    template_ids = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=True, default=list
    )

    def validate_template_ids(self, value):
        if not value:
            return value

        user = self.context["request"].user
        from core.models import CourseTemplate

        if getattr(user, "is_admin_user", False):
            templates = CourseTemplate.objects.filter(id__in=value)
        else:
            profile = getattr(user, "program_head_profile", None)
            if profile is None:
                raise serializers.ValidationError("Unable to determine program access.")
            templates = CourseTemplate.objects.filter(
                id__in=value, program_id=profile.program_id
            )

        found_ids = set(templates.values_list("id", flat=True))
        missing = set(value) - found_ids
        if missing:
            raise serializers.ValidationError(
                f"Invalid or inaccessible template IDs: {sorted(missing)}"
            )
        return value

    def create(self, validated_data):
        from django.db import transaction
        from core.models import Term

        old_term = self.context["old_term"]
        created_by = self.context["created_by"]

        with transaction.atomic():
            old_term.is_active = False
            old_term.save()

            new_term = Term.objects.create(
                semester=validated_data["semester"],
                academic_year=validated_data["academic_year"],
                name=f"{validated_data['semester'].capitalize()} {validated_data['academic_year']}",
                is_active=True,
            )

        return new_term
```

- [ ] **Step 4: Add next_term action to TermViewSet**

Open `backend/student_evaluation_system/core/views/academic_structure.py`. Find the `TermViewSet` class. Add the `next_term` action:

```python
# Add to TermViewSet, after the existing 'active' action
from core.services.audit import log_audit

class TermViewSet(viewsets.ModelViewSet):
    # ... existing code ...

    @action(detail=False, methods=["post"], url_path="next-term")
    def next_term(self, request):
        from core.models import Term, TermTransitionJob
        from core.tasks.term_transition import clone_templates_for_term_task
        from core.serializers import NextTermSerializer

        active_term = Term.objects.filter(is_active=True).first()
        if not active_term:
            return Response(
                {"error": "No active term to transition from."}, status=status.HTTP_400_BAD_REQUEST
            )

        serializer = NextTermSerializer(
            data=request.data,
            context={"request": request, "old_term": active_term, "created_by": request.user},
        )
        serializer.is_valid(raise_exception=True)

        new_term = serializer.save()

        job = TermTransitionJob.objects.create(
            old_term=active_term,
            new_term=new_term,
            triggered_by=request.user,
            template_ids=serializer.validated_data["template_ids"],
            status="pending",
        )

        template_ids = serializer.validated_data["template_ids"]
        if template_ids:
            task = clone_templates_for_term_task.delay(
                template_ids=template_ids,
                term_id=new_term.id,
                job_id=job.id,
            )
            job.celery_task_id = task.id
            job.save(update_fields=["celery_task_id"])

        log_audit(
            request.user,
            "TRANSITION",
            "Term",
            new_term.id,
            before={"id": active_term.id, "name": str(active_term)},
            after={"id": new_term.id, "name": str(new_term)},
            metadata={"template_ids": template_ids},
        )

        return Response(
            {
                "job_id": job.id,
                "old_term_id": active_term.id,
                "new_term_id": new_term.id,
                "new_term_name": str(new_term),
                "template_count": len(template_ids),
                "message": "Term transition started. Courses are being created from templates.",
            },
            status=status.HTTP_202_ACCEPTED,
        )
```

Import `status` from `rest_framework` if not already imported: `from rest_framework import status`.

- [ ] **Step 5: Run endpoint tests (some may still fail — missing Celery task)**

Run: `cd backend/student_evaluation_system && uv run pytest tests/test_term_transition.py::TestNextTermEndpoint -v`
Expected: Tests that don't depend on Celery task execution should pass (auth check, validation, response format). If the Celery task import fails, those tests will also fail.

- [ ] **Step 6: Commit**

```bash
git add backend/student_evaluation_system/core/serializers.py backend/student_evaluation_system/core/views/academic_structure.py backend/student_evaluation_system/tests/test_term_transition.py
git commit -m "feat: add NextTermSerializer and next-term endpoint on TermViewSet"
```

---

### Task 3: Celery Task for Template Cloning

**Files:**
- Create: `backend/student_evaluation_system/core/tasks/__init__.py`
- Create: `backend/student_evaluation_system/core/tasks/term_transition.py`
- Modify: `backend/student_evaluation_system/core/tasks/__init__.py` — ensure imports

- [ ] **Step 1: Create the Celery task**

```python
# Create directory: backend/student_evaluation_system/core/tasks/
# Create: backend/student_evaluation_system/core/tasks/__init__.py (empty)
# Create: backend/student_evaluation_system/core/tasks/term_transition.py

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
```

- [ ] **Step 2: Write Celery task tests**

```python
# Append to: backend/student_evaluation_system/tests/test_term_transition.py

from unittest.mock import patch
from core.models import Term, TermTransitionJob, CourseTemplate


@pytest.mark.django_db
class TestCloneTemplatesTask:

    @patch("core.tasks.term_transition.publish_progress")
    def test_clone_templates_creates_courses(self, mock_publish, active_term, course_template, student_user):
        """Task creates courses from templates and updates job."""
        # Create a job
        from core.models import TermTransitionJob, Term
        new_term = Term.objects.create(
            name="Spring 2026", semester="spring", academic_year=2026, is_active=False
        )
        job = TermTransitionJob.objects.create(
            old_term=active_term,
            new_term=new_term,
            triggered_by=student_user,
            template_ids=[course_template.id],
            status="pending",
        )

        from core.tasks.term_transition import clone_templates_for_term_task

        result = clone_templates_for_term_task(
            template_ids=[course_template.id],
            term_id=new_term.id,
            job_id=job.id,
        )

        assert result["courses_created"] == 1
        job.refresh_from_db()
        assert job.status == "success"
        assert job.courses_created == 1

        # Verify publish_progress was called
        assert mock_publish.called

        # Verify course was created from template
        new_term_courses = new_term.courses.filter(course_template=course_template)
        assert new_term_courses.count() == 1

    @patch("core.tasks.term_transition.publish_progress")
    def test_clone_empty_template_list(self, mock_publish, active_term, student_user):
        """Task with empty template list completes immediately."""
        from core.models import Term, TermTransitionJob
        from core.tasks.term_transition import clone_templates_for_term_task
        new_term = Term.objects.create(
            name="Spring 2026", semester="spring", academic_year=2026, is_active=False
        )
        job = TermTransitionJob.objects.create(
            old_term=active_term,
            new_term=new_term,
            triggered_by=student_user,
            template_ids=[],
            status="pending",
        )

        result = clone_templates_for_term_task(
            template_ids=[], term_id=new_term.id, job_id=job.id
        )

        assert result["courses_created"] == 0
        job.refresh_from_db()
        assert job.status == "success"
```

- [ ] **Step 3: Run task tests**

Run: `cd backend/student_evaluation_system && uv run pytest tests/test_term_transition.py::TestCloneTemplatesTask -v`
Expected: 2 passed

- [ ] **Step 4: Ensure Celery auto-discovers the new task**

Verify `backend/student_evaluation_system/student_evaluation_system/celery.py` has `app.autodiscover_tasks()`. The new task module `core.tasks.term_transition` should be auto-discovered since `core` is an installed app with a `tasks` package. If there's an existing `core/tasks.py` file (singular), you may need to convert it to a package (`core/tasks/__init__.py`).

- [ ] **Step 5: Commit**

```bash
git add backend/student_evaluation_system/core/tasks/ backend/student_evaluation_system/tests/test_term_transition.py
git commit -m "feat: add Celery task for cloning course templates during term transition"
```

---

### Task 4: NextTermModal Frontend Component

**Files:**
- Create: `frontend/src/features/head/components/NextTermModal.tsx`
- Create: `frontend/src/features/head/components/__tests__/NextTermModal.test.tsx`

- [ ] **Step 1: Write failing tests for modal**

```typescript
// Create: frontend/src/features/head/components/__tests__/NextTermModal.test.tsx

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { NextTermModal } from '../NextTermModal'

// Mock API hooks
vi.mock('@/shared/api/generated/core/core', () => ({
  useCoreTermsActiveRetrieve: () => ({ data: { id: 1, name: 'Fall 2025', semester: 'fall', academic_year: 2025 } }),
  useCoreCourseTemplatesList: () => ({
    data: {
      results: [
        { id: 1, code: 'MAT101', name: 'Calculus I', credits: 4 },
        { id: 2, code: 'PHY101', name: 'Physics I', credits: 3 },
      ],
    },
  }),
  coreTermsNextTermCreate: vi.fn(),
}))

// Mock JobProgressBar
vi.mock('@/shared/components/JobProgressBar', () => ({
  JobProgressBar: ({ jobId, onComplete }: any) => (
    <div data-testid="progress-bar">{jobId ? `Job ${jobId}` : 'No job'}</div>
  ),
}))

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

describe('NextTermModal', () => {
  const onClose = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders nothing when isOpen is false', () => {
    const { container } = renderWithProviders(
      <NextTermModal isOpen={false} onClose={onClose} />
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders modal when isOpen is true', async () => {
    renderWithProviders(<NextTermModal isOpen={true} onClose={onClose} />)
    await waitFor(() => {
      expect(screen.getByText('Start New Term')).toBeDefined()
    })
  })

  it('shows auto-calculated next semester (Fall -> Spring)', async () => {
    renderWithProviders(<NextTermModal isOpen={true} onClose={onClose} />)
    await waitFor(() => {
      // The semester dropdown should contain 'Spring' selected
      const select = screen.getByRole('combobox', { name: /semester/i }) as HTMLSelectElement
      expect(select).toBeDefined()
    })
  })

  it('shows course templates loaded from API', async () => {
    renderWithProviders(<NextTermModal isOpen={true} onClose={onClose} />)
    await waitFor(() => {
      expect(screen.getByText('MAT101')).toBeDefined()
      expect(screen.getByText('PHY101')).toBeDefined()
    })
  })

  it('calls onClose when cancel is clicked', async () => {
    const user = userEvent.setup()
    renderWithProviders(<NextTermModal isOpen={true} onClose={onClose} />)

    await waitFor(() => {
      expect(screen.getByText('Cancel')).toBeDefined()
    })

    await user.click(screen.getByText('Cancel'))
    expect(onClose).toHaveBeenCalled()
  })

  it('calls API and shows progress bar on submit', async () => {
    const { coreTermsNextTermCreate } = await import('@/shared/api/generated/core/core')
    vi.mocked(coreTermsNextTermCreate).mockResolvedValue({
      job_id: 42,
      new_term_id: 2,
      new_term_name: 'Spring 2026',
      template_count: 2,
      message: 'Term transition started.',
    })

    const user = userEvent.setup()
    renderWithProviders(<NextTermModal isOpen={true} onClose={onClose} />)

    await waitFor(() => {
      expect(screen.getByText('Start New Term')).toBeDefined()
    })

    // Select all templates
    const checkboxes = screen.getAllByRole('checkbox')
    for (const cb of checkboxes) {
      await user.click(cb)
    }

    // Click the submit button
    const submitBtn = screen.getByRole('button', { name: /start new term/i })
    await user.click(submitBtn)

    await waitFor(() => {
      expect(coreTermsNextTermCreate).toHaveBeenCalledWith({
        semester: 'spring',
        academic_year: 2025,
        template_ids: [1, 2],
      })
    })

    // After submission, progress bar should appear
    await waitFor(() => {
      expect(screen.getByTestId('progress-bar')).toBeDefined()
    })
  })
})
```

- [ ] **Step 2: Run test (should fail)**

Run: `cd frontend && npx vitest run src/features/head/components/__tests__/NextTermModal.test.tsx`
Expected: FAIL — component doesn't exist

- [ ] **Step 3: Create NextTermModal component**

```tsx
// Create: frontend/src/features/head/components/NextTermModal.tsx

import React, { useState, useMemo } from 'react'
import { X } from 'lucide-react'
import { useCoreCourseTemplatesList, useCoreTermsActiveRetrieve, coreTermsNextTermCreate } from '@/shared/api/generated/core/core'
import { JobProgressBar } from '@/shared/components/JobProgressBar'

interface NextTermModalProps {
  isOpen: boolean
  onClose: () => void
}

const SEMESTER_CYCLE: Record<string, string> = {
  fall: 'spring',
  spring: 'fall',
  summer: 'fall', // manual, but if summer is selected, next defaults to fall
}

export const NextTermModal: React.FC<NextTermModalProps> = ({ isOpen, onClose }) => {
  const { data: activeTerm } = useCoreTermsActiveRetrieve()
  const { data: templatesData } = useCoreCourseTemplatesList()

  const [semester, setSemester] = useState('fall')
  const [academicYear, setAcademicYear] = useState(new Date().getFullYear())
  const [selectedTemplates, setSelectedTemplates] = useState<Set<number>>(new Set())
  const [jobId, setJobId] = useState<number | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const templates = (templatesData as any)?.results ?? (templatesData as any) ?? []

  // Auto-calculate next semester when modal opens
  useMemo(() => {
    if (activeTerm && isOpen) {
      const nextSem = SEMESTER_CYCLE[activeTerm.semester ?? 'fall'] ?? 'fall'
      setSemester(nextSem)
      const year = nextSem === 'spring' ? (activeTerm.academic_year ?? 2025) : (activeTerm.academic_year ?? 2025) + 1
      setAcademicYear(year)
    }
  }, [activeTerm, isOpen])

  const toggleTemplate = (id: number) => {
    setSelectedTemplates((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const selectAll = () => {
    if (Array.isArray(templates)) {
      setSelectedTemplates(new Set(templates.map((t: any) => t.id)))
    }
  }

  const deselectAll = () => {
    setSelectedTemplates(new Set())
  }

  const handleSubmit = async () => {
    setSubmitting(true)
    setError(null)
    try {
      const result = await coreTermsNextTermCreate({
        semester,
        academic_year: academicYear,
        template_ids: Array.from(selectedTemplates),
      })
      setJobId((result as any).job_id ?? null)
    } catch (err: any) {
      setError(err?.message ?? 'Failed to start term transition.')
      setSubmitting(false)
    }
  }

  const handleComplete = () => {
    onClose()
    window.location.reload()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black bg-opacity-50" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-secondary-200">
          <h2 className="text-xl font-bold text-secondary-900">Start New Term</h2>
          <button onClick={onClose} className="text-secondary-400 hover:text-secondary-600 transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {activeTerm && (
            <p className="text-sm text-secondary-500">
              Current active term: <span className="font-medium text-secondary-700">{activeTerm.name}</span>
            </p>
          )}

          {/* Semester */}
          <div>
            <label htmlFor="semester" className="block text-sm font-medium text-secondary-700 mb-2">
              Semester
            </label>
            <select
              id="semester"
              value={semester}
              onChange={(e) => setSemester(e.target.value)}
              className="block w-full rounded-xl border border-secondary-300 px-4 py-2.5 text-sm text-secondary-900 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 transition"
              aria-label="Semester"
            >
              <option value="fall">Fall</option>
              <option value="spring">Spring</option>
              <option value="summer">Summer</option>
            </select>
          </div>

          {/* Academic Year */}
          <div>
            <label htmlFor="academicYear" className="block text-sm font-medium text-secondary-700 mb-2">
              Academic Year
            </label>
            <input
              id="academicYear"
              type="number"
              value={academicYear}
              onChange={(e) => setAcademicYear(Number(e.target.value))}
              min={2000}
              max={2100}
              className="block w-full rounded-xl border border-secondary-300 px-4 py-2.5 text-sm text-secondary-900 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 transition"
            />
          </div>

          {/* Template Selection */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-secondary-700">
                Select Course Templates to Instantiate
              </label>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={selectAll}
                  className="text-xs text-primary-600 hover:text-primary-700 font-medium"
                >
                  Select All
                </button>
                <button
                  type="button"
                  onClick={deselectAll}
                  className="text-xs text-secondary-500 hover:text-secondary-600 font-medium"
                >
                  Deselect All
                </button>
              </div>
            </div>
            <div className="border border-secondary-200 rounded-xl divide-y divide-secondary-100 max-h-48 overflow-y-auto">
              {Array.isArray(templates) && templates.map((template: any) => (
                <label
                  key={template.id}
                  className="flex items-center gap-3 px-4 py-2.5 cursor-pointer hover:bg-secondary-50"
                >
                  <input
                    type="checkbox"
                    checked={selectedTemplates.has(template.id)}
                    onChange={() => toggleTemplate(template.id)}
                    className="h-4 w-4 rounded border-secondary-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-secondary-900 font-medium">{template.code}</span>
                  <span className="text-sm text-secondary-500">{template.name}</span>
                  <span className="text-xs text-secondary-400 ml-auto">{template.credits}cr</span>
                </label>
              ))}
              {(!Array.isArray(templates) || templates.length === 0) && (
                <p className="px-4 py-3 text-sm text-secondary-400">No course templates available.</p>
              )}
            </div>
          </div>

          {/* Progress Bar (shown after submission) */}
          {jobId && (
            <JobProgressBar
              jobId={jobId}
              onComplete={handleComplete}
              label="Creating courses..."
            />
          )}

          {/* Error */}
          {error && (
            <div className="bg-danger-50 border border-danger-200 rounded-xl p-4">
              <p className="text-danger-800 text-sm">{error}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        {!jobId && (
          <div className="flex items-center justify-end gap-3 p-6 border-t border-secondary-200">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-secondary-600 hover:text-secondary-900 transition-colors"
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="flex items-center gap-2 px-6 py-2.5 bg-primary-600 text-white text-sm font-semibold rounded-xl shadow-lg hover:bg-primary-700 hover:shadow-xl hover:-translate-y-0.5 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Start New Term"
            >
              {submitting ? 'Starting...' : 'Start New Term'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run tests (should pass now)**

Run: `cd frontend && npx vitest run src/features/head/components/__tests__/NextTermModal.test.tsx`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/head/components/NextTermModal.tsx frontend/src/features/head/components/__tests__/NextTermModal.test.tsx
git commit -m "feat: add NextTermModal with template selection and progress streaming"
```

---

### Task 5: Wire "Next Term" Button into HeadCourses

**Files:**
- Modify: `frontend/src/features/courses/pages/HeadCourses.tsx` — add button + modal state

- [ ] **Step 1: Read current HeadCourses.tsx**

Read the file to locate where to add the button. The button should appear near the header/toolbar area, visible when an active term exists.

- [ ] **Step 2: Add button and modal integration**

```tsx
// In HeadCourses.tsx, add:
import { useState } from 'react'
import { ArrowRight } from 'lucide-react'
import { NextTermModal } from '@/features/head/components/NextTermModal'
import { useCoreTermsActiveRetrieve } from '@/shared/api/generated/core/core'

// Inside the component:
const [isNextTermModalOpen, setIsNextTermModalOpen] = useState(false)
const { data: activeTerm } = useCoreTermsActiveRetrieve()

// In the JSX, add near the page header (alongside other action buttons):
{activeTerm && (
  <button
    onClick={() => setIsNextTermModalOpen(true)}
    className="flex items-center gap-2 px-4 py-2 bg-violet-600 text-white text-sm font-semibold rounded-xl shadow-lg hover:bg-violet-700 hover:shadow-xl hover:-translate-y-0.5 transition-all duration-200"
  >
    <ArrowRight className="h-4 w-4" />
    Next Term
  </button>
)}

// Near the end of the JSX (before closing tag):
<NextTermModal
  isOpen={isNextTermModalOpen}
  onClose={() => setIsNextTermModalOpen(false)}
/>
```

Use violet-600 (instructor/admin accent) for the button to be consistent with the design system.

- [ ] **Step 3: Verify TypeScript compilation**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors in HeadCourses.tsx

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/courses/pages/HeadCourses.tsx
git commit -m "feat: wire Next Term button into HeadCourses page"
```

---

### Task 6: Final Integration

**Files:** None — verification only

- [ ] **Step 1: Run all backend tests**

Run: `cd backend/student_evaluation_system && uv run pytest -v`
Expected: All pass

- [ ] **Step 2: Run all frontend tests**

Run: `cd frontend && npx vitest run`
Expected: All pass

- [ ] **Step 3: Backend lint**

Run: `cd backend/student_evaluation_system && uv run ruff check .`
Expected: No errors

- [ ] **Step 4: Frontend lint + build**

Run: `cd frontend && npm run lint`
Expected: No errors

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 5: Commit**

```bash
git add -A
git diff --cached --stat
git commit -m "chore: final integration verification for Next Term feature"
```
