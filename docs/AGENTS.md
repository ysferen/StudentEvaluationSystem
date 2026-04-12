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
