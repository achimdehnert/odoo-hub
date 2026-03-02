#!/bin/bash
# docker/db/02_aifw_db.sh
# Erstellt die aifw-Datenbank und setzt Passwörter für aifw + nl2sql_user.
#
# Ausführung:
#   A) Automatisch: PostgreSQL-Entrypoint führt dieses Script beim ersten
#      Start aus (wenn Volume leer). Env-Vars kommen aus docker-compose.
#   B) Manuell (z.B. nach Passwortänderung oder neuem Volume):
#      docker exec odoo_db bash /docker-entrypoint-initdb.d/02_aifw_db.sh
#
# Idempotent: mehrfaches Ausführen ist sicher.
# Kein set -e: Einzelfehler sollen nicht das gesamte Script abbrechen.

POSTGRES_USER="${POSTGRES_USER:-odoo}"
AIFW_DB="${AIFW_DB_NAME:-aifw}"
AIFW_USER="${AIFW_DB_USER:-aifw}"
AIFW_PASS="${AIFW_DB_PASSWORD:-changeme_set_via_env_aifw}"
NL2SQL_PASS="${ODOO_NL2SQL_PASSWORD:-changeme_nl2sql}"

echo "[02_aifw_db.sh] === Start ==="

# ── 1. aifw User anlegen falls nicht vorhanden ───────────────────────────────
if ! psql -U "$POSTGRES_USER" -tAc "SELECT 1 FROM pg_roles WHERE rolname='${AIFW_USER}'" | grep -q 1; then
    echo "[02_aifw_db.sh] Erstelle User '${AIFW_USER}'..."
    psql -U "$POSTGRES_USER" -c "CREATE USER ${AIFW_USER} PASSWORD '${AIFW_PASS}';"
else
    echo "[02_aifw_db.sh] User '${AIFW_USER}' existiert bereits — setze Passwort."
    psql -U "$POSTGRES_USER" -c "ALTER USER ${AIFW_USER} PASSWORD '${AIFW_PASS}';"
fi

# ── 2. aifw Datenbank anlegen falls nicht vorhanden ──────────────────────────
# CREATE DATABASE muss außerhalb einer Transaktion laufen.
if ! psql -U "$POSTGRES_USER" -lqt | cut -d '|' -f 1 | grep -qw "${AIFW_DB}"; then
    echo "[02_aifw_db.sh] Erstelle DB '${AIFW_DB}'..."
    createdb -U "$POSTGRES_USER" -O "${AIFW_USER}" "${AIFW_DB}"
    echo "[02_aifw_db.sh] DB '${AIFW_DB}' angelegt."
else
    echo "[02_aifw_db.sh] DB '${AIFW_DB}' existiert bereits — übersprungen."
fi

# ── 3. Rechte sicherstellen ───────────────────────────────────────────────────
psql -U "$POSTGRES_USER" \
    -c "GRANT ALL PRIVILEGES ON DATABASE ${AIFW_DB} TO ${AIFW_USER};"
echo "[02_aifw_db.sh] Rechte auf DB '${AIFW_DB}' für User '${AIFW_USER}' gesetzt."

# ── 4. nl2sql_user Passwort setzen (idempotent) ───────────────────────────────
if psql -U "$POSTGRES_USER" -tAc "SELECT 1 FROM pg_roles WHERE rolname='nl2sql_user'" | grep -q 1; then
    psql -U "$POSTGRES_USER" -c "ALTER USER nl2sql_user PASSWORD '${NL2SQL_PASS}';"
    echo "[02_aifw_db.sh] Passwort für nl2sql_user gesetzt."
else
    echo "[02_aifw_db.sh] nl2sql_user nicht gefunden — wird von 01_init.sql angelegt."
fi

echo "[02_aifw_db.sh] === Fertig ==="
