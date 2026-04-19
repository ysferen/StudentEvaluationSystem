I# Assignment Validation Consolidation - Design

**Date:** 2026-04-16
**Status:** Approved (conversation)

---

## Overview

The current file-import validation path has overlapping assignment and assessment validation logic, which creates inconsistent behavior and makes the resolution flow hard to trust. This design consolidates everything under the assignment-scores format and makes validation, resolution, and import use one canonical contract.

Goals:
- Standardize on `assignment_scores` format and remove duplicate assessment validation paths.
- Ensure full-file validation covers all five phases with a single response shape.
- Ensure resolution choices are actually applied and reflected in both re-validation and final import.

Non-goals:
- No scope change for learning outcomes or program outcomes import.
- No route path changes for existing assignment-scores endpoints.

---

## Consolidation Scope

### Canonical validator

`AssignmentScoreValidator` becomes the single validation engine for assignment score imports.

Changes in `backend/student_evaluation_system/core/services/validation.py`:
- Remove parallel `assessment_scores` validation branches and dead import-type switching tied to those branches.
- Keep one pipeline for phases:
  1. file structure
  2. column structure
  3. assessment validation
  4. student validation
  5. score validation
- Keep shared parsing and extraction helpers as private helper methods used by the assignment pipeline only.

### Canonical response contract

Both `validate` and `resolve` must return a stable contract:

```json
{
  "is_valid": false,
  "phase_reached": "score_validation",
  "checks": {
    "file_structure": {"passed": true},
    "column_structure": {"passed": true},
    "assessment_validation": {"passed": false},
    "student_validation": {"passed": false},
    "score_validation": {"passed": false}
  },
  "errors": [],
  "warnings": [],
  "suggestions": [],
  "details": {}
}
```

`checks` is the canonical field for frontend rendering. `details` carries modal payloads and phase-specific structured data.

---

## Endpoint Behavior

### Validate endpoint

`POST /api/core/file-import/assignment-scores/validate/`

Behavior:
- Parse and validate file with hard-stop only on phases 1-2.
- Continue collecting issues for phases 3-5.
- Return structured result with `checks`, `phase_reached`, and `details` for UI actions.

### Resolve endpoint

`POST /api/core/file-import/assignment-scores/resolve/`

Resolution choices supported:
- `create_students`
- `enroll_students`
- `create_assessments`
- `skip_missing_assessments`
- `skip_missing_students`
- `skip_unenrolled_students`
- `skip_invalid_scores`
- `clamp_scores`

Resolution order:
1. create students
2. enroll students
3. create assessments
4. apply skip/clamp policy in validation context
5. re-run complete validation

Return shape mirrors validate response and includes `resolutions_applied` summary.

---

## Import Consistency Rule

The upload/import path must honor the same resolution policy acknowledged by resolve/validate.

Required behavior:
- If user chooses skip behavior, import skips those entities/rows deterministically.
- If user chooses clamp behavior, import uses clamped values consistently.
- Import should not contradict previously returned validation success under applied resolutions.

This prevents "resolved in UI but fails during import" inconsistencies.

---

## Frontend Integration

Changes in `frontend/src/features/courses/components/FileUploadModal.tsx`:
- Treat `checks` as primary source of phase status (remove fallback-heavy interpretation once backend is canonical).
- Wire Solve buttons to set `activeProblem` and open the correct modal.
- Keep loop: validate -> solve -> resolve -> re-render updated checks.

Changes in `frontend/src/features/courses/components/ResolutionModals.tsx`:
- Keep existing modal set; ensure emitted payloads map exactly to backend resolution keys.

---

## Error Handling Contract

Two classes of errors:

1. Request/transport errors (HTTP 4xx)
- missing query params
- invalid term/course references
- malformed resolutions payload

2. Domain validation results (HTTP 200)
- validation issues reported as `is_valid=false`
- structured `errors` with `{message, category, severity}`

This preserves progressive resolution UX while still surfacing true request failures correctly.

---

## Test Strategy

Backend tests:
- Validate assignment-only canonical path (no assessment duplicate path).
- Assert strict `checks` contract for validate and resolve responses.
- Assert each resolution knob changes re-validation outcome as expected.
- Assert import behavior follows skip/clamp policy.

Frontend tests:
- Solve button appears for failed checks.
- Solve button opens expected modal.
- Modal confirm calls resolve endpoint with correct payload.
- Re-validation result updates visible phase/check state.

---

## Risks and Mitigations

- Risk: Hidden dependencies on removed assessment-specific methods.
  - Mitigation: run targeted grep + test suite before deletion, keep temporary internal alias only if needed.

- Risk: Frontend regression from response-shape tightening.
  - Mitigation: backend emits stable `checks`; frontend retains short transitional fallback until tests pass.

- Risk: Resolve choices accepted but not reflected during upload.
  - Mitigation: explicit import-policy integration tests and one policy application path shared by resolve/import.

---

## Acceptance Criteria

- Only assignment-scores validation path remains active.
- `validate` and `resolve` return canonical `checks` contract.
- All declared resolution knobs are implemented and effective.
- Solve flow is reachable and functional from UI.
- Import behavior matches accepted resolution policy.
