# Student Evaluation System (SES)

Student Evaluation System (SES) is an outcome-based assessment platform for higher education.

It helps instructors and departments measure student performance from:

- Assessments (exams, quizzes, projects)
- Learning Outcomes (LOs)
- Program Outcomes (POs)

SES supports file-based grade imports, validation and resolution flows for problematic data, and asynchronous score recomputation in the background.

## Project Overview

The project has two main applications:

- `backend/`: Django REST API with Celery workers for asynchronous jobs
- `frontend/`: React + Vite web app for instructors, heads, and students

Core use cases include:

- Course-level grading and analytics
- Mapping assessments to learning/program outcomes
- Bulk import of assignment scores with guided validation
- Progress tracking and notifications for background recomputation jobs

## System Architecture

SES uses a service-oriented architecture with separate runtime components:

- `frontend` (React, Vite): UI, form flows, dashboards, and global notifications
- `backend` (Django + DRF): REST API, validation, import orchestration, business logic
- `postgres` (PostgreSQL): relational data store
- `redis` (Redis): Celery broker/result backend
- `celery_worker` (Celery): asynchronous recomputation and background processing

High-level flow for grade import:

1. User uploads file in frontend
2. Backend validates structure, students, assessments, and score consistency
3. Valid data is persisted
4. Backend enqueues score recomputation jobs (Celery)
5. Frontend polls job status and shows global session notifications
6. UI refreshes when recomputation completes

### Backend modules

- `core/`: courses, file import endpoints/services, validation pipeline
- `evaluation/`: enrollments, grades, recompute jobs, outcome calculations
- `users/`: authentication and user profile domain

### Frontend modules

- `features/auth/`: auth state and access flows
- `features/courses/`: course detail, mapping editor, import modal, resolution modals
- `features/dashboard/`: instructor/student/head dashboards
- `shared/`: API clients, layout, reusable UI, global contexts

## Installation (Docker-first)

This guide is the recommended setup for local development.

### Prerequisites

- Docker Desktop (or Docker Engine + Compose plugin)
- Git

### 1) Clone repository

```bash
git clone <your-repo-url> ses
cd ses
```

### 2) Configure environment files

Backend:

```bash
cp backend/.env.example backend/.env
```

Frontend (development):

```bash
cp frontend/.env.example frontend/.env.development
```

Defaults in compose already point services to:

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- Postgres: `localhost:5432`
- Redis: `localhost:6379`

### 3) Start all services

```bash
docker compose up --build
```

This starts:

- `db`
- `redis`
- `backend`
- `celery_worker`
- `frontend`

### 4) Run database migrations

In a new terminal:

```bash
docker compose exec backend uv run --no-sync python student_evaluation_system/manage.py migrate
```

### 5) Access the system

- Frontend: <http://localhost:5173>
- Backend API: <http://localhost:8000>
- API schema: <http://localhost:8000/api/schema/>
- Swagger docs: <http://localhost:8000/api/docs/>

### Useful Docker commands

Stop services:

```bash
docker compose down
```

Stop and remove volumes (fresh state):

```bash
docker compose down -v
```

View logs:

```bash
docker compose logs -f backend
docker compose logs -f celery_worker
docker compose logs -f frontend
```

## Local (non-Docker) workflow (optional)

Backend:

```bash
cd backend
uv sync
uv run python student_evaluation_system/manage.py migrate
uv run python student_evaluation_system/manage.py runserver
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Development Commands

Backend:

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

Frontend:

```bash
cd frontend
npm run lint
npm run test -- --run
npm run test:coverage
npm run build
```

Regenerate frontend API client after backend schema changes:

```bash
cd frontend
npm run generate:api
```

## Future Objectives

- Add push-based background job updates (WebSocket/SSE) to reduce polling overhead
- Expand analytics with richer LO/PO trend and cohort insights
- Improve role-based auditability for imports, resolutions, and recalculation actions
- Strengthen observability (job metrics, tracing, and dashboarding)
- Improve deployment docs for production environments (security hardening, scaling, backups)

## Notes

- CI and backend tooling use `uv`.
- Project-specific agent guidance lives in `.github/copilot-instructions.md`.
