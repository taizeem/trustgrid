FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv for fast, reproducible dependency resolution
COPY --from=ghcr.io/astral-sh/uv:0.4.15 /uv /bin/uv

# Copy project specification files
COPY pyproject.toml uv.lock* /app/

# Install dependencies into virtual environment
RUN uv sync --frozen --no-dev --no-install-project

# Final runtime image
FROM python:3.12-slim AS runtime

WORKDIR /app

# Create unprivileged runtime user
RUN groupadd -r trustgrid && useradd -r -g trustgrid -d /app -s /sbin/nologin trustgrid

# Copy virtual environment and application code
COPY --from=builder /app/.venv /app/.venv
COPY . /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER trustgrid

EXPOSE 8001

CMD ["python", "manage.py", "runserver", "0.0.0.0:8001"]