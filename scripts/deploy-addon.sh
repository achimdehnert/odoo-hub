#!/bin/bash
# deploy-addon.sh — Deploy one or more Odoo addons to production
# Usage: ./scripts/deploy-addon.sh [addon1] [addon2] ...
# Example: ./scripts/deploy-addon.sh mfg_management casting_foundry
# Flags:
#   --rebuild-aifw   Force rebuild of aifw_service Docker image
#
# What it does:
#   1. rsync odoo-hub + aifw source to server
#   2. Clear ir_attachment asset cache for the specified modules
#   3. Run odoo -u <addons> --stop-after-init
#   4. Rebuild aifw_service if --rebuild-aifw flag set
#   5. Restart full stack (down+up for clean Traefik routes)
#   6. Wait for healthy state and verify HTTP 200

set -euo pipefail

SERVER="root@46.225.127.211"
COMPOSE_DIR="/opt/odoo-hub"
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.prod"
DB_CONTAINER="odoo_db"
WEB_CONTAINER="odoo_web"
DB_NAME="odoo"
DB_USER="odoo"
DB_PASS="ODO2026odo."
LOCAL_REPO="$(cd "$(dirname "$0")/.." && pwd)"
AIFW_REPO="$(cd "${LOCAL_REPO}/../aifw" 2>/dev/null && pwd || echo "")"

REBUILD_AIFW=false
ADDONS_ARGS=()
for arg in "$@"; do
  if [ "$arg" = "--rebuild-aifw" ]; then
    REBUILD_AIFW=true
  else
    ADDONS_ARGS+=("$arg")
  fi
done

ADDONS="${ADDONS_ARGS[*]:-mfg_management}"
ADDONS_CSV="${ADDONS// /,}"

echo "==> [1/6] rsync odoo-hub to ${SERVER}:${COMPOSE_DIR}"
rsync -az \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='secrets.env' \
  --exclude='.env.prod' \
  "${LOCAL_REPO}/" "${SERVER}:${COMPOSE_DIR}/"

if [ -n "${AIFW_REPO}" ] && [ -d "${AIFW_REPO}" ]; then
  echo "     rsync aifw source to ${SERVER}:${COMPOSE_DIR}/aifw"
  rsync -az \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='dist/' \
    "${AIFW_REPO}/" "${SERVER}:${COMPOSE_DIR}/aifw/"
else
  echo "     (aifw source not found at ${LOCAL_REPO}/../aifw — skipping)"
fi

echo "==> [2/6] Clear ir_attachment asset cache on server"
ssh "${SERVER}" "docker exec ${DB_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} -c \
  \"DELETE FROM ir_attachment WHERE name LIKE '%assets%' AND res_model = 'ir.ui.view';\" \
  2>&1 | grep -E 'DELETE|ERROR'"

echo "==> [3/6] Update addon(s): ${ADDONS_CSV}"
ssh "${SERVER}" "docker exec ${WEB_CONTAINER} odoo \
  --db_host=db --db_user=${DB_USER} --db_password=${DB_PASS} \
  -d ${DB_NAME} -u ${ADDONS_CSV} --stop-after-init 2>&1 \
  | grep -E 'INFO.*loaded|ERROR|WARNING' | tail -8"

if [ "${REBUILD_AIFW}" = "true" ]; then
  echo "==> [4/6] Rebuild aifw_service image (--rebuild-aifw)"
  ssh "${SERVER}" "cd ${COMPOSE_DIR} && \
    docker compose -f ${COMPOSE_FILE} --env-file ${ENV_FILE} build --no-cache aifw_service 2>&1 | tail -5"
else
  echo "==> [4/6] aifw_service rebuild skipped (use --rebuild-aifw to force)"
fi

echo "==> [5/6] Restart stack (down + up for clean Traefik routes)"
ssh "${SERVER}" "cd ${COMPOSE_DIR} && \
  docker compose -f ${COMPOSE_FILE} --env-file ${ENV_FILE} down && \
  docker compose -f ${COMPOSE_FILE} --env-file ${ENV_FILE} up -d 2>&1 | tail -8"

echo "==> [6/6] Wait for healthy state..."
for i in $(seq 1 12); do
  sleep 10
  STATUS=$(ssh "${SERVER}" "curl -sk https://odoo.iil.pet/web/health -w '%{http_code}' -o /dev/null" 2>/dev/null || echo "000")
  AIFW_STATUS=$(ssh "${SERVER}" "docker exec aifw_service curl -s -o /dev/null -w '%{http_code}' http://localhost:8001/health" 2>/dev/null || echo "000")
  echo "    attempt ${i}/12: Odoo HTTP ${STATUS} | aifw_service HTTP ${AIFW_STATUS}"
  if [ "${STATUS}" = "200" ] && [ "${AIFW_STATUS}" = "200" ]; then
    echo "==> Done! Stack is healthy."
    echo "    Odoo:         https://odoo.iil.pet/web"
    echo "    aifw_service: http://aifw_service:8001/health (internal)"
    exit 0
  fi
done

echo "ERROR: Stack did not become healthy after 120s" >&2
exit 1
