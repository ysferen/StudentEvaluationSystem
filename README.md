# Student Evaluation System

Student Evaluation System (SES) is an outcome-based assessment platform for higher education.

It tracks student achievement from Assessment -> Learning Outcome (LO) -> Program Outcome (PO).

## Quick Start

## Prerequisites

- Python 3.12+
- Node.js 18+
- uv (recommended for local backend workflow)

## Backend (recommended local workflow)

```bash
cd backend
uv sync
cd student_evaluation_system
uv run python manage.py migrate
uv run python manage.py runserver
```

Backend runs on <http://localhost:8000>

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on <http://localhost:5173>

## Common Commands

## Backend

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

## Frontend Commands

```bash
cd frontend
npm run lint
npm run test -- --run
npm run test:coverage
npm run build
```

## API Docs

- Schema: /api/schema/
- Swagger UI: /api/docs/

## API Client Generation (Frontend)

Regenerate frontend API clients after backend serializer/view schema changes:

```bash
cd frontend
npm run generate:api
```

## Notes

- Local backend workflow prefers uv, but CI currently installs backend dependencies with pip and backend/requirements.txt.
- Agent-facing project context now lives in .github/copilot-instructions.md.
