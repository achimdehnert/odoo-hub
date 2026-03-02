#!/bin/bash
# docker/db/02_aifw_db.sh
# Erstellt die aifw-Datenbank + setzt Passwort via AIFW_DB_PASSWORD.
# Wird vom PostgreSQL-Entrypoint einmalig ausgeführt (nach 01_init.sql).
#
# Voraussetzung: User 'aifw' muss schon existieren (01_init.sql Abschnitt 6).

set -e

AIFW_DB="${AIFW_DB_NAME:-aifw}"
AIFW_USER="${AIFW_DB_USER:-aifw}"
AIFW_PASS="${AIFW_DB_PASSWORD:-changeme_set_via_env_aifw}"

echo "[02_aifw_db.sh] Prüfe ob DB '$AIFW_DB' existiert..."

# CREATE DATABASE muss außerhalb einer Transaktion laufen — psql direkt nutzen
if ! psql -U "$POSTGRES_USER" -lqt | cut -d \| -f 1 | grep -qw "$AIFW_DB"; then
    echo "[02_aifw_db.sh] Erstelle DB '$AIFW_DB'..."
    createdb -U "$POSTGRES_USER" -O "$AIFW_USER" "$AIFW_DB"
    echo "[02_aifw_db.sh] DB '$AIFW_DB' angelegt."
else
    echo "[02_aifw_db.sh] DB '$AIFW_DB' existiert bereits — übersprungen."
fi

# Passwort via env setzen (idempotent)
psql -U "$POSTGRES_USER" -c "ALTER USER ${AIFW_USER} PASSWORD '${AIFW_PASS}';"
echo "[02_aifw_db.sh] Passwort für User '$AIFW_USER' gesetzt."

# Rechte sicherstellen
psql -U "$POSTGRES_USER" -c "GRANT ALL PRIVILEGES ON DATABASE ${AIFW_DB} TO ${AIFW_USER};"
echo "[02_aifw_db.sh] Rechte auf DB '$AIFW_DB' für User '$AIFW_USER' gesetzt."

# nl2sql_user Passwort ebenfalls setzen
NL2SQL_PASS="${ODOO_NL2SQL_PASSWORD:-changeme_nl2sql}"
psql -U "$POSTGRES_USER" -c "ALTER USER nl2sql_user PASSWORD '${NL2SQL_PASS}';" 2>/dev/null || \
    echo "[02_aifw_db.sh] nl2sql_user nicht gefunden — übersprungen."

echo "[02_aifw_db.sh] Fertig."
