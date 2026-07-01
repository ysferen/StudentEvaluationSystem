# Contributing to SES

## Development setup

```bash
# Backend
cd backend
uv sync --dev
uv run python student_evaluation_system/manage.py migrate

# Frontend
cd frontend
npm ci
npm run dev
```

See [DEVELOPMENT.md](docs/DEVELOPMENT.md) for full details.

## Before submitting a PR

1. Run `uv run ruff check . && uv run ruff format --check .` (backend)
2. Run `uv run pytest` (backend)
3. Run `npx tsc --noEmit && npm run lint` (frontend)
4. Run `npm test` (frontend)
5. Keep changes minimal and focused — one concern per PR
6. Follow existing code patterns; no speculative abstractions

## Commit messages

- `feat:` new feature
- `fix:` bug fix
- `refactor:` code change that neither fixes a bug nor adds a feature
- `test:` adding or updating tests
- `docs:` documentation only
- `chore:` tooling, dependencies, CI
