# ADR-001 Review: aifw NL2SQL Extension + mfg_nl2sql Odoo-Modul

| Feld | Wert |
|------|------|
| **Review-Datum** | 2026-03-02 |
| **Reviewer** | Cascade (kritisches Architektur-Review) |
| **ADR-Status** | Proposed |
| **Ziel-Stack** | Django + HTMX + PostgreSQL 16 auf Hetzner VMs via Docker |
| **Scope** | ADR-001 (`aifw.nl2sql`), Prototyp `mfg_nl2sql`, Infrastruktur `docker-compose.prod.yml` |
| **Bewertung gesamt** | ⚠️ **Bedingt freigabefähig** — 7 kritische Befunde, 8 Empfehlungen |

---

## 0. Kontext & Prüfgrundlage

Geprüfte Dateien:
- `docs/adr/input/ADR-001-aifw-nl2sql-extension.md`
- `docs/adr/input/mfg_nl2sql/` (alle Unterverzeichnisse)
- `docs/adr/input/__manifest__.py` (erweiterte Variante)
- `docker-compose.prod.yml`
- `addons/scm_manufacturing/__manifest__.py`

Qualitätskriterien (Pflicht):
1. **DB-getrieben** — Konfiguration, Schema, Routing ausschließlich aus der Datenbank
2. **Konsequente Normalisierung** — keine redundanten Felder
3. **Separation of Concerns** — klare Schichttrennung
4. **Naming Conventions** — konsistente Namensgebung über alle Layer
5. **Minimaler Diff** — reviewbar, kein Over-Engineering
6. **Kein magisches Verhalten** — keine stillen Fallbacks
7. **Robustes Error Handling** — klare Exit Codes, kein swallow
8. **Idempotenz** — mehrfaches Ausführen darf nicht kaputt machen

---

## 1. Architekturkonformität

### 1.1 Stack-Mismatch: Odoo ≠ Django + HTMX

**Befund:**
Der ADR schreibt als Consumer-Stack „Django + HTMX + Postgres auf Hetzner VMs via Docker" vor.
Das Prototyp-Modul `mfg_nl2sql` ist jedoch ein **Odoo 18 OWL-Modul** — kein Django, kein HTMX.
Der Prototyp in `docs/adr/input/mfg_nl2sql/` nutzt Odoo-spezifische Primitiven:
- `odoo.http.Controller` statt Django Views/HTMX-Partials
- `ir.config_parameter` statt Django `settings` / DB-Tabelle
- OWL (Odoo Web Library) statt HTMX-Komponenten
- Odoo ORM statt Django ORM

Das `aifw`-Framework (v0.4.0) ist ein **Django**-Package (`from django.db import connections`).
Die Integration `mfg_nl2sql → aifw.nl2sql` im ADR-Abschnitt 5 (`asyncio.run(engine.ask(...))`) 
ruft Django-Code aus einem Odoo-Controller auf — das ist **architektonisch inkonsistent**.

**Risiko:** 🔴 KRITISCH
- `asyncio.run()` innerhalb eines synchronen Odoo-WSGI-Request-Handlers blockiert den Event Loop
- Django `connections[alias]` ist in einem Odoo-Prozess nicht verfügbar — führt zu `ImproperlyConfigured` zur Laufzeit
- `aifw.models.SchemaSource` setzt eine Django-DB-Verbindung voraus, die Odoo nicht bereitstellt

**Empfehlung:**
Klare Entscheidung treffen: **Entweder** `mfg_nl2sql` als reines Django+HTMX-Modul (ohne Odoo), **oder** `mfg_nl2sql` als Odoo-Modul ohne `aifw`-Django-Dependency.
Der aktuelle Prototyp (Odoo-Controller mit eigener HTTP-LLM-Integration, kein `aifw`) ist architektonisch die **sauberere Lösung** für den Odoo-Kontext.
`aifw.nl2sql` gehört in eine separate Django-App mit eigenen HTMX-Views.

---

### 1.2 Zwei divergierende `__manifest__.py`-Dateien

**Befund:**
Es existieren zwei verschiedene Manifest-Dateien für dasselbe Modul:

| Datei | `depends` | `data/schema_scm_manufacturing.xml` |
|-------|-----------|--------------------------------------|
| `docs/adr/input/__manifest__.py` | `base, web, mail, scm_manufacturing` | ✅ Referenziert |
| `docs/adr/input/mfg_nl2sql/__manifest__.py` | `base, web, mail` | ❌ Fehlt |

Die Module-interne Version (`mfg_nl2sql/__manifest__.py`) referenziert in `data/` nur `schema_metadata.xml`
(generisches Schema für Standard-Odoo-Tabellen), nicht das `scm_manufacturing`-spezifische Schema.
Das macht das Modul entkoppelt und damit eigenständig installierbar — **aber**: die Demo-Tiles in
`data/demo_data.xml` fragen `purchase_order`, `mrp_production`, `quality_check` ab — alles
Odoo-Enterprise/Community-Module, nicht `scm_manufacturing`. Das ist inkonsistent.

**Risiko:** 🟡 HOCH
- Beim Deployment des falschen Manifests installiert Odoo ohne `scm_manufacturing`-Dependency —
  `schema_scm_manufacturing.xml` fehlt → Modulinstallation schlägt fehl oder Schema-Metadaten
  zeigen die falschen Tabellen
- Kein Hinweis welche Version „die" Produktionsversion ist

**Empfehlung:**
Genau **eine** `__manifest__.py` im Modul-Root. Die Divergenz in `docs/adr/input/` ist
Planungsartefakt — entweder löschen oder klar als `__manifest__.example.py` markieren.
Dependency auf `scm_manufacturing` nur dann, wenn tatsächlich dessen Custom-Tabellen (`scm_*`)
im Schema stehen — Standard-Odoo-Tabellen (`mrp_*`, `purchase_*`) erfordern `mrp`, `purchase` etc.

---

### 1.3 Separation of Concerns: LLM-Call im HTTP-Controller

**Befund:**
`nl2sql_controller.py` enthält in einer einzigen Klasse `NL2SQLController`:
- LLM-Konfigurationslogik (`_get_llm_config`)
- System-Prompt-Building (`_build_system_prompt`)
- HTTP-Calls zu externen APIs (`_call_anthropic`, `_call_openai`)
- SQL-Sanitisierung (`sanitize_sql` als Modul-Funktion)
- SQL-Ausführung (`_execute_sql`)
- Chart-Typ-Erkennung (`detect_chart_type`)
- Chart.js-Config-Generierung (`build_chart_config`)
- Audit-Log-Schreibung (inline in `execute_query`)
- Dashboard-Tile-Management (in `get_dashboard_data`)

Das sind 8 verschiedene Verantwortlichkeiten in einer Klasse. Kein Service-Layer, keine Trennung.

**Risiko:** 🟡 HOCH
- Unit-Tests sind praktisch unmöglich ohne vollständige Odoo-Umgebung (kein mocking möglich)
- Änderungen an der LLM-API (Anthropic → OpenAI) erfordern Eingriff in Controller-Logik
- `sanitize_sql` als freie Modul-Funktion (kein `@staticmethod`, kein Klassen-Namespace) —
  importierbar von überall, aber nicht testbar ohne den gesamten Controller-Import-Kontext

**Empfehlung:**
Extraktion in eigenständige Python-Module:
```
mfg_nl2sql/
  services/
    llm_service.py     # LLM-Call + Prompt-Building
    sql_service.py     # sanitize + execute
    chart_service.py   # detect_chart_type + build_chart_config
  controllers/
    nl2sql_controller.py  # nur HTTP-Routing + Orchestrierung
```
Jeder Service ist einzeln testbar. Controller ist dann ~50 Zeilen reine Orchestrierung.

---

## 2. Invarianten

### 2.1 `result_data` / `result_columns` als JSON-Text-Felder (Denormalisierung)

**Befund:**
`nl2sql.query.history` speichert Abfrageergebnisse als:
```python
result_data = fields.Text(...)    # JSON-Array der Rows
result_columns = fields.Text(...) # JSON-Array der Column-Metadaten
chart_config = fields.Text(...)   # Chart.js Config als JSON
```
Das sind drei `Text`-Felder mit strukturierten JSON-Daten — **keine Normalisierung**.
PostgreSQL 16 hat natives `jsonb` — Odoo mappt `fields.Json` auf `jsonb`.

**Risiko:** 🟡 HOCH
- Keine DB-Ebene-Validierung des JSON-Formats — fehlerhafte JSON führt zu `json.loads()` Exceptions
  im Controller, die nur durch `or '[]'` / `or '{}'` Fallbacks (stille Fehler!) abgefangen werden
- `result_data` kann mehrere MB groß werden (bis 1000 Rows × viele Spalten) — `Text`-Feld
  ohne Längenbegrenzung, kein Truncation-Guard auf DB-Ebene
- Query auf History (`LIKE`, Suche) unmöglich auf JSON-Inhalten

**Empfehlung:**
```python
# Statt fields.Text für strukturierte Daten:
result_data    = fields.Json(string='Ergebnis', readonly=True)
result_columns = fields.Json(string='Spalten',  readonly=True)
chart_config   = fields.Json(string='Chart Config', readonly=True)
```
Odoo 16+ / Postgres 16: `fields.Json` → `jsonb` mit `@`-Operator-Support.
Zusätzlich: `result_row_count > 0` als Invariante vor `result_data`-Speicherung prüfen.

---

### 2.2 `nl2sql.query.history` — fehlende Invariante bei `state`-Transition

**Befund:**
Das Modell `nl2sql.query.history` hat 5 States: `draft → processing → success/error/timeout`.
Es gibt **keine `_sql_constraints`** und **keinen `@api.constrains`** für:
- `state='success'` erfordert `generated_sql IS NOT NULL` und `sanitized_sql IS NOT NULL`
- `state='error'` erfordert `error_message IS NOT NULL`
- `state='success'` erfordert `result_row_count >= 0`
- `result_data` und `result_columns` müssen konsistent sein (beide `NULL` oder beide gesetzt)

Im Controller wird `state='success'` gesetzt zusammen mit `result_data=json.dumps(...)` — aber
wenn `json.dumps()` scheitert, wird der History-Eintrag ohne `result_data` mit `state='success'`
gespeichert (kein Rollback in diesem Pfad).

**Risiko:** 🟠 MITTEL
- Daten-Inkonsistenz in der DB: `state='success'` ohne `result_data`
- `state='processing'` kann dauerhaft offen bleiben wenn der Prozess crasht (kein Timeout-Recovery)

**Empfehlung:**
```python
# In models/query_history.py:
_sql_constraints = [
    ('success_requires_sql',
     "CHECK(state != 'success' OR (generated_sql IS NOT NULL AND sanitized_sql IS NOT NULL))",
     'Erfolgreich abgeschlossene Abfragen müssen SQL enthalten.'),
    ('error_requires_message',
     "CHECK(state != 'error' OR error_message IS NOT NULL)",
     'Fehlerhafte Abfragen müssen eine Fehlermeldung enthalten.'),
    ('row_count_non_negative',
     "CHECK(result_row_count >= 0)",
     'Zeilenanzahl muss >= 0 sein.'),
]
```
Scheduled Action für `state='processing'`-Einträge älter als N Minuten → `state='timeout'` setzen.

---

### 2.3 `nl2sql.schema.table` — `domain`-Feld required, aber `display_name` computed ohne Store-Guard

**Befund:**
`SchemaTable._compute_display_name()` liest `domain_labels = dict(self._fields['domain'].selection)`.
Wenn ein Record mit `domain=False` (Pflichtfeld verletzt) in die DB gerät, produziert die Compute-
Methode `"[] tablename"` — kein Fehler, aber falscher Wert. Der `domain`-required-Constraint ist nur
auf ORM-Ebene, nicht in `_sql_constraints`.

**Risiko:** 🟢 NIEDRIG (aber Symptom mangelnder DB-Constraints)

**Empfehlung:**
```python
_sql_constraints = [
    ('unique_table_name', 'UNIQUE(name)', 'Table name must be unique.'),
    ('domain_required', 'CHECK(domain IS NOT NULL)', 'Domain ist Pflichtfeld.'),
]
```

---

## 3. Seiteneffekte

### 3.1 `_execute_sql` — `cr.rollback()` im Fehlerfall gefährlich

**Befund:**
```python
# nl2sql_controller.py, Zeile ~419
except Exception as exc:
    cr.rollback()  # ← KRITISCH
    return {'error': str(exc), ...}
```
In Odoo teilt sich der Controller-Request **einen** Cursor (`cr`) mit dem gesamten ORM-Framework.
Ein `cr.rollback()` nach einer fehlgeschlagenen SQL-Ausführung rollt **alle** im gleichen Request
vorgenommenen ORM-Writes zurück — inklusive anderer potentieller Writes die vor dem SQL-Call
stattgefunden haben.

Direkt nach dem Fehler-Return versucht `execute_query()` einen `nl2sql.query.history`-Create:
```python
request.env['nl2sql.query.history'].create({..., 'state': 'error', ...})
```
Dieser Write findet **nach** `cr.rollback()` statt — der History-Eintrag wird also committed,
aber alle vorherigen Writes dieses Requests sind verloren. Das Verhalten ist abhängig von der
Reihenfolge im Call-Stack und schwer reproduzierbar.

**Risiko:** 🔴 KRITISCH
- Datenverlust durch impliziten Rollback nicht-verwandter Writes
- Nicht reproduzierbar unter Last / Connection-Pooling

**Empfehlung:**
`SET LOCAL statement_timeout` und `LIMIT`-Wrapping **in einer eigenen Transaktion / Savepoint**:
```python
# Korrektur: Savepoint statt Rollback des Gesamt-Cursors
cr = request.env.cr
savepoint = f"nl2sql_{int(time.time() * 1000)}"
cr.execute(f"SAVEPOINT {savepoint}")
try:
    cr.execute(f"SET LOCAL statement_timeout = '{timeout_ms}'")
    cr.execute(f"SELECT * FROM ({sql}) AS _q LIMIT {max_rows}")
    # ... fetchall ...
    cr.execute(f"RELEASE SAVEPOINT {savepoint}")
except Exception as exc:
    cr.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
    return {'error': str(exc), ...}
```

---

### 3.2 `pgbouncer` — `SET LOCAL statement_timeout` inkompatibel mit Transaction Pooling

**Befund:**
Der ADR nennt `pgbouncer` als optionale Komponente. `_execute_sql()` nutzt:
```python
cr.execute(f"SET LOCAL statement_timeout = '{timeout_ms}'")
```
`SET LOCAL` ist **nur gültig innerhalb einer Transaktion** und wird bei pgbouncer im
**Transaction Pooling Mode** (`pool_mode=transaction`) nach dem Commit zurückgesetzt.
Im **Session Pooling Mode** ist `SET LOCAL` korrekt, aber Session Pooling ist nicht skalierbar.

**Risiko:** 🔴 KRITISCH (wenn pgbouncer mit Transaction Pooling)
- `statement_timeout` greift nicht → unkontrollierte SQL-Ausführungszeiten
- Full-Table-Scans ohne Timeout möglich

**Empfehlung:**
Entweder:
1. **pgbouncer Session Pooling** explizit dokumentieren (und kein Statement Pooling verwenden)
2. **Timeout auf Anwendungsebene** als Backup zusätzlich zu `SET LOCAL`:
   ```python
   # In _execute_sql():
   cr.execute("BEGIN")  # explizite Transaktion
   cr.execute(f"SET LOCAL statement_timeout = {timeout_ms}")
   # ... query ...
   cr.execute("COMMIT")
   ```
3. Alternativ: **Dedizierter Read-Only DB-User** mit `ALTER ROLE nl2sql_ro SET statement_timeout = '30s'`
   auf PostgreSQL-Ebene — dann ist pgbouncer-Mode irrelevant.

Die Empfehlung (3) ist die robusteste Lösung:
```sql
-- idempotentes Setup-Script (einmalig, als Migration):
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nl2sql_ro') THEN
        CREATE ROLE nl2sql_ro NOLOGIN;
    END IF;
END $$;
ALTER ROLE nl2sql_ro SET statement_timeout = '30s';
ALTER ROLE nl2sql_ro SET default_transaction_read_only = on;
```

---

### 3.3 Stille Fallbacks im Controller — verletzt Qualitätskriterium

**Befund:**
```python
# nl2sql_controller.py
columns = json.loads(history.result_columns or '[]')  # ← stiller Fallback
rows     = json.loads(history.result_data    or '[]')  # ← stiller Fallback
config   = json.loads(history.chart_config   or '{}')  # ← stiller Fallback
```
Wenn `result_columns` `None` ist (z.B. durch den unter 3.1 beschriebenen Rollback-Bug),
gibt der Endpoint `{"columns": [], "rows": [], ...}` zurück — **ohne Fehlerindikation**.
Das Frontend zeigt eine leere Tabelle, kein Error.

Weiterer stiller Fallback:
```python
'provider': ICP.get_param('mfg_nl2sql.llm_provider', 'anthropic'),  # default ohne Warnung
```
Wenn kein Provider konfiguriert ist, wird `anthropic` verwendet — ohne Log-Warnung.

**Risiko:** 🟡 HOCH
- Debugging produktiver Fehler extrem schwierig (Frontend zeigt kein Problem)
- API-Key-Check (`if not config['api_key']`) gibt Fehlermeldung zurück — aber Provider-Check fehlt

**Empfehlung:**
```python
# Kein stiller Fallback — explizites None-Handling:
if not history.result_columns:
    return {'error': 'Kein Ergebnis gespeichert (result_columns ist NULL)'}
columns = json.loads(history.result_columns)
rows    = json.loads(history.result_data)
```
Für Config-Parameter: `_get_llm_config()` soll alle Pflicht-Parameter validieren und
bei fehlendem API-Key **sofort** mit klarem Error zurückkehren (nicht erst bei API-Call).

---

### 3.4 `asyncio.run()` in Odoo WSGI-Kontext (ADR Abschnitt 5)

**Befund:**
ADR-Abschnitt 5 zeigt die geplante Integration:
```python
result = asyncio.run(engine.ask(question, user=request.env.user))
```
Odoo nutzt `gevent`-basiertes WSGI (Gunicorn + gevent workers in Production).
`asyncio.run()` in einem `gevent`-Patch-Kontext führt zu **Event-Loop-Konflikt**:
- gevent patcht `socket`, `threading`, `select` — asyncio nutzt denselben Loop
- `asyncio.run()` erstellt einen neuen Event-Loop, der mit dem gevent-Loop kollidiert
- Ergebnis: Deadlocks, hängende Workers, unerklärliche Timeouts

**Risiko:** 🔴 KRITISCH (für die ADR-geplante aifw-Integration)

**Empfehlung:**
Wenn `aifw.nl2sql` in Odoo genutzt werden soll: **kein `asyncio.run()`**.
Synchron-Variante verwenden:
```python
# In aifw: sync_completion() statt completion()
result = engine.ask_sync(question, user=request.env.user)
```
Oder: `aifw.nl2sql` nur in Django-HTMX-App nutzen, Odoo-Modul bleibt eigenständig mit
synchronem `requests`-Call (wie im aktuellen Prototyp).

---

## 4. Migrationsrisiken

### 4.1 `docker-compose.prod.yml` — fehlende Härtung für Produktionsbetrieb

**Befund:**
```yaml
# docker-compose.prod.yml (aktuell)
services:
  db:
    image: postgres:16-alpine
    env_file: .env.prod          # POSTGRES_PASSWORD im Klartext in .env.prod?
    volumes:
      - odoo_pgdata:/var/lib/postgresql/data
    # Kein: max_connections, shared_buffers, work_mem
    # Kein: log_statement, log_min_duration_statement
    # Kein: Netzwerk-Isolation (kein networks:-Block)
    # Kein: pgbouncer-Service (obwohl ADR optional erwähnt)
```

Weitere Befunde:
- **Kein `networks:`-Block** — alle Services im Default-Bridge-Network, nicht isoliert
- **Kein `mem_limit`/`cpus`** — NL2SQL-Queries können DB-Prozess bei CPU/RAM erschöpfen
- **Kein `pg_isready`-Healthcheck mit Datenbankname** — `pg_isready -U odoo` prüft nicht ob
  die gewünschte DB existiert, nur ob Postgres antwortet
- **Kein Backup-Volume oder Backup-Service** definiert
- **Odoo-Container hat Port `8069` direkt exponiert** — sollte hinter Nginx/Traefik liegen

**Risiko:** 🟡 HOCH (Production-Readiness)

**Empfehlung** — vollständiges, idempotentes `docker-compose.prod.yml`:

```yaml
# docker-compose.prod.yml
# Produktions-Compose für odoo-hub (Hetzner VM)
# Anforderungen: Docker >= 25, Compose V2
# Idempotent: mehrfaches `docker compose up -d` ist sicher

services:

  # ── Traefik Reverse Proxy ──────────────────────────────────────────────
  traefik:
    image: traefik:v3.1
    container_name: odoo_traefik
    restart: unless-stopped
    command:
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.le.acme.tlschallenge=true"
      - "--certificatesresolvers.le.acme.email=${ACME_EMAIL}"
      - "--certificatesresolvers.le.acme.storage=/letsencrypt/acme.json"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - traefik_certs:/letsencrypt
    networks:
      - proxy
    labels:
      - "traefik.enable=true"

  # ── Odoo Web ──────────────────────────────────────────────────────────
  web:
    build:
      context: .
      dockerfile: docker/app/Dockerfile
    image: ghcr.io/achimdehnert/odoo-hub:${IMAGE_TAG:-latest}
    container_name: odoo_web
    restart: unless-stopped
    env_file: .env.prod
    # Kein direktes Port-Mapping — Traffic nur über Traefik
    expose:
      - "8069"
    volumes:
      - odoo_data:/var/lib/odoo
    depends_on:
      db:
        condition: service_healthy
      pgbouncer:
        condition: service_healthy
    command: ["odoo", "--config=/etc/odoo/odoo.conf"]
    networks:
      - internal
      - proxy
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.odoo.rule=Host(`${ODOO_DOMAIN}`)"
      - "traefik.http.routers.odoo.entrypoints=websecure"
      - "traefik.http.routers.odoo.tls.certresolver=le"
      - "traefik.http.services.odoo.loadbalancer.server.port=8069"
    # Ressourcen-Limits: NL2SQL-Queries dürfen nicht den ganzen Host erschöpfen
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 2G

  # ── PgBouncer Connection Pooler ───────────────────────────────────────
  pgbouncer:
    image: pgbouncer/pgbouncer:1.23
    container_name: odoo_pgbouncer
    restart: unless-stopped
    environment:
      # Session Pooling für Odoo (Transaction Pooling inkompatibel mit SET LOCAL)
      - PGBOUNCER_POOL_MODE=session
      - PGBOUNCER_MAX_CLIENT_CONN=100
      - PGBOUNCER_DEFAULT_POOL_SIZE=20
      - PGBOUNCER_DATABASE_HOST=db
      - PGBOUNCER_DATABASE_PORT=5432
      - PGBOUNCER_DATABASE_NAME=${POSTGRES_DB}
      - PGBOUNCER_DATABASE_USER=${POSTGRES_USER}
      - PGBOUNCER_DATABASE_PASSWORD=${POSTGRES_PASSWORD}
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -h localhost -p 5432 -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - internal

  # ── PostgreSQL 16 ─────────────────────────────────────────────────────
  db:
    image: postgres:16-alpine
    container_name: odoo_db
    restart: unless-stopped
    env_file: .env.prod
    volumes:
      - odoo_pgdata:/var/lib/postgresql/data
      # Init-Script: einmalig ausgeführt wenn DB leer (idempotent durch IF NOT EXISTS)
      - ./docker/db/init.sql:/docker-entrypoint-initdb.d/01_init.sql:ro
    # PostgreSQL-Performance-Tuning für 4GB RAM Hetzner VM
    command: >
      postgres
        -c max_connections=50
        -c shared_buffers=512MB
        -c work_mem=16MB
        -c maintenance_work_mem=128MB
        -c effective_cache_size=1536MB
        -c log_statement=ddl
        -c log_min_duration_statement=1000
        -c log_line_prefix='%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
    healthcheck:
      # Prüft Postgres UND ob die Datenbank existiert
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - internal
    deploy:
      resources:
        limits:
          cpus: "1.5"
          memory: 1G

volumes:
  odoo_data:
    name: odoo_hub_data          # expliziter Name für Backup-Scripts
  odoo_pgdata:
    name: odoo_hub_pgdata        # expliziter Name für Backup-Scripts
  traefik_certs:
    name: odoo_hub_traefik_certs

networks:
  internal:
    name: odoo_hub_internal      # DB + pgbouncer nicht von außen erreichbar
    internal: true               # kein Internet-Zugang für interne Services
  proxy:
    name: odoo_hub_proxy         # Traefik + Web
```

---

### 4.2 Fehlendes DB-Init-Script für NL2SQL Read-Only Role

**Befund:**
Der ADR beschreibt `SET LOCAL statement_timeout` und `SET TRANSACTION READ ONLY` als
Sicherheitsmechanismus. Es gibt jedoch kein idempotentes Init-Script, das:
- einen dedizierten Read-Only-Datenbankbenutzer für NL2SQL anlegt
- `statement_timeout` dauerhaft auf Rollen-Ebene konfiguriert
- die SQL-Whitelist (welche Tabellen darf `nl2sql_ro` lesen) per `GRANT` definiert

**Risiko:** 🟡 HOCH
- Ohne DB-seitige Read-Only-Rolle läuft NL2SQL-Execution als Odoo-Superuser → volle Schreibrechte
- `allow_write = False` im Odoo-Config-Parameter ist keine Sicherheitsgarantie (umgehbar durch
  direkte API-Calls ohne Sanitisierung)

**Empfehlung** — vollständiges, idempotentes Init-Script:

```sql
-- docker/db/init.sql
-- NL2SQL Read-Only Role Setup
-- Idempotent: mehrfaches Ausführen ist sicher (IF NOT EXISTS / DO $$ Blöcke)
-- Wird von PostgreSQL Docker-Image beim ersten Start ausgeführt

-- ── 1. Read-Only Rolle anlegen ──────────────────────────────────────────
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nl2sql_ro') THEN
        CREATE ROLE nl2sql_ro NOLOGIN;
        RAISE NOTICE 'Rolle nl2sql_ro angelegt';
    ELSE
        RAISE NOTICE 'Rolle nl2sql_ro existiert bereits — kein Eingriff';
    END IF;
END $$;

-- ── 2. Sicherheits-Defaults auf Rollen-Ebene ───────────────────────────
-- Verhindert unkontrollierte Langläufer unabhängig von pgbouncer-Mode
ALTER ROLE nl2sql_ro SET statement_timeout      = '30s';
ALTER ROLE nl2sql_ro SET lock_timeout           = '5s';
ALTER ROLE nl2sql_ro SET default_transaction_read_only = on;

-- ── 3. Login-User für NL2SQL-Execution ─────────────────────────────────
-- Passwort über Umgebungsvariable (nicht hardcoded)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nl2sql_user') THEN
        -- Passwort wird via ALTER USER nach dem Start gesetzt (siehe entrypoint.sh)
        CREATE USER nl2sql_user PASSWORD 'CHANGEME_VIA_ENTRYPOINT' IN ROLE nl2sql_ro;
        RAISE NOTICE 'User nl2sql_user angelegt';
    ELSE
        RAISE NOTICE 'User nl2sql_user existiert bereits — kein Eingriff';
    END IF;
END $$;

-- ── 4. Schema-Berechtigungen (nur lesend) ──────────────────────────────
-- GRANT auf die Tabellen, die NL2SQL abfragen darf (explizite Whitelist)
-- Muss nach Odoo-Modulinstallation erneut ausgeführt werden (neue Tabellen)
GRANT USAGE ON SCHEMA public TO nl2sql_ro;

-- Standard-Odoo-Tabellen (NL2SQL-Schema-Whitelist aus schema_metadata.xml)
GRANT SELECT ON TABLE
    purchase_order,
    purchase_order_line,
    stock_quant,
    stock_location,
    res_partner,
    product_product,
    product_template,
    mrp_production,
    mrp_workcenter,
    mrp_workorder,
    quality_check,
    quality_point,
    quality_alert
TO nl2sql_ro;

-- SCM-Custom-Tabellen (falls scm_manufacturing installiert)
-- GRANT SELECT ON TABLE
--     scm_part, scm_bom, scm_production_order, scm_work_step,
--     scm_purchase_order, scm_warehouse, scm_delivery
-- TO nl2sql_ro;
```

---

### 4.3 Fehlende Migration für `SchemaSource`-Model (ADR Abschnitt 4.1)

**Befund:**
ADR Abschnitt 8 (Rollout) plant `SchemaSource` als neues Django-Model mit Migration
`0002_schema_source.py`. Diese Migration existiert **nicht** im Repository.
Der `SchemaRegistry._parse_xml()` (ADR Abschnitt 4.2) parst Schema-XML aus
`SchemaSource.schema_xml` — aber die Migrations-Datei für das `aifw_schema_sources`-Table
fehlt komplett.

**Risiko:** 🟠 MITTEL
- Deployment schlägt fehl bei `python manage.py migrate` wenn `0002_schema_source.py` nicht existiert
- `SchemaRegistry.get_context()` läuft in `OperationalError: relation "aifw_schema_sources" does not exist`

**Empfehlung:**
Migration als vollständige Datei liefern (kein Platzhalter):

```python
# src/aifw/migrations/0002_schema_source.py
# Generiert: 2026-03-02
# Idempotent: Django-Migrations sind von Natur aus idempotent (RunSQL mit IF NOT EXISTS)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("aifw", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SchemaSource",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "code",
                    models.CharField(
                        max_length=100,
                        unique=True,
                        verbose_name="Code",
                        help_text="Eindeutiger Identifier (z.B. 'scm_manufacturing')",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        max_length=200,
                        verbose_name="Name",
                    ),
                ),
                (
                    "db_alias",
                    models.CharField(
                        max_length=100,
                        default="default",
                        verbose_name="DB Alias",
                        help_text="Django DB-Alias aus settings.DATABASES",
                    ),
                ),
                (
                    "schema_xml",
                    models.TextField(
                        blank=True,
                        verbose_name="Schema XML",
                        help_text="Schema-Metadaten als XML (DDL, Beschreibungen, Beispiel-Queries)",
                    ),
                ),
                (
                    "table_prefix",
                    models.CharField(
                        max_length=50,
                        blank=True,
                        verbose_name="Tabellen-Prefix",
                        help_text="Erlaubter Tabellen-Prefix (z.B. 'scm_')",
                    ),
                ),
                (
                    "max_rows",
                    models.IntegerField(
                        default=500,
                        verbose_name="Max Zeilen",
                    ),
                ),
                (
                    "timeout_seconds",
                    models.IntegerField(
                        default=30,
                        verbose_name="Query-Timeout (s)",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        verbose_name="Aktiv",
                    ),
                ),
            ],
            options={
                "app_label": "aifw",
                "db_table": "aifw_schema_sources",
                "verbose_name": "NL2SQL Schema Source",
                "verbose_name_plural": "NL2SQL Schema Sources",
                "ordering": ["code"],
            },
        ),
    ]
```

---

### 4.4 Naming Convention Inkonsistenz

**Befund:**
Über alle Layer hinweg werden verschiedene Naming-Stile gemischt:

| Layer | Gefundener Name | Problem |
|-------|----------------|---------|
| Odoo Model | `nl2sql.query.history` | ✅ Odoo-Konvention |
| Odoo Model | `nl2sql.save.query.wizard` | ✅ |
| Django Model | `SchemaSource` | ✅ Django-Konvention |
| DB Table | `aifw_schema_sources` | ✅ |
| Odoo `_name` | `nl2sql.schema.table` | ✅ |
| `_rec_name` | `display_name` | ⚠️ Schattiert Odoo-Base-Computed-Field |
| Config Param | `mfg_nl2sql.llm_provider` | ✅ |
| Config Param | `mfg_nl2sql.api_key` | ✅ |
| Modul-Name | `mfg_nl2sql` | ✅ |
| ADR-Package | `aifw.nl2sql` | ✅ |
| Controller-Route | `/mfg_nl2sql/query` | ✅ |
| Controller-Route | `/mfg_nl2sql/dashboard_data` | ⚠️ `data` nicht REST-konform, besser `/dashboard` |
| Security Group | `group_nl2sql_user` | ✅ |
| Security Group | `group_nl2sql_manager` | ✅ |

**Kritischer Befund:** `_rec_name = 'display_name'` in `SchemaTable` überschreibt das von
Odoo automatisch berechnete `display_name`-Feld (`name_get()`). Das kann zu Konflikten mit
Odoo-internen Mechanismen führen (Many2one-Dropdown-Anzeige, `name_search()`).

**Risiko:** 🟠 MITTEL

**Empfehlung:**
```python
# Statt _rec_name = 'display_name':
_rec_name = 'name'
# display_name als separates computed field mit anderem Namen:
label = fields.Char(
    string='Bezeichnung',
    compute='_compute_label',
    store=True,
)
```

---

## 5. Zusammenfassung

### Kritische Befunde (🔴 Blocker für Production)

| # | Befund | Datei | Zeile |
|---|--------|-------|-------|
| C1 | `cr.rollback()` im Exception-Handler rollt nicht-verwandte ORM-Writes zurück | `nl2sql_controller.py` | ~419 |
| C2 | `asyncio.run()` kollidiert mit gevent in Odoo Production (ADR Abschnitt 5) | ADR-001.md | §5 |
| C3 | `SET LOCAL statement_timeout` unwirksam mit pgbouncer Transaction Pooling | `nl2sql_controller.py` | ~369 |
| C4 | Stack-Mismatch: ADR schreibt Django+HTMX vor, Prototyp ist Odoo+OWL | alle | — |

### Hohe Befunde (🟡 Vor Deployment beheben)

| # | Befund | Datei |
|---|--------|-------|
| H1 | `result_data`/`result_columns`/`chart_config` als `Text` statt `fields.Json` | `query_history.py` |
| H2 | Stille Fallbacks (`or '[]'`, `or '{}'`) verbergen Datenfehler | `nl2sql_controller.py` |
| H3 | 8 Verantwortlichkeiten in `NL2SQLController` — kein Service Layer | `nl2sql_controller.py` |
| H4 | Zwei divergierende `__manifest__.py` — keine klare Produktionsversion | beide Manifeste |
| H5 | `docker-compose.prod.yml` fehlen: Netzwerk-Isolation, Ressourcen-Limits, Traefik | `docker-compose.prod.yml` |
| H6 | Kein DB-seitiger Read-Only-User für NL2SQL-Execution | fehlt komplett |

### Mittlere Befunde (🟠 In nächstem Sprint)

| # | Befund |
|---|--------|
| M1 | Fehlende `_sql_constraints` für `state`-Transitionen in `nl2sql.query.history` |
| M2 | `_rec_name = 'display_name'` überschreibt Odoo-Base-Field |
| M3 | Django-Migration `0002_schema_source.py` fehlt im Repository |

### Niedrige Befunde (🟢 Backlog)

| # | Befund |
|---|--------|
| L1 | `domain`-Pflichtfeld ohne DB-Constraint in `nl2sql.schema.table` |
| L2 | `/mfg_nl2sql/dashboard_data` Route nicht REST-konform |
| L3 | `state='processing'` ohne Timeout-Recovery (Scheduled Action fehlt) |

---

## 6. Freigabe-Entscheidung

> **⚠️ BEDINGT FREIGABEFÄHIG**
>
> Der **Odoo-Prototyp** (`mfg_nl2sql`) ist technisch funktionsfähig für eine Entwicklungsumgebung,
> aber **nicht production-ready** ohne Behebung der Kritischen Befunde C1 und C3.
>
> Der **ADR-Plan** (`aifw.nl2sql` Integration) ist in seiner aktuellen Form **nicht umsetzbar**
> wegen C2 (asyncio/gevent) und C4 (Stack-Mismatch). Der ADR muss vor Implementierungsbeginn
> überarbeitet werden mit einer klaren Entscheidung: Odoo-Modul ODER Django-App — nicht beides.
>
> **Empfohlene Vorgehensweise:**
> 1. Befunde C1, C3 im Prototyp beheben (Savepoints, DB-Role)
> 2. ADR-001 überarbeiten: `aifw.nl2sql` für Django-App, `mfg_nl2sql` als eigenständiges Odoo-Modul
> 3. `docker-compose.prod.yml` gemäß Abschnitt 4.1 ersetzen
> 4. `docker/db/init.sql` aus Abschnitt 4.2 hinzufügen
> 5. Django-Migration aus Abschnitt 4.3 committen
