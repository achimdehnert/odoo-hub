#!/bin/bash
# entrypoint.sh — aifw-service container startup
#
# Design:
#   - set -e only wraps FATAL steps (migrate). Non-fatal steps use '|| true'.
#   - DB wait loop prevents race condition when container starts before PG is ready
#     (docker-compose depends_on: healthy is best-effort with restart policies).
#   - Management commands that may fail on first run (missing tables etc.) are
#     non-fatal — the service still starts and retries are possible via 'docker exec'.
set -euo pipefail

DB_HOST="${AIFW_DB_HOST:-db}"
DB_PORT="${AIFW_DB_PORT:-5432}"
DB_USER="${AIFW_DB_USER:-aifw}"
DB_NAME="${AIFW_DB_NAME:-aifw}"

# ── 1. Wait for PostgreSQL ────────────────────────────────────────────────────
echo "==> [aifw-service] Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."
for i in $(seq 1 30); do
    if pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -q 2>/dev/null; then
        echo "==> [aifw-service] PostgreSQL ready (attempt ${i})"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "ERROR: PostgreSQL not ready after 30 attempts — aborting"
        exit 1
    fi
    echo "     attempt ${i}/30 — waiting 2s..."
    sleep 2
done

# ── 2. Migrations (FATAL if fails — service cannot run without schema) ────────
echo "==> [aifw-service] Running migrations..."
python manage.py migrate --noinput --verbosity 1

# ── 3. Seed LLM providers + models (non-fatal — idempotent, safe to retry) ───
echo "==> [aifw-service] Seeding LLM providers + models..."
python manage.py init_aifw_config || \
    echo "WARN: init_aifw_config failed — service starts anyway, retry via: docker exec aifw_service python manage.py init_aifw_config"

# ── 4. Seed Odoo schema + nl2sql action (non-fatal) ──────────────────────────
echo "==> [aifw-service] Seeding Odoo MFG schema + nl2sql action..."
python manage.py init_odoo_schema || \
    echo "WARN: init_odoo_schema failed — service starts anyway, retry via: docker exec aifw_service python manage.py init_odoo_schema"

# ── 5. Start Gunicorn ─────────────────────────────────────────────────────────
echo "==> [aifw-service] Starting gunicorn..."
exec gunicorn aifw_service.wsgi:application \
    --bind 0.0.0.0:8001 \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
