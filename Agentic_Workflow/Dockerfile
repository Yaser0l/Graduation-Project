# Build stage
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/app/.venv

# Use wildcards (*) so the build doesn't crash if optional files are missing
COPY pyproject.toml* uv.lock* ./

# Install dependencies into /app/.venv (cache uv downloads)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv "$UV_PROJECT_ENVIRONMENT" \
    && if [ -f uv.lock ]; then \
        uv sync --frozen --no-dev --no-install-project; \
    fi

# Use wildcard for optional requirements.txt
COPY requirements.txt* ./
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=cache,target=/root/.cache/pip \
    if [ ! -f uv.lock ] && [ -f requirements.txt ]; then \
        uv pip install --python "$UV_PROJECT_ENVIRONMENT/bin/python" -r requirements.txt; \
    elif [ ! -f uv.lock ] && [ ! -f requirements.txt ]; then \
        echo "Missing uv.lock and requirements.txt" >&2; \
        exit 1; \
    fi

# Copy app code
COPY data ./data
COPY runner.py ./runner.py
COPY config.py ./config.py
COPY src ./src

# Runtime stage
FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"

# 1. Create the user FIRST
RUN useradd -m -u 1000 appuser \
    && mkdir -p /app/output /app/data/users /app/data/chroma_db \
    && chown -R appuser:appuser /app

# 2. Copy files and set ownership in the same step to prevent layer bloat
COPY --chown=appuser:appuser --from=builder /app/.venv /app/.venv
COPY --chown=appuser:appuser --from=builder /app/src /app/src
COPY --chown=appuser:appuser --from=builder /app/config.py /app/config.py
COPY --chown=appuser:appuser --from=builder /app/runner.py /app/runner.py
COPY --chown=appuser:appuser --from=builder /app/data /app/data

# 3. Switch to the non-root user
USER appuser

EXPOSE 8000

# 4. Use 'exec' to ensure uvicorn receives SIGTERM for graceful shutdowns
CMD ["sh", "-c", "exec uvicorn src.api:app --host 0.0.0.0 --port ${PORT:-8000}"]