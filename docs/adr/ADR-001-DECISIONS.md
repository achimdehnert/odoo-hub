# ADR-001 Entscheidungsanalyse — drei offene Fragen

| Feld | Wert |
|------|------|
| **Datum** | 2026-03-02 |
| **Basis** | ADR-001-REVIEW.md + aifw v0.5.0 Wheel-Analyse + Hetzner odoo-prod CPX32 |
| **Status** | Entscheidung ausstehend (3 Fragen) |

---

## Frage 1 — Manifest-Diskrepanz: Welche `__manifest__.py` ist die finale?

### Ist-Zustand: zwei divergierende Dateien

```
docs/adr/input/__manifest__.py          ← "äußere" Version (ADR-Planungsartefakt)
docs/adr/input/mfg_nl2sql/__manifest__.py ← "innere" Version (Modul-eigene)
```

| Attribut | `docs/adr/input/__manifest__.py` | `mfg_nl2sql/__manifest__.py` |
|----------|----------------------------------|------------------------------|
| `depends` | `base, web, mail, **scm_manufacturing**` | `base, web, mail` |
| `data/` | `schema_metadata.xml` + **`schema_scm_manufacturing.xml`** + `demo_data.xml` | `schema_metadata.xml` + `demo_data.xml` |
| Alle anderen Felder | identisch | identisch |

### Analyse der Konsequenzen

**Variante A — `scm_manufacturing`-Dependency (äußere Version):**
- `mfg_nl2sql` kann NL2SQL-Queries gegen die Custom-Tabellen `scm_part`, `scm_bom`,
  `scm_production_order`, `scm_work_step` etc. stellen
- `schema_scm_manufacturing.xml` (44 KB, vorhanden in `docs/adr/input/`) enthält
  spezifische Tabellen/Spalten-Metadaten für `scm_manufacturing`
- **Problem:** `mfg_nl2sql` hängt zwingend von `scm_manufacturing` ab → nicht auf
  anderen Odoo-Instanzen installierbar ohne SCM-Modul
- **Problem:** Die Demo-Tiles in `demo_data.xml` fragen `purchase_order`, `mrp_production`,
  `quality_check` ab — das sind **Standard-Odoo-Tabellen** (nicht `scm_*`),
  die `mrp`, `purchase`, `quality` als Odoo-Module erfordern, **nicht** `scm_manufacturing`

**Variante B — ohne `scm_manufacturing`-Dependency (innere Version, im Modul):**
- `mfg_nl2sql` ist eigenständig installierbar auf jeder Odoo 18-Instanz
- Schema-Metadaten in `schema_metadata.xml` (24 KB) decken Standard-Odoo-Tabellen ab:
  `purchase_order`, `stock_quant`, `mrp_production`, `quality_check` etc.
- Demo-Tiles passen zu diesen Standard-Tabellen → konsistent
- `scm_manufacturing`-Schema kann **optional nachinstalliert** werden via separates
  `data/schema_scm_manufacturing.xml` das Nutzer manuell importieren

### **Empfehlung: Variante B (innere Version) ist die finale `__manifest__.py`**

**Begründung:**
1. **Entkopplung** — `mfg_nl2sql` als generisches NL2SQL-Dashboard für Odoo 18,
   nicht spezifisch an `scm_manufacturing` gekoppelt
2. **Konsistenz** — Demo-Tiles matchen `schema_metadata.xml` (Standard-Tabellen)
3. **Erweiterbarkeit** — `scm_manufacturing`-Schema als optionales Data-File nachrüstbar
4. **Die äußere Version** (`docs/adr/input/__manifest__.py`) ist ein Planungsartefakt
   aus der ADR-Phase und soll gelöscht/archiviert werden

**Sofortmaßnahme:**
```bash
# Die innere Version (mfg_nl2sql/) ist korrekt — keine Änderung nötig
# Die äußere Version archivieren:
mv docs/adr/input/__manifest__.py docs/adr/input/__manifest__.example_with_scm.py
mv docs/adr/input/__init__.py     docs/adr/input/__init__.example.py
mv docs/adr/input/module_init.py  docs/adr/input/module_init.example.py
```

**Optionales Schema für scm_manufacturing** (in `mfg_nl2sql/__manifest__.py` kommentiert):
```python
'data': [
    'security/security.xml',
    'security/ir.model.access.csv',
    'data/schema_metadata.xml',           # Standard-Odoo-Schema (immer)
    # Optional: nur wenn scm_manufacturing installiert ist
    # 'data/schema_scm_manufacturing.xml',
    'data/demo_data.xml',
],
```

---

## Frage 2 — `aifw.nl2sql` in `iil-aifw` integrieren?

### Ist-Zustand: aifw v0.5.0

**Repository:** `/home/dehnert/github/aifw/`
**PyPI-Package:** `iil-aifw==0.5.0` (`.whl` gebaut: `dist/iil_aifw-0.5.0-py3-none-any.whl`)

**Tatsächlicher Code-Stand (aus Wheel analysiert):**
```
aifw/
├── __init__.py          # Public API: completion, sync_completion, LLMResult, ...
├── apps.py              # AifwConfig (signal wiring in ready())
├── admin.py             # 4 ModelAdmins
├── models.py            # LLMProvider, LLMModel, AIActionType, AIUsageLog
├── schema.py            # LLMResult, RenderedPromptProtocol, ToolCall
├── service.py           # completion(), streaming, fallback, config cache
├── signals.py           # Cache-Invalidierung bei Model-Änderungen
└── management/
    └── commands/
        └── init_aifw_config.py
```

**Kritische Ergänzung gegenüber ADR-001:**
- `src/aifw/` im Repo ist **leer** — Code nur im `.whl` und vermutlich als Submodule/extern
- `pyproject.toml` zeigt Version `0.5.0` — bereits auf dem Stand den der ADR als Ziel hatte
- `sync_completion_with_fallback()` existiert bereits in v0.5.0 → kein asyncio-Problem für
  synchrone Django-Views
- **`aifw.nl2sql`-Subpackage existiert NICHT** im v0.5.0-Wheel — ADR-Planung noch offen

### Analyse: Soll `aifw.nl2sql` in `iil-aifw` integriert werden?

#### Option A: `aifw.nl2sql` als Subpackage in `iil-aifw` (ADR-Plan)

**Pro:**
- Zentrales LLM-Routing via `AIActionType(code="nl2sql")` → DB-gesteuert ✅
- `AIUsageLog` mit `tenant_id`, `object_id`, `metadata` → Audit-Trail ✅
- `completion_with_fallback()` bereits vorhanden → Claude → GPT-4o Fallback ✅
- `sync_completion()` / `sync_completion_with_fallback()` → gevent-kompatibel ✅
  (kein `asyncio.run()` nötig, ADR-Kritikpunkt C2 damit **gelöst**)
- Budget-Tracking via `AIActionType.budget_per_day` ✅
- Dependencies minimal: nur `psycopg2-binary`, `pandas` als optionales Extra

**Con:**
- `aifw.nl2sql` würde Django-`connections` nutzen → **nicht in Odoo verwendbar**
  (das ist aber korrekt — `aifw.nl2sql` gehört in Django-Apps, nicht Odoo)
- `src/aifw/` ist aktuell leer → Repo-Struktur muss geklärt werden
- `SchemaSource`-Model (Migration 0004) muss noch implementiert werden

#### Option B: Eigenständiges `nl2sql`-Paket (verworfen im ADR)

**Verworfen** — dupliziert LLM-Infrastruktur die in `aifw` schon existiert.

#### Option C: `mfg_nl2sql` bleibt Standalone (aktueller Stand)

**Pro:** Funktioniert in Odoo ohne Django-Abhängigkeit
**Con:** Kein DB-gesteuertes Model-Routing, kein Budget-Tracking, kein Audit-Log,
        hartcodierter API-Key statt `AIActionType`-Konfiguration

### **Empfehlung: JA — `aifw.nl2sql` in `iil-aifw` integrieren, aber mit klarer Scope-Trennung**

**Entscheidung:**

```
iil-aifw (Django)
└── aifw/
    └── nl2sql/              ← NEU in v0.6.0
        ├── __init__.py      # NL2SQLEngine Facade
        ├── registry.py      # SchemaRegistry + SchemaSource Model
        ├── generator.py     # SQLGenerator → aifw.sync_completion()
        ├── validator.py     # SQLValidator (read-only, Blocklist)
        ├── executor.py      # SQLExecutor (read-only Cursor, Timeout)
        └── formatter.py     # ResultFormatter → ChartRecommendation

Consumer A: Django HTMX Apps (bfagent, travel-beat, weltenhub)
  → from aifw.nl2sql import NL2SQLEngine
  → engine.ask("Frage")  # sync, kein asyncio.run()

Consumer B: Odoo mfg_nl2sql
  → KEINE direkte aifw-Dependency
  → Eigenständiger Odoo-Controller (aktueller Prototyp ist korrekt)
  → LLM-Call via direktem HTTP (requests) gegen Anthropic/OpenAI API
  → Optional: aifw läuft als separater Django-Microservice, Odoo ruft dessen
              REST-Endpoint auf (Entkopplung statt Package-Import)
```

**Warum Odoo NICHT direkt `aifw.nl2sql` importiert:**
- Odoo ist kein Django — `django.db.connections` nicht verfügbar
- Mixing Django+Odoo ORM in einem Prozess ist nicht supportet
- `sync_completion()` würde zwar gevent-kompatibel funktionieren,
  aber `SchemaRegistry` braucht `SchemaSource.objects.filter()` → Django-DB-Call

**Konkreter nächster Schritt für `iil-aifw`:**

```toml
# pyproject.toml — v0.6.0 Ergänzung
[project.optional-dependencies]
nl2sql = [
    "psycopg2-binary>=2.9",
    "pandas>=2.0",
]
```

**Migration 0004 für `SchemaSource`:** Siehe `ADR-001-REVIEW.md` Abschnitt 4.3 —
vollständige Django-Migration ist dort bereits als Code-Output dokumentiert.

### Repo-Struktur-Problem: `src/aifw/` ist leer

```bash
# Prüfung:
ls -la /home/dehnert/github/aifw/src/aifw/
# → 0 items

# Code liegt nur im Wheel:
# dist/iil_aifw-0.5.0-py3-none-any.whl
```

**Das ist ein kritisches Repo-Problem.** Der Source-Code fehlt im Git-Repo — nur Tests
und `pyproject.toml` sind committed, der eigentliche Code fehlt (vermutlich `.gitignore`-
Fehler oder falsches Arbeitsverzeichnis).

**Sofortmaßnahme:**
```bash
# Code aus Wheel extrahieren und in src/ committen:
cd /home/dehnert/github/aifw
python3 -c "
import zipfile, os
zf = zipfile.ZipFile('dist/iil_aifw-0.5.0-py3-none-any.whl')
for name in zf.namelist():
    if name.startswith('aifw/') and not name.endswith('.dist-info/'):
        target = os.path.join('src', name)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, 'wb') as f:
            f.write(zf.read(name))
        print(f'Extracted: {target}')
"
git -C /home/dehnert/github/aifw add src/
git -C /home/dehnert/github/aifw status
```

---

## Frage 3 — Migration odoo-hub → odoo-prod (CPX32, 46.225.127.211)?

### Ist-Zustand

**odoo-prod Server (Hetzner CPX32):**
- 4 vCPU, 8 GB RAM, 160 GB Disk
- IP: `46.225.127.211` / `2a01:4f8:1c1c:9d12::/64`
- Kosten: €10.49/Monat
- Status: `AN` (läuft)

**odoo-hub (Dev-Server, aktuell auf bfagent-Server):**
- Konkurriert um Ressourcen mit `bfagent` (Python AI Agent Framework)
- `bfagent` ist produktionskritisch → Ressourcenkonflikt = Risiko

**odoo-prod** ist laut Name bereits für Odoo bestimmt — der Server existiert und läuft.

### Analyse: Migration sinnvoll?

#### Argumente FÜR Migration zu odoo-prod:

| Argument | Gewicht |
|----------|---------|
| CPX32 (4 vCPU, 8 GB) ist ausreichend für Odoo 18 Community | ✅ Hoch |
| Entlastet bfagent-Dev-Server (produktionskritisch) | ✅ Hoch |
| odoo-prod ist bereits dediziert für Odoo (Name, bestehend) | ✅ Hoch |
| Postgres 16 persistent auf eigenem Volume (`odoo_pgdata`) | ✅ Hoch |
| €10.49/Monat = kostengünstig für 4 vCPU | ✅ Mittel |

#### Risiken der Migration:

| Risiko | Mitigierung |
|--------|-------------|
| Datenverlust beim DB-Dump | `pg_dump` + Verifikation vor Migration |
| Downtime während Migration | Maintenance-Fenster, kurz (< 30 min) |
| DNS/IP-Änderungen | Nginx-Config anpassen, kein DNS-Cutover nötig wenn direkt-IP |
| Konfigurationsabweichungen | `docker-compose.prod.yml` ist versioniert |
| odoo-prod evtl. schon belegt | **Prüfen ob bereits etwas läuft!** |

### **Empfehlung: JA — Migration zu odoo-prod durchführen**

**Voraussetzung:** Prüfen ob odoo-prod bereits einen anderen Dienst hostet.

### Migrations-Playbook (vollständig, idempotent)

```bash
#!/usr/bin/env bash
# migrate_odoo_to_prod.sh
# Migriert odoo-hub von Dev-Server auf odoo-prod (46.225.127.211)
# Idempotent: mehrfaches Ausführen ist sicher (prüft Voraussetzungen)
# Voraussetzungen: ssh-Zugang zu odoo-prod, Docker auf odoo-prod installiert
set -euo pipefail

PROD_HOST="46.225.127.211"
PROD_USER="root"
DB_NAME="${POSTGRES_DB:-odoo}"
DB_USER="${POSTGRES_USER:-odoo}"
BACKUP_FILE="odoo_backup_$(date +%Y%m%d_%H%M%S).dump"
REPO_DIR="/home/dehnert/github/odoo-hub"

echo "=== odoo-hub → odoo-prod Migration ==="
echo "Ziel: ${PROD_USER}@${PROD_HOST}"
echo ""

# ── Schritt 1: Prüfe ob odoo-prod bereits belegt ───────────────────────────
echo "[1/7] Prüfe odoo-prod auf bestehende Container..."
ssh "${PROD_USER}@${PROD_HOST}" "docker ps --format '{{.Names}}'" || true

# ── Schritt 2: DB-Dump auf Dev-Server ──────────────────────────────────────
echo "[2/7] Erstelle PostgreSQL-Dump..."
docker exec odoo_db pg_dump \
    -U "${DB_USER}" \
    -Fc \
    --no-privileges \
    --no-owner \
    "${DB_NAME}" > "/tmp/${BACKUP_FILE}"

echo "  Dump-Größe: $(du -sh /tmp/${BACKUP_FILE} | cut -f1)"

# ── Schritt 3: Odoo-Daten-Volume sichern ───────────────────────────────────
echo "[3/7] Sichere Odoo-Filestore..."
docker run --rm \
    -v odoo_data:/source:ro \
    -v /tmp:/backup \
    alpine \
    tar czf "/backup/odoo_filestore_$(date +%Y%m%d_%H%M%S).tar.gz" -C /source .

# ── Schritt 4: Dateien auf odoo-prod übertragen ────────────────────────────
echo "[4/7] Übertrage Dateien auf odoo-prod..."
# Repo
ssh "${PROD_USER}@${PROD_HOST}" "mkdir -p /opt/odoo-hub"
rsync -avz --exclude='.git' "${REPO_DIR}/" \
    "${PROD_USER}@${PROD_HOST}:/opt/odoo-hub/"

# DB-Dump
scp "/tmp/${BACKUP_FILE}" \
    "${PROD_USER}@${PROD_HOST}:/tmp/${BACKUP_FILE}"

# Filestore
scp /tmp/odoo_filestore_*.tar.gz \
    "${PROD_USER}@${PROD_HOST}:/tmp/"

# ── Schritt 5: Auf odoo-prod: Docker starten ───────────────────────────────
echo "[5/7] Starte Dienste auf odoo-prod..."
ssh "${PROD_USER}@${PROD_HOST}" bash -s << 'REMOTE'
set -euo pipefail
cd /opt/odoo-hub

# .env.prod muss bereits vorhanden sein (Secrets nicht im Repo!)
if [ ! -f .env.prod ]; then
    echo "FEHLER: .env.prod fehlt auf odoo-prod! Bitte manuell anlegen."
    exit 1
fi

# Starte nur DB zuerst (für Restore)
docker compose -f docker-compose.prod.yml up -d db
echo "  Warte auf PostgreSQL..."
sleep 10

# DB-Restore (idempotent: Drop+Create vor Restore)
BACKUP_FILE=$(ls /tmp/odoo_backup_*.dump | sort | tail -1)
docker exec -i odoo_db psql -U odoo -c "
    SELECT pg_terminate_backend(pid)
    FROM pg_stat_activity
    WHERE datname = 'odoo' AND pid <> pg_backend_pid();
" postgres || true

docker exec -i odoo_db psql -U odoo -c "DROP DATABASE IF EXISTS odoo;" postgres
docker exec -i odoo_db psql -U odoo -c "CREATE DATABASE odoo OWNER odoo;" postgres
docker exec -i odoo_db pg_restore \
    -U odoo \
    -d odoo \
    --no-privileges \
    --no-owner \
    < "${BACKUP_FILE}"
echo "  DB-Restore abgeschlossen."

# Filestore wiederherstellen
FILESTORE=$(ls /tmp/odoo_filestore_*.tar.gz | sort | tail -1)
docker run --rm \
    -v odoo_hub_data:/target \
    -v /tmp:/backup \
    alpine \
    tar xzf "/backup/$(basename ${FILESTORE})" -C /target
echo "  Filestore wiederhergestellt."

# Alle Dienste starten
docker compose -f docker-compose.prod.yml up -d
echo "  Alle Dienste gestartet."
REMOTE

# ── Schritt 6: Health-Check ────────────────────────────────────────────────
echo "[6/7] Health-Check..."
sleep 15
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    "http://${PROD_HOST}:8069/web/health" || echo "000")

if [ "${HTTP_STATUS}" = "200" ]; then
    echo "  ✅ Odoo antwortet: HTTP ${HTTP_STATUS}"
else
    echo "  ⚠️  Odoo antwortet mit HTTP ${HTTP_STATUS} — Logs prüfen:"
    ssh "${PROD_USER}@${PROD_HOST}" \
        "docker logs odoo_web --tail=50"
    exit 1
fi

# ── Schritt 7: Aufräumen ───────────────────────────────────────────────────
echo "[7/7] Aufräumen..."
rm -f "/tmp/${BACKUP_FILE}" /tmp/odoo_filestore_*.tar.gz
echo ""
echo "=== Migration abgeschlossen ==="
echo "  Odoo-prod: http://${PROD_HOST}:8069"
echo "  Nächster Schritt: Nginx/Traefik für SSL konfigurieren"
echo "  Nächster Schritt: DNS odoo.iil.pet → ${PROD_HOST}"
```

### Ressourcenbewertung odoo-prod CPX32 für den kombinierten Stack

| Dienst | RAM | CPU | Disk |
|--------|-----|-----|------|
| Odoo 18 Web (1 Worker) | ~800 MB | 0.5 vCPU | — |
| PostgreSQL 16 | ~512 MB | 0.3 vCPU | ~5 GB |
| PgBouncer | ~50 MB | minimal | — |
| Traefik | ~50 MB | minimal | — |
| **Gesamt** | **~1.4 GB** | **~0.8 vCPU** | **~6 GB** |
| **Verfügbar** | **8 GB** | **4 vCPU** | **160 GB** |
| **Headroom** | **~6.6 GB frei** ✅ | **~3.2 vCPU frei** ✅ | **~154 GB frei** ✅ |

→ **CPX32 ist großzügig bemessen** — genug Reserve für `mfg_nl2sql` + zukünftige Module.
→ Wenn `aifw`-Django-App für NL2SQL als zusätzlicher Container: weitere ~300 MB RAM.

---

## Zusammenfassung: Drei Entscheidungen

| # | Frage | Empfehlung | Priorität |
|---|-------|-----------|-----------|
| **F1** | Welche `__manifest__.py` ist final? | **Innere (`mfg_nl2sql/`) — ohne `scm_manufacturing`-Dependency** | Sofort |
| **F2** | `aifw.nl2sql` in `iil-aifw` integrieren? | **Ja — als `aifw.nl2sql` Subpackage für Django-Apps. Odoo-Modul bleibt eigenständig.** | Sprint 1 |
| **F3** | Migration odoo-hub → odoo-prod? | **Ja — CPX32 hat ausreichend Reserven, entlastet bfagent-Dev-Server** | Diese Woche |

## Sofort-Aktionen (nächste 48h)

1. **aifw-Repo reparieren** — `src/aifw/` ist leer, Code aus Wheel extrahieren und committen
2. **`docs/adr/input/__manifest__.py`** archivieren (umbenennen zu `*.example.py`)
3. **odoo-prod prüfen** — `ssh root@46.225.127.211 "docker ps"` vor Migration
4. **`.env.prod` auf odoo-prod anlegen** — Secrets vorbereiten (POSTGRES_PASSWORD, etc.)
5. **Migrations-Playbook ausführen** — `migrate_odoo_to_prod.sh`
