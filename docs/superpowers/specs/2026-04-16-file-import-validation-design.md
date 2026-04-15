# File Import Validation & Resolution — Design

**Date:** 2026-04-16
**Status:** Approved

---

## Overview

The file import system for assignment scores currently validates only file format and size. This design introduces comprehensive, multi-phase validation with structured error reporting and a step-by-step resolution flow so instructors can fix problems before importing.

---

## Validation Pipeline

Validation runs in five ordered phases. Each phase either **passes** or **fails** (hard stop for early phases, soft pass for later ones).

### Phase 1 — File Structure (hard stop on failure)
- File extension: `.xlsx`, `.xls`
- File size: max 10MB
- Parseable as Excel (pandas `read_excel`)
- **Failure here stops all further checks**

### Phase 2 — Column Structure (hard stop on failure)
- Required columns present (case-insensitive partial match):
  - `öğrenci no` (student ID)
  - `adı` (first name)
  - `soyadı` (last name)
- At least one assessment score column detected
- **Failure here stops all further checks**

### Phase 3 — Assessment Validation (soft failure)
- Parse assessment names from all columns (strips `_XXXX` suffixes and `(%NN)` weight patterns per existing logic)
- Match parsed names against `Assessment.objects.filter(course=course)` in DB
- Report: found assessments (matched), missing assessments (not in DB), available assessments (all in DB)
- **Continues to next phase even on failure**

### Phase 4 — Student Validation (soft failure)
- Extract student IDs from `öğrenci no` column
- Cross-reference against `StudentProfile.objects.filter(student_id__in=...)`
- Cross-reference enrolled students against `CourseEnrollment.objects.filter(course=course)`
- Report per student:
  - Found in DB (yes/no)
  - Enrolled in course (yes/no)
  - Name extracted from file (`adı`, `soyadı`)
- **Continues to next phase even on failure**

### Phase 5 — Score Validation (soft failure)
- For each found+enrolled student × found assessment cell:
  - Check value is numeric
  - Check value is within 0–100 (or 0–`assessment.total_score` if capped)
- Report: list of `(row, column, value)` for invalid scores
- **Continues to next phase even on failure**

---

## Validation Response Shape

```json
{
  "is_valid": false,
  "phase_reached": "student_validation",
  "checks": {
    "file_structure": {
      "passed": true
    },
    "column_structure": {
      "passed": true,
      "details": {
        "row_count": 45,
        "columns": ["öğrenci no", "adı", "soyadı", "Midterm(%30)_ABC"]
      }
    },
    "assessment_validation": {
      "passed": false,
      "found_assessments": [
        {"column": "Midterm(%30)_ABC", "parsed_name": "Midterm", "db_name": "Midterm Exam"}
      ],
      "missing_assessments": [
        {"column": "Quiz(%10)_XYZ", "parsed_name": "Quiz"}
      ],
      "available_in_database": ["Midterm Exam", "Final Exam", "Project"]
    },
    "student_validation": {
      "passed": false,
      "total_in_file": 45,
      "found_in_database": 43,
      "missing_from_database": [
        {"student_id": "S1234", "first_name": "Ali", "last_name": "Veli"},
        {"student_id": "S5678", "first_name": "Ayşe", "last_name": "Demir"}
      ],
      "enrolled_in_course": 41,
      "not_enrolled": [
        {"student_id": "S9012", "first_name": "Mehmet", "last_name": "Yılmaz"}
      ]
    },
    "score_validation": {
      "passed": true,
      "invalid_scores": []
    }
  }
}
```

`phase_reached` indicates the first phase that failed, or `"complete"` if all phases ran.

---

## Resolution Flow

### Step-by-step modal

1. Instructor uploads file and clicks **Validate File**
2. Validation results shown in a structured panel:
   - Each check shows a pass/fail badge
   - Failed checks show details and a **"Solve"** button
3. Instructor clicks "Solve" on the first problem → resolution modal opens
4. Instructor chooses a resolution, confirms
5. Backend applies resolution + re-validates
6. Updated validation result shown; instructor moves to next problem
7. When all problems are **resolved** or **explicitly skipped**, "Upload & Import" becomes active

### Resolution Types

#### Problem: Missing Assessments
**Trigger:** `assessment_validation.passed == false`

| Option | Behavior |
|--------|----------|
| Skip missing | Import only scores for found assessments; ignore missing columns |
| Auto-create | Create each missing assessment in DB with parsed name and default weight (10%), then proceed |

#### Problem: Missing Students (not in DB)
**Trigger:** `student_validation.missing_from_database` is non-empty

| Option | Behavior |
|--------|----------|
| Skip missing | Import only scores for students that exist in DB; ignore others |
| Bulk review then create | Show confirmation table with pre-filled data (student_id, first_name, last_name). Instructor reviews and clicks **Confirm** → creates user accounts with `username=student_id`, generated password, `StudentProfile`, and enrolls them in the course |

#### Problem: Unenrolled Students (in DB but not in course)
**Trigger:** `student_validation.not_enrolled` is non-empty

| Option | Behavior |
|--------|----------|
| Skip | Import only scores for enrolled students; ignore others |
| Auto-enroll | Add `CourseEnrollment` records for these students, then proceed |

#### Problem: Invalid Scores
**Trigger:** `score_validation.invalid_scores` is non-empty

| Option | Behavior |
|--------|----------|
| Skip invalid rows | Import only rows with valid scores |
| Clamp to range | Clamp out-of-range scores to 0–100 (or assessment max), then import |

---

## Backend Changes

### Wire `validate_complete()` into the validate endpoint

**Endpoint:** `POST /api/core/file-import/assignment-scores/validate/`
**Query params:** `course_code`, `term_id` (required)

Change: the view's `validate_file()` action calls `AssignmentScoreValidator.validate_complete(file_obj, course)` instead of just `validate_file()`. The validator already produces the structured `ValidationResult` needed — the view serializes it to the response shape above.

### New resolve endpoint

**Endpoint:** `POST /api/core/file-import/assignment-scores/resolve/`
**Query params:** `course_code`, `term_id` (required)
**Body (multipart/form-data):**
```
file: <File>
resolutions: JSON string of ResolutionChoices
```

**ResolutionChoices schema:**
```json
{
  "skip_missing_assessments": true,
  "create_assessments": ["Quiz"],          // names to auto-create
  "skip_missing_students": true,
  "create_students": [                     // ignored if skip_missing_students=true
    {"student_id": "S1234", "first_name": "Ali", "last_name": "Veli"}
  ],
  "skip_unenrolled_students": true,
  "enroll_students": ["S9012"],            // ignored if skip_unenrolled_students=true
  "skip_invalid_scores": true,
  "clamp_scores": false
}
```

**Behavior:**
1. Parse file
2. Apply resolutions in order: create students → enroll students → create assessments
3. Re-validate with resolved context
4. Return updated validation result

### Student creation behavior

When `create_students` is provided:
- For each entry: look up `CustomUser` by `username=student_id`
  - If exists: skip (don't recreate)
  - If not: create with `username=student_id`, `email={student_id}@placeholder.local`, `first_name`, `last_name`, `is_student=True`, random password (never returned)
- Create `StudentProfile` linking to user
- Create `CourseEnrollment` linking user + course

---

## Frontend Changes

### FileUploadModal — Validation Panel

State changes:
```typescript
interface ValidationResult {
  is_valid: boolean
  phase_reached: string
  checks: {
    file_structure: { passed: boolean }
    column_structure: { passed: boolean; details?: {...} }
    assessment_validation: { passed: boolean; found_assessments?: [...]; missing_assessments?: [...]; available_in_database?: string[] }
    student_validation: { passed: boolean; total_in_file?: number; found_in_database?: number; missing_from_database?: [...]; not_enrolled?: [...] }
    score_validation: { passed: boolean; invalid_scores?: [...] }
  }
}
```

After "Validate File":
- Show structured panel with pass/fail badge per check
- Expandable details for failed checks
- "Solve" button per failed check

### Resolution Modals

Four modal types (one per problem type):

1. **MissingAssessmentsModal** — checklist of missing assessments; toggle each to create or skip
2. **MissingStudentsModal** — table with student_id, first_name, last_name from file; "Create All" button (opens confirmation)
3. **UnenrolledStudentsModal** — list with "Enroll All" / "Skip All"
4. **InvalidScoresModal** — table of invalid (row, column, value) entries; "Skip Invalid" / "Clamp" buttons

### Solve Flow

1. Instructor clicks "Solve" → modal opens with resolution options
2. Instructor selects option(s), confirms
3. `FormData` with file + resolutions JSON sent to `/resolve/`
4. Response is new `ValidationResult` → update UI
5. Repeat for next problem

---

## Open Questions / Future

- [ ] Learning outcomes and program outcomes imports currently have no per-row validation. Extending this framework to those imports is out of scope for this phase.
- [ ] Email notification to students when accounts are auto-created is out of scope.
- [ ] Audit log of who imported what and when is out of scope.
