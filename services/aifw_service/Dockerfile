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

# ── Layer 2: Application code (changes most often) ───────────────────────────
# Note: iil-aifw is now installed from PyPI via requirements.txt
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
