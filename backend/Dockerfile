# syntax=docker/dockerfile:1.7

# Use UV's official Python image
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock* ./

ENV UV_LINK_MODE=copy

# Install only dependencies first (cache-friendly layer)
RUN --mount=type=cache,target=/root/.cache/uv \
	uv sync --frozen --no-install-project

# Copy application code
COPY . .

# Install project after source is copied
RUN --mount=type=cache,target=/root/.cache/uv \
	uv sync --frozen

CMD ["uv", "run", "--no-sync", "python", "student_evaluation_system/manage.py", "runserver", "0.0.0.0:8000"]
