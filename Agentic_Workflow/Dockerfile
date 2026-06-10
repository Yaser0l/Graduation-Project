# Build stage
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
ENV HF_HOME=/app/data/hf_cache

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

# Copy prewarm dependencies (keep cache stable when app code changes)
COPY data ./data
COPY scripts ./scripts
COPY config.py ./config.py
COPY src/__init__.py ./src/__init__.py
COPY src/rag ./src/rag

ARG HF_DATASET_REPO=aziz9788/automotive-rag-kb
ARG RAG_PREWARM=0
ARG RAG_PREWARM_STRICT=0
RUN --mount=type=secret,id=hf_token \
    --mount=type=cache,target=/root/.cache/huggingface \
    --mount=type=cache,target=/tmp/data-cache \
    if [ "$RAG_PREWARM" = "1" ]; then \
        HF_TOKEN="$(cat /run/secrets/hf_token 2>/dev/null || echo '')"; \
        HF_TOKEN="$HF_TOKEN" HF_DATASET_REPO="$HF_DATASET_REPO" \
        RAG_PREWARM_STRICT="$RAG_PREWARM_STRICT" \
        HF_HOME=/app/data/hf_cache \
        CHROMA_DB_PATH=/tmp/data-cache/chroma_db \
        RAG_SOURCES_DIR=/tmp/data-cache/sources \
        /app/.venv/bin/python scripts/prewarm_rag.py; \
        mkdir -p /app/data; \
        cp -a /tmp/data-cache/. /app/data/; \
        /app/.venv/bin/python -c "from huggingface_hub import snapshot_download; snapshot_download('BAAI/bge-m3')"; \
    else \
        echo "RAG prewarm skipped (RAG_PREWARM=0)"; \
    fi

# Copy remaining app code after prewarm to preserve cache
COPY src ./src
COPY runner.py ./runner.py

# Runtime stage
FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"
ENV HF_HOME=/app/data/hf_cache

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