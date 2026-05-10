# Assessment Description Collection + Weight Suggestion — Implementation Plan

**Date:** 2026-05-08
**Spec:** `2026-05-08-assessment-descriptions-weight-suggestion-design.md`

---

## Phase 1: Backend

### Task 1.1 — Add `BulkAssessmentDescriptionUpdateSerializer`
**File:** `student_evaluation_system/evaluation/serializers.py`
- Add new serializer class `BulkAssessmentDescriptionUpdateSerializer` with `assessments: ListField[DictField]`
- Validate each item has `id` (int) and `description` (str)

### Task 1.2 — Add `bulk_descriptions` endpoint
**File:** `student_evaluation_system/evaluation/views.py`, in `AssessmentViewSet`
- Add `@action(detail=False, methods=["post"])` named `bulk_descriptions`
- Use `BulkAssessmentDescriptionUpdateSerializer` for input validation
- Within `transaction.atomic()`: loop over `data["assessments"]`, call `Assessment.objects.filter(id=id).update(description=description)`
- Return `{ updated_count: int }` (or similar lightweight response)
- Use `extend_schema` decorator with OpenAPI request/response docs

### Task 1.3 — Verify backend
**Run:** Django syntax check — `cd backend && python3 -c "import student_evaluation_system.evaluation.views"`

---

## Phase 2: Frontend API Generation

### Task 2.1 — Regenerate Orval API
**Command:** `cd frontend && npm run generate:api`
- New endpoint will generate `useEvaluationAssessmentsBulkDescriptionsCreate` mutation hook
- Verify the new hook appears in `src/shared/api/generated/evaluation/evaluation.ts`

---

## Phase 3: Frontend Component

### Task 3.1 — Create `AssessmentDescriptionsModal.tsx`
**File:** `frontend/src/features/courses/components/AssessmentDescriptionsModal.tsx`
- Props interface:
  ```typescript
  interface Props {
    isOpen: boolean
    onClose: () => void
    onSubmit: (descriptions: Array<{id: number; description: string}>) => Promise<void>
    assessments: Assessment[]
  }
  ```
- Internal state: `Map<assessmentId, string>` for textarea values
- Initialize textarea values from `assessments` on mount/open
- Layout:
  - Full-screen overlay (`fixed inset-0 bg-black/50 z-[60]`)
  - White card (`bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[80vh] flex flex-col m-4`)
  - Header: title + subtitle
  - Body: `flex-1 overflow-y-auto p-6 space-y-4`
    - Each assessment row: label (name + type pill), textarea (pre-filled, placeholder if empty)
    - Placeholder example: `"Vize sınavı: Temel kavramları ve uygulamaları değerlendirir."`
  - Footer: sticky `flex justify-end gap-3 p-4 border-t`
    - Cancel button (ghost/secondary style)
    - Submit button (primary, disabled if any textarea is empty)

### Task 3.2 — Import new hook in `MappingEditor.tsx`
- Add `useEvaluationAssessmentsBulkDescriptionsCreate` to existing import from `evaluation`
- Add `AssessmentDescriptionsModal` import

### Task 3.3 — Add state to `MappingEditor`
```typescript
const [showDescriptionsModal, setShowDescriptionsModal] = useState(false)
```

### Task 3.4 — Place modal in JSX
- Add `<AssessmentDescriptionsModal>` inside the `MappingEditor` return, near other modals (WeightModal, closeConfirm)
- Render it when `showDescriptionsModal` is true
- Pass `assessments`, `onClose`, `onSubmit`

### Task 3.5 — Implement `onSubmit` handler
```typescript
const handleDescriptionsSubmit = async (descriptions) => {
  await useEvaluationAssessmentsBulkDescriptionsCreate.mutateAsync({
    data: { assessments: descriptions }
  })
  setShowDescriptionsModal(false)
  // After modal closes, trigger the suggestion flow
  // Re-use the existing handleSuggestWeights logic by extracting it
}
```

### Task 3.6 — Modify `handleSuggestWeights`
- Extract the suggestion-job-queuing logic into a separate function `queueWeightSuggestion()`
- In `handleSuggestWeights`:
  ```typescript
  const needsDescriptions = assessments.some(a => !a.description?.trim())
  if (needsDescriptions) {
    setShowDescriptionsModal(true)
  } else {
    queueWeightSuggestion()
  }
  ```

### Task 3.7 — TypeScript check
**Run:** `cd frontend && npx tsc --noEmit`
Fix any type errors.

---

## Verification

1. Open MappingEditor for a course with assessments
2. Click "Suggest Weights" — if any assessment has empty `description`, the new modal appears
3. Fill descriptions, click "Submit & Get Suggestions"
4. Modal closes, suggestion job is queued, results apply to mappings
5. If all descriptions are already filled, modal is skipped and suggestion runs directly
