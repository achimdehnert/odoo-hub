#!/bin/bash
# _update-secrets.sh — Fügt aifw-Keys zu secrets.enc.env hinzu (ADR-045)
# Intern — wird von update-secrets-wrapper aufgerufen via sops exec-env
# Nicht direkt ausführen.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENCRYPTED_FILE="${REPO_ROOT}/secrets.enc.env"
AIFW_SECRET_KEY="d916314b35edd3ba202a21f5e9828728bcd23dd1c853c9759dd915b6c2758120"

# Baue neuen Plaintext aus bestehenden + neuen Keys
NEW_CONTENT="POSTGRES_USER=${POSTGRES_USER:-odoo}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=${POSTGRES_DB:-odoo}
ODOO_ADMIN_PASSWD=${ODOO_ADMIN_PASSWD}
ODOO_DOMAIN=${ODOO_DOMAIN}
ACME_EMAIL=${ACME_EMAIL}
SCHUTZTAT_DJANGO_API_KEY=${SCHUTZTAT_DJANGO_API_KEY:-}
DEPLOYMENT_MCP_ODOO=${DEPLOYMENT_MCP_ODOO:-}
NL2SQL_USER_PASSWORD=${NL2SQL_USER_PASSWORD:-}
AIFW_SECRET_KEY=${AIFW_SECRET_KEY}
AIFW_DB_PASSWORD=${NL2SQL_USER_PASSWORD:-ODO2026odo.}
ODOO_NL2SQL_PASSWORD=${NL2SQL_USER_PASSWORD:-ODO2026odo.}
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
OPENAI_API_KEY=${OPENAI_API_KEY:-}
"

# Neu verschlüsseln (überschreibt secrets.enc.env)
echo "${NEW_CONTENT}" | sops \
    --encrypt \
    --input-type dotenv \
    --output-type dotenv \
    --filename-override secrets.enc.env \
    /dev/stdin > "${ENCRYPTED_FILE}"

echo "OK: secrets.enc.env aktualisiert mit aifw-Keys"
echo "Enthaltene Keys:"
grep -E "^[A-Z_]+=" "${ENCRYPTED_FILE}" | cut -d= -f1 | sed 's/^/  - /'
