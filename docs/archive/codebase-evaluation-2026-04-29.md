# SES Full-Stack Codebase Evaluation

**Date:** 2026-04-29
**Evaluator:** Senior Software Architect — Automated Review
**Scope:** Full-stack (Django REST Framework backend + React/TypeScript frontend)

---

## Task 1 — Vision Synthesis

The **Student Evaluation System (SES)** aims to be an outcome-based assessment platform for higher education that traces student achievement through a three-tier hierarchy: **Assessment → Learning Outcome (LO) → Program Outcome (PO)**. The ideal finished product serves four distinct roles — student, instructor, program head, and admin — each with tailored dashboards that surface actionable analytics (radar charts, grade distributions, box plots, heatmaps, year-level breakdowns). The backend is a Django 5.2 + DRF API with a well-structured domain model spanning universities, departments, programs, courses, outcomes, assessments, grades, and calculated scores. Authentication uses HTTP-only cookie JWT with rotation and CSRF protection. File-based grade import accepts Turkish-format Excel files and runs them through a five-phase validation pipeline (file structure → column structure → assessment validation → student validation → score validation) before persisting data. Score recomputation is offloaded to Celery workers with Redis as the broker/result backend, while the React/TypeScript frontend polls job status and shows global notifications.

The target architecture (partially implemented) adds PostgreSQL as the default database (with indexing), Redis caching, push-based real-time updates via Django Channels/WebSocket, an AI-assisted weight recommendation service with rule-based fallback, a risk analytics engine, comprehensive audit logging, and PDF/Excel reporting. The frontend follows a feature-based folder structure with Orval-generated API clients and a consistent design system using Tailwind color tokens (primary teal, secondary gray-blue, violet for instructors, green for heads/admins). The ideal state is a production-grade, compliance-ready academic platform with strong observability, low latency for score calculations on large courses, and a polished UX with proper loading states, empty states, and error recovery.

---

## Task 2 — Full-Stack Codebase Evaluation

### 1. Framework Best Practices & Architecture: 7/10

**Backend (DRF) — Strengths:**
- Consistent use of `ModelViewSet` + `DefaultRouter` across `core`, `evaluation`, and `users` apps for RESTful routing.
- Clean serializer patterns with bidirectional read/write field splitting (e.g., `program` read-only Object vs `program_id` write-only PrimaryKeyRelatedField).
- Custom permission classes (`IsInstructorOfCourse`, `IsAdminOrProgramHeadOrReadOnly`, `InstructorPermissionMixin`) implement the full RBAC model consistently.
- `drf-spectacular` is properly integrated for OpenAPI 3.0 schema generation and Swagger docs.
- Service layer separation in `evaluation/services.py` isolates business logic from views.

**Backend — Weaknesses:**
- **Duplicate `CourseViewSet`**: Defined in BOTH `core/views/academic_structure.py` (lines 231–290) AND `core/views/course.py` (lines 61–133). Only the latter implements proper role-based querysets (instructor/student/program-head scoping). The `academic_structure.py` variant uses `AllowAny, IsAdminOrProgramHeadOrReadOnly` which treats authenticated users differently based on URL path but may let unauthenticated users through on non-versioned routes.
- **Dynamic imports in serializers**: `users/serializers.py` lines 75, 82 use `__import__("core.models", fromlist=["Term"])` instead of proper `from core.models import Term`. This breaks static analysis and IDE support.
- **Legacy view duplication**: `academic_structure.py` retains `CourseListView`, `CourseDetailView`, `ProgramOutcomeListView`, `ProgramOutcomeDetailView` (lines 697–714) that are unreachable through routed URLs. Dead code.
- **`DummyImportSerializer`** (line 51 of `academic_structure.py`): A stub serializer exists solely because `GenericViewSet` requires one. Better to declare a proper serializer-less base pattern.
- **Cross-app serializer naming**: `CoreLearningOutcomeSerializer` vs `EvaluationLearningOutcomeSerializer` — renaming due to import conflicts signals insufficient namespace encapsulation.

**Frontend (React) — Strengths:**
- React 18 + TypeScript strict mode + Vite with `React.lazy` code splitting on every route.
- React Router v6 with nested routes and layout components.
- `@tanstack/react-query` for server state management with a sensible 5-minute stale time.
- Feature-based folder structure (`features/auth/`, `features/dashboard/`, `features/courses/`) with clear `pages/`, `components/`, `hooks/` subdirectories.
- Orval-generated API client with full TypeScript types from the OpenAPI schema.
- `ErrorBoundary` for crash recovery.

**Frontend — Weaknesses:**
- `useAuth` hooks into `window.location.pathname` directly (line 102) instead of using React Router's `useLocation()`. This bypasses the router context and creates fragile coupling.
- `Sidebar` uses `window.location.hash` directly (line 109) instead of React Router state.
- `AuthProvider.isLoading` blocks the entire `Layout` component (and its children) with a full-screen spinner, even for public pages that don't need authentication state.
- Only one shared context (`RecomputeJobsContext`) — no centralized notification system, theme management, or user preferences store.
- `CourseDetail.tsx` is 644 lines with data fetching, complex heatmap SVG rendering, box plot calculations, and modal management all in one component.
- Empty `shared/hooks/index.ts` exports nothing.

---

### 2. Performance & Efficiency: 7/10

**Backend — Strengths:**
- Score calculation service (`evaluation/services.py`) is well-optimized: pre-fetches all grades, assessments, mappings into dictionaries, uses O(1) lookups, and `bulk_create` for writes. Includes explicit `select_related` and `prefetch_related`.
- Proper use of database indexes (`Term.is_active`, `Course.program+term`, `Department.university+code`, `Program.department+degree_level`, unique constraints, etc.).
- DRF pagination (`PageNumberPagination`, page_size=100, max 1000).
- Celery integration for async task offloading of score recomputation.

**Backend — Weaknesses:**
- **Analytics N+1 pattern**: `ProgramStatsView.get()` iterates over all programs serially, making 4 aggregate queries per program (`Course.objects.filter(program=p)`, `CourseEnrollment.filter(course_id__in=...)`, `ProgramOutcome.filter(program=p)`, `StudentLearningOutcomeScore.filter(...)`), plus PO and LO aggregations. For 10 programs, that's ~40+ additional queries beyond the initial `Program` fetch. Should batch these into a single aggregation pass.
- **Score format heuristic**: In `core/views/academic_structure.py` lines 542 and 602, the `course_averages` and `lo_averages` actions test `if avg_score is not None and avg_score <= 1: avg_score = avg_score * 100`. A genuinely low average (e.g., 0.5% on a normalized scale) would be incorrectly multiplied to 50%. There's no reliable way to discriminate decimal vs. percentage format without metadata.
- **No caching layer**: Redis is configured for Celery but not used as a Django cache backend. Repeated aggregate queries on dashboards hit the database every time.
- **`_calculate_year_level_breakdown`** in `analytics.py` fetches all PO scores for each year bucket individually. Could be refactored to a single annotated query with `Case`/`When`.

**Frontend — Strengths:**
- `React.lazy` for route-level code splitting.
- `useMemo` used for derived state (e.g., `totalStudents`, `overallAvg`, `poRadarData`, `boxPlotData`, `heatmapData`).
- React Query default options set `retry: 1` and `refetchOnWindowFocus: false`.

**Frontend — Weaknesses:**
- `InstructorDashboard` fires `useQueries` for *every* course's analytics in parallel on mount. For 20 courses, that's 40 simultaneous API requests (2 per course: LO averages + grade averages).
- `StudentDashboard` calls `coreStudentPoScoresList()` without a student filter parameter — fetches all PO scores server-side, then relies on backend role-based filtering. This should pass the `student` query param.
- **1-second polling** in `RecomputeJobsContext` (line 146: `setInterval(() => { void poll() }, 1000)`) is aggressive. Exponential backoff or WebSocket/SSE push would be more efficient.
- No `useCallback` on event handlers in dashboard components (`nextCourse`, `prevCourse`, `setActiveChart`, etc.), causing child components to re-render unnecessarily.
- `CourseDetail` queryFn makes three sequential API calls (`coreCoursesRetrieve`, `coreLearningOutcomesList`, `coreStudentLoScoresList`). These are independent and should be `Promise.all`'d.

---

### 3. Security: 8/10

**Backend — Strengths:**
- JWT with rotation enabled (`ROTATE_REFRESH_TOKENS`) and blacklisting (`BLACKLIST_AFTER_ROTATION`).
- HTTP-only cookies for tokens (`AUTH_COOKIE_HTTP_ONLY = True`) — XSS resistant.
- CSRF protection via `csrftoken` cookie + `X-CSRFToken` header validation in `CookieJWTAuthentication._validate_csrf()`.
- `SameSite=Strict` in production, `SameSite=Lax` in development.
- CORS whitelist via `CORS_ALLOWED_ORIGINS` environment variable.
- Rate limiting: login (5/min), file upload (10/min), general API (anon 100/day, user 1000/day).
- Password validators configured (similarity, min length, common passwords, numeric).
- Input sanitization in `LoginView`: whitespace stripping, username length cap (≤150 chars).
- Security headers in production: HSTS, SSL redirect, XSS filter, content-type nosniff.
- Exception handler hides internal details in production (`settings.DEBUG` check).

**Backend — Weaknesses:**
- `SECRET_KEY` has a hardcoded fallback (`"django-insecure-dev-key-only-for-local-development-change-in-production"`). Any production deployment that forgets to set the env var gets a trivially guessable key.
- `UserRegistrationSerializer` exists but is not wired to any view or endpoint — unused code that could create confusion.
- The `StudentProfileViewSet` does not specify `permission_classes`, defaulting to DRF's `IsAuthenticatedOrReadOnly`. This makes student profile data publicly readable.

**Frontend — Strengths:**
- CSRF token bootstrap via `ensureCsrfToken()` that automatically fetches a `csrftoken` cookie from `/api/users/auth/csrf/` before any mutating request.
- Token refresh queue pattern: multiple concurrent 401s trigger a single refresh, queued requests replay after success.
- `withCredentials: true` on all Axios requests ensures cookies are sent.

**Frontend — Weaknesses:**
- The `login` function (line 183) sends `email: ''` as a required type field. This is a workaround for an Orval-generated type that requires `email`. Better to adjust the API or the generated type.
- No Content Security Policy headers configured in the Vite setup.
- `useAuth`'s `userError` effect (lines 159–161) calls `logout()` which does `window.location.href = '/login'`. If multiple tabs are open and one causes an auth error, all tabs redirect. A `document.hidden` check or BroadcastChannel could prevent this.

---

### 4. Robustness & Error Handling: 7/10

**Backend — Strengths:**
- Centralized `custom_exception_handler` produces consistent `{ "error": { "code": ..., "message": ..., "details": ... } }` responses.
- Model-level validation via `clean()` methods (e.g., `StudentGrade.clean()` validates score ≤ total_score and student enrollment).
- Serializer validation for weight sums (1% tolerance).
- Database transactions (`transaction.atomic()`) in score calculation to prevent partial writes.
- `ScoreRecomputeJob` model tracks job status with `pending → running → success/failed` lifecycle.

**Backend — Weaknesses:**
- File import views use broad `except Exception` catches (e.g., `academic_structure.py` line 982, 1124) with mixed response shapes. The error response includes `self.file_service.get_import_summary()` which may raise if `self.file_service` was never set.
- The `course_averages` action (line 506) returns `{"error": ...}` for missing params instead of using `raise ValidationError` — inconsistent with the rest of the API.
- `_calculate_year_level_breakdown` silently returns all-zero buckets if `enrolled_students` is empty — caller cannot distinguish "no data" from "no active term."
- No 404 handling for invalid course IDs in `CourseViewSet.get_queryset()`. DRF catches this at the view level, but the filter-based queryset may return empty results silently for list endpoints.
- The `_calculate_per_student_averages` method (line 362) iterates over enrollments and hits the DB inside the loop for each student. While it uses `select_related`, the annotation is per-student — a bulk approach would be more robust.

**Frontend — Strengths:**
- `ErrorBoundary` catches rendering crashes and shows a user-friendly fallback.
- Loading states throughout: spinners, skeleton patterns, empty state cards with icons.
- React Query's built-in retry (1 attempt) and error state propagation.

**Frontend — Weaknesses:**
- `CourseDetail` shows a generic red box on error with no "Try Again" button. Users must refresh the page.
- `InstructorDashboard` wraps analytics queries in try/catch and returns empty arrays (`loAverages: [], gradeAverages: []`) — failures are silently swallowed, and charts render as empty with no indication of error.
- `toLoAverages` type guard (line 33 of `InstructorDashboard`) silently drops malformed API responses. This masks API changes and bugs.
- No global toast/notification system for API errors. Only upload-related notifications exist (from `RecomputeJobsContext`).
- `StudentDashboard` uses `!userId` guard in queryFn which throws a generic `Error` — this error surfaces as a red React Query error state instead of being handled gracefully.

---

### 5. Readability & Maintainability (DRY): 7/10

**Backend — Strengths:**
- Consistent docstring conventions on models, serializers, views, permissions, and services — one of the most thoroughly documented Django codebases.
- Type hints on service functions (e.g., `calculate_course_scores(course_id: int) -> Dict[str, Any]`).
- Clear separation: `models.py` / `serializers.py` / `views/` / `services/` / `urls.py`.
- `TimeStampedModel` abstract base model for consistent timestamp tracking.
- `ResourceArea` and `PermissionTier` as `TextChoices` for self-documenting enums.

**Backend — Weaknesses:**
- View code is split across `core/views/` subdirectory AND the `academic_structure.py` file. Some ViewSets are defined in both (`CourseViewSet`, `ProgramOutcomeViewSet`, etc.). This makes it unclear which version is active.
- Serializer naming: `UserSerializer` vs `CustomUserSerializer` vs `UserRegistrationSerializer` vs `UserDetailSerializer` — 4 serializers for the same model with overlapping fields.
- `DummyImportSerializer` is an explicit anti-pattern.
- The `__import__` pattern in `users/serializers.py` is a readability and maintainability issue.

**Frontend — Strengths:**
- Feature-based folder structure with clear public API `index.ts` files.
- TypeScript types from Orval generation.
- Tailwind CSS with consistent color token usage (primary, secondary, success, warning, danger).
- Component conventions documented in `docs/architecture/FRONTEND.md`.

**Frontend — Weaknesses:**
- `CourseDetail.tsx` (644 lines): Contains SVG rendering logic for box plots (lines 429–533), heatmap color computation (lines 238–280), data transformation, and modal management. Should extract chart components and computational helpers.
- `InstructorDashboard.tsx` (508 lines): Contains grade distribution math (lines 113–157), LO score formatting, analytics query orchestration, and chart configuration. Multiple sub-components and hooks should be extracted.
- `isRecord` type guard is duplicated verbatim in `CourseDetail.tsx` (line 39) and `InstructorDashboard.tsx` (line 29). Should live in `shared/utils/`.
- Dark section pattern, alert patterns, and loading skeleton patterns from the design system are re-implemented inline instead of being reusable components.
- `shared/hooks/index.ts` is empty and exports nothing.
- Multiple parallel file trees exist: `src/components/ui/` (shadcn/ui) vs `src/shared/components/ui/` (custom UI) — these overlap in naming (both have `Card` components) and could confuse developers.

---

## Task 3 — Actionable Recommendations

### 1. Framework Best Practices — Recommendations

**A. Resolve duplicate `CourseViewSet` definitions (CRITICAL)**
```
# BEFORE: Two definitions exist —
# core/views/academic_structure.py:231 (AllowAny, IsAdminOrProgramHeadOrReadOnly)
# core/views/course.py:61 (AllowAny, InstructorPermissionMixin, with role-based querysets)
#
# AFTER: Keep only core/views/course.py version. Remove lines 231–290 from academic_structure.py.
# Update academic_structure.py's imports to use the course.py version.
```
```python
# In academic_structure.py — REMOVE the entire CourseViewSet class and instead import:
from core.views.course import CourseViewSet  # reuse the canonical version
```

**B. Replace `__import__` with proper imports**
```python
# BEFORE (users/serializers.py lines 75, 82):
enrollment_term_id = serializers.PrimaryKeyRelatedField(
    queryset=__import__("core.models", fromlist=["Term"]).Term.objects.all(),
    ...
)

# AFTER:
from core.models import Term, Program

enrollment_term_id = serializers.PrimaryKeyRelatedField(
    queryset=Term.objects.all(),
    ...
)
```

**C. Extract CourseDetail sub-components**
```tsx
// BEFORE: 644-line CourseDetail.tsx with inline SVG rendering
// AFTER:
// features/courses/components/BoxPlotChart.tsx
// features/courses/components/StudentHeatmap.tsx
// features/courses/components/CourseHeader.tsx
// And shared/utils/isRecord.ts for the duplicated type guard
```

**D. Fix `useAuth` to not depend on `window.location.pathname`**
```tsx
// BEFORE (useAuth.ts line 102):
enabled: typeof window !== 'undefined' && window.location.pathname !== '/login'

// AFTER — provide a prop or use React Router:
interface AuthProviderProps {
  children: ReactNode
  requireAuth?: boolean  // caller controls this
}
```

---

### 2. Performance — Recommendations

**A. Fix score format heuristic (CRITICAL)**
```python
# BEFORE (core/views/academic_structure.py lines 542-543):
if avg_score is not None and avg_score <= 1:
    avg_score = avg_score * 100

# AFTER: Use a metadata field in the response or a configurable multiplier.
# Option 1: Always store/return scores in a consistent format (e.g., always 0-100).
# Option 2: Add a "score_format" field to the response:
return Response({
    "course_id": cid,
    "weighted_average": round(avg_score, 2) if avg_score is not None else None,
    "score_format": "percentage",  # explicit
})
```

**B. Batch analytics queries**
```python
# BEFORE: N program loops with separate aggregate queries each
for program in programs:
    total_students = CourseEnrollment.objects.filter(course_id__in=prog_course_ids)...count()
    # ...4 more queries per program...

# AFTER: Single annotated queryset
from django.db.models import Count, Q, Subquery, OuterRef

program_stats = Program.objects.annotate(
    total_courses=Count("courses"),
    course_ids=Subquery(...),  # pre-fetch all course IDs per program
).select_related("department", "degree_level")

# Then compute student counts with a single CourseEnrollment.values().annotate()
```

**C. Add Django cache for analytics**
```python
# settings.py addition:
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_CACHE_URL", default="redis://redis:6379/1"),
    }
}

# In analytics view:
from django.core.cache import cache

cache_key = f"program-stats:{user.id}"
cached = cache.get(cache_key)
if cached:
    return Response(cached)
# ... compute ...
cache.set(cache_key, data, timeout=300)  # 5 min TTL
```

**D. Use `useCallback` for event handlers**
```tsx
// BEFORE:
const nextCourse = () => setCurrentIndex((prev) => (prev + 1) % courses.length)

// AFTER:
const nextCourse = useCallback(
  () => setCurrentIndex((prev) => (prev + 1) % courses.length),
  [courses.length]
)
```

---

### 3. Security — Recommendations

**A. Enforce SECRET_KEY in production (HIGH)**
```python
# BEFORE (settings.py line 36):
SECRET_KEY = env("SECRET_KEY", default="django-insecure-dev-key-only-for-local-development-change-in-production")

# AFTER — fail hard in production:
SECRET_KEY = env("SECRET_KEY")
if not DEBUG and SECRET_KEY == "django-insecure-dev-key-only-for-local-development-change-in-production":
    raise ImproperlyConfigured("SECRET_KEY must be set in production")
```

**B. Add permission_classes to StudentProfileViewSet**
```python
# BEFORE (users/views.py line 88-90):
class StudentProfileViewSet(viewsets.ModelViewSet):
    queryset = StudentProfile.objects.select_related(...).all()
    serializer_class = StudentProfileSerializer
    # No permission_classes → defaults to IsAuthenticatedOrReadOnly (public read)

# AFTER:
class StudentProfileViewSet(viewsets.ModelViewSet):
    queryset = StudentProfile.objects.select_related(...).all()
    serializer_class = StudentProfileSerializer
    permission_classes = [IsAuthenticated]  # Require authentication
```

---

### 4. Robustness — Recommendations

**A. Add retry/refresh to error states in CourseDetail**
```tsx
// BEFORE: Error shows static box
if (error) {
  return <div className="bg-red-50 ...">Error: {error.message}</div>
}

// AFTER: Add retry button
if (error) {
  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-6">
      <p className="text-red-800 mb-4">
        Error: {error instanceof Error ? error.message : 'Failed to load course'}
      </p>
      <button onClick={() => refetch()} className="px-4 py-2 bg-red-600 text-white rounded-lg">
        Try Again
      </button>
    </div>
  )
}
```

**B. Surface analytics errors instead of swallowing them**
```tsx
// BEFORE: catch block silently returns empty arrays
} catch (error) {
  console.error(`Error fetching analytics for course ${course.id}:`, error)
  return { courseId: course.id, loAverages: [], gradeAverages: [] }
}

// AFTER: Use React Query's error state
// Remove the try/catch — let React Query handle errors.
// In the UI, check `analyticsQueries[index]?.isError` and render an error indicator.
```

---

### 5. Readability — Recommendations

**A. Extract duplicated `isRecord` helper**
```ts
// Add to shared/utils/guards.ts:
export const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null

// Import from both CourseDetail.tsx and InstructorDashboard.tsx
```

**B. Remove dead code: legacy views**
```python
# In core/views/academic_structure.py — remove lines 697-714:
# CourseListView, CourseDetailView, ProgramOutcomeListView, ProgramOutcomeDetailView
# These are unreachable via URL routing (only ViewSets are registered).
```

**C. Consolidate UI component directories**
```
# Current confusion:
# src/components/ui/        → shadcn/ui (Button, Input, Card, Dialog, Form)
# src/shared/components/ui/ → custom (Card, Badge, Modal, ChartWidget)

# Recommended: Merge or clearly namespace:
# src/components/ui/shadcn/  → Shadcn components
# src/components/ui/custom/  → Custom components (Card, Badge, Modal, ChartWidget)
```

**D. Remove or populate empty `shared/hooks/index.ts`**
```typescript
// BEFORE:
// Shared hooks exports
// Add shared hooks here as needed
export {}

// AFTER: Either delete the file or add shared hooks when they exist.
// If the file must exist, add a meaningful comment:
// Use useDebounce, useLocalStorage, etc. — consider adding @/shared/hooks/useDebounce.ts
```

---

## Task 4 — Prioritization Matrix

### [CRITICAL] — Must Fix Immediately

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| C1 | **Duplicate `CourseViewSet`** — two definitions diverging in permissions. The weaker one (`AllowAny, IsAdminOrProgramHeadOrReadOnly`) may allow unauthorized course data access on non-versioned routes. | `core/views/academic_structure.py:231` vs `core/views/course.py:61` | Broken RBAC — unauthenticated users potentially see all course data |
| C2 | **Score format heuristic** — `if avg_score <= 1: * 100` can incorrectly multiply legitimate low scores by 100x. A student with 0.5% average would see 50%. | `core/views/academic_structure.py:542, 602` | Silent data corruption on analytics endpoints |
| C3 | **Production SECRET_KEY fallback** — `django-insecure-dev-key-only-for-local-development-change-in-production` is publicly known. A production deployment that forgets the env var gets this key. | `student_evaluation_system/settings.py:36` | All JWT tokens trivially forgeable |
| C4 | **StudentProfileViewSet missing permission_classes** — defaults to `IsAuthenticatedOrReadOnly`, exposing all student profile data to anyone with a session. | `users/views.py:88` | Data leak of student personal information |

### [HIGH] — Strongly Recommended for Final Release

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| H1 | **Analytics N+1 queries** — serial aggregate queries per program in `ProgramStatsView`. | `core/views/analytics.py:112-150` | Dashboard degrades linearly with program count |
| H2 | **No caching** — Redis is available but unused for query caching. Dashboards hit DB every render. | `settings.py` — no `CACHES` config | Unnecessary load on every dashboard page load |
| H3 | **StudentDashboard fetches all PO scores** — no student filter param sent. | `frontend/.../StudentDashboard.tsx:30` | Unnecessary data transfer and backend load |
| H4 | **`useAuth` blocks layout** — `isLoading` spinner blocks entire app including publicly accessible routes like course details. | `useAuth.ts:88-105`, `Layout.tsx:16-25` | Poor UX — public pages blocked during auth check |
| H5 | **Analytics errors silently swallowed** — InstructorDashboard returns empty arrays on API failure. | `InstructorDashboard.tsx:99-106` | Instructors see blank charts with no indication of failure |
| H6 | **`__import__` pattern in serializers** — breaks IDE support and static analysis. | `users/serializers.py:75, 82` | Maintainability hazard and potential import errors |
| H7 | **Remove dead legacy views** — unreachable `CourseListView`, `CourseDetailView`, etc. | `academic_structure.py:697-714` | Code confusion — developers may modify dead code by mistake |

### [MEDIUM] — Good to Have

| # | Issue | Location |
|---|-------|----------|
| M1 | Refactor large components: extract `BoxPlotChart`, `StudentHeatmap` from `CourseDetail.tsx` (644 lines); extract `GradeDistributionChart`, `LoRadarChart` from `InstructorDashboard.tsx` (508 lines). | Frontend |
| M2 | Add `useCallback` to event handlers in dashboard components to prevent unnecessary re-renders. | All dashboard pages |
| M3 | Parallelize independent API calls in `CourseDetail` queryFn using `Promise.all`. | `CourseDetail.tsx:77-88` |
| M4 | Extract duplicated `isRecord` type guard to `shared/utils/guards.ts`. | Frontend |
| M5 | Add retry/refresh button to error states in `CourseDetail.tsx`. | `CourseDetail.tsx:290-295` |
| M6 | Use React Router's `useLocation()` instead of `window.location.pathname` / `window.location.hash` in `useAuth` and `Sidebar`. | `useAuth.ts:102`, `Sidebar.tsx:109` |
| M7 | Merge `src/components/ui/` (shadcn) and `src/shared/components/ui/` (custom) directories or clearly namespace them. | Frontend |
| M8 | Change 1-second poll to exponential backoff or WebSocket in `RecomputeJobsContext`. | `RecomputeJobsContext.tsx:146` |

### [LOW] — Nitpicks & Future Considerations

| # | Issue | Location |
|---|-------|----------|
| L1 | Remove `DummyImportSerializer` — refactor `BaseFileImportViewSet` to not require a serializer. | `academic_structure.py:51` |
| L2 | Remove or populate empty `shared/hooks/index.ts`. | Frontend |
| L3 | `db_index=True` on ForeignKey fields is redundant (Django adds these automatically). Remove for clarity. | `core/models.py` (multiple fields) |
| L4 | Consolidate serializer naming: `UserSerializer` vs `CustomUserSerializer` vs `UserRegistrationSerializer` vs `UserDetailSerializer`. | Backend |
| L5 | `_calculate_per_student_averages` hits DB per student — refactor to bulk approach. | `evaluation/views.py:362` |
| L6 | Add CSP headers to Vite config for defense-in-depth. | `vite.config.ts` |
| L7 | Implement WebSocket/SSE for real-time job updates to replace polling. | Future — Semester 2 |
| L8 | Add audit logging for grade changes, imports, and permission modifications. | Future — Semester 2 |

---

## Summary Scorecard

| Metric | Score |
|--------|-------|
| Framework Best Practices & Architecture | 7/10 |
| Performance & Efficiency | 7/10 |
| Security | 8/10 |
| Robustness & Error Handling | 7/10 |
| Readability & Maintainability (DRY) | 7/10 |
| **Overall** | **7.2/10** |

The codebase demonstrates solid architectural foundations with well-structured Django apps, a clean React feature-based layout, and strong security practices around JWT cookie authentication. The primary concerns are the duplicate `CourseViewSet` causing potential permission bypasses, the fragile score format heuristic, missing caching, and several components that have grown too large. With the recommended fixes applied — particularly the 4 CRITICAL items — this codebase would be well-positioned for a production release.
