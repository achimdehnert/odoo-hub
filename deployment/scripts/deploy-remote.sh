#!/usr/bin/env bash
# =============================================================================
# deploy-remote.sh — Deploy odoo-hub to production (ADR-022 compliant)
# =============================================================================
set -euo pipefail

SERVER="46.225.127.211"
PROJECT_DIR="/opt/odoo"
IMAGE="ghcr.io/achimdehnert/odoo-hub"
IMAGE_TAG="${1:-latest}"
HEALTH_URL="http://127.0.0.1:8069/web/login"

echo "=== Deploying odoo-hub:${IMAGE_TAG} to ${SERVER} ==="

# Pull new image
ssh root@${SERVER} "cd ${PROJECT_DIR} && docker compose pull web"

# Backup DB before deploy
ssh root@${SERVER} \
    "docker exec odoo_db pg_dump -U odoo -Fc odoo \
     > ${PROJECT_DIR}/backups/pre-deploy-$(date +%Y%m%d_%H%M%S).dump" \
    || true

# Recreate
ssh root@${SERVER} \
    "cd ${PROJECT_DIR} && IMAGE_TAG=${IMAGE_TAG} docker compose up -d --force-recreate web"

# Health check (wait up to 60s)
for i in $(seq 1 12); do
    if ssh root@${SERVER} "curl -sf ${HEALTH_URL}" > /dev/null 2>&1; then
        echo "=== Health check passed ==="
        exit 0
    fi
    echo "Waiting for health... (${i}/12)"
    sleep 5
done

echo "=== HEALTH CHECK FAILED — consider rollback ==="
exit 1
