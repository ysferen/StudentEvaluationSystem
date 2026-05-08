# Assessment Description Collection + Weight Suggestion Design

**Date:** 2026-05-08
**Status:** Approved

## Overview

Before requesting AI-powered weight suggestions, users must provide a brief description for each assessment. This description is used as the embedded text for cosine-similarity matching against learning outcome descriptions.

The assessment `description` field already exists in the database. The feature adds:
1. A **backend bulk-update endpoint** for assessment descriptions
2. A **frontend modal** that collects descriptions before triggering the suggestion job
3. **Integration** into the existing "Suggest Weights" flow

---

## Backend Changes

### New Serializer

**File:** `student_evaluation_system/evaluation/serializers.py`

```python
class BulkAssessmentDescriptionUpdateSerializer(serializers.Serializer):
    """Bulk update assessment descriptions."""
    assessments = serializers.ListField(
        child=serializers.DictField(),  # [{id: int, description: str}, ...]
        min_length=1,
    )
```

### New Endpoint

**File:** `student_evaluation_system/evaluation/views.py`
**ViewSet:** `AssessmentViewSet`
**Action:** `bulk_descriptions` at `POST /api/evaluation/assessments/bulk_descriptions/`

- Request: `{ assessments: [{id: int, description: str}, ...] }`
- Updates all assessments in a single atomic transaction
- Returns: `{ updated: [AssessmentSerializer, ...] }`
- Permissions: same as existing `AssessmentViewSet` CRUD (`IsAuthenticated, IsInstructorOfCourse, InstructorPermissionMixin`)
- No score recalculation needed — description is informational only

---

## Frontend Changes

### New Component: `AssessmentDescriptionsModal`

A modal component that displays one textarea per assessment for collecting descriptions.

**Props:**
- `isOpen: boolean`
- `onClose: () => void`
- `onSubmit: (descriptions: Array<{id: number, description: string}>) => void`
- `assessments: Assessment[]` (current assessments with existing descriptions)

**Layout:**
- Full overlay: `fixed inset-0 bg-black/50 z-[60]`
- Container: `bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[80vh] flex flex-col`
- Header: title "Assessment Descriptions" + subtitle text
- Body: scrollable list, one row per assessment
  - Row: `<assessment_name> <type_badge>` label above textarea
  - Textarea: pre-filled with existing `a.description || ""`, placeholder if empty
  - Placeholder example (Turkish): `"Vize sınavı: Temel kavramları ve uygulamaları değerlendirir."`
- Footer (sticky): "Cancel" ghost button + "Submit & Get Suggestions" primary button (disabled if any textarea empty)

### State in `MappingEditor`

```tsx
const [showDescriptionsModal, setShowDescriptionsModal] = useState(false)
```

### Modified "Suggest Weights" Flow

```tsx
const handleSuggestWeights = async () => {
  const needsDescriptions = assessments.some(a => !a.description?.trim())
  if (needsDescriptions) {
    setShowDescriptionsModal(true)
  } else {
    // existing path: queue suggestion job
  }
}
```

### `AssessmentDescriptionsModal` Submit

1. Collect all `{ id, description }` pairs from form state
2. Call `useEvaluationAssessmentsBulkDescriptionsCreate({ data: { assessments } })`
3. On success: close modal → proceed to existing `handleSuggestWeights` queue job flow

### Orval

After backend endpoint is live, regenerate API:
```bash
cd frontend && npm run generate:api
```

New hook: `useEvaluationAssessmentsBulkDescriptionsCreate`

---

## Data Flow

```
User clicks "Suggest Weights"
  → Any assessment has empty description?
    → YES: Open AssessmentDescriptionsModal
      → User fills all descriptions
      → Submit: POST /bulk_descriptions/
      → On success: close modal → queue suggestion job (existing flow)
    → NO:  Queue suggestion job directly (existing flow)
```

---

## Key Decisions

1. **No schema migration** — `Assessment.description` field already exists
2. **Bulk endpoint** — single transaction, one round-trip, avoids per-assessment PATCH overhead
3. **No score recalculation** — description is read-only metadata for embedding; no business logic changes
4. **Turkish placeholder** — aligned with existing app language; can be made i18n-ready later
5. **Modal blocks suggestion** — ensures descriptions are always provided when using AI suggestion
