# Course Edit/Create Modal Design

## Overview
Add edit and delete buttons to the Course Detail page with permission checks, and implement two course creation flows (blank vs from template).

## Permissions
- **Edit button**: Shown if user has `courses.change_course` permission
- **Delete button**: Shown if user has `courses.delete_course` permission

## Edit Course Modal

### Fields
| Field | Type | Notes |
|-------|------|-------|
| name | CharField(255) | Required |
| code | CharField(10) | Required, unique per program+term |
| credits | PositiveIntegerField | Default 3 |

### Excluded (editable later via dedicated UI)
- instructors, learning outcomes, assessments, students — handled in respective sections of Course Detail

---

## Create Course Modal — Two Flows

### Flow Selection
Radio toggle: "Blank course" | "From template"

### Common Fields (both flows)
| Field | Type | Notes |
|-------|------|-------|
| name | CharField(255) | Required |
| code | CharField(10) | Required |
| credits | PositiveIntegerField | Default 3 |
| program_option | enum | "My program" / "Select from list" |
| program_id | ForeignKey | Required if "Select from list" |
| term_option | enum | "Active term" / "Select from list" |
| term_id | ForeignKey | Required if "Select from list" |

### Blank Course Flow
- Fields above
- On success: Show dialog "Would you like to create a corresponding template for this course?"

### From Template Flow
- Additional field: `course_template_id` (required)
- Pre-populates: LOs, assessments, mappings (cloned on instantiation)

---

## API Changes Needed
- Backend: `PATCH /api/core/courses/{id}/` — partial update (name, code, credits)
- Backend: `DELETE /api/core/courses/{id}/` — delete course
- Frontend: New `patchCourse` and `deleteCourse` Orval generated functions

## File Changes
- `frontend/src/features/courses/pages/CourseDetail.tsx` — add buttons, modal
- `backend/student_evaluation_system/core/views/courses.py` — PATCH action (if not already present)
- Schema sync frontend/schema.yml
