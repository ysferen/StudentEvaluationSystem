# Codebase Hardening Design

**Date:** 2026-05-12
**Status:** Design

## Overview

Address the HIGH and MEDIUM priority issues identified in the codebase evaluation (2026-04-29) that have not yet been fixed. These are engineering quality improvements with no new features — purely refactoring, extraction, and UX polish.

---

## H1 — Batch Analytics Queries

**Current state:** `ProgramStatsView.get()` iterates programs one by one, issuing ~5 aggregate queries per program (enrollment count, PO average, LO count, PO count, course count). For N programs, this is ~5N queries.

### Approach

Replace per-program aggregate queries with a single annotated queryset. Must be DB-agnostic (works on SQLite for local dev and PostgreSQL for production).

```python
from django.db.models import Count, Avg, Subquery, OuterRef, IntegerField, FloatField

program_stats = Program.objects.select_related(
    "department", "degree_level"
).annotate(
    total_students=Count(
        "courses__enrollments__student_id", distinct=True
    ),
    total_courses=Count("courses", distinct=True),
    po_avg=Subquery(
        StudentProgramOutcomeScore.objects.filter(
            program_outcome__program=OuterRef("pk")
        ).values("program_outcome__program").annotate(
            avg=Avg("score")
        ).values("avg"),
        output_field=FloatField()
    ),
    lo_count=Subquery(
        StudentLearningOutcomeScore.objects.filter(
            learning_outcome__course__program=OuterRef("pk")
        ).values("learning_outcome__course__program").annotate(
            cnt=Count("*")
        ).values("cnt"),
        output_field=IntegerField()
    ),
    po_count=Count("program_outcomes", distinct=True),
)
```

Course IDs and PO IDs are collected separately in a single prefetch pass (already handled by `_calculate_year_level_breakdown` and `_calculate_gpa_by_year` which were refactored in the prior fix to accept batched IDs).

### Files changed
- `backend/student_evaluation_system/core/views/analytics.py` — `ProgramStatsView.get()`

### Verification
- `pytest backend/student_evaluation_system/tests/test_analytics.py` passes
- `assertNumQueries` in test confirms reduction

---

## M1 — Extract Large Components

**Current state:** `CourseDetail.tsx` is 781 lines with inline SVG rendering, box plot calculations, heatmap color logic, and modal management. `InstructorDashboard.tsx` is 544 lines with grade distribution math, LO score formatting, and chart configuration.

### Target: CourseDetail.tsx (~350 lines after extraction)

| New File | Extracted From | Contents |
|----------|---------------|----------|
| `features/courses/components/BoxPlotChart.tsx` | CourseDetail L429-533 | SVG rendering for box plots |
| `features/courses/components/StudentHeatmap.tsx` | CourseDetail L238-280 | Heatmap color computation + grid |
| `features/courses/components/CourseHeader.tsx` | CourseDetail L108-195 | Header with course name, code, instructor, stats |
| `features/courses/components/LoRadarChart.tsx` | CourseDetail L410-428 | Radar chart for LO scores |

### Target: InstructorDashboard.tsx (~250 lines after extraction)

| New File | Extracted From | Contents |
|----------|---------------|----------|
| `features/dashboard/components/GradeDistributionChart.tsx` | InstructorDashboard L109-157 | Grade bucket calculation and bar rendering |
| `features/dashboard/components/AtRiskPanel.tsx` | InstructorDashboard L147-170 | Students-at-risk list |
| `features/dashboard/components/CourseAnalyticsCard.tsx` | InstructorDashboard L175-235 | Per-course analytics card wrapper |

### Key constraint
- All extracted components receive data via props — no shared mutable state.
- Chart computation helpers (`calculateGradeDistribution`, `calculateAverageScore`, `identifyStudentsAtRisk`) move to `features/dashboard/utils/analytics.ts`.

### Files changed
- `frontend/src/features/courses/pages/CourseDetail.tsx` — reduce, import from new components
- `frontend/src/features/courses/components/BoxPlotChart.tsx` — **new**
- `frontend/src/features/courses/components/StudentHeatmap.tsx` — **new**
- `frontend/src/features/courses/components/CourseHeader.tsx` — **new**
- `frontend/src/features/courses/components/LoRadarChart.tsx` — **new**
- `frontend/src/features/dashboard/pages/InstructorDashboard.tsx` — reduce, import from new components
- `frontend/src/features/dashboard/components/GradeDistributionChart.tsx` — **new**
- `frontend/src/features/dashboard/components/AtRiskPanel.tsx` — **new**
- `frontend/src/features/dashboard/components/CourseAnalyticsCard.tsx` — **new**
- `frontend/src/features/dashboard/utils/analytics.ts` — **new**

---

## M3 — Parallelize API Calls in CourseDetail

**Current state:** Three independent API calls are sequential `await`s:

```typescript
const courseResponse = await coreCoursesRetrieve(Number(courseId))
const loResponse = await coreLearningOutcomesList({ course: Number(courseId) })
const loScoresResponse = await coreStudentLoScoresList({ course: Number(courseId) })
```

### After

```typescript
const [courseResponse, loResponse, loScoresResponse] = await Promise.all([
  coreCoursesRetrieve(Number(courseId)),
  coreLearningOutcomesList({ course: Number(courseId) }),
  coreStudentLoScoresList({ course: Number(courseId) })
])
```

### Files changed
- `frontend/src/features/courses/pages/CourseDetail.tsx` L91-95

---

## M4 — Extract `isRecord` Type Guard

**Current state:** `isRecord` is defined inline in 6 files: `CourseDetail.tsx`, `InstructorDashboard.tsx`, `StudentCourseDetail.tsx`, `InstructorCourses.tsx`, `MappingEditor.tsx`, `FileUploadModal.tsx`. All are identical.

### After

```typescript
// frontend/src/shared/utils/guards.ts
export const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null
```

Import in all 6 files, remove local definitions.

### Files changed
- `frontend/src/shared/utils/guards.ts` — **new**
- 6 consumer files — replace local `isRecord` with import

---

## M5 — Retry Button on Error States

**Current state:** `CourseDetail.tsx` shows a static red box on error — users must manually refresh. `StudentDashboard.tsx` shows a generic React Query error without retry.

### After

Both error states gain an "Try Again" button calling `refetch()`:

```tsx
if (error) {
  return (
    <div className="bg-danger-50 border border-danger-200 rounded-xl p-6">
      <p className="text-danger-800 mb-4">
        Error: {error instanceof Error ? error.message : 'An error occurred'}
      </p>
      <button
        onClick={() => refetch()}
        className="px-4 py-2 bg-danger-600 text-white rounded-lg hover:bg-danger-700 transition-colors"
      >
        Try Again
      </button>
    </div>
  )
}
```

### Files changed
- `frontend/src/features/courses/pages/CourseDetail.tsx` L339-345
- `frontend/src/features/dashboard/pages/StudentDashboard.tsx` — error state
- `frontend/src/features/courses/pages/InstructorCourses.tsx` — error state
- `frontend/src/features/dashboard/pages/HeadDashboard.tsx` — error state

---

## M6 — React Router over `window.location`

**Current state:** `useAuth.ts` checks `window.location.pathname` directly. `Sidebar.tsx` uses `window.location.hash`. Both bypass React Router's context.

### After

```typescript
// useAuth.ts
import { useLocation } from 'react-router-dom'
const location = useLocation()
// ... enabled: location.pathname !== '/login'

// Sidebar.tsx
import { useLocation } from 'react-router-dom'
const location = useLocation()
// ... location.hash === item.href
```

### Files changed
- `frontend/src/features/auth/hooks/useAuth.ts` L102 — replace `window.location.pathname` with `useLocation().pathname`
- `frontend/src/shared/components/Sidebar.tsx` L109 — replace `window.location.hash` with `useLocation().hash`

---

## M2 — `useCallback` on Event Handlers

**Current state:** Dashboard event handlers (`nextCourse`, `prevCourse`, `setActiveChart`) are recreated on every render, causing unnecessary child re-renders.

### After

Wrap all event handlers with `useCallback`:

```typescript
const nextCourse = useCallback(
  () => setCurrentIndex((prev) => (prev + 1) % courses.length),
  [courses.length]
)
const prevCourse = useCallback(
  () => setCurrentIndex((prev) => (prev - 1 + courses.length) % courses.length),
  [courses.length]
)
```

### Files changed
- `frontend/src/features/dashboard/pages/InstructorDashboard.tsx`
- `frontend/src/features/dashboard/pages/HeadDashboard.tsx`
- `frontend/src/features/courses/pages/CourseDetail.tsx`

---

## M7 — UI Component Directory Consolidation

**Current state:** `src/components/ui/` holds shadcn/ui components (Button, Input, Card, Dialog, Form). `src/shared/components/ui/` holds custom components (Card, Badge, Modal, ChartWidget). Both have a `Card` component — naming collision causes confusion.

### After

```
src/
  components/
    ui/
      shadcn/       ← shadcn/ui (Button, Input, Dialog, Form)
      custom/        ← custom components moved from shared/components/ui/
        Card.tsx
        Badge.tsx
        Modal.tsx
        ChartWidget.tsx
  shared/
    components/
      ui/            ← DELETED
```

All imports updated across the codebase.

### Files changed
- Move: `src/shared/components/ui/*` → `src/components/ui/custom/*`
- Delete: `src/shared/components/ui/` directory
- Update imports in all files referencing `@/shared/components/ui/Card` etc.

---

## H4 — Auth Loading Split from Layout

**Current state:** `Layout.tsx` conditionally shows a full-screen spinner when `requireAuth && isLoading`, blocking the sidebar and all children. While `requireAuth=false` is already used for course detail routes, the spinner still blocks the entire component tree when `requireAuth=true`.

### Approach

Split into two layers:

```tsx
// AuthGate.tsx — NEW, handles auth-only blocking
const AuthGate: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { isLoading, isAuthenticated } = useAuth()

  if (isLoading) {
    return <FullPageSpinner />
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" />
  }

  return <>{children}</>
}

// AppShell.tsx — NEW, sidebar + content, no auth awareness
const AppShell: React.FC<{ children: ReactNode }> = ({ children }) => {
  return (
    <div className="flex h-screen">
      <Sidebar />
      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  )
}

// Layout.tsx — orchestrates
const Layout: React.FC<LayoutProps> = ({ requireAuth = true, children }) => {
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

### Key benefit
- Public pages (landing, login, course details at `/student/courses/:id`) render `AppShell` immediately — no spinner flash.
- Protected pages get the spinner only during auth check, not after.

### Files changed
- `frontend/src/shared/components/AuthGate.tsx` — **new**
- `frontend/src/shared/components/AppShell.tsx` — **new**
- `frontend/src/shared/components/Layout.tsx` — refactor to use AuthGate + AppShell

---

## Verification Checklist

- [ ] `pytest backend/` — all backend tests pass
- [ ] `npm run test -- --run` — all frontend tests pass
- [ ] `npm run build` — TypeScript compilation succeeds
- [ ] `npm run lint` — ESLint passes
- [ ] Analytics page loads without N+1 queries (verify via `django-debug-toolbar` or `assertNumQueries`)
- [ ] Course detail page loads error with visible "Try Again" button
- [ ] Public course detail page renders immediately (no spinner flash)
- [ ] No `window.location` usage remains in components
- [ ] No `isRecord` duplication remains
- [ ] All shadcn/custom component imports resolve correctly
