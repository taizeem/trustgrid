FROM python:3.12-slim AS builder

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.4.15 /uv /bin/uv

COPY pyproject.toml /app/

RUN uv sync --no-dev --no-install-project

FROM python:3.12-slim AS runtime

WORKDIR /app

RUN groupadd -r trustgrid && useradd -r -g trustgrid -d /app -s /sbin/nologin trustgrid

# Ensure the unprivileged user owns the virtualenv and application directory
COPY --chown=trustgrid:trustgrid --from=builder /app/.venv /app/.venv
COPY --chown=trustgrid:trustgrid . /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER trustgrid

EXPOSE 8007

CMD ["python", "manage.py", "runserver", "0.0.0.0:8007"]