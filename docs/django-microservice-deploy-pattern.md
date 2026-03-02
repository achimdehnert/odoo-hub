# Django Microservice Deploy Pattern

Lessons learned from the `aifw_service` integration in `odoo-hub`.
Applicable to all repos on the 88.198.191.108 / 46.225.127.211 stack.

---

## Problem-Katalog (Root Causes)

| # | Problem | Root Cause | Fix |
|---|---------|-----------|-----|
| 1 | PyPI-Paket nicht verfügbar | `requirements.txt` pinnte unveröffentlichte Version | Source-COPY im Dockerfile statt PyPI |
| 2 | `DisallowedHost` HTTP 400 | Docker-Containername mit Unterstrich verletzt RFC 1034 — Django middleware ruft `request.get_host()` auf | `ALLOWED_HOSTS=["*"]` + `MIDDLEWARE=[]` für interne JSON-APIs |
| 3 | Restart-Loop im Container | `set -e` + Management-Command-Fehler = sofortiger Exit + Docker restart-policy = Endlosschleife | Non-fatal Befehle mit `\|\| echo WARN` statt `set -e` |
| 4 | `init_odoo_schema` nicht gefunden | App-Label nicht in `INSTALLED_APPS` → Django findet Management Commands nicht | Eigene App in `INSTALLED_APPS` eintragen |
| 5 | `password auth failed` beim ersten Start | PostgreSQL-Init-Scripts laufen nur bei leerem Volume — Volume existierte bereits | `02_aifw_db.sh` in jedem Deploy manuell ausführen (idempotent) |
| 6 | Build-Cache-Problem | `docker compose build` ohne `--no-cache` trotz geänderter Settings | Source-Hash-Vergleich im Deploy-Script → automatisch `--no-cache` |
| 7 | Kein Internet im Container | Service nur im `internal: true`-Netz | Zusätzlich in `proxy`-Netz (kein `internal: true`) für LLM-API-Calls |
| 8 | Race-Condition beim Start | Container startet bevor PostgreSQL bereit ist | `pg_isready`-Wait-Loop im Entrypoint |

---

## Pattern: Dockerfile für intern-gehostete Python-Deps

Wenn eine Abhängigkeit nicht auf PyPI ist, direkt aus dem Repo bauen:

```dockerfile
# Build context: repo root (nicht services/myservice/)
# In docker-compose.yml:
#   build:
#     context: .
#     dockerfile: services/myservice/Dockerfile

# Layer 1: Selten ändernde Deps (max. Cache-Nutzung)
COPY services/myservice/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Layer 2: Lokale Bibliothek (ändert sich gelegentlich)
COPY mylib/pyproject.toml /tmp/mylib/pyproject.toml
COPY mylib/README.md      /tmp/mylib/README.md
COPY mylib/src/           /tmp/mylib/src/
RUN pip install --no-cache-dir /tmp/mylib && rm -rf /tmp/mylib

# Layer 3: App-Code (ändert sich am häufigsten)
COPY services/myservice/ .
```

**Wichtig:** Build-Context = Repo-Root, damit alle Quellen zugänglich sind.

---

## Pattern: Django-Settings für interne Docker-Services

```python
# IMMER für interne Docker-Services (nicht Traefik-exposed):
ALLOWED_HOSTS = ["*"]  # Containername mit _ verletzt RFC 1034

# IMMER für interne JSON-APIs ohne Browser-Clients:
MIDDLEWARE = []  # SecurityMiddleware + CommonMiddleware rufen get_host() auf
                 # → DisallowedHost für 'my_service:8001' auch mit ALLOWED_HOSTS=["*"]

# IMMER:
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# LiteLLM-Spam unterdrücken:
LOGGING = {
    "loggers": {
        "LiteLLM": {"level": "WARNING"},
    }
}
```

---

## Pattern: Entrypoint-Script ohne Restart-Loops

```bash
#!/bin/bash
set -euo pipefail

# 1. DB-Wait-Loop (verhindert Race Condition)
for i in $(seq 1 30); do
    if pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -q 2>/dev/null; then
        break
    fi
    [ "$i" -eq 30 ] && echo "ERROR: DB not ready" && exit 1
    sleep 2
done

# 2. FATAL steps (mit set -e — Fehler = Container-Stop, kein Restart-Loop)
python manage.py migrate --noinput

# 3. NON-FATAL steps (|| verhindert Exit trotz set -e)
python manage.py seed_config || echo "WARN: seed_config failed — retry: docker exec <container> python manage.py seed_config"
```

**Regel:** Alles was beim ersten Start fehlen *kann* (Tabellen noch nicht da, externe Deps
fehlen) → non-fatal mit `|| echo WARN`. Nur `migrate` ist fatal.

---

## Pattern: Idempotentes DB-Init-Script

PostgreSQL-Init-Scripts in `docker-entrypoint-initdb.d/` laufen **nur beim leeren Volume**.
Bei bestehenden Volumes (nach Rebuild, Passwortänderung etc.) muss das Script manuell ausführbar sein:

```bash
#!/bin/bash
# Kein set -e — Einzelfehler sollen nicht alles abbrechen
POSTGRES_USER="${POSTGRES_USER:-postgres}"
MY_USER="${MY_DB_USER:-myapp}"
MY_PASS="${MY_DB_PASSWORD:-changeme}"
MY_DB="${MY_DB_NAME:-myapp}"

# User anlegen oder Passwort aktualisieren
if ! psql -U "$POSTGRES_USER" -tAc "SELECT 1 FROM pg_roles WHERE rolname='${MY_USER}'" | grep -q 1; then
    psql -U "$POSTGRES_USER" -c "CREATE USER ${MY_USER} PASSWORD '${MY_PASS}';"
else
    psql -U "$POSTGRES_USER" -c "ALTER USER ${MY_USER} PASSWORD '${MY_PASS}';"
fi

# DB anlegen falls nicht vorhanden
if ! psql -U "$POSTGRES_USER" -lqt | cut -d'|' -f1 | grep -qw "${MY_DB}"; then
    createdb -U "$POSTGRES_USER" -O "${MY_USER}" "${MY_DB}"
fi

psql -U "$POSTGRES_USER" -c "GRANT ALL PRIVILEGES ON DATABASE ${MY_DB} TO ${MY_USER};"
```

**Deploy-Script muss dieses Script in jedem Deploy manuell ausführen:**
```bash
ssh $SERVER "docker exec db bash /docker-entrypoint-initdb.d/02_myapp_db.sh"
```

---

## Pattern: Deploy-Script mit Auto-Rebuild-Detection

```bash
# Hash der Quelldateien vor und nach rsync vergleichen
HASH_LOCAL=$(find mylib/src mylib/pyproject.toml -type f -exec md5sum {} \; | sort | md5sum | cut -d' ' -f1)
HASH_REMOTE=$(ssh $SERVER "find /opt/repo/mylib/src -type f -exec md5sum {} \; | sort | md5sum | cut -d' ' -f1")

if [ "$HASH_LOCAL" != "$HASH_REMOTE" ]; then
    # Source hat sich geändert → --no-cache Build erzwingen
    ssh $SERVER "docker compose build --no-cache myservice"
fi
```

Dies verhindert, dass gecachte Docker-Layers veralteten Code enthalten.

---

## Checkliste: Neuen Django-Microservice aufsetzen

- [ ] `Dockerfile`: Build-Context = Repo-Root, Layer-Reihenfolge: deps → libs → app
- [ ] `Dockerfile`: `postgresql-client` installieren (für `pg_isready` im Entrypoint)
- [ ] `settings.py`: `ALLOWED_HOSTS=["*"]`, `MIDDLEWARE=[]`, `USE_TZ=True`
- [ ] `settings.py`: Eigene App in `INSTALLED_APPS` (für Management Commands)
- [ ] `entrypoint.sh`: DB-Wait-Loop, fatale und non-fatale Schritte trennen
- [ ] `docker-compose.yml`: `internal`-Netz für DB-Zugriff + `proxy`-Netz wenn externe API-Calls nötig
- [ ] DB-Init-Script: idempotent (User anlegen **oder** Passwort setzen)
- [ ] Deploy-Script: DB-Init in jedem Deploy ausführen (Step: "Ensure DB + users")
- [ ] Deploy-Script: Source-Hash-Vergleich für Auto-Rebuild
- [ ] `.gitignore`: `*.whl`, `dist/`, `*.egg-info/`
- [ ] `.dockerignore`: `__pycache__`, `*.pyc`, `*.whl`, `.env*`
- [ ] Container-Name: **keinen Unterstrich** verwenden (RFC 1034) — oder obige Django-Settings anwenden

---

## Anwendbarkeit auf andere Repos

Alle Repos auf dem Stack (`risk_hub`, `weltenhub`, `travel_beat`, etc.) die Django nutzen
und ähnliche Microservice-Muster einsetzen, können diese Patterns direkt übernehmen.

**Priorität für Übernahme:**
- Repos mit eigenem `entrypoint.sh` ohne DB-Wait-Loop → **restart-loop-gefährdet**
- Repos mit Init-Scripts die nur bei leerem Volume laufen → **deploy-nach-rebuild bricht**
- Repos die lokale Libs bauen → Dockerfile-Layer-Pattern + Hash-basierter Auto-Rebuild
