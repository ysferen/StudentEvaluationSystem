# Auto-Create Instructor Permissions on Course Assignment

**Date:** 2026-04-29
**Status:** Approved

## Problem

The head's permissions page (`/head/permissions`) shows no objects because `InstructorPermission` rows don't exist in the database. Permissions must be created manually through the bulk_set endpoint, but there's no automatic seeding when instructors are added to courses.

## Solution

Auto-create default "view" permissions for all 8 resource areas when an instructor is first added to a course in a program head's program.

## Design

### 1. Signal handler (`core/signals.py` — new file)

Listen to `m2m_changed` on `Course.instructors.through` for `post_add`:

- When instructors are added to a course (`action == "post_add"`)
- Get `course.program.program_head_profile` to find the program head
- If no program head exists for the course's program, skip silently
- For each added instructor ID in `pk_set`, call `get_or_create` for all 8 `ResourceArea` values with `permission_tier="view"`, scoped to `instructor` and `program_head`

### 2. AppConfig registration (`core/apps.py`)

Add `ready()` method that imports `core.signals` to register the handler.

### 3. Data migration (`core/migrations/`)

A migration with `RunPython` that backfills permissions for all existing `Course` → `instructor` → `program.program_head_profile` relationships using the same `get_or_create` logic.

### Key properties

- **Idempotent:** `get_or_create` ensures no duplicates if signal fires multiple times
- **Scoped:** Each permission row is associated with the specific program_head who oversees the course's program
- **Silent failure:** If a course has no program or no program head, no permissions are created — this is fine because permissions are only needed for head-managed programs
- **Default tier:** All permissions start as "view" — heads use the permissions page to upgrade instructors' access

## Files changed

| File | Change |
|------|--------|
| `core/signals.py` | New — m2m_changed handler |
| `core/apps.py` | Add `ready()` to import signals |
| `core/migrations/XXXX_auto_create_instructor_permissions.py` | New — data migration |
