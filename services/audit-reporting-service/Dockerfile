FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv for deterministic dependency resolution
COPY --from=ghcr.io/astral-sh/uv:0.4.15 /uv /bin/uv

# Copy project specification
COPY pyproject.toml /app/

# Install dependencies including dev dependencies
RUN uv sync --no-install-project

# Final runtime image
FROM python:3.12-slim AS runtime

WORKDIR /app

# Unprivileged system user
RUN groupadd -r trustgrid && useradd -r -g trustgrid -d /app -s /sbin/nologin trustgrid

COPY --chown=trustgrid:trustgrid --from=builder /app/.venv /app/.venv
COPY --chown=trustgrid:trustgrid . /app

RUN mkdir -p /app/audit/migrations && chown -R trustgrid:trustgrid /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER trustgrid

EXPOSE 8008

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8008/health/')" || exit 1

CMD ["python", "manage.py", "runserver", "0.0.0.0:8008"]