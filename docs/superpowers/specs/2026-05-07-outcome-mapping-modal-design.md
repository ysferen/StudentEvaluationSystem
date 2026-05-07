# Outcome Mapping Modal — Bulk Save & State Management

> **Status:** Design approved — transitioning to implementation plan

## Goal

Replace the current auto-save-per-change behavior in the Outcome Mapping Editor with a local state / bulk save model. Users make changes locally, then save all at once. Score recompute is dispatched as an async Celery task instead of blocking synchronously.

## State Management

The component maintains two copies of mapping state:

| State | Purpose | Source |
|---|---|---|
| `initialMappings` | Snapshot from server on modal open | Server query (frozen on mount) |
| `workingMappings` | Editable local copy, all mutations applied here | Deep clone of `initialMappings` on mount |

State arrays:
- `assessmentLOMappings` → split into `initialAssessmentLOMappings` + `workingAssessmentLOMappings`
- `loPOMappings` → split into `initialLoPOMappings` + `workingLoPOMappings`

On modal open (`isMappingEditorOpen` becomes true), both `initial*` and `working*` are set from the server query data. After that, all mutations (add, update, delete) operate only on `working*`. The server query data is NOT used to sync after initial load — it's only fetched once on open.

## Change Detection

Diff is computed by comparing `working*` against `initial*`:

```
creates  = items in working with temp negative IDs
updates  = items where working[id].weight !== initial[id].weight
deletes  = IDs in initial but not in working
```

**Save button state:** enabled when diff is non-empty (any creates, updates, or deletes), disabled/greyed when empty. Reactively computed from the diff, no separate `isDirty` flag needed.

**Temporary IDs:** New mappings get negative IDs (`-Date.now()`). The bulk save response maps them to real server IDs, and the frontend replaces them in `working*` and updates `initial*`.

## Header Layout

```
┌────────────────────────────────────────────────────────┐
│ Outcome Mapping Editor          [✨ Suggest] [✕]       │
├────────────────────────────────────────────────────────┤
│                    3-column grid                        │
├────────────────────────────────────────────────────────┤
│                              [↺ Reset] [Save Changes]  │
└────────────────────────────────────────────────────────┘
```

- **✨ Suggest Weights** (top-right, before X): Placeholder button — renders visually but has no onClick handler. Shows tooltip "AI Weight Suggestion".
- **X button** (top-right): Closes the modal. If there are unsaved changes, shows confirmation dialog instead of closing immediately.
- **Save Changes** (footer, right-aligned): Disabled/greyed when no changes exist. Primary color when changes exist. Triggers bulk save.
- **↺ Reset** (footer, next to Save): Restores `working*` from `initial*`. Disabled when no changes exist.

## Footer Buttons

Both right-aligned in a footer bar at the bottom of the modal, with a top border separator:

```
[↺ Reset Changes]  [Save Changes]
```

- **Save Changes**: Disabled (greyed `bg-gray-200 text-gray-400`) when diff is empty. Enabled (`bg-blue-600 text-white`) when diff is non-empty. Calls `handleSave()`.
- **Reset Changes**: Same disabled/enabled states. Calls `handleReset()` which restores `working*` from `initial*`.

## Close Confirmation Dialog

When the user tries to close (X button or backdrop click) AND there are unsaved changes, a confirmation dialog appears:

```
┌────────────────────────────────────┐
│ Unsaved Changes                    │
│ You have unsaved mapping changes.  │
│ What would you like to do?         │
│                                    │
│ [Keep Editing] [Discard] [Save & Close] │
└────────────────────────────────────┘
```

- **Keep Editing**: Dismisses dialog, returns to editor
- **Discard**: Resets `working*` to `initial*` and closes modal
- **Save & Close**: Calls `handleSave()` with `closeAfterSave = true`, then closes on success

Implement as a simple modal overlay within the MappingEditor (inline component, not a separate file). Use the same style as the existing WeightModal.

## Bulk Save Flow

### API Endpoints

Two new `@action` methods:

**1. Assessment-LO bulk sync**
```
POST /api/evaluation/assessment-lo-mappings/bulk_sync/
```
On `AssessmentLearningOutcomeMappingViewSet`, following existing `bulk_enroll` pattern on `CourseEnrollmentViewSet`.

**2. LO-PO bulk sync**
```
POST /api/core/lo-po-mappings/bulk_sync/
```
On the LO-PO mapping viewset.

### Request Payload

```json
{
  "course_id": 5,
  "creates": [
    {"assessment_id": 10, "learning_outcome_id": 3, "weight": 3}
  ],
  "updates": [
    {"id": 42, "weight": 5}
  ],
  "deletes": [7, 8]
}
```

All arrays can be empty. At least one must be non-empty for the request to be valid.

### Backend Processing

1. Validate all operations (permissions, existing IDs, weight range 0-5)
2. Process in order: deletes first, then updates, then creates — all in a single `transaction.atomic()` block
3. For creates, accept a `temp_id` field (negative number) and return the mapping
4. Collect all affected course IDs
5. Commit transaction
6. Dispatch `recompute_course_scores_task.delay()` via Celery for each affected course — **asynchronously**, response returns immediately
7. Return summary with temp_id → real_id mapping

### Response Payload

```json
{
  "created": [
    {"temp_id": -1700000001, "real_id": 99, "assessment": 10, "learning_outcome": 3, "weight": 3}
  ],
  "updated": [
    {"id": 42, "assessment": 10, "learning_outcome": 5, "weight": 5}
  ],
  "deleted": [7, 8],
  "recompute_job_ids": [15, 16]
}
```

- `temp_id` in created items allows frontend to match and replace negative IDs
- `recompute_job_ids` are for informational display (optional — frontend may ignore)

### Frontend HandleSave

```ts
const handleSave = async (closeAfterSave = false) => {
  // Compute diffs for both mapping types
  const { creates, updates, deletes } = computeDiff(workingALO, initialALO)
  const loPoChanges = computeDiff(workingLoPo, initialLoPo)

  // Send both bulk requests in parallel
  const [aloResult, lopoResult] = await Promise.all([
    bulkSyncALO({ course_id, creates, updates, deletes }),
    bulkSyncLoPo({ course_id, creates: loPoChanges.creates, updates: loPoChanges.updates, deletes: loPoChanges.deletes }),
  ])

  // Replace temp IDs with real IDs
  setWorkingALO(replaceTempIds(workingALO, aloResult.created))
  setWorkingLoPo(replaceTempIds(workingLoPo, lopoResult.created))

  // Set new initial state
  setInitialALO(clone(workingALO))
  setInitialLoPo(clone(workingLoPo))

  if (closeAfterSave) {
    onClose?.()
  }
}
```

## Weight Suggestion Button

- Renders in the header, before the X button
- Visual only: no `onClick` handler, no API call
- Shows a tooltip: "AI Weight Suggestion"
- Use a lightning bolt icon or similar
- Styled as a subtle icon button

## Score Recompute

- **Before this change:** `calculate_course_scores()` called synchronously in `perform_create`/`perform_update`/`perform_destroy` — blocks response
- **After this change:** `recompute_course_scores_task.delay()` dispatched asynchronously in `bulk_sync` — response returns immediately, scores compute in background via Celery
- The existing synchronous calls in the individual CRUD endpoints remain unchanged (backward compat)

## Files to Create/Modify

| File | Action | What |
|---|---|---|
| `frontend/src/features/courses/components/MappingEditor.tsx` | Modify | Dual-state management, footer bar, close confirmation, save/reset handlers |
| `backend/.../evaluation/views.py` | Modify | Add `bulk_sync` action to `AssessmentLearningOutcomeMappingViewSet` |
| `backend/.../core/views/lo_po_mappings.py` | Modify | Add `bulk_sync` action to LO-PO mapping viewset |
| `backend/.../evaluation/serializers.py` | Modify | Add `BulkSyncSerializer` for request/response validation |
| `backend/.../core/serializers.py` | Modify | Add LO-PO `BulkSyncSerializer` |
| `backend/.../tests/test_views.py` | New tests | Bulk sync endpoint tests |
| `backend/.../tests/test_serializers.py` | New tests | Bulk sync serializer validation |
