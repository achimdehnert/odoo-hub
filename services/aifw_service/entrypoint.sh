#!/bin/bash
set -e

echo "==> [aifw-service] Running migrations..."
python manage.py migrate --noinput --verbosity 1

echo "==> [aifw-service] Seeding providers + models..."
python manage.py init_aifw_config

echo "==> [aifw-service] Seeding Odoo MFG schema + nl2sql action..."
python manage.py init_odoo_schema || echo "WARN: init_odoo_schema failed (non-fatal, run manually if needed)"

echo "==> [aifw-service] Starting gunicorn..."
exec gunicorn aifw_service.wsgi:application \
    --bind 0.0.0.0:8001 \
    --workers 2 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -
