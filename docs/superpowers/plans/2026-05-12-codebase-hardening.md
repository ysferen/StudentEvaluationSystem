# Codebase Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Address the 9 remaining HIGH/MEDIUM priority issues from the 2026-04-29 codebase evaluation — batch analytics queries, component extraction, type guard deduplication, error UX, React Router fixes, memoization, directory consolidation, and auth loading split.

**Architecture:** All 9 tasks are independent (different files, zero shared state). They can be executed in any order and in parallel by different engineers. Each task is self-contained with its own test→implement→commit cycle.

**Tech Stack:** Django REST Framework, React/TypeScript, React Query, React Router v6, Tailwind CSS

**Pre-requisite:** None — these are standalone improvements to existing code. Plan C (SSE) and Plan B (Next Term) are not required.

---

## File Structure

| Task | Files Affected |
|------|---------------|
| H1 | `backend/.../core/views/analytics.py`, `tests/test_analytics.py` |
| M4 | `frontend/src/shared/utils/guards.ts` (NEW), 6 consumer files |
| M3 | `frontend/src/features/courses/pages/CourseDetail.tsx` |
| M5 | `CourseDetail.tsx`, `StudentDashboard.tsx`, `InstructorCourses.tsx`, `HeadDashboard.tsx` |
| M6 | `useAuth.ts`, `Sidebar.tsx` |
| M2 | `InstructorDashboard.tsx`, `HeadDashboard.tsx`, `CourseDetail.tsx` |
| M1 | 8 new component files + 2 page refactors |
| M7 | Move 4 files, delete 1 directory, update imports |
| H4 | `AuthGate.tsx` (NEW), `AppShell.tsx` (NEW), `Layout.tsx` (refactor) |

---

### Task 1 (H1): Batch Analytics Queries

**Files:**
- Modify: `backend/student_evaluation_system/core/views/analytics.py` — `ProgramStatsView.get()`
- Modify: `backend/student_evaluation_system/tests/test_analytics.py` — add query count assertion

- [ ] **Step 1: Write test that verifies query reduction**

```python
# Append to backend/student_evaluation_system/tests/test_analytics.py
# (If test file doesn't exist, create it)

import pytest
from django.test.utils import override_settings


@pytest.mark.django_db
class TestProgramStatsPerformance:

    def test_program_stats_uses_constant_queries(self, authenticated_api_client, program, active_term):
        """Program stats endpoint should not scale queries with number of programs."""
        from core.models import Program, Department, DegreeLevel
        # Create a second program to verify N+1 is fixed
        dept = Department.objects.first() or Department.objects.create(name="Test", code="TEST")
        level = DegreeLevel.objects.first() or DegreeLevel.objects.create(name="Bachelor", duration_years=4)
        Program.objects.create(name="Program B", code="PB", department=dept, degree_level=level, duration_years=4)

        from django.test.utils import CaptureQueriesContext
        from django.db import connections

        with CaptureQueriesContext(connections["default"]) as ctx:
            response = authenticated_api_client.get("/api/core/program-stats/")
            assert response.status_code == 200

        # Should use significantly fewer queries than 5N (where N=programs)
        # With 2 programs, old code would do ~10+ queries. New code should be less.
        query_count = len(ctx.captured_queries)
        assert query_count < 15, f"Expected <15 queries, got {query_count}"
```

- [ ] **Step 2: Run the test (should fail on query count)**

Run: `cd backend/student_evaluation_system && uv run pytest tests/test_analytics.py -v`
Expected: Fails with query count > 15 (or test file not found if creating new)

- [ ] **Step 3: Refactor ProgramStatsView.get()**

Open `backend/student_evaluation_system/core/views/analytics.py`. Replace the per-program loop (lines 268-302) with a single annotated queryset:

```python
from django.db.models import Count, Avg, Subquery, OuterRef, IntegerField, FloatField

# Inside ProgramStatsView.get(), REPLACE the for-loop block:

program_stats = programs.annotate(
    total_students=Count("courses__enrollments__student_id", distinct=True),
    total_courses=Count("courses", distinct=True),
    po_avg=Subquery(
        StudentProgramOutcomeScore.objects.filter(
            program_outcome__program=OuterRef("pk")
        ).values("program_outcome__program").annotate(
            avg=Avg("score")
        ).values("avg")[:1],
        output_field=FloatField(),
    ),
    lo_count=Subquery(
        StudentLearningOutcomeScore.objects.filter(
            learning_outcome__course__program=OuterRef("pk")
        ).values("learning_outcome__course__program").annotate(
            cnt=Count("*")
        ).values("cnt")[:1],
        output_field=IntegerField(),
    ),
    po_count=Count("program_outcomes", distinct=True),
)

# Collect course/PO IDs for year-level breakdown and GPA (these are already batched)
prog_course_ids = list(
    Course.objects.filter(program__in=programs).values_list("id", flat=True)
)
prog_po_ids = list(
    ProgramOutcome.objects.filter(program__in=programs).values_list("id", flat=True)
)

# Build response list from annotated queryset
result_list = []
max_duration_years = 4
for p in program_stats:
    result_list.append({
        "id": p.id,
        "code": p.code,
        "name": p.name,
        "total_students": p.total_students,
        "total_courses": p.total_courses,
        "avg_score": round(p.po_avg, 2) if p.po_avg is not None else None,
        "lo_count": p.lo_count or 0,
        "po_count": p.po_count,
    })
    max_duration_years = max(max_duration_years, p.duration_years)

# Use the batched IDs for downstream calculations
all_course_ids = prog_course_ids
all_po_ids = prog_po_ids
program_stats_data = result_list
```

Ensure imports from `django.db.models` include `Count`, `Avg`, `Subquery`, `OuterRef`, `IntegerField`, `FloatField`.

- [ ] **Step 4: Run the test (should pass now)**

Run: `cd backend/student_evaluation_system && uv run pytest tests/test_analytics.py::TestProgramStatsPerformance -v`
Expected: PASS with query count < 15

- [ ] **Step 5: Run all backend tests**

Run: `cd backend/student_evaluation_system && uv run pytest -v`
Expected: All pass (existing tests must not break)

- [ ] **Step 6: Commit**

```bash
git add backend/student_evaluation_system/core/views/analytics.py backend/student_evaluation_system/tests/test_analytics.py
git commit -m "perf: batch analytics queries to eliminate N+1 in ProgramStatsView"
```

---

### Task 2 (M4): Extract `isRecord` to Shared Utils

**Files:**
- Create: `frontend/src/shared/utils/guards.ts`
- Modify: 6 files that define `isRecord` inline

- [ ] **Step 1: Read the 6 files to understand current state**

The files with inline `isRecord` definitions:
1. `frontend/src/features/courses/pages/CourseDetail.tsx` (line 53)
2. `frontend/src/features/dashboard/pages/InstructorDashboard.tsx` (line 30)
3. `frontend/src/features/courses/pages/StudentCourseDetail.tsx` (line 17)
4. `frontend/src/features/courses/pages/InstructorCourses.tsx` (line 38)
5. `frontend/src/features/courses/components/MappingEditor.tsx` (line 63)
6. `frontend/src/features/courses/components/FileUploadModal.tsx` (line 143)

Check each file to confirm the exact inline definition — all should be:
```typescript
const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null
```

- [ ] **Step 2: Create shared utility**

```typescript
// Create: frontend/src/shared/utils/guards.ts

/**
 * Type guard: checks if a value is a non-null object (Record).
 * Used for safely narrowing unknown API responses.
 */
export const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null
```

- [ ] **Step 3: Update all 6 consumer files**

For each of the 6 files:
1. Remove the local `const isRecord = ...` definition
2. Add import: `import { isRecord } from '@/shared/utils/guards'`

Example for CourseDetail.tsx:
```typescript
// REMOVE (line ~53):
// const isRecord = (value: unknown): value is Record<string, unknown> =>
//   typeof value === 'object' && value !== null

// ADD at top of imports:
import { isRecord } from '@/shared/utils/guards'
```

- [ ] **Step 4: Verify build and tests**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors (especially from the 6 modified files)

Run: `cd frontend && npx vitest run`
Expected: All existing tests pass

- [ ] **Step 5: Commit**

```bash
git add frontend/src/shared/utils/guards.ts frontend/src/features/courses/pages/CourseDetail.tsx frontend/src/features/dashboard/pages/InstructorDashboard.tsx frontend/src/features/courses/pages/StudentCourseDetail.tsx frontend/src/features/courses/pages/InstructorCourses.tsx frontend/src/features/courses/components/MappingEditor.tsx frontend/src/features/courses/components/FileUploadModal.tsx
git commit -m "refactor: extract isRecord type guard to shared/utils/guards.ts"
```

---

### Task 3 (M3): Parallelize CourseDetail API Calls

**Files:**
- Modify: `frontend/src/features/courses/pages/CourseDetail.tsx` — `queryFn`

- [ ] **Step 1: Locate the sequential calls**

Find the `queryFn` in CourseDetail.tsx (approximately lines 91-95):

```typescript
const courseResponse = await coreCoursesRetrieve(Number(courseId))
const loResponse = await coreLearningOutcomesList({ course: Number(courseId) })
const loScoresResponse = await coreStudentLoScoresList({ course: Number(courseId) })
```

- [ ] **Step 2: Replace with Promise.all**

```typescript
const [courseResponse, loResponse, loScoresResponse] = await Promise.all([
  coreCoursesRetrieve(Number(courseId)),
  coreLearningOutcomesList({ course: Number(courseId) }),
  coreStudentLoScoresList({ course: Number(courseId) }),
])
```

- [ ] **Step 3: Verify TypeScript and build**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors in CourseDetail.tsx

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/courses/pages/CourseDetail.tsx
git commit -m "perf: parallelize CourseDetail API calls with Promise.all"
```

---

### Task 4 (M5): Retry Button on Error States

**Files:**
- Modify: `frontend/src/features/courses/pages/CourseDetail.tsx`
- Modify: `frontend/src/features/dashboard/pages/StudentDashboard.tsx`
- Modify: `frontend/src/features/courses/pages/InstructorCourses.tsx`
- Modify: `frontend/src/features/dashboard/pages/HeadDashboard.tsx`

- [ ] **Step 1: Update CourseDetail error state (line 339-345)**

Replace the static error block:

```tsx
// BEFORE:
if (error) {
  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-6">
      <div className="text-red-800">Error: {error instanceof Error ? error.message : '...'}</div>
    </div>
  )
}

// AFTER:
if (error) {
  return (
    <div className="bg-danger-50 border border-danger-200 rounded-xl p-6">
      <p className="text-danger-800 font-medium mb-4">
        Error: {error instanceof Error ? error.message : 'An error occurred while loading course details'}
      </p>
      <button
        onClick={() => refetch()}
        className="px-4 py-2 bg-danger-600 text-white text-sm font-semibold rounded-lg hover:bg-danger-700 transition-colors"
      >
        Try Again
      </button>
    </div>
  )
}
```

- [ ] **Step 2: Update StudentDashboard error state**

Find the error handling in `StudentDashboard.tsx`. If it uses React Query's error state, add a retry button using `refetch`. Same pattern as CourseDetail.

- [ ] **Step 3: Update InstructorCourses error state**

Same pattern — add `refetch()` button using `useCoreCoursesList`'s returned `refetch`.

- [ ] **Step 4: Update HeadDashboard error state**

Same pattern — add retry button to any error display.

- [ ] **Step 5: Verify**

Run: `cd frontend && npx tsc --noEmit && npx vitest run`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/courses/pages/CourseDetail.tsx frontend/src/features/dashboard/pages/StudentDashboard.tsx frontend/src/features/courses/pages/InstructorCourses.tsx frontend/src/features/dashboard/pages/HeadDashboard.tsx
git commit -m "fix: add Try Again button to error states across dashboard pages"
```

---

### Task 5 (M6): React Router over `window.location`

**Files:**
- Modify: `frontend/src/features/auth/hooks/useAuth.ts`
- Modify: `frontend/src/shared/components/Sidebar.tsx`

- [ ] **Step 1: Fix useAuth.ts (line 102)**

Replace `window.location.pathname` with `useLocation()`:

```typescript
// ADD import:
import { useLocation } from 'react-router-dom'

// Inside the hook:
const location = useLocation()

// CHANGE line 102 from:
// enabled: typeof window !== 'undefined' && window.location.pathname !== '/login'
// TO:
enabled: location.pathname !== '/login'
```

Keep the login redirect at line 146 as-is (`window.location.href = '/login'`) since that's a hard redirect, not a rendering concern.

- [ ] **Step 2: Fix Sidebar.tsx (line 109)**

Replace `window.location.hash` with `useLocation().hash`:

```typescript
// ADD import:
import { useLocation } from 'react-router-dom'

// Inside the component:
const location = useLocation()

// CHANGE line 109 from:
// window.location.hash === item.href
// TO:
location.hash === item.href
```

- [ ] **Step 3: Verify**

Run: `cd frontend && npx tsc --noEmit && npx vitest run`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/auth/hooks/useAuth.ts frontend/src/shared/components/Sidebar.tsx
git commit -m "fix: replace window.location with useLocation() in useAuth and Sidebar"
```

---

### Task 6 (M2): `useCallback` on Event Handlers

**Files:**
- Modify: `frontend/src/features/dashboard/pages/InstructorDashboard.tsx`
- Modify: `frontend/src/features/dashboard/pages/HeadDashboard.tsx`
- Modify: `frontend/src/features/courses/pages/CourseDetail.tsx`

- [ ] **Step 1: Add useCallback imports**

In each file, add to the React import:
```typescript
import { useState, useEffect, useMemo, useCallback } from 'react'
```

- [ ] **Step 2: Wrap event handlers in InstructorDashboard**

```typescript
// Find handlers like:
const nextCourse = () => setCurrentIndex((prev) => (prev + 1) % courses.length)

// Wrap with useCallback:
const nextCourse = useCallback(
  () => setCurrentIndex((prev) => (prev + 1) % courses.length),
  [courses.length]
)

const prevCourse = useCallback(
  () => setCurrentIndex((prev) => (prev - 1 + courses.length) % courses.length),
  [courses.length]
)

const setActiveChart = useCallback(
  (chart: string) => setActiveChartState(chart),
  []
)
```

- [ ] **Step 3: Wrap event handlers in HeadDashboard**

Find and wrap navigation/toggle handlers with `useCallback`.

- [ ] **Step 4: Wrap event handlers in CourseDetail**

Find handlers like `handleUploadComplete`, `setLoChartView`, modal open/close handlers — wrap with `useCallback` with appropriate dependencies.

- [ ] **Step 5: Verify**

Run: `cd frontend && npx tsc --noEmit && npx vitest run`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/dashboard/pages/InstructorDashboard.tsx frontend/src/features/dashboard/pages/HeadDashboard.tsx frontend/src/features/courses/pages/CourseDetail.tsx
git commit -m "perf: add useCallback to event handlers in dashboard components"
```

---

### Task 7 (M1): Extract Large Components

**Files:**
- Create: `frontend/src/features/courses/components/BoxPlotChart.tsx`
- Create: `frontend/src/features/courses/components/StudentHeatmap.tsx`
- Create: `frontend/src/features/courses/components/CourseHeader.tsx`
- Create: `frontend/src/features/courses/components/LoRadarChart.tsx`
- Create: `frontend/src/features/dashboard/components/GradeDistributionChart.tsx`
- Create: `frontend/src/features/dashboard/components/AtRiskPanel.tsx`
- Create: `frontend/src/features/dashboard/components/CourseAnalyticsCard.tsx`
- Create: `frontend/src/features/dashboard/utils/analytics.ts`
- Modify: `frontend/src/features/courses/pages/CourseDetail.tsx` — import from extracted components
- Modify: `frontend/src/features/dashboard/pages/InstructorDashboard.tsx` — import from extracted components

This is the largest task. Execute each extraction as a sub-step:

- [ ] **Step 1: Extract `CourseHeader`**

Read `CourseDetail.tsx` lines ~108-195 (getInstructorNames, getAverageScore, course header JSX). Extract into:

```tsx
// Create: frontend/src/features/courses/components/CourseHeader.tsx
// Move the course header rendering (name, code, instructor, stats) here.
// Accept props: course, averageScore, instructorNames
```

Update `CourseDetail.tsx` to import and use `<CourseHeader ... />`.

- [ ] **Step 2: Extract `BoxPlotChart`**

Read `CourseDetail.tsx` lines ~429-533 (SVG box plot rendering). Extract into:

```tsx
// Create: frontend/src/features/courses/components/BoxPlotChart.tsx
// Accept props: data (LO scores), width, height
```

- [ ] **Step 3: Extract `StudentHeatmap`**

Read `CourseDetail.tsx` lines ~238-280 (heatmap color computation and grid). Extract into:

```tsx
// Create: frontend/src/features/courses/components/StudentHeatmap.tsx
// Accept props: loScores, learningOutcomes, getHeatmapColor callback
```

- [ ] **Step 4: Extract `LoRadarChart`**

Read `CourseDetail.tsx` lines ~410-428 (radar chart). Extract into:

```tsx
// Create: frontend/src/features/courses/components/LoRadarChart.tsx
// Accept props: learningOutcomes, loScores
```

- [ ] **Step 5: Extract analytics utilities**

Move `calculateGradeDistribution`, `calculateAverageScore`, `identifyStudentsAtRisk` from `InstructorDashboard.tsx` to:

```typescript
// Create: frontend/src/features/dashboard/utils/analytics.ts
```

- [ ] **Step 6: Extract `GradeDistributionChart`**

Read `InstructorDashboard.tsx` lines ~109-157. Move chart rendering into:

```tsx
// Create: frontend/src/features/dashboard/components/GradeDistributionChart.tsx
```

- [ ] **Step 7: Extract `AtRiskPanel`**

Read `InstructorDashboard.tsx` lines ~147-170. Move at-risk list into:

```tsx
// Create: frontend/src/features/dashboard/components/AtRiskPanel.tsx
```

- [ ] **Step 8: Extract `CourseAnalyticsCard`**

Read `InstructorDashboard.tsx` lines ~175-235. Move per-course card into:

```tsx
// Create: frontend/src/features/dashboard/components/CourseAnalyticsCard.tsx
```

- [ ] **Step 9: Verify**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors. Fix any import mismatches.

Run: `cd frontend && npx vitest run`
Expected: All pass (if existing tests reference internals, update imports).

Run: `cd frontend && npm run build`
Expected: Build succeeds.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/features/courses/components/BoxPlotChart.tsx frontend/src/features/courses/components/StudentHeatmap.tsx frontend/src/features/courses/components/CourseHeader.tsx frontend/src/features/courses/components/LoRadarChart.tsx frontend/src/features/dashboard/components/GradeDistributionChart.tsx frontend/src/features/dashboard/components/AtRiskPanel.tsx frontend/src/features/dashboard/components/CourseAnalyticsCard.tsx frontend/src/features/dashboard/utils/analytics.ts frontend/src/features/courses/pages/CourseDetail.tsx frontend/src/features/dashboard/pages/InstructorDashboard.tsx
git commit -m "refactor: extract chart components and analytics utils from large page files"
```

---

### Task 8 (M7): UI Component Directory Consolidation

**Files:**
- Move: `frontend/src/shared/components/ui/Card.tsx` → `frontend/src/components/ui/custom/Card.tsx`
- Move: `frontend/src/shared/components/ui/Badge.tsx` → `frontend/src/components/ui/custom/Badge.tsx`
- Move: `frontend/src/shared/components/ui/Modal.tsx` → `frontend/src/components/ui/custom/Modal.tsx`
- Move: `frontend/src/shared/components/ui/ChartWidget.tsx` → `frontend/src/components/ui/custom/ChartWidget.tsx`
- Delete: `frontend/src/shared/components/ui/` directory
- Move: `frontend/src/components/ui/Card.tsx` etc. → `frontend/src/components/ui/shadcn/Card.tsx` (rename shadcn components)

- [ ] **Step 1: Create target directory structure**

```bash
mkdir -p frontend/src/components/ui/shadcn
mkdir -p frontend/src/components/ui/custom
```

- [ ] **Step 2: Move shadcn components into `shadcn/`**

```bash
# List current shadcn components
ls frontend/src/components/ui/
# Move each: Button.tsx, Input.tsx, Card.tsx, Dialog.tsx, Form.tsx
# Example:
git mv frontend/src/components/ui/Button.tsx frontend/src/components/ui/shadcn/Button.tsx
# Repeat for all shadcn components
```

- [ ] **Step 3: Move custom components into `custom/`**

```bash
git mv frontend/src/shared/components/ui/Card.tsx frontend/src/components/ui/custom/Card.tsx
git mv frontend/src/shared/components/ui/Badge.tsx frontend/src/components/ui/custom/Badge.tsx
git mv frontend/src/shared/components/ui/Modal.tsx frontend/src/components/ui/custom/Modal.tsx
git mv frontend/src/shared/components/ui/ChartWidget.tsx frontend/src/components/ui/custom/ChartWidget.tsx
```

- [ ] **Step 4: Delete old directories**

```bash
rm -rf frontend/src/shared/components/ui/
rm -f frontend/src/components/ui/Card.tsx frontend/src/components/ui/Button.tsx
# (original files are now in shadcn/ or custom/)
```

- [ ] **Step 5: Update all imports across the codebase**

Search and replace imports:
- `@/components/ui/Card` → `@/components/ui/shadcn/Card`
- `@/components/ui/Button` → `@/components/ui/shadcn/Button`
- `@/shared/components/ui/Card` → `@/components/ui/custom/Card`
- `@/shared/components/ui/Badge` → `@/components/ui/custom/Badge`
- etc.

Use global search/replace in the frontend directory. Check each import matches the new path.

- [ ] **Step 6: Verify**

Run: `cd frontend && npx tsc --noEmit`
Expected: No import errors

Run: `cd frontend && npx vitest run`
Expected: All pass

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 7: Commit**

```bash
git add -A frontend/src/components/ui/ frontend/src/shared/components/ui/
# And all modified import files
git commit -m "refactor: consolidate UI components into shadcn/ and custom/ directories"
```

---

### Task 9 (H4): Split Auth Loading from Layout

**Files:**
- Create: `frontend/src/shared/components/AuthGate.tsx`
- Create: `frontend/src/shared/components/AppShell.tsx`
- Modify: `frontend/src/shared/components/Layout.tsx`

- [ ] **Step 1: Create AuthGate**

```tsx
// Create: frontend/src/shared/components/AuthGate.tsx

import React from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '@/features/auth/hooks/useAuth'

interface AuthGateProps {
  children: React.ReactNode
}

export const AuthGate: React.FC<AuthGateProps> = ({ children }) => {
  const { isLoading, isAuthenticated } = useAuth()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-secondary-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-primary-600 mx-auto" />
          <p className="mt-4 text-secondary-600 font-medium">Loading...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}
```

- [ ] **Step 2: Create AppShell**

```tsx
// Create: frontend/src/shared/components/AppShell.tsx

import React, { useState } from 'react'
import { Sidebar } from '@/shared/components/Sidebar'

interface AppShellProps {
  children: React.ReactNode
}

export const AppShell: React.FC<AppShellProps> = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="min-h-screen bg-secondary-50 flex">
      <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  )
}
```

- [ ] **Step 3: Simplify Layout**

```tsx
// Modify: frontend/src/shared/components/Layout.tsx

import React from 'react'
import { AuthGate } from './AuthGate'
import { AppShell } from './AppShell'

interface LayoutProps {
  requireAuth?: boolean
  children: React.ReactNode
}

export const Layout: React.FC<LayoutProps> = ({
  requireAuth = true,
  children,
}) => {
  if (requireAuth) {
    return (
      <AuthGate>
        <AppShell>{children}</AppShell>
      </AuthGate>
    )
  }

  return <AppShell>{children}</AppShell>
}
```

- [ ] **Step 4: Verify existing Layout consumers still work**

Check that all current `<Layout>` usages in `App.tsx` still pass the `requireAuth` prop correctly (they already do — it was added in a prior fix).

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

Run: `cd frontend && npx vitest run`
Expected: All pass (update Layout-related tests if they import from Layout directly)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/shared/components/AuthGate.tsx frontend/src/shared/components/AppShell.tsx frontend/src/shared/components/Layout.tsx
git commit -m "refactor: split Layout into AuthGate + AppShell for faster public page rendering"
```

---

### Task 10: Final Integration

**Files:** None — verification only

- [ ] **Step 1: Run all backend tests**

Run: `cd backend/student_evaluation_system && uv run pytest -v`
Expected: All pass

- [ ] **Step 2: Run all frontend tests**

Run: `cd frontend && npx vitest run`
Expected: All pass

- [ ] **Step 3: Backend lint**

Run: `cd backend/student_evaluation_system && uv run ruff check .`
Expected: No errors

- [ ] **Step 4: Frontend lint + build**

Run: `cd frontend && npm run lint`
Expected: No errors

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 5: Commit**

```bash
git add -A
git diff --cached --stat
git commit -m "chore: final integration verification for codebase hardening"
```
