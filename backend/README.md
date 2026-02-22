## `backend/README.md` (Django + `uv`)

Backend service for the **Student Evaluation System**.
Built with Django, Django REST Framework, and JWT auth.

---

### Requirements

- Python **3.12+**
- [`uv`](https://docs.astral.sh/uv/) installed

Check versions:

```bash
python --version
uv --version
```

---

### Setup

From project root:

```bash
cd backend
uv sync
```

Run commands with `uv run` (no manual venv activation needed).

---

### Run the App

```bash
cd backend/student_evaluation_system
uv run python manage.py migrate
uv run python manage.py runserver
```

Backend URL: `http://localhost:8000`

Useful docs endpoints:

- OpenAPI schema: `/api/schema/`
- Swagger UI: `/api/docs/`

---

### Common Commands

From `backend/student_evaluation_system`:

```bash
# Django checks
uv run python manage.py check

# Create/apply migrations
uv run python manage.py makemigrations
uv run python manage.py migrate

# Run tests
uv run pytest
uv run pytest --cov=student_evaluation_system

# Lint
uv run ruff check .
uv run ruff format --check .
```
---

### Notes

After backend serializer/view changes, regenerate frontend API client:

```bash
cd frontend
npm run generate:api
```
