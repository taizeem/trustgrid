FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv for fast, reproducible dependency resolution
COPY --from=ghcr.io/astral-sh/uv:0.4.15 /uv /bin/uv

# Copy project specification
COPY pyproject.toml /app/

# Install dependencies into isolated virtual environment
RUN uv sync --no-dev --no-install-project

# Final runtime image
FROM python:3.12-slim AS runtime

WORKDIR /app

# Create unprivileged runtime user and group
RUN groupadd -r trustgrid && useradd -r -g trustgrid -d /app -s /sbin/nologin trustgrid

# Ensure the unprivileged user owns the virtual environment and application directory
COPY --chown=trustgrid:trustgrid --from=builder /app/.venv /app/.venv
COPY --chown=trustgrid:trustgrid . /app

# Pre-create migrations directory with write ownership for trustgrid user
RUN mkdir -p /app/billing/migrations && chown -R trustgrid:trustgrid /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER trustgrid

EXPOSE 8007

# Docker engine healthcheck
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8007/health/')" || exit 1

CMD ["python", "manage.py", "runserver", "0.0.0.0:8007"]