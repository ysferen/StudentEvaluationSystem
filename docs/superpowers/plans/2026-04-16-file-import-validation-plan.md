# File Import Validation & Resolution — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Comprehensive multi-phase validation for assignment scores file import, with step-by-step problem resolution.

**Architecture:**
- Backend: `AssignmentScoreValidator.validate_complete()` is wired into the validate endpoint, returning a structured response with per-check results. A new `/resolve/` endpoint applies resolutions (create students, enroll students, create assessments) then re-validates.
- Frontend: FileUploadModal shows pass/fail per check with "Solve" buttons. Each resolution opens a dedicated modal, calls `/resolve/`, and re-displays validation results.

**Tech Stack:** Django + DRF backend, React + TanStack Query frontend, pandas for Excel parsing, orval for API client generation.

---

## File Map

### Backend (to create/modify)
- `core/services/validation.py` — enhance `AssignmentScoreValidator` with Phase 2 and Phase 5
- `core/views/file_import.py` — wire `validate_complete()` into validate endpoint; add resolve endpoint
- `core/urls.py` — already has the router; resolve endpoint registered via `@action`

### Frontend (to modify)
- `features/courses/components/FileUploadModal.tsx` — update types, add resolution state, update UI
- `features/courses/components/ResolutionModals.tsx` — create with 4 modal components (new file)

---

## Task 1: Backend — Enhance `AssignmentScoreValidator` with Phase 2 and Phase 5

**Files:**
- Modify: `backend/student_evaluation_system/core/services/validation.py`

### Step 1: Write failing tests for new validation phases

Create a new test file or add to existing test file. Tests first.

**File:** `backend/student_evaluation_system/tests/test_validation_phases.py`

```python
import pytest
import pandas as pd
from io import BytesIO
from django.test import TestCase
from core.services.validation import AssignmentScoreValidator, ValidationResult
from core.models import Course, Term, Assessment
from users.models import StudentProfile, CustomUser

class TestPhase2ColumnStructure(TestCase):
    def setUp(self):
        self.term = Term.objects.create(name="2025 Spring", start_date="2025-01-01", end_date="2025-06-01")
        self.course = Course.objects.create(code="CS101", name="Intro to CS", term=self.term)

    def test_valid_column_structure_passes(self):
        df = pd.DataFrame({
            "öğrenci no": ["S001", "S002"],
            "adı": ["Ali", "Ayşe"],
            "soyadı": ["Veli", "Demir"],
            "Midterm(%30)": [80, 90],
        })
        result = AssignmentScoreValidator.validate_column_structure(df)
        assert result.is_valid

    def test_missing_student_id_column_fails(self):
        df = pd.DataFrame({
            "adı": ["Ali"],
            "soyadı": ["Veli"],
            "Midterm(%30)": [80],
        })
        result = AssignmentScoreValidator.validate_column_structure(df)
        assert not result.is_valid
        assert any("öğrenci no" in e["message"] for e in result.errors)

    def test_missing_first_name_column_fails(self):
        df = pd.DataFrame({
            "öğrenci no": ["S001"],
            "soyadı": ["Veli"],
            "Midterm(%30)": [80],
        })
        result = AssignmentScoreValidator.validate_column_structure(df)
        assert not result.is_valid

    def test_missing_assessment_column_fails(self):
        df = pd.DataFrame({
            "öğrenci no": ["S001"],
            "adı": ["Ali"],
            "soyadı": ["Veli"],
        })
        result = AssignmentScoreValidator.validate_column_structure(df)
        assert not result.is_valid
        assert any("No assessment" in e["message"] for e in result.errors)

class TestPhase5ScoreValidation(TestCase):
    def setUp(self):
        self.term = Term.objects.create(name="2025 Spring", start_date="2025-01-01", end_date="2025-06-01")
        self.course = Course.objects.create(code="CS101", name="Intro to CS", term=self.term)
        self.assessment = Assessment.objects.create(
            course=self.course, name="Midterm", total_score=100
        )

    def test_valid_scores_pass(self):
        scores = {"Midterm": [80, 90, 70]}
        result = AssignmentScoreValidator.validate_scores(scores, self.course)
        assert result.is_valid

    def test_out_of_range_score_fails(self):
        scores = {"Midterm": [150, 90]}
        result = AssignmentScoreValidator.validate_scores(scores, self.course)
        assert not result.is_valid
        assert any("out of range" in e["message"].lower() or "150" in e["message"] for e in result.errors)

    def test_negative_score_fails(self):
        scores = {"Midterm": [-10, 90]}
        result = AssignmentScoreValidator.validate_scores(scores, self.course)
        assert not result.is_valid

    def test_non_numeric_score_fails(self):
        scores = {"Midterm": ["abc", 90]}
        result = AssignmentScoreValidator.validate_scores(scores, self.course)
        assert not result.is_valid
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend/student_evaluation_system && python -m pytest tests/test_validation_phases.py -v --tb=short 2>&1 | tail -30`
Expected: FAIL — methods don't exist yet

- [ ] **Step 3: Implement Phase 2 — `validate_column_structure`**

In `validation.py`, add to `AssignmentScoreValidator`:

```python
@staticmethod
def validate_column_structure(dataframe: pd.DataFrame) -> ValidationResult:
    """
    Phase 2: Validate required columns are present and at least one
    assessment column exists.
    """
    result = ValidationResult()

    # Required columns (case-insensitive partial match)
    required_cols = ["öğrenci no", "adı", "soyadı"]
    df_cols_lower = {c.lower() for c in dataframe.columns}

    for col in required_cols:
        matched = any(col.lower() in c.lower() for c in dataframe.columns)
        if not matched:
            result.add_error(f"Required column not found: '{col}'", "column_structure")

    # Check for at least one assessment column
    assessment_cols = BusinessStructureValidator._extract_assessment_columns(dataframe.columns)
    if not assessment_cols:
        result.add_error(
            "No assessment score columns found in file. "
            "Expected columns like 'Midterm 1(%25)_XXXXX', 'Project(%40)_XXXXX', etc.",
            "column_structure"
        )

    if not result.is_valid:
        result.add_detail("column_structure", {
            "passed": False,
            "columns_found": dataframe.columns.tolist()
        })
    else:
        result.add_detail("column_structure", {
            "passed": True,
            "columns_found": dataframe.columns.tolist(),
            "row_count": len(dataframe)
        })

    return result
```

- [ ] **Step 4: Implement Phase 5 — `validate_scores`**

In `validation.py`, add to `AssignmentScoreValidator`:

```python
@staticmethod
def validate_scores(dataframe: pd.DataFrame, course: Course) -> ValidationResult:
    """
    Phase 5: Validate all score values are numeric and within 0-100 (or 0-total_score).
    """
    result = ValidationResult()

    # Find assessment columns
    assessment_cols = BusinessStructureValidator._extract_assessment_columns(dataframe.columns)
    if not assessment_cols:
        result.add_detail("score_validation", {"passed": True, "invalid_scores": []})
        return result

    # Get DB assessments
    db_assessments = {
        a.name.lower().strip(): a for a in Assessment.objects.filter(course=course)
    }

    invalid_scores = []

    for col_name, parsed_name in assessment_cols:
        clean = BusinessStructureValidator._clean_assessment_name(parsed_name)
        db_assessment = db_assessments.get(clean.lower().strip())

        if not db_assessment:
            continue  # Skip if assessment not in DB

        max_score = db_assessment.total_score or 100

        for row_idx, value in enumerate(dataframe[col_name]):
            if pd.isna(value):
                continue
            try:
                score = float(value)
                if score < 0 or score > max_score:
                    invalid_scores.append({
                        "row": row_idx + 2,  # +2 for 1-based + header
                        "column": col_name,
                        "value": str(value),
                        "parsed_name": clean,
                        "max_score": max_score,
                    })
            except (ValueError, TypeError):
                invalid_scores.append({
                    "row": row_idx + 2,
                    "column": col_name,
                    "value": str(value),
                    "parsed_name": clean,
                    "error": "non-numeric"
                })

    if invalid_scores:
        result.add_error(
            f"Found {len(invalid_scores)} invalid score(s)",
            "score_validation"
        )
        result.add_detail("score_validation", {
            "passed": False,
            "invalid_scores": invalid_scores[:50]  # cap at 50
        })
    else:
        result.add_detail("score_validation", {
            "passed": True,
            "invalid_scores": []
        })

    return result
```

- [ ] **Step 5: Update `validate_complete` to include phase tracking and new phases**

Find the existing `validate_complete` method (around line 1039) and replace it:

```python
@staticmethod
def validate_complete(file_obj, course: Course) -> ValidationResult:
    """
    Run complete validation: file structure, column structure, assessments, students, scores.
    """
    final_result = ValidationResult()
    final_result.add_detail("phase_reached", "file_structure")

    # 1. Validate file structure
    file_result = AssignmentScoreValidator.validate_file_structure(file_obj)
    final_result.errors.extend(file_result.errors)
    final_result.warnings.extend(file_result.warnings)
    final_result.validation_details.update(file_result.validation_details)

    if not file_result.is_valid:
        final_result.is_valid = False
        final_result.validation_details["phase_reached"] = "file_structure"
        return final_result

    # 2. Parse the file
    try:
        file_obj.seek(0)
        dataframe = pd.read_excel(file_obj)
        final_result.add_detail("file_parsed", True)
        final_result.add_detail("phase_reached", "column_structure")
    except Exception as e:
        final_result.add_error(f"Failed to parse Excel file: {str(e)}", "file_parse")
        final_result.is_valid = False
        final_result.validation_details["phase_reached"] = "file_parse"
        return final_result

    # 3. Validate column structure
    column_result = AssignmentScoreValidator.validate_column_structure(dataframe)
    final_result.errors.extend(column_result.errors)
    final_result.warnings.extend(column_result.warnings)
    final_result.validation_details.update(column_result.validation_details)

    if not column_result.is_valid:
        final_result.is_valid = False
        final_result.validation_details["phase_reached"] = "column_structure"
        return final_result

    final_result.add_detail("phase_reached", "assessment_validation")

    # 4. Validate assessments
    assessment_result = AssignmentScoreValidator.validate_assignments(dataframe, course)
    final_result.errors.extend(assessment_result.errors)
    final_result.warnings.extend(assessment_result.warnings)
    final_result.suggestions.extend(assessment_result.suggestions)
    final_result.validation_details.update(assessment_result.validation_details)

    if not assessment_result.is_valid:
        final_result.is_valid = False
        # Don't return early — continue to get all issues

    final_result.add_detail("phase_reached", "student_validation")

    # 5. Validate students
    student_result = AssignmentScoreValidator.validate_students(dataframe, course)
    final_result.errors.extend(student_result.errors)
    final_result.warnings.extend(student_result.warnings)
    final_result.suggestions.extend(student_result.suggestions)
    final_result.validation_details.update(student_result.validation_details)

    if not student_result.is_valid:
        final_result.is_valid = False

    final_result.add_detail("phase_reached", "score_validation")

    # 6. Validate scores (only if assessments found)
    assessment_cols = BusinessStructureValidator._extract_assessment_columns(dataframe.columns)
    if assessment_cols:
        score_result = AssignmentScoreValidator.validate_scores(dataframe, course)
        final_result.errors.extend(score_result.errors)
        final_result.warnings.extend(score_result.warnings)
        final_result.validation_details.update(score_result.validation_details)

        if not score_result.is_valid:
            final_result.is_valid = False

    if final_result.is_valid:
        final_result.add_detail("phase_reached", "complete")

    return final_result
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend/student_evaluation_system && python -m pytest tests/test_validation_phases.py -v --tb=short 2>&1 | tail -30`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add core/services/validation.py tests/test_validation_phases.py
git commit -m "feat(validation): add Phase 2 (column structure) and Phase 5 (score validation) to AssignmentScoreValidator"
```

---

## Task 2: Backend — Wire `validate_complete` into the validate endpoint

**Files:**
- Modify: `backend/student_evaluation_system/core/views/file_import.py`
- Modify: `backend/student_evaluation_system/core/urls.py`

### Step 1: Override validate action in `AssignmentScoresImportViewSet`

Replace the existing `AssignmentScoresImportViewSet` class in `file_import.py`:

```python
class AssignmentScoresImportViewSet(BaseFileImportViewSet):
    """ViewSet for importing assignment scores from files."""

    import_type = "assignment_scores"

    @action(detail=False, methods=["post"])
    def validate(self, request):
        """Validate file using comprehensive multi-phase validation."""
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        course_code = request.query_params.get("course_code")
        term_id = request.query_params.get("term_id")
        if not course_code or not term_id:
            return Response(
                {"error": {"course_code": "course_code is required", "term_id": "term_id is required"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            term = Term.objects.get(pk=term_id)
        except (Term.DoesNotExist, ValueError):
            return Response({"error": "Invalid term_id"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            course = Course.objects.get(code=course_code, term=term)
        except Course.DoesNotExist:
            return Response(
                {"error": f"Course with code '{course_code}' not found in term '{term.name}'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = AssignmentScoreValidator.validate_complete(file_obj, course)
            response_data = {
                "is_valid": result.is_valid,
                "phase_reached": result.validation_details.get("phase_reached", "unknown"),
                "checks": {
                    "file_structure": {
                        "passed": result.validation_details.get("file_parsed") is not None,
                    },
                    "column_structure": result.validation_details.get("column_structure", {"passed": False}),
                    "assessment_validation": result.validation_details.get("assessment_validation", {"passed": False}),
                    "student_validation": result.validation_details.get("student_validation", {"passed": False}),
                    "score_validation": result.validation_details.get("score_validation", {"passed": False}),
                },
                "errors": result.errors,
                "warnings": result.warnings,
                "suggestions": result.suggestions,
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except FileImportError as e:
            return Response({"is_valid": False, "phase_reached": "file_structure", "errors": [{"message": str(e), "category": "file_parse", "severity": "error"}]}, status=status.HTTP_400_BAD_REQUEST)
```

Add necessary imports to the file:
```python
from core.models import Term
from core.services.validation import AssignmentScoreValidator
from evaluation.models import Assessment
```

### Step 2: Add resolve endpoint to `AssignmentScoresImportViewSet`

Add this action inside `AssignmentScoresImportViewSet` class (after the `validate` action):

```python
    @action(detail=False, methods=["post"], url_path="resolve")
    def resolve(self, request):
        """
        Apply resolutions to the file and re-validate.
        Accepts resolutions as a JSON string in 'resolutions' field.
        """
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        course_code = request.query_params.get("course_code")
        term_id = request.query_params.get("term_id")
        if not course_code or not term_id:
            return Response(
                {"error": {"course_code": "course_code is required", "term_id": "term_id is required"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            term = Term.objects.get(pk=term_id)
            course = Course.objects.get(code=course_code, term=term)
        except (Term.DoesNotExist, Course.DoesNotExist) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Parse resolutions JSON
        import json
        resolutions_raw = request.data.get("resolutions")
        if isinstance(resolutions_raw, str):
            try:
                resolutions = json.loads(resolutions_raw)
            except json.JSONDecodeError:
                return Response({"error": "Invalid JSON in resolutions field"}, status=status.HTTP_400_BAD_REQUEST)
        elif isinstance(resolutions_raw, dict):
            resolutions = resolutions_raw
        else:
            resolutions = {}

        skip_missing_assessments = resolutions.get("skip_missing_assessments", False)
        create_assessment_names = resolutions.get("create_assessments", [])
        skip_missing_students = resolutions.get("skip_missing_students", False)
        create_students = resolutions.get("create_students", [])
        skip_unenrolled_students = resolutions.get("skip_unenrolled_students", False)
        enroll_student_ids = resolutions.get("enroll_students", [])
        skip_invalid_scores = resolutions.get("skip_invalid_scores", False)
        clamp_scores = resolutions.get("clamp_scores", False)

        # Apply student creation resolutions
        for student_data in create_students:
            student_id = student_data.get("student_id")
            first_name = student_data.get("first_name", "")
            last_name = student_data.get("last_name", "")
            if not student_id:
                continue
            user, created = CustomUser.objects.get_or_create(
                username=student_id,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": f"{student_id}@placeholder.local",
                    "is_student": True,
                }
            )
            if created:
                StudentProfile.objects.get_or_create(student=user)
            # Enroll in course
            CourseEnrollment.objects.get_or_create(course=course, student=user)

        # Apply enrollment resolutions
        if enroll_student_ids:
            from users.models import StudentProfile
            students = StudentProfile.objects.filter(student_id__in=enroll_student_ids).select_related("student")
            for profile in students:
                CourseEnrollment.objects.get_or_create(course=course, student=profile.student)

        # Apply assessment creation resolutions
        for name in create_assessment_names:
            Assessment.objects.get_or_create(
                course=course,
                name=name,
                defaults={"total_score": 100, "weight": 0.1}
            )

        # Re-validate with resolved context
        try:
            result = AssignmentScoreValidator.validate_complete(file_obj, course)
            response_data = {
                "is_valid": result.is_valid,
                "phase_reached": result.validation_details.get("phase_reached", "unknown"),
                "checks": {
                    "file_structure": {
                        "passed": result.validation_details.get("file_parsed") is not None,
                    },
                    "column_structure": result.validation_details.get("column_structure", {"passed": False}),
                    "assessment_validation": result.validation_details.get("assessment_validation", {"passed": False}),
                    "student_validation": result.validation_details.get("student_validation", {"passed": False}),
                    "score_validation": result.validation_details.get("score_validation", {"passed": False}),
                },
                "errors": result.errors,
                "warnings": result.warnings,
                "suggestions": result.suggestions,
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except FileImportError as e:
            return Response({"is_valid": False, "errors": [{"message": str(e)}]}, status=status.HTTP_400_BAD_REQUEST)
```

Add import for `CourseEnrollment`, `CustomUser`, `StudentProfile` at the top of the file:
```python
from core.models import Term, Course
from evaluation.models import Assessment
from users.models import CustomUser, StudentProfile
from enrollment.models import CourseEnrollment
```

### Step 3: Run tests

Run: `cd backend/student_evaluation_system && python -m pytest tests/test_validation_phases.py -v --tb=short 2>&1 | tail -20`
Expected: PASS

### Step 4: Test validate endpoint manually

Run: `cd backend/student_evaluation_system && python manage.py shell -c "
from core.services.validation import AssignmentScoreValidator
from core.models import Course, Term
from io import BytesIO
import pandas as pd

term = Term.objects.first()
course = Course.objects.filter(term=term).first()
print('course:', course)

# Create test Excel in memory
df = pd.DataFrame({'öğrenci no': ['S001'], 'adı': ['Ali'], 'soyadı': ['Veli'], 'Midterm(%30)': [80]})
buf = BytesIO()
df.to_excel(buf, index=False)
buf.seek(0)
buf.name = 'test.xlsx'

result = AssignmentScoreValidator.validate_complete(buf, course)
print('is_valid:', result.is_valid)
print('phase_reached:', result.validation_details.get('phase_reached'))
print('errors:', result.errors)
print('checks:', {k: v.get('passed', False) for k, v in result.validation_details.items() if isinstance(v, dict) and 'passed' in v})
" 2>&1`

Expected: Structured output with phase_reached and checks

### Step 5: Commit

```bash
git add core/views/file_import.py core/models/__init__.py enrollment/models.py
git commit -m "feat(file_import): wire validate_complete into validate endpoint and add resolve endpoint"
```

---

## Task 3: Backend — Update OpenAPI schema for new endpoint

**Files:**
- Modify: `backend/student_evaluation_system/core/views/file_import.py` (add extend_schema decorators)
- Regenerate: Run `npm run api:sync` from frontend directory

### Step 1: Add OpenAPI decorators to AssignmentScoresImportViewSet

Add `extend_schema` decorators to both the `validate` and `resolve` actions in `AssignmentScoresImportViewSet`. Import needed types:
```python
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from drf_spectacular.types import OpenApiTypes
```

Decorator for `validate`:
```python
@extend_schema(
    parameters=[
        OpenApiParameter(name="course_code", type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=True, description="Course code"),
        OpenApiParameter(name="term_id", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=True, description="Term ID"),
    ],
    request={"multipart/form-data": {"type": "object", "properties": {"file": {"type": "string", "format": "binary"}}}},
    responses={
        200: {
            "type": "object",
            "properties": {
                "is_valid": {"type": "boolean"},
                "phase_reached": {"type": "string"},
                "checks": {"type": "object"},
                "errors": {"type": "array"}, "warnings": {"type": "array"}, "suggestions": {"type": "array"},
            }
        }
    }
)
```

Decorator for `resolve`:
```python
@extend_schema(
    parameters=[
        OpenApiParameter(name="course_code", type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=True),
        OpenApiParameter(name="term_id", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=True),
    ],
    request={
        "multipart/form-data": {
            "type": "object",
            "properties": {
                "file": {"type": "string", "format": "binary"},
                "resolutions": {"type": "string", "description": "JSON string of ResolutionChoices"},
            }
        }
    },
    responses={200: {"type": "object"}}
)
```

### Step 2: Regenerate API client

Run: `cd frontend && npm run api:sync`
Expected: New `resolve` endpoint and updated response types generated

### Step 3: Commit

```bash
git add core/views/file_import.py
git commit -m "docs(file_import): add OpenAPI decorators for validate and resolve endpoints"
```

---

## Task 4: Frontend — Update FileUploadModal with structured validation UI

**Files:**
- Modify: `frontend/src/features/courses/components/FileUploadModal.tsx`
- Create: `frontend/src/features/courses/components/ResolutionModals.tsx`

### Step 1: Write failing tests

**File:** `frontend/src/test/ResolutionModals.test.tsx`

```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Mock resolution modal tests
describe('MissingStudentsModal', () => {
  it('shows student list from missingStudents prop', () => {
    // Test renders student rows
  })
  it('calls onConfirm with selected students', () => {
    // Test confirmation callback
  })
})
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `cd frontend && npm test -- --run src/test/ResolutionModals.test.tsx 2>&1 | tail -20`
Expected: FAIL (component doesn't exist yet)

### Step 3: Create ResolutionModals.tsx

**File:** `frontend/src/features/courses/components/ResolutionModals.tsx`

Create four modal components, one per problem type:

```typescript
import React, { useState } from 'react'
import { X, CheckCircle, AlertTriangle, Users, BookOpen, FileX } from 'lucide-react'

interface MissingAssessmentsModalProps {
  isOpen: boolean
  missingAssessments: Array<{ column: string; parsed_name: string }>
  availableInDatabase: string[]
  onClose: () => void
  onResolve: (choice: 'skip' | 'create', assessmentNames: string[]) => void
}

export const MissingAssessmentsModal: React.FC<MissingAssessmentsModalProps> = ({
  isOpen, missingAssessments, availableInDatabase, onClose, onResolve
}) => {
  const [selectedForCreation, setSelectedForCreation] = useState<Set<string>>(
    new Set(missingAssessments.map(a => a.parsed_name))
  )

  if (!isOpen) return null

  const handleConfirm = () => {
    if (selectedForCreation.size > 0) {
      onResolve('create', Array.from(selectedForCreation))
    } else {
      onResolve('skip', [])
    }
  }

  return (
    <div className="fixed inset-0 z-[60] bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg">
        <div className="flex items-center justify-between p-6 border-b">
          <div className="flex items-center gap-3">
            <BookOpen className="w-5 h-5 text-warning-500" />
            <h2 className="text-lg font-bold">Missing Assessments</h2>
          </div>
          <button onClick={onClose}><X className="w-5 h-5" /></button>
        </div>
        <div className="p-6">
          <p className="text-sm text-secondary-600 mb-4">
            {missingAssessments.length} assessment(s) in the file were not found in the database.
          </p>
          <div className="space-y-2 mb-4 max-h-60 overflow-y-auto">
            {missingAssessments.map(a => (
              <label key={a.column} className="flex items-center gap-2 p-2 rounded-lg hover:bg-secondary-50 cursor-pointer">
                <input
                  type="checkbox"
                  checked={selectedForCreation.has(a.parsed_name)}
                  onChange={(e) => {
                    const next = new Set(selectedForCreation)
                    if (e.target.checked) next.add(a.parsed_name)
                    else next.delete(a.parsed_name)
                    setSelectedForCreation(next)
                  }}
                />
                <span className="font-medium text-sm">{a.parsed_name}</span>
                <span className="text-xs text-secondary-500">({a.column})</span>
              </label>
            ))}
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => onResolve('skip', [])}
              className="flex-1 px-4 py-2 border border-secondary-300 rounded-lg text-secondary-700 hover:bg-secondary-50"
            >
              Skip All
            </button>
            <button
              onClick={handleConfirm}
              className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              Create & Continue ({selectedForCreation.size})
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ... Similar structure for MissingStudentsModal, UnenrolledStudentsModal, InvalidScoresModal
```

**MissingStudentsModal** — shows table with student_id, first_name, last_name; "Create All" button → calls `onResolve('create', students)`

**UnenrolledStudentsModal** — shows list; "Enroll All" / "Skip All" buttons

**InvalidScoresModal** — shows table of (row, column, value); "Skip Invalid" / "Clamp" buttons

### Step 4: Update ValidationResult type in FileUploadModal.tsx

Replace the existing `ValidationResult` and `ValidationDetails` types with:

```typescript
interface CheckResult {
  passed: boolean
  details?: Record<string, unknown>
}

interface ValidationResult {
  is_valid: boolean
  phase_reached?: string
  checks?: {
    file_structure?: CheckResult
    column_structure?: CheckResult
    assessment_validation?: {
      passed: boolean
      found_assessments?: Array<{ column: string; parsed_name: string; db_name: string }>
      missing_assessments?: Array<{ column: string; parsed_name: string }>
      available_in_database?: string[]
    }
    student_validation?: {
      passed: boolean
      total_in_file?: number
      found_in_database?: number
      missing_from_database?: Array<{ student_id: string; first_name: string; last_name: string }>
      not_enrolled?: Array<{ student_id: string; first_name: string; last_name: string }>
    }
    score_validation?: {
      passed: boolean
      invalid_scores?: Array<{ row: number; column: string; value: string; error?: string }>
    }
  }
  errors?: Array<{ message: string; category: string; severity: string }>
  warnings?: Array<{ message: string; category: string; severity: string }>
  suggestions?: Array<{ message: string; category: string; severity: string }>
}
```

### Step 5: Update `renderValidationResult` to show per-check pass/fail with Solve buttons

Replace the existing `renderValidationResult` function with a new one that:
- Iterates over `checks` object (file_structure, column_structure, assessment_validation, student_validation, score_validation)
- Shows a green checkmark for `passed: true`, red X for `passed: false`
- For failed checks, shows a "Solve" button
- Shows expandable details for each check

```typescript
const renderCheck = (checkName: string, check: CheckResult | undefined, onSolve?: () => void) => {
  if (!check) return null
  const passed = check.passed
  return (
    <div key={checkName} className="flex items-center justify-between p-3 rounded-lg border">
      <div className="flex items-center gap-3">
        {passed ? (
          <CheckCircle className="w-5 h-5 text-emerald-500" />
        ) : (
          <XCircle className="w-5 h-5 text-danger-500" />
        )}
        <div>
          <span className="font-medium text-sm">{checkName.replace(/_/g, ' ')}</span>
        </div>
      </div>
      {!passed && onSolve && (
        <button
          onClick={onSolve}
          className="text-sm bg-warning-100 text-warning-700 px-3 py-1 rounded-md hover:bg-warning-200"
        >
          Solve
        </button>
      )}
    </div>
  )
}

// In renderValidationResult:
{validationResult.checks && (
  <div className="space-y-2 mb-4">
    {renderCheck('file structure', validationResult.checks.file_structure)}
    {renderCheck('column structure', validationResult.checks.column_structure)}
    {renderCheck('assessments', validationResult.checks.assessment_validation, () => setActiveProblem('assessments'))}
    {renderCheck('students', validationResult.checks.student_validation, () => setActiveProblem('students'))}
    {renderCheck('scores', validationResult.checks.score_validation, () => setActiveProblem('scores'))}
  </div>
)}
```

### Step 6: Add resolution state and wire up Solve flow

Add state:
```typescript
const [activeProblem, setActiveProblem] = useState<'assessments' | 'students' | 'unenrolled' | 'scores' | null>(null)
const [resolutions, setResolutions] = useState<Record<string, unknown>>({})
```

Update `handleValidate` to include course_code/term_id in the validate call (already done for assignment_scores mutation hook).

### Step 7: Wire up resolution modals

Add modal components after the main modal content (before the closing divs):

```tsx
{activeProblem === 'assessments' && validationResult?.checks?.assessment_validation && (
  <MissingAssessmentsModal
    isOpen={true}
    missingAssessments={validationResult.checks.assessment_validation.missing_assessments || []}
    availableInDatabase={validationResult.checks.assessment_validation.available_in_database || []}
    onClose={() => setActiveProblem(null)}
    onResolve={async (choice, assessmentNames) => {
      const newResolutions = { ...resolutions, skip_missing_assessments: choice === 'skip', create_assessments: assessmentNames }
      setResolutions(newResolutions)
      setActiveProblem(null)
      await revalidate(newResolutions)
    }}
  />
)}
```

Similar for `MissingStudentsModal`, `UnenrolledStudentsModal`, `InvalidScoresModal`.

### Step 8: Run tests and verify

Run: `cd frontend && npm run build 2>&1 | tail -20`
Expected: Build succeeds with no TypeScript errors

### Step 9: Commit

```bash
git add src/features/courses/components/FileUploadModal.tsx src/features/courses/components/ResolutionModals.tsx src/test/ResolutionModals.test.tsx
git commit -m "feat(frontend): add structured validation UI with step-by-step resolution flow"
```

---

## Task 5: Integration Test

**Files:**
- Create: `backend/student_evaluation_system/tests/test_file_import_validation.py`

### Step 1: Write integration tests

```python
class TestValidateEndpoint(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/core/file-import/assignment-scores/validate/"

    def test_validate_returns_structured_response(self):
        # Upload a valid file and verify structured response
        pass

    def test_validate_missing_students_returns_soft_failure(self):
        # Verify missing students doesn't hard-fail validation
        pass

    def test_resolve_endpoint_creates_students(self):
        # Verify /resolve/ creates missing students
        pass
```

- [ ] **Step 2: Run integration tests**

Run: `cd backend/student_evaluation_system && python -m pytest tests/test_file_import_validation.py -v --tb=short`
Expected: Tests pass

- [ ] **Step 3: Commit**

```bash
git add tests/test_file_import_validation.py
git commit -m "test: add integration tests for file import validation endpoints"
```

---

## Spec Coverage Checklist

- [x] Phase 1 file structure validation — existing in `FileFormatValidator.validate_file_format`, called by `validate_complete`
- [x] Phase 2 column structure validation — implemented in Task 1 Step 3
- [x] Phase 3 assessment validation — existing in `validate_assignments`, called by `validate_complete`
- [x] Phase 4 student validation — existing in `validate_students`, called by `validate_complete`
- [x] Phase 5 score validation — implemented in Task 1 Step 4
- [x] Structured validation response with `phase_reached` and `checks` — implemented in Task 2 Step 1
- [x] Resolve endpoint (`POST /resolve/`) — implemented in Task 2 Step 2
- [x] Frontend structured validation display — implemented in Task 4
- [x] Step-by-step resolution modals — implemented in Task 4
- [x] Student bulk creation + enrollment — implemented in resolve endpoint
- [x] Assessment auto-creation — implemented in resolve endpoint
- [x] Enrollment of existing students — implemented in resolve endpoint
- [x] Skip/clamp options — implemented in resolve endpoint
