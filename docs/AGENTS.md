# Student Evaluation System - Copilot Instructions

## Purpose

This file is the default machine-readable project context for coding agents.

Use it as the main development guide.

Project status terms used in this file:

- Implemented: available in current codebase.
- Planned (Semester 2): target architecture and features from the final project plan, not fully implemented yet.

## Documentation Priority

When documents conflict, use this priority order:

1. Runtime/config files and manifests (source of truth):
   - backend/pyproject.toml
   - backend/pytest.ini
   - backend/student_evaluation_system/student_evaluation_system/settings.py
   - frontend/package.json
   - frontend/tsconfig.json
   - docker-compose.yml
2. This file: .github/copilot-instructions.md
3. API Documentation: docs/api/API_CONTRACT_V1.md
4. Backend README: backend/README.md
5. Root README.md (human-facing, may be stale)

## Documentation Locations

- **Frontend Architecture Guide**: docs/architecture/FRONTEND.md (how to add pages, component conventions)
- **API Contract**: docs/api/API_CONTRACT_V1.md (human-readable API specification)
- **Auto-generated OpenAPI Schema**: backend/student_evaluation_system/schema.yml (used by Orval for API client generation)
- **Architecture Info**: This file and backend/README.md

## Project Goal

Student Evaluation System (SES) is an outcome-based assessment platform for higher education.

Core goal:

- Track student achievement from Assessment -> Learning Outcome (LO) -> Program Outcome (PO).
- Support role-based workflows for guest, student, instructor, and admin.
- Frontend exposes admin-level oversight pages under /head routes.

## Current Architecture (Implemented)

### Backend

- Framework: Django 5.2.8 + Django REST Framework 3.16.1
- Language: Python 3.12+
- Auth: JWT (SimpleJWT), access and refresh tokens with rotation and blacklist
- API schema/docs: drf-spectacular at /api/schema/ and /api/docs/
- Database: SQLite default for local dev, PostgreSQL supported via DATABASE_URL
- Main apps:
  - core: academic structure, outcomes, score models, permissions, file import endpoints
  - evaluation: assessments, grades, enrollments, score calculation service
  - users: custom user model and profiles

### Frontend

- Framework: React 18 + TypeScript + Vite
- State/query: @tanstack/react-query
- HTTP: Axios mutator with JWT interceptors
- API clients: Orval-generated files currently located under frontend/src/shared/api/
- App structure is feature-based:
  - frontend/src/features/
  - frontend/src/shared/

### Deployment/Containers

- docker-compose.yml includes db (PostgreSQL), backend, frontend services.
- Frontend dev server runs on port 5173.
- Backend runs on port 8000.

## Domain Model (Implemented)

### Core entities

- Academic structure: University, Department, DegreeLevel, Program, Term, Course
- Outcomes:
  - ProgramOutcome (PO)
  - LearningOutcome (LO)
  - LearningOutcomeProgramOutcomeMapping (LO -> PO weight)
- Evaluation:
  - Assessment
  - AssessmentLearningOutcomeMapping (Assessment -> LO weight)
  - StudentGrade
  - CourseEnrollment
- Calculated scores:
  - StudentLearningOutcomeScore
  - StudentProgramOutcomeScore

### Score calculation flow

1. Grades are entered for each student-assessment pair.
2. Course LO scores are computed using assessment weights and assessment-LO mapping weights.
3. Program PO scores are aggregated from LO scores using LO-PO mapping weights.
4. Current implementation is synchronous in backend/evaluation/services.py.

## Roles and Access Model (Implemented)

Defined in users.CustomUser.role:

- guest
- student
- instructor
- admin

Access control patterns:

- Default DRF permission is IsAuthenticatedOrReadOnly.
- Many viewsets expose public read access with AllowAny + role-based write restrictions.
- Custom permission classes exist in core/permissions.py, including:
  - IsAdmin
  - IsInstructorOrAdmin
  - IsOwnerOrInstructorOrAdmin
  - IsAdminOrReadOnly

## API and Routing (Implemented)

- Versioned routes: /api/v1/users/, /api/v1/core/, /api/v1/evaluation/
- Backward-compatible non-versioned routes are also active under /api/users/, /api/core/, /api/evaluation/

Authentication endpoints (users app):

- POST /api/users/auth/login/
- POST /api/users/auth/refresh/
- GET /api/users/auth/me/

## Local Development Workflow

### Backend (preferred local workflow)

Preferred package manager for local development: uv.

From repository root:

```bash
cd backend
uv sync
cd student_evaluation_system
uv run python manage.py migrate
uv run python manage.py runserver
```

Useful backend commands:

```bash
cd backend/student_evaluation_system
uv run python manage.py check
uv run python manage.py makemigrations
uv run python manage.py migrate
uv run pytest
uv run pytest --cov=student_evaluation_system
uv run ruff check .
uv run ruff format --check .
```

### Frontend

From repository root:

```bash
cd frontend
npm install
npm run dev
```

Useful frontend commands:

```bash
cd frontend
npm run lint
npm run test -- --run
npm run test:coverage
npm run build
```

## CI Difference

CI currently installs backend dependencies using pip and backend/requirements.txt, while local docs recommend uv.
Do not assume CI uses uv yet.

## Environment Variables

### Backend (.env in backend/)

Important keys:

- SECRET_KEY
- DEBUG
- ALLOWED_HOSTS
- DATABASE_URL
- CORS_ALLOWED_ORIGINS
- ACCESS_TOKEN_LIFETIME_MINUTES
- REFRESH_TOKEN_LIFETIME_DAYS
- ANON_THROTTLE_RATE
- USER_THROTTLE_RATE
- LOGIN_THROTTLE_RATE
- FILE_UPLOAD_THROTTLE_RATE
- MAX_UPLOAD_SIZE_MB
- LOG_LEVEL

Backend settings load backend/.env via environs.

### Frontend (.env.development/.env.production in frontend/)

Important keys:

- VITE_API_URL
- VITE_API_BASE_PATH
- VITE_APP_NAME
- VITE_APP_VERSION
- VITE_ENABLE_DEBUG
- VITE_ENABLE_MOCK_API

## Testing and Quality Gates

### Backend

- Test framework: pytest + pytest-django
- Coverage threshold is enforced at 70 percent (backend/pytest.ini)
- Markers include: unit, integration, slow
- Lint/format: ruff
- Ruff complexity limit: 10
- Ruff line length: 127

### Frontend

- Test framework: Vitest (jsdom)
- ESLint with TypeScript rules
- TypeScript strict mode enabled
- Coverage reporting configured, but no hard fail threshold in vitest config

## API Client Generation Rules

Generated clients are used by the frontend and should not be hand-edited.

Source schema: backend/student_evaluation_system/schema.yml (auto-generated by drf-spectacular)

Command:
```bash
cd frontend
npm run generate:api
```

Important notes:
- Current app imports generated clients from frontend/src/shared/api/generated.
- schema.yml is auto-generated at /api/schema/ or via `python manage.py spectacular --file schema.yml`
- For Postman/API testing: Import schema.yml directly (supports OpenAPI 3.0)

## Common Implementation Patterns

### Add or modify a backend API endpoint

1. Update model/service/serializer/view as needed.
2. Register/update route in app urls.py.
3. Run migrations if model changed.
4. Run backend lint/tests.
5. Regenerate frontend API clients if schema changed.
6. Update frontend feature code using generated hooks/functions.

### Add or modify a frontend page/feature

1. Implement under frontend/src/features/<feature>/.
2. Wire route in frontend/src/App.tsx.
3. Use API clients from frontend/src/shared/api/generated.
4. Run lint/tests/build.

## Security and Compliance Baseline

### Implemented baseline

- JWT auth with refresh rotation and token blacklisting.
- CORS configuration via env.
- DRF throttling classes configured in settings.
- Custom exception middleware/handler.
- File upload size limits and validator-based import processing.

### Planned (Semester 2)

- Full audit logging for sensitive actions (grade changes, exports, auth events).
- KVKK/GDPR workflow features (consent, retention, export/portability, breach tracking).
- Expanded monitoring and compliance reporting.

Do not claim planned compliance features as complete unless code and tests are added.

## Semester 2 Roadmap Guidance (Planned, Not Fully Implemented)

This section guides implementation order for remaining project work.

### Target capabilities

- Async processing for heavy workloads using Celery + Redis.
- Real-time updates using Django Channels + Redis pub/sub.
- Performance improvements (query optimization, caching, background tasks).
- AI-assisted weight recommendation service (local LLM via Ollama) with rule-based fallback.
- Risk analytics engine (rule-based first, ML later when sufficient data exists).
- Reporting/export features (PDF/Excel) and notification service.
- Optional RPA integration for external university system synchronization.

### Suggested implementation phases

1. Infrastructure foundation: PostgreSQL default path, Redis, Celery integration.
2. Performance: async score calculation and import jobs, caching layer.
3. Real-time: WebSocket events for grade and dashboard updates.
4. AI assistance: weight recommendation API + instructor approval workflow.
5. Compliance and governance: audit trails and privacy operations.
6. Hardening: load/security testing, deployment readiness.

### Acceptance-oriented targets from proposal

- Substantial score calculation speedup for large courses.
- Reduced manual weight assignment effort for instructors.
- Higher test coverage targets over current baseline.
- Better reliability and observability for production operation.

## Known Gaps and Constraints

- Score calculation service is synchronous today.
- Real-time messaging stack is not fully integrated yet.
- SQLite is still used by many local environments.
- Frontend API generation config appears partially stale versus current folder layout.
- run.bat still assumes backend/venv activation; local preferred backend workflow is uv.

Treat these as active engineering tasks, not documentation noise.

## Agent Guardrails

1. Preserve backward-compatible API routes unless migration plan is explicit.
2. Keep generated API code auto-generated; avoid manual edits in generated folders.
3. Include migrations for model changes and run checks before finishing.
4. Ensure implemented versus planned status is always explicit in commits and PRs.
5. Prefer minimal, targeted changes aligned with existing architecture.

## UI Design System

This project follows a consistent design language established by the landing page. All new UI components, dashboards, and modals must follow these patterns.

### Color Palette

The project uses three main color scales plus contextual accent colors:

| Scale | Usage | Key Values |
|-------|-------|------------|
| **primary** (teal) | CTAs, active states, brand identity | 50: `#f0fdfa` → 900: `#134e4a`, 600: `#0d9488` (default) |
| **secondary** (gray-blue) | Surfaces, text, borders, backgrounds | 50: `#f8fafc` → 900: `#0f172a`, 900 for dark sections, 50 for page backgrounds |
| **violet** | Secondary accent, instructor features, highlights | 500: `#a855f7`, 600: `#7c3aed` |
| **success** | Positive feedback | 500: `#22c55e`, 600: `#16a34a` |
| **warning** | Caution states | 500: `#f59e0b`, 600: `#d97706` |
| **danger** | Error/destructive states | 500: `#ef4444`, 600: `#dc2626` |

Accent pairing convention:
- primary → student-facing features
- violet → instructor features
- green → department head/admin features
- amber/orange → warnings and trend indicators

### Typography

- Font: `Inter, system-ui, sans-serif` (set in tailwind.config.js)
- Headings: `font-bold`, scale from `text-lg` (cards) → `text-4xl`/`text-6xl` (hero)
- Body: `text-sm` to `text-lg`, `text-secondary-500` for muted, `text-secondary-600` for secondary
- Labels: `text-xs uppercase tracking-wide` for small labels above values
- Stats: `text-3xl font-bold text-secondary-900` for large numbers

### Layout & Spacing

- Max content width: `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8`
- Section padding: `py-20 sm:py-28` (landing), `p-6` (dashboard cards)
- Grid layouts: `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-8`
- Card padding: `p-6 sm:p-8`
- Inter-element spacing: `space-y-6` or `space-y-8` for section-level, `gap-6` for grids

### Card Patterns

Use the `Card` component from `shared/components/ui/Card`:

- **default**: `bg-white shadow-card border border-secondary-200 rounded-xl` — standard cards
- **hover**: Same as default + `hover:shadow-card-hover hover:-translate-y-0.5` — interactive cards
- **flat**: `bg-white border border-secondary-200 rounded-xl` — no shadow
- **glass**: `bg-white/70 backdrop-blur-lg border border-white/20 shadow-lg` — overlay cards

Card with icon badge pattern:
```
<div className="h-12 w-12 rounded-xl {accent-bg} flex items-center justify-center mb-5">
  <Icon className="h-6 w-6 {accent-icon}" />
</div>
<h3 className="text-lg font-bold text-secondary-900 mb-2">{title}</h3>
<p className="text-secondary-500 text-sm leading-relaxed">{description}</p>
```

### Stat Card Pattern (from HeadDashboard)

For displaying key metrics:
```tsx
<Card variant="flat" className="bg-white border-secondary-200">
  <div className="flex items-center space-x-4">
    <div className="p-3 {accent-bg} rounded-xl">
      <Icon className="h-8 w-8 {accent-text}" />
    </div>
    <div>
      <p className="text-sm text-secondary-600 font-medium">{label}</p>
      <p className="text-3xl font-bold text-secondary-900">{value}</p>
    </div>
  </div>
</Card>
```

### Section Structure

Landing page section pattern:
```tsx
<section className="py-20 sm:py-28 {bg-class}">
  <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div className="text-center mb-16">
      <h2 className="text-3xl sm:text-4xl font-bold text-secondary-900 mb-4">
        {heading}
      </h2>
      <p className="text-lg text-secondary-500 max-w-2xl mx-auto">
        {subtitle}
      </p>
    </div>
    {/* Content */}
  </div>
</section>
```

Background alternation for landing sections: white → secondary-50 → white → secondary-900 → white → primary-600

Dashboard section pattern:
```tsx
<main className="p-6 max-w-7xl mx-auto">
  {/* Content */}
</main>
```

### Button Styles

| Role | Classes |
|------|---------|
| **Primary CTA** | `px-8 py-3.5 bg-primary-600 text-white font-semibold rounded-xl shadow-lg hover:bg-primary-700 hover:shadow-xl hover:-translate-y-0.5 transition-all duration-200` |
| **Secondary CTA** | `px-8 py-3.5 bg-white/10 text-white font-semibold rounded-xl border border-white/20 hover:bg-white/20 transition-all duration-200` (on dark bg) |
| **Small action** | `flex items-center gap-2 px-3 py-1.5 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 transition-colors` |
| **Tab toggle** | `px-3 py-1.5 text-sm rounded-lg transition {active ? 'bg-primary-600 text-white' : 'bg-secondary-100 text-secondary-600 hover:bg-secondary-200'}` |
| **Ghost/Nav** | `text-sm font-medium text-secondary-600 hover:text-primary-600 transition-colors` |

### Modal Pattern

Modals use `fixed inset-0 z-50` overlay with centered content:
- Overlay: `bg-black bg-opacity-50` (or `bg-secondary-900/50 backdrop-blur-sm` for more polish)
- Container: `bg-white rounded-2xl shadow-xl w-full max-w-2xl relative`
- Header: `flex items-center justify-between p-6 border-b border-secondary-200`
- Body: `p-6 max-h-[70vh] overflow-y-auto`
- Close button: top-right X icon with `text-secondary-400 hover:text-secondary-600 transition-colors`

### Form Input Pattern

- Label: `block text-sm font-medium text-secondary-700 mb-2`
- Text input: `block w-full rounded-xl border border-secondary-300 px-4 py-2.5 text-sm text-secondary-900 placeholder-secondary-400 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 transition`
- File input: custom styled with `file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100`

### Feedback/Alert Patterns

| Type | Classes |
|------|---------|
| **Success** | `bg-emerald-50 border border-emerald-200 rounded-xl p-6` with `text-emerald-800` heading, `text-emerald-600` body |
| **Error** | `bg-danger-50 border border-danger-200 rounded-xl p-6` with `text-danger-800` heading, `text-danger-600` body |
| **Warning** | `bg-warning-50 border border-warning-200 rounded-xl p-6` with `text-warning-800` heading |
| **Info** | `bg-primary-50 border border-primary-200 rounded-xl p-4` with `text-primary-800` heading, `text-primary-700` body |

Dismiss pattern:
```tsx
<button className="mt-4 px-4 py-2 bg-{color}-600 text-white rounded-lg hover:bg-{color}-700 transition-colors">
  Dismiss
</button>
```

### Loading & Empty States

Loading spinner:
```tsx
<div className="flex items-center justify-center h-96">
  <div className="text-center">
    <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-primary-600 mx-auto" />
    <p className="mt-4 text-secondary-600 font-medium">Loading...</p>
  </div>
</div>
```

Skeleton loading (for inline):
```tsx
<div className="h-10 w-16 bg-secondary-200 rounded animate-pulse mx-auto mb-2" />
<div className="h-4 w-20 bg-secondary-100 rounded animate-pulse mx-auto" />
```

Empty state:
```tsx
<Card className="text-center py-12">
  <Icon className="h-12 w-12 mx-auto mb-4 text-secondary-300" />
  <h3 className="text-lg font-semibold text-secondary-900 mb-2">{title}</h3>
  <p className="text-secondary-500">{description}</p>
</Card>
```

### Step/Process Indicator Pattern

From HowItWorksSection: numbered circles with color coding:
```tsx
<div className={`w-10 h-10 ${color} text-white rounded-full flex items-center justify-center mx-auto mb-3 font-bold text-lg`}>
  {number}
</div>
```

### Dark Section Pattern (from RoleCardsSection, Footer)

For hero-scale and footer sections:
- Background: `bg-secondary-900`
- Text colors: headings `text-white`, body `text-secondary-400`, links `text-secondary-300 hover:text-primary-400`
- Cards on dark: `bg-secondary-800 rounded-xl border border-{accent}-600/20`
- Dividers: `border-t border-secondary-700`

### Icon Box Pattern

For feature cards and stat cards:
```tsx
<div className="h-12 w-12 rounded-xl {accent-bg-color} flex items-center justify-center">
  <Icon className="h-6 w-6 {accent-icon-color}" />
</div>
```

Size variants: `h-10 w-10 rounded-lg` (compact), `h-12 w-12 rounded-xl` (default), `p-3 rounded-xl` (stat cards with larger icons `h-8 w-8`)

### Animation & Transitions

- Card hover: `hover:shadow-lg hover:-translate-y-1 transition-all duration-300`
- Button hover: `hover:-translate-y-0.5 hover:shadow-xl transition-all duration-200`
- Link/nav: `transition-colors duration-300`
- Navbar scroll: `transition-all duration-300`

### Responsive Breakpoints

- Mobile first approach
- Key breakpoints: `sm:`, `md:`, `lg:`
- Section padding: `py-20 sm:py-28`, `px-4 sm:px-6 lg:px-8`
- Grid: 1 col → `md:grid-cols-2` → `lg:grid-cols-3` (or `-4` for stats)
- Font scaling: `text-3xl sm:text-4xl lg:text-6xl` (hero), `text-xl sm:text-4xl` (section headings)

## Useful Paths

- docs/api/API_CONTRACT_V1.md
- backend/student_evaluation_system/schema.yml
- backend/student_evaluation_system/student_evaluation_system/settings.py
- backend/student_evaluation_system/student_evaluation_system/urls.py
- backend/student_evaluation_system/core/
- backend/student_evaluation_system/evaluation/
- backend/student_evaluation_system/users/
- backend/student_evaluation_system/tests/
- frontend/src/App.tsx
- frontend/src/features/
- frontend/src/shared/api/
- frontend/orval.config.cjs
- backend/pyproject.toml
- backend/pytest.ini
- frontend/package.json
