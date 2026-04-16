# Use UV's official Python image
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

LABEL project="ses" service="backend"

RUN groupadd -g 1000 django && \
    useradd -m -u 1000 -g django django

RUN mkdir -p /app && chown django:django /app
WORKDIR /app

USER django

COPY --chown=django:django pyproject.toml uv.lock* ./

ENV UV_LINK_MODE=copy
ENV UV_CACHE_DIR=/app/.cache/uv

RUN --mount=type=cache,target=/app/.cache/uv,uid=1000,gid=1000 \
    uv sync --frozen --no-install-project

COPY --chown=django:django student_evaluation_system ./student_evaluation_system

EXPOSE 8000

CMD ["uv", "run", "--no-sync", "python", "student_evaluation_system/manage.py", "runserver", "0.0.0.0:8000"]
