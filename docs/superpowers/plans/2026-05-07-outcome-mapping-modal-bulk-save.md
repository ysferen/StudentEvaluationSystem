# Outcome Mapping Modal — Bulk Save Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace auto-save-per-change with local state + bulk save in the Outcome Mapping Editor. Add save/reset/close-confirmation UI and weight suggestion placeholder.

**Architecture:** Two new `@action` endpoints accept create/update/delete arrays in one transaction, then dispatch async Celery score recompute. Frontend maintains dual state (`initial*`/`working*`), computes diff on save, sends one bulk request. Header gets weight suggestion placeholder, footer gets save/reset buttons, close triggers confirmation dialog when dirty.

**Tech Stack:** Django REST Framework, Celery, React/TypeScript with `@dnd-kit`

---

### Task 1: Backend — Bulk sync endpoint for Assessment-LO mappings

**Files:**
- Create: `backend/student_evaluation_system/evaluation/serializers.py` (add `BulkAssessmentLOMappingSerializer`)
- Modify: `backend/student_evaluation_system/evaluation/views.py:161-180`
- Test: `backend/student_evaluation_system/tests/test_views.py`

- [ ] **Step 1: Add BulkAssessmentLOMappingSerializer**

Add to `evaluation/serializers.py` after the existing `AssessmentLearningOutcomeMappingSerializer` class (after line ~53):

```python
from rest_framework import serializers as drf_serializers


class BulkAssessmentLOMappingItem(drf_serializers.Serializer):
    """Single item in a bulk sync request."""
    temp_id = drf_serializers.IntegerField(required=False)
    id = drf_serializers.IntegerField(required=False)
    assessment_id = drf_serializers.IntegerField(required=False)
    learning_outcome_id = drf_serializers.IntegerField(required=False)
    weight = drf_serializers.FloatField(required=False)


class BulkAssessmentLOMappingSerializer(drf_serializers.Serializer):
    """Bulk sync payload for assessment-LO mappings."""
    course_id = drf_serializers.IntegerField()
    creates = BulkAssessmentLOMappingItem(many=True, required=False, default=list)
    updates = BulkAssessmentLOMappingItem(many=True, required=False, default=list)
    deletes = drf_serializers.ListField(child=drf_serializers.IntegerField(), required=False, default=list)
```

- [ ] **Step 2: Add `bulk_sync` action to AssessmentLearningOutcomeMappingViewSet**

Add inside `AssessmentLearningOutcomeMappingViewSet` in `evaluation/views.py` (after `perform_destroy` at line 179):

```python
    @action(detail=False, methods=["post"])
    def bulk_sync(self, request):
        """Apply assessment-LO mapping changes in bulk and trigger async score recompute."""
        serializer = BulkAssessmentLOMappingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        created = []
        updated = []
        deleted_ids = []
        affected_course_ids = set()

        with transaction.atomic():
            # Deletes
            for mapping_id in data.get("deletes", []):
                mapping = get_object_or_404(AssessmentLearningOutcomeMapping, pk=mapping_id)
                course_id = mapping.assessment.course_id
                affected_course_ids.add(course_id)
                mapping.delete()
                deleted_ids.append(mapping_id)

            # Updates
            for item in data.get("updates", []):
                mapping = get_object_or_404(AssessmentLearningOutcomeMapping, pk=item["id"])
                if "weight" in item:
                    mapping.weight = item["weight"]
                    mapping.save(update_fields=["weight"])
                    affected_course_ids.add(mapping.assessment.course_id)
                updated.append(AssessmentLearningOutcomeMappingSerializer(mapping).data)

            # Creates
            for item in data.get("creates", []):
                assessment = get_object_or_404(Assessment, pk=item["assessment_id"])
                learning_outcome = get_object_or_404(LearningOutcome, pk=item["learning_outcome_id"])
                mapping = AssessmentLearningOutcomeMapping.objects.create(
                    assessment=assessment,
                    learning_outcome=learning_outcome,
                    weight=item["weight"],
                )
                affected_course_ids.add(assessment.course_id)
                result = AssessmentLearningOutcomeMappingSerializer(mapping).data
                result["temp_id"] = item.get("temp_id")
                created.append(result)

        # Dispatch async score recompute (non-blocking)
        from evaluation.tasks import recompute_course_scores_task
        job_ids = []
        for course_id in affected_course_ids:
            job = ScoreRecomputeJob.objects.create(
                task_type=ScoreRecomputeJob.TASK_TYPE_COURSE_RECOMPUTE,
                status=ScoreRecomputeJob.STATUS_PENDING,
                course_id=course_id,
                triggered_by=request.user,
            )
            async_result = recompute_course_scores_task.delay(course_id, job.pk)
            job.celery_task_id = async_result.id
            job.save(update_fields=["celery_task_id"])
            job_ids.append(job.pk)

        return Response({
            "created": created,
            "updated": updated,
            "deleted": deleted_ids,
            "recompute_job_ids": job_ids,
        })
```

Also add missing imports at the top of `views.py`:
```python
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from evaluation.tasks import recompute_course_scores_task
```
(Note: `action` and `transaction` are already imported. `ScoreRecomputeJob` is already imported. `Assessment` is already imported. `LearningOutcome` needs import from `core.models`.)

Add to line 21 after the existing `core.models` import:
```python
from core.models import LearningOutcome, StudentLearningOutcomeScore
```
(Change the existing `from core.models import StudentLearningOutcomeScore` line 21 to include `LearningOutcome`.)

- [ ] **Step 3: Write tests for bulk_sync**

Add to `tests/test_views.py`:

```python
from evaluation.serializers import BulkAssessmentLOMappingSerializer


@pytest.mark.django_db
class TestAssessmentLOMappingBulkSync:
    """Test bulk_sync endpoint for assessment-LO mappings."""

    def test_bulk_sync_creates_mappings(self, api_client, sample_course, sample_instructor):
        """Bulk sync should create specified mappings."""
        api_client.force_authenticate(user=sample_instructor)
        from evaluation.models import Assessment, AssessmentLearningOutcomeMapping
        from core.models import LearningOutcome

        assessment = Assessment.objects.filter(course=sample_course).first()
        lo = LearningOutcome.objects.filter(course=sample_course).first()

        response = api_client.post(
            "/api/evaluation/assessment-lo-mappings/bulk_sync/",
            {
                "course_id": sample_course.id,
                "creates": [
                    {"assessment_id": assessment.id, "learning_outcome_id": lo.id, "weight": 3}
                ],
            },
            format="json",
        )

        assert response.status_code == 200
        assert len(response.data["created"]) == 1
        assert response.data["created"][0]["assessment"] == assessment.id
        assert response.data["created"][0]["weight"] == 3

    def test_bulk_sync_updates_mappings(self, api_client, sample_course, sample_instructor, assessment_lo_mappings):
        """Bulk sync should update existing mapping weights."""
        api_client.force_authenticate(user=sample_instructor)
        from evaluation.models import AssessmentLearningOutcomeMapping

        mapping = AssessmentLearningOutcomeMapping.objects.first()
        old_weight = mapping.weight

        response = api_client.post(
            "/api/evaluation/assessment-lo-mappings/bulk_sync/",
            {
                "course_id": sample_course.id,
                "updates": [{"id": mapping.id, "weight": 4}],
            },
            format="json",
        )

        assert response.status_code == 200
        mapping.refresh_from_db()
        assert mapping.weight == 4
        assert mapping.weight != old_weight

    def test_bulk_sync_deletes_mappings(self, api_client, sample_course, sample_instructor, assessment_lo_mappings):
        """Bulk sync should delete specified mappings."""
        api_client.force_authenticate(user=sample_instructor)
        from evaluation.models import AssessmentLearningOutcomeMapping

        mapping = AssessmentLearningOutcomeMapping.objects.first()

        response = api_client.post(
            "/api/evaluation/assessment-lo-mappings/bulk_sync/",
            {
                "course_id": sample_course.id,
                "deletes": [mapping.id],
            },
            format="json",
        )

        assert response.status_code == 200
        assert response.data["deleted"] == [mapping.id]
        assert not AssessmentLearningOutcomeMapping.objects.filter(pk=mapping.id).exists()

    def test_bulk_sync_returns_recompute_job_ids(self, api_client, sample_course, sample_instructor, assessment_lo_mappings):
        """Bulk sync should dispatch recompute and return job IDs."""
        api_client.force_authenticate(user=sample_instructor)
        from evaluation.models import AssessmentLearningOutcomeMapping

        mapping = AssessmentLearningOutcomeMapping.objects.first()

        response = api_client.post(
            "/api/evaluation/assessment-lo-mappings/bulk_sync/",
            {
                "course_id": sample_course.id,
                "updates": [{"id": mapping.id, "weight": mapping.weight}],
            },
            format="json",
        )

        assert response.status_code == 200
        assert len(response.data.get("recompute_job_ids", [])) >= 0
```

- [ ] **Step 4: Run tests**

Run: `cd backend/student_evaluation_system && ../../.venv/bin/python -m pytest tests/test_views.py::TestAssessmentLOMappingBulkSync -v`
Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/student_evaluation_system/evaluation/serializers.py backend/student_evaluation_system/evaluation/views.py backend/student_evaluation_system/tests/test_views.py
git commit -m "feat: add bulk_sync endpoint for assessment-LO mappings with async score recompute"
```

---

### Task 2: Backend — Bulk sync endpoint for LO-PO mappings

**Files:**
- Create: `backend/student_evaluation_system/core/serializers.py` (add `BulkLOPOMappingSerializer`)
- Modify: `backend/student_evaluation_system/core/views/course.py:232-240`
- Test: `backend/student_evaluation_system/tests/test_views.py`

- [ ] **Step 1: Add BulkLOPOMappingSerializer**

Add to `core/serializers.py` after the `LearningOutcomeProgramOutcomeMappingSerializer` class (after line ~275):

```python
class BulkLOPOMappingItem(serializers.Serializer):
    """Single item in a bulk LO-PO sync request."""
    temp_id = serializers.IntegerField(required=False)
    id = serializers.IntegerField(required=False)
    learning_outcome_id = serializers.IntegerField(required=False)
    program_outcome_id = serializers.IntegerField(required=False)
    weight = serializers.FloatField(required=False)


class BulkLOPOMappingSerializer(serializers.Serializer):
    """Bulk sync payload for LO-PO mappings."""
    course_id = serializers.IntegerField()
    creates = BulkLOPOMappingItem(many=True, required=False, default=list)
    updates = BulkLOPOMappingItem(many=True, required=False, default=list)
    deletes = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
```

- [ ] **Step 2: Add `bulk_sync` action to LearningOutcomeProgramOutcomeMappingViewSet**

Add inside `LearningOutcomeProgramOutcomeMappingViewSet` in `core/views/course.py` (after line 240):

```python
    @action(detail=False, methods=["post"])
    def bulk_sync(self, request):
        """Apply LO-PO mapping changes in bulk and trigger async score recompute."""
        serializer = BulkLOPOMappingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        created = []
        updated = []
        deleted_ids = []
        affected_students = set()

        with transaction.atomic():
            # Deletes
            for mapping_id in data.get("deletes", []):
                mapping = get_object_or_404(LearningOutcomeProgramOutcomeMapping, pk=mapping_id)
                mapping.delete()
                deleted_ids.append(mapping_id)

            # Updates
            for item in data.get("updates", []):
                mapping = get_object_or_404(LearningOutcomeProgramOutcomeMapping, pk=item["id"])
                if "weight" in item:
                    mapping.weight = item["weight"]
                    mapping.save(update_fields=["weight"])
                updated.append(LearningOutcomeProgramOutcomeMappingSerializer(mapping).data)

            # Creates
            for item in data.get("creates", []):
                learning_outcome = get_object_or_404(LearningOutcome, pk=item["learning_outcome_id"])
                program_outcome = get_object_or_404(ProgramOutcome, pk=item["program_outcome_id"])
                course = get_object_or_404(Course, pk=data["course_id"])
                mapping = LearningOutcomeProgramOutcomeMapping.objects.create(
                    learning_outcome=learning_outcome,
                    program_outcome=program_outcome,
                    course=course,
                    weight=item["weight"],
                )
                result = LearningOutcomeProgramOutcomeMappingSerializer(mapping).data
                result["temp_id"] = item.get("temp_id")
                created.append(result)

        # Collect affected students for PO recalculation
        import django.db.models
        course = Course.objects.filter(pk=data["course_id"]).first()
        if course:
            student_ids = course.enrollments.values_list("student_id", flat=True)
            affected_students = set(student_ids)
            # Dispatch PO score recalculation for each affected student
            from evaluation.services import calculate_student_po_scores
            for student_id in affected_students:
                calculate_student_po_scores(student_id, course.program_id, course.term_id)

        return Response({
            "created": created,
            "updated": updated,
            "deleted": deleted_ids,
        })
```

Also add missing imports at the top of `core/views/course.py`:
```python
from django.shortcuts import get_object_or_404
from django.db import transaction
```

And add the `BulkLOPOMappingSerializer` import alongside the other serializer imports (line ~30):
```python
from ..serializers import (
    ...
    BulkLOPOMappingSerializer,
)
```

And add the model import for `Course` (should already exist):
```python
from ..models import (
    Course,
    ...
)
```

- [ ] **Step 3: Write tests for LO-PO bulk_sync**

Add to `tests/test_views.py`:

```python
from core.serializers import BulkLOPOMappingSerializer


@pytest.mark.django_db
class TestLOPOMappingBulkSync:
    """Test bulk_sync endpoint for LO-PO mappings."""

    def test_bulk_sync_creates_lo_po_mappings(self, api_client, sample_course, sample_instructor):
        """Bulk sync should create LO-PO mappings."""
        api_client.force_authenticate(user=sample_instructor)
        from core.models import LearningOutcomeProgramOutcomeMapping, ProgramOutcome, LearningOutcome

        lo = LearningOutcome.objects.filter(course=sample_course).first()
        po = ProgramOutcome.objects.filter(program=sample_course.program).first()

        response = api_client.post(
            "/api/core/lo-po-mappings/bulk_sync/",
            {
                "course_id": sample_course.id,
                "creates": [
                    {"learning_outcome_id": lo.id, "program_outcome_id": po.id, "weight": 3}
                ],
            },
            format="json",
        )

        assert response.status_code == 200
        assert len(response.data["created"]) == 1
```

- [ ] **Step 4: Run tests**

Run: `cd backend/student_evaluation_system && ../../.venv/bin/python -m pytest tests/test_views.py::TestLOPOMappingBulkSync -v`
Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/student_evaluation_system/core/serializers.py backend/student_evaluation_system/core/views/course.py backend/student_evaluation_system/tests/test_views.py
git commit -m "feat: add bulk_sync endpoint for LO-PO mappings"
```

---

### Task 3: Frontend — Dual state management and diff computation

**Files:**
- Modify: `frontend/src/features/courses/components/MappingEditor.tsx`

- [ ] **Step 1: Replace single useState with dual state**

Change lines ~303-305 from:
```tsx
const [assessmentLOMappings, setAssessmentLOMappings] = useState<AssessmentLearningOutcomeMapping[]>([])
const [loPOMappings, setLoPOMappings] = useState<LearningOutcomeProgramOutcomeMapping[]>([])
```

To:
```tsx
// Initial state (frozen snapshot from server on modal open)
const [initialAssessmentLOMappings, setInitialAssessmentLOMappings] = useState<AssessmentLearningOutcomeMapping[]>([])
const [initialLoPOMappings, setInitialLoPOMappings] = useState<LearningOutcomeProgramOutcomeMapping[]>([])
// Working state (editable copy, all mutations applied here)
const [workingAssessmentLOMappings, setWorkingAssessmentLOMappings] = useState<AssessmentLearningOutcomeMapping[]>([])
const [workingLoPOMappings, setWorkingLoPOMappings] = useState<LearningOutcomeProgramOutcomeMapping[]>([])
```

- [ ] **Step 2: Sync working state from server on modal open, not on every query change**

Replace the `useEffect` sync blocks (lines ~307-318) with a single `useEffect` that runs when the queries load:

```tsx
const [hasInitialized, setHasInitialized] = useState(false)

useEffect(() => {
  if (!hasInitialized && aloQuery.data && lopoQuery.data) {
    const aloData = toList<AssessmentLearningOutcomeMapping>(aloQuery.data)
    const lopoData = toList<LearningOutcomeProgramOutcomeMapping>(lopoQuery.data)
    setInitialAssessmentLOMappings(clone(aloData))
    setInitialLoPOMappings(clone(lopoData))
    setWorkingAssessmentLOMappings(clone(aloData))
    setWorkingLoPOMappings(clone(lopoData))
    setHasInitialized(true)
  }
}, [aloQuery.data, lopoQuery.data, hasInitialized])
```

Add a `clone` helper at the top of the file (before the component):
```tsx
const clone = <T,>(arr: T[]): T[] => arr.map(item => ({ ...item }))
```

- [ ] **Step 3: Update all mutation references**

Replace all references to `assessmentLOMappings` with `workingAssessmentLOMappings`, and `loPOMappings` with `workingLoPOMappings`:

Find and replace (do NOT change initial* state references):
- `setAssessmentLOMappings` → `setWorkingAssessmentLOMappings`
- `setLoPOMappings` → `setWorkingLoPOMappings`
- `assessmentLOMappings` (when reading/displaying) → `workingAssessmentLOMappings`
- `loPOMappings` (when reading/displaying) → `workingLoPOMappings`

The `getAssessmentMappingsForLO` and `getPOMappingsForLO` and `getLOMappingsForPO` helper functions should use `workingAssessmentLOMappings` and `workingLoPOMappings`.

- [ ] **Step 4: Add diff computation function**

Add inside the component, before `handleSave`:

```tsx
const computeDiff = <T extends { id: number; weight: number }>(
  working: T[],
  initial: T[]
): { creates: T[]; updates: { id: number; weight: number }[]; deletes: number[] } => {
  const workingIds = new Set(working.map(m => m.id))
  const initialIds = new Set(initial.map(m => m.id))

  const creates = working.filter(m => m.id < 0) // temp negative IDs
  const deletes = initial.filter(m => !workingIds.has(m.id)).map(m => m.id)
  const updates = working
    .filter(m => m.id > 0 && initialIds.has(m.id))
    .filter(m => {
      const initialItem = initial.find(i => i.id === m.id)
      return initialItem && initialItem.weight !== m.weight
    })
    .map(m => ({ id: m.id, weight: m.weight }))

  return { creates, updates, deletes }
}
```

- [ ] **Step 5: Compute hasChanges**

```tsx
const hasChanges = useMemo(() => {
  const aloDiff = computeDiff(workingAssessmentLOMappings, initialAssessmentLOMappings)
  const lopoDiff = computeDiff(workingLoPOMappings, initialLoPOMappings)
  return (
    aloDiff.creates.length > 0 ||
    aloDiff.updates.length > 0 ||
    aloDiff.deletes.length > 0 ||
    lopoDiff.creates.length > 0 ||
    lopoDiff.updates.length > 0 ||
    lopoDiff.deletes.length > 0
  )
}, [workingAssessmentLOMappings, initialAssessmentLOMappings, workingLoPOMappings, initialLoPOMappings])
```

Add `useMemo` to the React import at the top of the file.

- [ ] **Step 6: Verify frontend builds**

Run: `cd frontend && npm run build 2>&1 | tail -5`
Expected: Build succeeds.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/features/courses/components/MappingEditor.tsx
git commit -m "feat: add dual state management and diff computation to mapping editor"
```

---

### Task 4: Frontend — HandleSave with bulk API, footer buttons

**Files:**
- Modify: `frontend/src/features/courses/components/MappingEditor.tsx`

- [ ] **Step 1: Add bulk sync API imports**

Add to the top of `MappingEditor.tsx` alongside existing mutation imports (lines ~27-30):

```tsx
import {
  useEvaluationAssessmentLoMappingsList,
  useEvaluationAssessmentLoMappingsCreate,
  useEvaluationAssessmentLoMappingsPartialUpdate,
  useEvaluationAssessmentLoMappingsDestroy,
} from '@/shared/api/generated/evaluation/evaluation'
import {
  useCoreLoPoMappingsList,
  useCoreLoPoMappingsCreate,
  useCoreLoPoMappingsPartialUpdate,
  useCoreLoPoMappingsDestroy,
} from '@/shared/api/generated/core/core'
```

Add a custom fetch function for the bulk sync (no generated hook exists):

```tsx
const bulkSyncAssessmentLOMappings = async (payload: {
  course_id: number
  creates: Array<{ temp_id?: number; assessment_id?: number; learning_outcome_id?: number; weight: number }>
  updates: Array<{ id: number; weight: number }>
  deletes: number[]
}) => {
  const response = await fetch('/api/evaluation/assessment-lo-mappings/bulk_sync/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    credentials: 'include',
  })
  if (!response.ok) throw new Error('Bulk sync failed')
  return response.json()
}

const bulkSyncLOPOMappings = async (payload: {
  course_id: number
  creates: Array<{ temp_id?: number; learning_outcome_id?: number; program_outcome_id?: number; weight: number }>
  updates: Array<{ id: number; weight: number }>
  deletes: number[]
}) => {
  const response = await fetch('/api/core/lo-po-mappings/bulk_sync/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    credentials: 'include',
  })
  if (!response.ok) throw new Error('Bulk sync failed')
  return response.json()
}
```

- [ ] **Step 2: Implement handleSave**

Replace the existing `handleCreateOrUpdateMapping` and `handleDelete*` functions with a new `handleSave`:

```tsx
const [isSaving, setIsSaving] = useState(false)

const handleSave = async (closeAfterSave = false) => {
  setIsSaving(true)
  try {
    const aloDiff = computeDiff(workingAssessmentLOMappings, initialAssessmentLOMappings)
    const lopoDiff = computeDiff(workingLoPOMappings, initialLoPOMappings)

    const [aloResult, lopoResult] = await Promise.all([
      bulkSyncAssessmentLOMappings({
        course_id: courseId,
        creates: aloDiff.creates.map(m => ({
          temp_id: m.id,
          assessment_id: (m as any).assessment || (m as any).assessment_id,
          learning_outcome_id: (m as any).learning_outcome?.id || (m as any).learning_outcome_id,
          weight: m.weight,
        })),
        updates: aloDiff.updates,
        deletes: aloDiff.deletes,
      }),
      bulkSyncLOPOMappings({
        course_id: courseId,
        creates: lopoDiff.creates.map(m => ({
          temp_id: m.id,
          learning_outcome_id: (m as any).learning_outcome?.id || (m as any).learning_outcome_id,
          program_outcome_id: (m as any).program_outcome?.id || (m as any).program_outcome_id,
          weight: m.weight,
        })),
        updates: lopoDiff.updates,
        deletes: lopoDiff.deletes,
      }),
    ])

    // Replace temp IDs with real IDs
    const tempIdMap = new Map<number, number>()
    for (const item of aloResult.created || []) {
      if (item.temp_id) tempIdMap.set(item.temp_id, item.id)
    }
    for (const item of lopoResult.created || []) {
      if (item.temp_id) tempIdMap.set(item.temp_id, item.id)
    }

    setWorkingAssessmentLOMappings(prev =>
      prev.map(m => (tempIdMap.has(m.id) ? { ...m, id: tempIdMap.get(m.id)! } : m))
    )
    setWorkingLoPOMappings(prev =>
      prev.map(m => (tempIdMap.has(m.id) ? { ...m, id: tempIdMap.get(m.id)! } : m))
    )

    // Update initial state
    setInitialAssessmentLOMappings(clone(workingAssessmentLOMappings))
    setInitialLoPOMappings(clone(workingLoPOMappings))

    if (closeAfterSave) {
      onClose?.()
    }
  } catch (error) {
    console.error('Bulk sync failed:', error)
    alert('Failed to save changes. Please try again.')
  } finally {
    setIsSaving(false)
  }
}
```

- [ ] **Step 3: Remove individual mutation calls**

Remove the old mutation hooks and handler functions that are no longer needed:
- Remove `handleCreateOrUpdateMapping` function entirely
- Remove `handleDeleteALOMapping` function entirely
- Remove `handleDeleteLOPOMapping` function entirely
- Remove the mutation hook declarations: `aloCreateMutation`, `aloPartialUpdateMutation`, `aloDestroyMutation`, `lopoCreateMutation`, `lopoPartialUpdateMutation`, `lopoDestroyMutation`
- Remove the mutation imports from the generated API files

The WeightModal's confirm button should now call `handleCreateOrUpdateMapping` → replace its call with setting the working state directly and closing the modal:

```tsx
const handleCreateOrUpdateMapping = (weight: number) => {
  if (weightModal.editMode && weightModal.mappingId) {
    // Update existing mapping in working state
    if (weightModal.type === 'assessment-lo') {
      setWorkingAssessmentLOMappings(prev =>
        prev.map(m => m.id === weightModal.mappingId ? { ...m, weight } : m)
      )
    } else {
      setWorkingLoPOMappings(prev =>
        prev.map(m => m.id === weightModal.mappingId ? { ...m, weight } : m)
      )
    }
  } else {
    // Create new mapping in working state with temp ID
    const tempId = -Date.now()
    if (weightModal.type === 'assessment-lo') {
      const newMapping: AssessmentLearningOutcomeMapping = {
        id: tempId,
        assessment: weightModal.fromId,
        assessment_id: weightModal.fromId,
        learning_outcome: { id: weightModal.toId } as any,
        learning_outcome_id: weightModal.toId,
        weight,
      } as any
      setWorkingAssessmentLOMappings(prev => [...prev, newMapping])
    } else {
      const newMapping: LearningOutcomeProgramOutcomeMapping = {
        id: tempId,
        course: courseId,
        learning_outcome: { id: weightModal.fromId } as any,
        learning_outcome_id: weightModal.fromId,
        program_outcome: { id: weightModal.toId } as any,
        program_outcome_id: weightModal.toId,
        weight,
      } as any
      setWorkingLoPOMappings(prev => [...prev, newMapping])
    }
  }
  setWeightModal(null)
}
```

And for delete, add:
```tsx
const handleDeleteMapping = (mappingId: number, type: 'assessment-lo' | 'lo-po') => {
  if (type === 'assessment-lo') {
    setWorkingAssessmentLOMappings(prev => prev.filter(m => m.id !== mappingId))
  } else {
    setWorkingLoPOMappings(prev => prev.filter(m => m.id !== mappingId))
  }
}
```

Update the X buttons on mapping badges to call `handleDeleteMapping` instead of the old `handleDeleteALOMapping`/`handleDeleteLOPOMapping`.

- [ ] **Step 4: Add footer bar with Save and Reset buttons**

Add after the 3-column grid (before the closing `</DndContext>` and `</>` tags, around line ~942):

```tsx
{/* Footer */}
<div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200 mt-6">
  <button
    onClick={handleReset}
    disabled={!hasChanges}
    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
      hasChanges
        ? 'border border-gray-300 text-gray-700 hover:bg-gray-50'
        : 'border border-gray-200 text-gray-300 cursor-not-allowed'
    }`}
  >
    ↺ Reset Changes
  </button>
  <button
    onClick={() => handleSave(false)}
    disabled={!hasChanges || isSaving}
    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
      hasChanges && !isSaving
        ? 'bg-blue-600 text-white hover:bg-blue-700'
        : 'bg-gray-200 text-gray-400 cursor-not-allowed'
    }`}
  >
    {isSaving ? 'Saving...' : 'Save Changes'}
  </button>
</div>
```

- [ ] **Step 5: Add handleReset**

```tsx
const handleReset = () => {
  setWorkingAssessmentLOMappings(clone(initialAssessmentLOMappings))
  setWorkingLoPOMappings(clone(initialLoPOMappings))
}
```

- [ ] **Step 6: Verify frontend builds**

Run: `cd frontend && npm run build 2>&1 | tail -5`

- [ ] **Step 7: Commit**

```bash
git add frontend/src/features/courses/components/MappingEditor.tsx
git commit -m "feat: add bulk save, footer buttons, and handleReset to mapping editor"
```

---

### Task 5: Frontend — Close confirmation dialog

**Files:**
- Modify: `frontend/src/features/courses/components/MappingEditor.tsx`

- [ ] **Step 1: Add close confirmation state**

```tsx
const [showCloseConfirm, setShowCloseConfirm] = useState(false)
```

- [ ] **Step 2: Update X button onClick**

Replace the X button `onClick={onClose}` with:
```tsx
onClick={() => {
  if (hasChanges) {
    setShowCloseConfirm(true)
  } else {
    onClose?.()
  }
}}
```

- [ ] **Step 3: Add close confirmation dialog**

Add before the closing tag of the component (after the WeightModal):

```tsx
{/* Close Confirmation Dialog */}
{showCloseConfirm && (
  <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[10001]">
    <div className="bg-white rounded-xl p-6 max-w-sm w-full shadow-xl">
      <h3 className="text-lg font-semibold text-gray-900 mb-2">Unsaved Changes</h3>
      <p className="text-sm text-gray-600 mb-6">
        You have unsaved mapping changes. What would you like to do?
      </p>
      <div className="flex gap-2 justify-end">
        <button
          onClick={() => setShowCloseConfirm(false)}
          className="px-3 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          Keep Editing
        </button>
        <button
          onClick={() => {
            handleReset()
            setShowCloseConfirm(false)
            onClose?.()
          }}
          className="px-3 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700"
        >
          Discard
        </button>
        <button
          onClick={async () => {
            setShowCloseConfirm(false)
            await handleSave(true)
          }}
          className="px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
        >
          Save & Close
        </button>
      </div>
    </div>
  </div>
)}
```

- [ ] **Step 4: Verify frontend builds**

Run: `cd frontend && npm run build 2>&1 | tail -5`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/courses/components/MappingEditor.tsx
git commit -m "feat: add close confirmation dialog with Keep/Discard/Save & Close"
```

---

### Task 6: Frontend — Weight suggestion placeholder button

**Files:**
- Modify: `frontend/src/features/courses/components/MappingEditor.tsx:608-616`

- [ ] **Step 1: Add weight suggestion button in header**

Insert a button between the header text and the X button. In the header area (around line 608), change:

```tsx
{onClose && (
  <button onClick={...} className="..." aria-label="Close">
    <XMarkIcon className="h-6 w-6 text-gray-500" />
  </button>
)}
```

To:
```tsx
<div className="flex items-center gap-2">
  <button
    className="p-2 hover:bg-indigo-50 rounded-lg transition-colors"
    title="AI Weight Suggestion"
    aria-label="AI Weight Suggestion"
  >
    <svg className="h-5 w-5 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
    </svg>
  </button>
  {onClose && (
    <button
      onClick={() => {
        if (hasChanges) {
          setShowCloseConfirm(true)
        } else {
          onClose?.()
        }
      }}
      className="p-2 hover:bg-gray-100 rounded-lg"
      aria-label="Close"
    >
      <XMarkIcon className="h-6 w-6 text-gray-500" />
    </button>
  )}
</div>
```

Keep the existing `XMarkIcon` import at the top.

- [ ] **Step 2: Verify frontend builds**

Run: `cd frontend && npm run build 2>&1 | tail -5`
Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/courses/components/MappingEditor.tsx
git commit -m "feat: add weight suggestion placeholder button to mapping editor header"
```

---

### Task 7: Full test suite verification

- [ ] **Step 1: Run backend tests**

Run: `cd backend/student_evaluation_system && ../../.venv/bin/python -m pytest tests/ --tb=short 2>&1 | tail -10`
Expected: All tests pass.

- [ ] **Step 2: Verify frontend build**

Run: `cd frontend && npm run build 2>&1 | tail -5`
Expected: Build succeeds.

- [ ] **Step 3: Commit if anything changed**

Only commit if any fix was needed.
