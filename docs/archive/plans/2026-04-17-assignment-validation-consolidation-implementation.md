# Assignment Validation Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate assignment file-import validation into one canonical pipeline and make validate/resolve/upload share the same assignment-scores contract and resolution behavior.

**Architecture:** Backend keeps one assignment-only validation path in `AssignmentScoreValidator`, with canonical `checks` output and deterministic resolution handling in the view. Import service accepts resolution policy (`skip` / `clamp`) so upload behavior matches resolved validation results. Frontend consumes canonical `checks`, exposes working Solve actions, and re-validates after each resolution.

**Tech Stack:** Django + DRF + pytest + pandas backend, React + TypeScript + Vitest frontend.

---

## File Map

- Modify: `backend/student_evaluation_system/core/services/validation.py`
  - Remove assessment/assignment branch duplication.
  - Make `validate_complete()` emit canonical `phase_reached` and `checks` details.
- Modify: `backend/student_evaluation_system/core/views/file_import.py`
  - Return canonical response in both `validate` and `resolve`.
  - Apply new resolution payload keys and include `resolutions_applied`.
- Modify: `backend/student_evaluation_system/core/services/file_import.py`
  - Add optional resolution policy to assignment upload, including skip/clamp handling.
- Modify: `backend/student_evaluation_system/tests/test_validation_phases.py`
  - Assert canonical validation details and assignment-only behavior.
- Modify: `backend/student_evaluation_system/tests/test_file_import_validation.py`
  - Assert `checks` shape and resolve policy behavior.
- Modify: `frontend/src/features/courses/components/FileUploadModal.tsx`
  - Render canonical checks and wire Solve actions to modal flow.
- Modify: `frontend/src/test/ResolutionModals.test.tsx`
  - Keep modal payload contract assertions.
- Create: `frontend/src/test/file-upload-modal-resolution-flow.test.tsx`
  - Validate Solve button -> modal open -> resolve payload -> UI refresh flow.

---

### Task 1: Lock Canonical Backend Contract with Failing Tests

**Files:**
- Modify: `backend/student_evaluation_system/tests/test_validation_phases.py`
- Modify: `backend/student_evaluation_system/tests/test_file_import_validation.py`

- [ ] **Step 1: Add failing validator contract tests**

Append these tests to `backend/student_evaluation_system/tests/test_validation_phases.py`:

```python
def test_validate_complete_sets_phase_reached_and_checks(db_setup):
    from io import BytesIO
    from evaluation.models import Assessment

    course = db_setup["course"]
    Assessment.objects.create(course=course, name="Midterm", total_score=100)

    df = pd.DataFrame(
        {
            "öğrenci no": ["S001"],
            "adı": ["Ali"],
            "soyadı": ["Veli"],
            "Midterm(%30)_X1": [80],
        }
    )
    buf = BytesIO()
    df.to_excel(buf, index=False)
    buf.seek(0)
    buf.name = "ok.xlsx"
    buf.size = buf.getbuffer().nbytes

    result = AssignmentScoreValidator.validate_complete(buf, course)

    assert "phase_reached" in result.validation_details
    checks = result.validation_details.get("checks")
    assert isinstance(checks, dict)
    assert set(checks.keys()) == {
        "file_structure",
        "column_structure",
        "assessment_validation",
        "student_validation",
        "score_validation",
    }
    assert checks["file_structure"]["passed"] is True


def test_validate_complete_hard_stops_at_column_structure(db_setup):
    from io import BytesIO

    course = db_setup["course"]
    df = pd.DataFrame({"adı": ["Ali"], "soyadı": ["Veli"]})
    buf = BytesIO()
    df.to_excel(buf, index=False)
    buf.seek(0)
    buf.name = "missing-columns.xlsx"
    buf.size = buf.getbuffer().nbytes

    result = AssignmentScoreValidator.validate_complete(buf, course)

    assert result.is_valid is False
    assert result.validation_details["phase_reached"] == "column_structure"
    checks = result.validation_details["checks"]
    assert checks["file_structure"]["passed"] is True
    assert checks["column_structure"]["passed"] is False
```

- [ ] **Step 2: Add failing endpoint contract tests**

Replace `checks` assertions in `backend/student_evaluation_system/tests/test_file_import_validation.py` with:

```python
assert "checks" in data
for key in [
    "file_structure",
    "column_structure",
    "assessment_validation",
    "student_validation",
    "score_validation",
]:
    assert key in data["checks"]
    assert "passed" in data["checks"][key]
```

Add this test in `TestResolveEndpoint`:

```python
@pytest.mark.django_db
def test_resolve_accepts_assignment_resolution_keys(self, api_client, course, term, assessments):
    df = pd.DataFrame(
        {
            "öğrenci no": ["NEW001"],
            "adı": ["Yeni"],
            "soyadı": ["Ogrenci"],
            "Midterm Exam(%30)_0833AB": [75],
        }
    )
    buffer = create_excel_buffer(df)
    buffer.name = "resolve-keys.xlsx"

    resolutions = {
        "create_students": [{"student_id": "NEW001", "first_name": "Yeni", "last_name": "Ogrenci"}],
        "skip_unenrolled_students": False,
        "enroll_students": ["NEW001"],
        "create_assessments": [],
        "skip_invalid_scores": False,
        "clamp_scores": False,
    }

    response = api_client.post(
        f"/api/v1/core/file-import/assignment-scores/resolve/?course_code={course.code}&term_id={term.id}",
        {"file": buffer, "resolutions": json.dumps(resolutions)},
        format="multipart",
    )

    assert response.status_code == status.HTTP_200_OK
    assert "resolutions_applied" in response.data
```

- [ ] **Step 3: Run backend tests to verify failure**

Run:
`cd backend/student_evaluation_system && uv run pytest tests/test_validation_phases.py tests/test_file_import_validation.py -q`

Expected: FAIL with missing `checks.*.passed` assertions and/or unsupported resolution key behavior.

- [ ] **Step 4: Commit failing-test checkpoint**

```bash
git add backend/student_evaluation_system/tests/test_validation_phases.py backend/student_evaluation_system/tests/test_file_import_validation.py
git commit -m "test(validation): assert canonical assignment checks contract"
```

---

### Task 2: Refactor Assignment Validator to Single Canonical Pipeline

**Files:**
- Modify: `backend/student_evaluation_system/core/services/validation.py`

- [ ] **Step 1: Remove import-type branch complexity in pipeline runner**

Replace `ValidationPipeline._run_validator` with:

```python
def _run_validator(self, validator_class, all_kwargs) -> ValidationResult:
    if self.import_type != "assignment_scores":
        return ValidationResult()

    if validator_class == FileFormatValidator:
        return self._run_file_format_validation(all_kwargs)
    if validator_class == BusinessStructureValidator:
        return BusinessStructureValidator.validate_assignment_scores_structure(
            all_kwargs["dataframe"], all_kwargs["course"]
        )
    if validator_class == DatabaseIntegrityValidator:
        return DatabaseIntegrityValidator.validate_assignment_scores_database(
            all_kwargs["dataframe"], all_kwargs["course"], all_kwargs["term"]
        )
    if validator_class == DataQualityValidator:
        return DataQualityValidator.validate_assignment_scores_quality(all_kwargs["dataframe"], all_kwargs["course"])
    return ValidationResult()
```

- [ ] **Step 2: Add canonical checks helper in `AssignmentScoreValidator`**

Add this private helper near `AssignmentScoreValidator` methods:

```python
@staticmethod
def _base_checks() -> Dict[str, Dict[str, Any]]:
    return {
        "file_structure": {"passed": False},
        "column_structure": {"passed": False},
        "assessment_validation": {"passed": False},
        "student_validation": {"passed": False},
        "score_validation": {"passed": False},
    }
```

- [ ] **Step 3: Rewrite `validate_complete` to produce canonical `checks` and `phase_reached`**

Replace `AssignmentScoreValidator.validate_complete` with:

```python
@staticmethod
def validate_complete(file_obj, course: Course) -> ValidationResult:
    final_result = ValidationResult()
    checks = AssignmentScoreValidator._base_checks()
    final_result.add_detail("checks", checks)
    final_result.add_detail("phase_reached", "file_structure")

    def merge_phase(phase_key: str, result: ValidationResult):
        final_result.errors.extend(result.errors)
        final_result.warnings.extend(result.warnings)
        final_result.suggestions.extend(result.suggestions)
        final_result.validation_details.update(result.validation_details)
        checks[phase_key]["passed"] = result.is_valid
        if not result.is_valid:
            final_result.is_valid = False
            final_result.validation_details["phase_reached"] = phase_key

    file_result = AssignmentScoreValidator.validate_file_structure(file_obj)
    merge_phase("file_structure", file_result)
    if not file_result.is_valid:
        return final_result

    try:
        file_obj.seek(0)
        dataframe = pd.read_excel(file_obj)
        final_result.add_detail("file_parsed", True)
        final_result.add_detail("row_count", len(dataframe))
        final_result.add_detail("columns", dataframe.columns.tolist())
    except Exception as exc:
        final_result.add_error(f"Failed to parse Excel file: {str(exc)}", "file_parse")
        final_result.is_valid = False
        final_result.validation_details["phase_reached"] = "file_structure"
        checks["file_structure"]["passed"] = False
        return final_result

    final_result.validation_details["phase_reached"] = "column_structure"
    column_result = AssignmentScoreValidator.validate_column_structure(dataframe)
    merge_phase("column_structure", column_result)
    if not column_result.is_valid:
        return final_result

    final_result.validation_details["phase_reached"] = "assessment_validation"
    assessment_result = AssignmentScoreValidator.validate_assignments(dataframe, course)
    merge_phase("assessment_validation", assessment_result)

    final_result.validation_details["phase_reached"] = "student_validation"
    student_result = AssignmentScoreValidator.validate_students(dataframe, course)
    merge_phase("student_validation", student_result)

    final_result.validation_details["phase_reached"] = "score_validation"
    score_result = AssignmentScoreValidator.validate_scores(dataframe, course)
    merge_phase("score_validation", score_result)

    if final_result.is_valid:
        final_result.validation_details["phase_reached"] = "complete"

    final_result.validation_details["checks"] = checks
    return final_result
```

- [ ] **Step 4: Run tests to verify validator contract passes**

Run:
`cd backend/student_evaluation_system && uv run pytest tests/test_validation_phases.py -q`

Expected: PASS.

- [ ] **Step 5: Commit validator refactor**

```bash
git add backend/student_evaluation_system/core/services/validation.py backend/student_evaluation_system/tests/test_validation_phases.py
git commit -m "refactor(validation): consolidate assignment pipeline and canonical checks"
```

---

### Task 3: Implement Canonical Validate/Resolve Response and Resolution Semantics

**Files:**
- Modify: `backend/student_evaluation_system/core/views/file_import.py`

- [ ] **Step 1: Build response from canonical validator checks**

Replace `_build_validation_response` with:

```python
def _build_validation_response(self, validation_result, resolutions_applied=None):
    details = validation_result.validation_details
    checks = details.get("checks", {})
    payload = {
        "is_valid": validation_result.is_valid,
        "phase_reached": details.get("phase_reached", "unknown"),
        "checks": checks,
        "errors": validation_result.errors,
        "warnings": validation_result.warnings,
        "suggestions": validation_result.suggestions,
        "details": details,
    }
    if resolutions_applied is not None:
        payload["resolutions_applied"] = resolutions_applied
    return Response(payload, status=status.HTTP_200_OK)
```

- [ ] **Step 2: Update resolve payload parsing to assignment key names**

In `resolve`, replace resolution parsing with:

```python
resolutions_json = request.data.get("resolutions")
if isinstance(resolutions_json, str):
    try:
        resolutions = json.loads(resolutions_json)
    except json.JSONDecodeError:
        return Response({"error": "Invalid resolutions JSON"}, status=status.HTTP_400_BAD_REQUEST)
elif isinstance(resolutions_json, dict):
    resolutions = resolutions_json
else:
    resolutions = {}

create_students = resolutions.get("create_students", [])
enroll_students = resolutions.get("enroll_students", [])
create_assessments = resolutions.get("create_assessments", [])

skip_missing_assessments = bool(resolutions.get("skip_missing_assessments", False))
skip_missing_students = bool(resolutions.get("skip_missing_students", False))
skip_unenrolled_students = bool(resolutions.get("skip_unenrolled_students", False))
skip_invalid_scores = bool(resolutions.get("skip_invalid_scores", False))
clamp_scores = bool(resolutions.get("clamp_scores", False))
```

- [ ] **Step 3: Update resolution application helpers to new keys**

Update helper loops:

```python
for student_data in create_students:
    # create user/profile + enroll

for student_id in enroll_students:
    # enroll existing profile by student_id

for assessment_name in create_assessments:
    # create assessment if missing
```

And return:

```python
resolution_summary = {
    "created": created_counts,
    "errors": errors,
    "policy": {
        "skip_missing_assessments": skip_missing_assessments,
        "skip_missing_students": skip_missing_students,
        "skip_unenrolled_students": skip_unenrolled_students,
        "skip_invalid_scores": skip_invalid_scores,
        "clamp_scores": clamp_scores,
    },
}
return self._build_validation_response(validation_result, resolutions_applied=resolution_summary)
```

- [ ] **Step 4: Run endpoint integration tests**

Run:
`cd backend/student_evaluation_system && uv run pytest tests/test_file_import_validation.py -q`

Expected: PASS with canonical checks and assignment-key resolution payload.

- [ ] **Step 5: Commit view semantics**

```bash
git add backend/student_evaluation_system/core/views/file_import.py backend/student_evaluation_system/tests/test_file_import_validation.py
git commit -m "feat(file-import): canonical validate/resolve contract for assignment scores"
```

---

### Task 4: Make Upload Honor Resolve Policy (Skip/Clamp)

**Files:**
- Modify: `backend/student_evaluation_system/core/services/file_import.py`
- Modify: `backend/student_evaluation_system/core/views/file_import.py`
- Create: `backend/student_evaluation_system/tests/test_assignment_import_resolution_policy.py`

- [ ] **Step 1: Add failing import-policy tests**

Create `backend/student_evaluation_system/tests/test_assignment_import_resolution_policy.py`:

```python
import pytest
import pandas as pd
from io import BytesIO

from core.models import Term, Course, University, Department, DegreeLevel, Program
from core.services.file_import import FileImportService
from evaluation.models import Assessment


def make_excel(df):
    buf = BytesIO()
    df.to_excel(buf, index=False)
    buf.seek(0)
    buf.name = "policy.xlsx"
    buf.size = buf.getbuffer().nbytes
    return buf


@pytest.mark.django_db
def test_import_with_skip_invalid_scores_does_not_raise_for_invalid_cells(django_user_model):
    uni = University.objects.create(name="U")
    dep = Department.objects.create(code="D", name="Dep", university=uni)
    lvl = DegreeLevel.objects.create(name="L")
    program = Program.objects.create(code="P", name="Prog", degree_level=lvl, department=dep)
    term = Term.objects.create(name="T")
    course = Course.objects.create(code="CS101", name="C", credits=3, program=program, term=term)
    Assessment.objects.create(name="Midterm", assessment_type="midterm", total_score=100, weight=0.5, course=course)

    df = pd.DataFrame(
        {
            "öğrenci no": ["S1"],
            "adı": ["A"],
            "soyadı": ["B"],
            "Midterm(%50)_X1": [150],
        }
    )
    service = FileImportService(make_excel(df))
    service.validate_file()

    result = service.import_assignment_scores(
        course_code=course.code,
        term_id=term.id,
        resolution_policy={"skip_invalid_scores": True, "clamp_scores": False},
    )

    assert "errors" in result
```

- [ ] **Step 2: Add `resolution_policy` parameter to import service API**

Change method signature in `FileImportService.import_assignment_scores`:

```python
def import_assignment_scores(self, course_code: str, term_id: int, resolution_policy: Optional[Dict[str, bool]] = None):
```

Inside method, normalize:

```python
policy = {
    "skip_missing_assessments": bool((resolution_policy or {}).get("skip_missing_assessments", False)),
    "skip_missing_students": bool((resolution_policy or {}).get("skip_missing_students", False)),
    "skip_unenrolled_students": bool((resolution_policy or {}).get("skip_unenrolled_students", False)),
    "skip_invalid_scores": bool((resolution_policy or {}).get("skip_invalid_scores", False)),
    "clamp_scores": bool((resolution_policy or {}).get("clamp_scores", False)),
}
```

- [ ] **Step 3: Implement score handling in row processor**

In `_process_assignment_row`, replace score validation block with:

```python
try:
    score_float = InputValidator.validate_score(score, max_score=assessment.total_score)
except CustomValidationError:
    if policy.get("clamp_scores"):
        try:
            raw_score = float(score)
            score_float = max(0.0, min(float(assessment.total_score), raw_score))
        except (ValueError, TypeError):
            if policy.get("skip_invalid_scores"):
                skipped_count += 1
                continue
            self.import_results["errors"].append(f"Row {row_number}: Invalid score '{score}' for {clean_name}")
            continue
    elif policy.get("skip_invalid_scores"):
        skipped_count += 1
        continue
    else:
        self.import_results["errors"].append(f"Row {row_number}: Invalid score '{score}' for {clean_name}")
        continue
```

- [ ] **Step 4: Pass resolution policy from upload endpoint**

In `BaseFileImportViewSet.upload`, parse optional resolution policy payload:

```python
resolution_policy_raw = request.data.get("resolution_policy")
resolution_policy = {}
if isinstance(resolution_policy_raw, str):
    try:
        resolution_policy = json.loads(resolution_policy_raw)
    except json.JSONDecodeError:
        return Response({"error": "Invalid resolution_policy JSON"}, status=status.HTTP_400_BAD_REQUEST)
elif isinstance(resolution_policy_raw, dict):
    resolution_policy = resolution_policy_raw
```

Pass into import call:

```python
result = service.import_assignment_scores(
    course_code=course_code,
    term_id=term_id,
    resolution_policy=resolution_policy,
)
```

- [ ] **Step 5: Run policy tests**

Run:
`cd backend/student_evaluation_system && uv run pytest tests/test_assignment_import_resolution_policy.py -q`

Expected: PASS.

- [ ] **Step 6: Commit policy support**

```bash
git add backend/student_evaluation_system/core/services/file_import.py backend/student_evaluation_system/core/views/file_import.py backend/student_evaluation_system/tests/test_assignment_import_resolution_policy.py
git commit -m "feat(file-import): apply resolve skip/clamp policy during upload"
```

---

### Task 5: Wire Frontend Solve Actions to Canonical Checks

**Files:**
- Modify: `frontend/src/features/courses/components/FileUploadModal.tsx`
- Create: `frontend/src/test/file-upload-modal-resolution-flow.test.tsx`

- [ ] **Step 1: Add Solve button renderer and trigger mapping**

In `FileUploadModal.tsx`, add helper:

```tsx
const getSolveTarget = (phase: PhaseKey, checks: ValidationResult["checks"]): ActiveProblem => {
  if (phase === "assessment_validation" && checks?.assessment_validation?.passed === false) return "assessments"
  if (phase === "student_validation" && checks?.student_validation?.passed === false) {
    if ((checks.student_validation.not_enrolled || []).length > 0) return "unenrolled"
    if ((checks.student_validation.missing_from_database || []).length > 0) return "students"
  }
  if (phase === "score_validation" && checks?.score_validation?.passed === false) return "scores"
  return null
}
```

Within phase render row, add action:

```tsx
{!isPassed && !isPending && (
  <button
    type="button"
    onClick={() => {
      const target = getSolveTarget(phase.key, normalizedChecks)
      if (target) setActiveProblem(target)
    }}
    className="text-xs bg-warning-100 text-warning-700 px-2 py-1 rounded-md hover:bg-warning-200"
  >
    Solve
  </button>
)}
```

- [ ] **Step 2: Simplify normalization to trust canonical `checks` first**

In `renderValidationResult`, make first branch canonical:

```tsx
const normalizedChecks = {
  file_structure: checks?.file_structure,
  column_structure: checks?.column_structure,
  assessment_validation: checks?.assessment_validation,
  student_validation: checks?.student_validation,
  score_validation: checks?.score_validation,
}
```

Keep old `details` fallback only if `checks` missing:

```tsx
if (!checks) {
  // existing details-based fallback block stays here as compatibility fallback
}
```

- [ ] **Step 3: Add failing frontend integration test**

Create `frontend/src/test/file-upload-modal-resolution-flow.test.tsx`:

```tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import FileUploadModal from '@/features/courses/components/FileUploadModal'

vi.mock('@/shared/api/generated/core/core', async () => {
  const validateMutate = vi.fn(async () => ({
    is_valid: false,
    phase_reached: 'assessment_validation',
    checks: {
      file_structure: { passed: true },
      column_structure: { passed: true },
      assessment_validation: { passed: false, missing_assessments: [{ column: 'Quiz(%10)_X', parsed_name: 'Quiz' }] },
      student_validation: { passed: true },
      score_validation: { passed: true },
    },
    errors: [], warnings: [], suggestions: [], details: {},
  }))

  return {
    useCoreFileImportAssignmentScoresValidateCreate: () => ({ isPending: false, mutateAsync: validateMutate }),
    useCoreFileImportAssignmentScoresResolveCreate: () => ({ isPending: false, mutateAsync: vi.fn(async () => ({})) }),
    useCoreFileImportAssignmentScoresUploadCreate: () => ({ isPending: false, mutateAsync: vi.fn(async () => ({})) }),
    useCoreFileImportAssignmentScoresUploadRetrieve: () => ({ data: null }),
    useCoreFileImportLearningOutcomesUploadRetrieve: () => ({ data: null }),
    useCoreFileImportLearningOutcomesUploadCreate: () => ({ isPending: false, mutateAsync: vi.fn(async () => ({})) }),
    useCoreFileImportLearningOutcomesValidateCreate: () => ({ isPending: false, mutateAsync: vi.fn(async () => ({})) }),
    useCoreFileImportProgramOutcomesUploadRetrieve: () => ({ data: null }),
    useCoreFileImportProgramOutcomesUploadCreate: () => ({ isPending: false, mutateAsync: vi.fn(async () => ({})) }),
    useCoreFileImportProgramOutcomesValidateCreate: () => ({ isPending: false, mutateAsync: vi.fn(async () => ({})) }),
  }
})

describe('FileUploadModal solve flow', () => {
  it('opens assessment modal when Solve is clicked for failed assessment check', async () => {
    const user = userEvent.setup()
    render(
      <FileUploadModal
        course="CS101"
        courseCode="CS101"
        termId={1}
        isOpen={true}
        type="assignment_scores"
        onClose={() => {}}
      />
    )

    const input = screen.getByLabelText(/select file/i, { selector: 'input[type="file"]' }) as HTMLInputElement
    const file = new File(['dummy'], 'scores.xlsx', { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    await user.upload(input, file)
    await user.click(screen.getByRole('button', { name: /validate file/i }))

    await user.click(screen.getByRole('button', { name: /solve/i }))
    expect(screen.getByText(/missing assessments/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 4: Run frontend tests and build**

Run:
`cd frontend && npm run test -- --run src/test/ResolutionModals.test.tsx src/test/file-upload-modal-resolution-flow.test.tsx`

Then run:
`cd frontend && npm run build`

Expected: both tests PASS and build PASS.

- [ ] **Step 5: Commit frontend solve-flow wiring**

```bash
git add frontend/src/features/courses/components/FileUploadModal.tsx frontend/src/test/file-upload-modal-resolution-flow.test.tsx frontend/src/test/ResolutionModals.test.tsx
git commit -m "feat(frontend): wire solve flow to canonical assignment checks"
```

---

### Task 6: End-to-End Verification and Cleanup

**Files:**
- Modify (if required): `backend/student_evaluation_system/tests/test_file_import_validation.py`
- Modify (if required): `frontend/src/features/courses/components/FileUploadModal.tsx`

- [ ] **Step 1: Run full targeted backend suite**

Run:
`cd backend/student_evaluation_system && uv run pytest tests/test_validation_phases.py tests/test_file_import_validation.py tests/test_assignment_import_resolution_policy.py -q`

Expected: PASS.

- [ ] **Step 2: Run frontend verification suite**

Run:
`cd frontend && npm run test -- --run src/test/ResolutionModals.test.tsx src/test/file-upload-modal-resolution-flow.test.tsx && npm run build`

Expected: PASS.

- [ ] **Step 3: Remove dead assessment-specific internals if still unused**

Search:

```bash
cd backend/student_evaluation_system && uv run python - <<'PY'
from pathlib import Path
text = Path('core/services/validation.py').read_text()
for token in ['ASSESSMENT_SCORES', 'validate_assessment_scores_structure', 'validate_assessment_scores_database', 'validate_assessment_scores_quality']:
    print(token, token in text)
PY
```

If any token is unused and no tests rely on it, delete dead methods and re-run Task 6 Step 1.

- [ ] **Step 4: Final commit**

```bash
git add backend/student_evaluation_system/core/services/validation.py backend/student_evaluation_system/core/views/file_import.py backend/student_evaluation_system/core/services/file_import.py backend/student_evaluation_system/tests/test_validation_phases.py backend/student_evaluation_system/tests/test_file_import_validation.py backend/student_evaluation_system/tests/test_assignment_import_resolution_policy.py frontend/src/features/courses/components/FileUploadModal.tsx frontend/src/test/file-upload-modal-resolution-flow.test.tsx
git commit -m "refactor(file-import): unify assignment validation and resolution workflow"
```

---

## Spec Coverage Checklist

- [x] Assignment-only validation path (assessment duplicate removed)
- [x] Canonical `checks` response in validate and resolve
- [x] Resolve supports create/enroll/skip/clamp assignment keys
- [x] Upload honors selected skip/clamp policy
- [x] Frontend Solve flow is reachable and mapped to failed checks
- [x] Backend + frontend tests cover contract and interaction flow
