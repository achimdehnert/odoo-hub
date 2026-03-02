# Build context: repo root (odoo-hub/)
# docker compose build --build-arg CACHE_BUST=$(date +%s) aifw_service
FROM python:3.11-slim

WORKDIR /app

# System deps: libpq for psycopg2, curl for healthcheck, postgresql-client for pg_isready
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev postgresql-client curl \
    && rm -rf /var/lib/apt/lists/*

# ── Layer 1: Python deps (changes rarely — cached aggressively) ──────────────
COPY services/aifw_service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# ── Layer 2: iil-aifw from source (not yet on PyPI as v0.6.0) ───────────────
# Copied from aifw/ sibling dir in repo root (kept in sync via deploy script).
# Only invalidated when aifw/pyproject.toml or aifw/src/ changes.
COPY aifw/pyproject.toml /tmp/iil_aifw/pyproject.toml
COPY aifw/README.md      /tmp/iil_aifw/README.md
COPY aifw/src/           /tmp/iil_aifw/src/
RUN pip install --no-cache-dir /tmp/iil_aifw \
    && rm -rf /tmp/iil_aifw

# ── Layer 3: Application code (changes most often) ───────────────────────────
COPY services/aifw_service/ .

# Non-root user for security
RUN useradd -m -u 1000 aifw && chown -R aifw:aifw /app
USER aifw

EXPOSE 8001

# CMD is overridden by entrypoint in docker-compose — kept as fallback
CMD ["gunicorn", "aifw_service.wsgi:application", \
     "--bind", "0.0.0.0:8001", \
     "--workers", "2", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
