#!/bin/bash
# deploy-addon.sh — Deploy one or more Odoo addons to production
# Usage: ./scripts/deploy-addon.sh [addon1] [addon2] ...
# Example: ./scripts/deploy-addon.sh mfg_management casting_foundry
#
# What it does:
#   1. rsync addons to server
#   2. Clear ir_attachment asset cache for the specified modules
#   3. Run odoo -u <addons> --stop-after-init
#   4. Restart odoo_web (stack down+up to avoid Traefik 504)
#   5. Wait for healthy state and verify HTTP 200

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

ADDONS="${*:-mfg_management}"
ADDONS_CSV="${ADDONS// /,}"

echo "==> [1/5] rsync to ${SERVER}:${COMPOSE_DIR}"
rsync -az \
  --exclude='.git' \
  --exclude='secrets.env' \
  --exclude='.env.prod' \
  "${LOCAL_REPO}/" "${SERVER}:${COMPOSE_DIR}/"

echo "==> [2/5] Clear ir_attachment asset cache on server"
ssh "${SERVER}" "docker exec ${DB_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} -c \
  \"DELETE FROM ir_attachment WHERE name LIKE '%assets%' AND res_model = 'ir.ui.view';\" \
  2>&1 | grep -E 'DELETE|ERROR'"

echo "==> [3/5] Update addon(s): ${ADDONS_CSV}"
ssh "${SERVER}" "docker exec ${WEB_CONTAINER} odoo \
  --db_host=db --db_user=${DB_USER} --db_password=${DB_PASS} \
  -d ${DB_NAME} -u ${ADDONS_CSV} --stop-after-init 2>&1 \
  | grep -E 'INFO.*loaded|ERROR|WARNING' | tail -8"

echo "==> [4/5] Restart stack (down + up for clean Traefik routes)"
ssh "${SERVER}" "cd ${COMPOSE_DIR} && \
  docker compose -f ${COMPOSE_FILE} --env-file ${ENV_FILE} down && \
  docker compose -f ${COMPOSE_FILE} --env-file ${ENV_FILE} up -d 2>&1 | tail -6"

echo "==> [5/5] Wait for healthy state..."
for i in $(seq 1 12); do
  sleep 10
  STATUS=$(ssh "${SERVER}" "curl -sk https://odoo.iil.pet/web/health -w '%{http_code}' -o /dev/null" 2>/dev/null || echo "000")
  echo "    attempt ${i}/12: HTTP ${STATUS}"
  if [ "${STATUS}" = "200" ]; then
    echo "==> Done! Stack is healthy. https://odoo.iil.pet/web"
    exit 0
  fi
done

echo "ERROR: Stack did not become healthy after 120s" >&2
exit 1
