#!/bin/bash
# deploy-addon.sh — Deploy one or more Odoo addons to production
#
# Usage:
#   ./scripts/deploy-addon.sh [addon1] [addon2] ...
#   ./scripts/deploy-addon.sh mfg_management casting_foundry --rebuild-aifw
#
# Flags:
#   --rebuild-aifw   Force --no-cache rebuild of aifw_service image.
#                    Auto-triggered when aifw/ source hash changes.
#
# Steps:
#   1. rsync odoo-hub + aifw source to server
#   2. Detect if aifw source changed → auto-set REBUILD_AIFW
#   3. Clear Odoo JS asset cache for updated modules
#   4. Run odoo -u <addons> --stop-after-init
#   5. Build aifw_service (--no-cache if source changed or flag set)
#   6. Ensure aifw DB + users exist (idempotent — safe on existing volumes)
#   7. Restart full stack (down+up for clean Traefik routes)
#   8. Wait for healthy state (Odoo + aifw_service)

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

# ── Parse args ────────────────────────────────────────────────────────────────
REBUILD_AIFW=false
ADDONS_ARGS=()
for arg in "$@"; do
  case "$arg" in
    --rebuild-aifw) REBUILD_AIFW=true ;;
    *) ADDONS_ARGS+=("$arg") ;;
  esac
done

ADDONS="${ADDONS_ARGS[*]:-mfg_management}"
ADDONS_CSV="${ADDONS// /,}"

# ── Compute local aifw source hash (md5 of all .py + pyproject.toml) ─────────
# Used to auto-detect when aifw source changed → triggers --no-cache rebuild.
AIFW_HASH_LOCAL=""
if [ -n "${AIFW_REPO}" ] && [ -d "${AIFW_REPO}" ]; then
  AIFW_HASH_LOCAL=$(find "${AIFW_REPO}/src" "${AIFW_REPO}/pyproject.toml" \
    -type f \( -name "*.py" -o -name "pyproject.toml" \) \
    -exec md5sum {} \; 2>/dev/null | sort | md5sum | cut -d' ' -f1)
fi

# ── Step 1: rsync ─────────────────────────────────────────────────────────────
echo "==> [1/8] rsync odoo-hub → ${SERVER}:${COMPOSE_DIR}"
rsync -az \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='*.whl' \
  --exclude='secrets.env' \
  --exclude='.env.prod' \
  "${LOCAL_REPO}/" "${SERVER}:${COMPOSE_DIR}/"

if [ -n "${AIFW_REPO}" ] && [ -d "${AIFW_REPO}" ]; then
  echo "     rsync aifw → ${SERVER}:${COMPOSE_DIR}/aifw"
  rsync -az \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='dist/' \
    --exclude='*.egg-info' \
    "${AIFW_REPO}/" "${SERVER}:${COMPOSE_DIR}/aifw/"
else
  echo "     WARN: aifw source not found at ${LOCAL_REPO}/../aifw — NL2SQL may use stale image"
fi

# ── Step 2: Auto-detect aifw source change ────────────────────────────────────
echo "==> [2/8] Checking aifw source hash..."
if [ -n "${AIFW_HASH_LOCAL}" ]; then
  AIFW_HASH_REMOTE=$(ssh "${SERVER}" \
    "find ${COMPOSE_DIR}/aifw/src ${COMPOSE_DIR}/aifw/pyproject.toml \
     -type f \( -name '*.py' -o -name 'pyproject.toml' \) \
     -exec md5sum {} \; 2>/dev/null | sort | md5sum | cut -d' ' -f1" 2>/dev/null || echo "")
  if [ "${AIFW_HASH_LOCAL}" != "${AIFW_HASH_REMOTE}" ]; then
    echo "     aifw source changed (${AIFW_HASH_REMOTE:-none} → ${AIFW_HASH_LOCAL}) — forcing --no-cache rebuild"
    REBUILD_AIFW=true
  else
    echo "     aifw source unchanged (${AIFW_HASH_LOCAL}) — skipping rebuild"
  fi
fi

# ── Step 3: Clear Odoo JS asset cache ─────────────────────────────────────────
echo "==> [3/8] Clear ir_attachment asset cache for: ${ADDONS_CSV}"
ssh "${SERVER}" "docker exec ${DB_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} -c \
  \"DELETE FROM ir_attachment WHERE name LIKE '%assets%' AND res_model = 'ir.ui.view';\" \
  2>&1 | grep -E 'DELETE|ERROR'"

# ── Step 4: Update Odoo addon(s) ──────────────────────────────────────────────
echo "==> [4/8] odoo -u ${ADDONS_CSV}"
ssh "${SERVER}" "docker exec ${WEB_CONTAINER} odoo \
  --db_host=db --db_user=${DB_USER} --db_password=${DB_PASS} \
  -d ${DB_NAME} -u ${ADDONS_CSV} --stop-after-init 2>&1 \
  | grep -E 'INFO.*loaded|ERROR|WARNING' | tail -8"

# ── Step 5: Build aifw_service ────────────────────────────────────────────────
if [ "${REBUILD_AIFW}" = "true" ]; then
  echo "==> [5/8] Building aifw_service (--no-cache)..."
  ssh "${SERVER}" "cd ${COMPOSE_DIR} && \
    docker compose -f ${COMPOSE_FILE} --env-file ${ENV_FILE} \
    build --no-cache aifw_service 2>&1 | tail -6"
else
  echo "==> [5/8] aifw_service: no source changes, build skipped"
fi

# ── Step 6: Ensure aifw DB + users exist (idempotent) ────────────────────────
# Runs 02_aifw_db.sh manually — handles case where PG volume already existed
# when the script was first added (init-scripts only run on empty volumes).
echo "==> [6/8] Ensuring aifw DB + users (idempotent)..."
ssh "${SERVER}" "docker exec ${DB_CONTAINER} \
  bash /docker-entrypoint-initdb.d/02_aifw_db.sh 2>&1 | grep -v '^$'" || \
  echo "     WARN: 02_aifw_db.sh failed — check manually if aifw DB auth fails"

# ── Step 7: Restart stack ─────────────────────────────────────────────────────
echo "==> [7/8] Restart stack (down + up for clean Traefik routes)..."
ssh "${SERVER}" "cd ${COMPOSE_DIR} && \
  docker compose -f ${COMPOSE_FILE} --env-file ${ENV_FILE} down && \
  docker compose -f ${COMPOSE_FILE} --env-file ${ENV_FILE} up -d 2>&1 | tail -8"

# ── Step 8: Health wait ───────────────────────────────────────────────────────
echo "==> [8/8] Waiting for healthy state (max 120s)..."
for i in $(seq 1 12); do
  sleep 10
  ODOO_STATUS=$(ssh "${SERVER}" \
    "curl -sk https://odoo.iil.pet/web/health -w '%{http_code}' -o /dev/null" \
    2>/dev/null || echo "000")
  AIFW_STATUS=$(ssh "${SERVER}" \
    "docker exec aifw_service curl -sf -o /dev/null -w '%{http_code}' http://localhost:8001/health" \
    2>/dev/null || echo "000")
  echo "    [${i}/12] Odoo=${ODOO_STATUS} aifw_service=${AIFW_STATUS}"
  if [ "${ODOO_STATUS}" = "200" ] && [ "${AIFW_STATUS}" = "200" ]; then
    echo ""
    echo "==> Stack healthy ✓"
    echo "    Odoo:  https://odoo.iil.pet/web"
    echo "    aifw:  internal http://aifw_service:8001/health"
    exit 0
  fi
done

echo "" >&2
echo "ERROR: Stack not healthy after 120s" >&2
echo "  Odoo last status:         ${ODOO_STATUS}" >&2
echo "  aifw_service last status: ${AIFW_STATUS}" >&2
echo "  Debug: ssh ${SERVER} 'docker logs aifw_service --tail 30'" >&2
exit 1
