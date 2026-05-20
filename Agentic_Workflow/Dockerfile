# Build stage
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/app/.venv

# Copy dependency files first to maximize layer caching
COPY pyproject.toml uv.lock requirements.txt ./

# Install dependencies into /app/.venv
RUN uv venv "$UV_PROJECT_ENVIRONMENT" \
	&& if [ -f uv.lock ]; then \
		uv sync --frozen --no-dev --no-install-project; \
	elif [ -f requirements.txt ]; then \
		uv pip install --python "$UV_PROJECT_ENVIRONMENT/bin/python" -r requirements.txt; \
	else \
		echo "Missing uv.lock and requirements.txt" >&2; \
		exit 1; \
	fi

# Copy app code
COPY src ./src
COPY config.py ./config.py
COPY runner.py ./runner.py
COPY data ./data

# Runtime stage
FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"

# Copy virtualenv and app files from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/config.py /app/config.py
COPY --from=builder /app/runner.py /app/runner.py
COPY --from=builder /app/data /app/data

# Create non-root user and ensure ownership
RUN useradd -m -u 1000 appuser \
	&& mkdir -p /app/output /app/data/users /app/data/chroma_db \
	&& chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["sh", "-c", "uvicorn src.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
