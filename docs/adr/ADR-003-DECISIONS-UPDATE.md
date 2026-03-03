# ADR-003: Entscheidungsupdate — Produktstrategie & Architektur

| Feld | Wert |
|------|------|
| **Datum** | 2026-03-03 |
| **Basis** | ADR-002-PRODUCT-STRATEGY.md (Entscheidungspunkte D1–D6) |
| **Status** | **ENTSCHIEDEN + ERWEITERT** — D7/D8/D9 ergänzt (ADR-005, 2026-03-03) |
| **Entscheidungsträger** | Achim Dehnert |
| **Reviewer** | Cascade |

---

## Bestätigte Entscheidungen

### D1 — Produktstrategie: Odoo + NL2SQL als Produkt ✅ BESTÄTIGT

**Entscheidung:** Option B — Odoo + `mfg_nl2sql` als vertikales Produkt mit proprietärem
KI-Layer. Nicht reiner Implementierungsdienstleister.

**Konsequenzen:**
- `mfg_nl2sql` + `casting_foundry` sind Product IP — kein Open-Source-Release ohne
  explizite Entscheidung
- Pricing-Modell (ADR-002 Abschnitt 5) wird umgesetzt: Odoo-Lizenz + NL2SQL Add-on Tier
- `aifw_service` wird als produktkritische Komponente behandelt (nicht optional)
- Alle 5 Sprints aus ADR-002 Abschnitt 3.2 sind autorisiert

**Abgeleitete Folge-Entscheidungen (bereits durch D1 geklärt):**
- F1 (ADR-001-DECISIONS): `mfg_nl2sql/__manifest__.py` ohne `scm_manufacturing`-Dependency ✅
- F2 (ADR-001-DECISIONS): `aifw.nl2sql` in `iil-aifw` als Subpackage, Odoo bleibt entkoppelt ✅

---

### D3 — Hosting: Eigener Hetzner-Server, kein Odoo.sh ✅ BESTÄTIGT

**Entscheidung:** Odoo + `aifw_service` laufen auf eigenem Hetzner-Server (aktuell `odoo-prod`,
46.225.127.211, CPX32). Odoo.sh wird **nicht** genutzt.

**Begründung (technisch zwingend):**
- Odoo.sh erlaubt keine Custom-Docker-Container — `aifw_service` (Django-Microservice) ist
  auf Odoo.sh nicht deploybar
- Der NL2SQL-Layer (D1) erfordert einen eigenständigen Container im selben Docker-Netzwerk
- Datensouveränität (D6): eigenes Hosting ist Voraussetzung für DSGVO-Konformität

**Konsequenzen für Infrastruktur:**

```
Hetzner CPX32 (46.225.127.211)
├── odoo_traefik      (Traefik v3.3, TLS via Let's Encrypt)
├── odoo_web          (Odoo 18.0)
├── odoo_db           (PostgreSQL 16-alpine)
└── aifw_service      (Django-Microservice, intern only)
```

- `aifw_service` ist **nicht** über Traefik nach außen exponiert — nur intern im
  Docker-Netzwerk `odoo_hub_internal` erreichbar
- `odoo_web` kommuniziert mit `aifw_service` über `http://aifw_service:8001/api/nl2sql/`
- Kein direkter Internet-Zugang für `aifw_service`

**Ressourcencheck (CPX32: 4 vCPU, 8 GB RAM):**

| Service | RAM (est.) | CPU (est.) |
|---------|-----------|-----------|
| Odoo 18 Web | ~800 MB | 0.5 vCPU |
| PostgreSQL 16 | ~512 MB | 0.3 vCPU |
| aifw_service | ~300 MB | 0.2 vCPU |
| Traefik | ~50 MB | minimal |
| **Gesamt** | **~1.7 GB** | **~1.0 vCPU** |
| **Headroom** | **~6.3 GB frei** ✅ | **~3.0 vCPU frei** ✅ |

→ CPX32 ist ausreichend für Einzelmandant-Betrieb. Bei > 3 Kunden auf einer Instanz: Upgrade
auf CX42 (8 vCPU, 16 GB, ~€21/Monat) evaluieren.

---

### D6 — DSGVO: Keine Kundendaten an LLM-APIs ✅ BESTÄTIGT

**Entscheidung:** Das NL2SQL-System sendet **ausschließlich Schema-Metadaten** an
externe LLM-APIs (Anthropic Claude, OpenAI GPT). Keine Produktionsdaten, keine
Kundenstammdaten, keine Messwerte verlassen den Server.

**Was an Anthropic/OpenAI gesendet wird (erlaubt):**
```
- Tabellen- und Spaltennamen (z.B. "casting_order", "total_scrap_pct")
- Spalten-Beschreibungen aus schema_metadata.xml (deutsch, neutral)
- Beispiel-Query-Strukturen (ohne echte Werte)
- Die Benutzer-Frage in natürlicher Sprache (z.B. "Ausschuss letzten Monat?")
```

**Was NICHT an LLM-APIs gesendet wird:**
```
- Tatsächliche Datenbankwerte (Stückzahlen, Messwerte, Namen)
- Kundenstammdaten (res_partner, Namen, Adressen)
- Auftragsdetails (Mengen, Preise, Kundennummern)
- Query-Ergebnisse
```

**Technische Umsetzung (verbindlich für alle Implementierungen):**

```python
# aifw_service/nl2sql/generator.py — verbindliches Muster
def build_system_prompt(schema_source: SchemaSource) -> str:
    """
    System-Prompt enthält NUR Schema-Metadaten — KEINE Datenbankwerte.
    Geprüft durch: DSGVO-Review 2026-03-03, D6.
    """
    return f"""Du bist ein SQL-Experte für eine Gießerei-Datenbank.
    
Verfügbare Tabellen:
{schema_source.schema_xml_summary}   ← nur Struktur, keine Werte

Regeln:
- Generiere NUR SELECT-Statements
- Kein INSERT, UPDATE, DELETE, DROP, TRUNCATE
- Kein COPY, EXECUTE, DO, CALL
- Maximal {schema_source.max_rows} Zeilen (LIMIT immer gesetzt)
"""

def ask(self, question: str, schema_source: SchemaSource) -> NL2SQLResult:
    """
    question: Benutzer-Frage (geht an LLM-API)
    schema_source: Schema-Metadaten (gehen an LLM-API)
    
    NICHT gesendet: Datenbankwerte, Query-Ergebnisse, Stammdaten.
    """
    prompt = self.build_system_prompt(schema_source)
    # completion() sendet: system_prompt + question → empfängt: SQL-String
    result = sync_completion(
        action_type="nl2sql",
        messages=[{"role": "user", "content": question}],
        system=prompt,
    )
    return result
```

**Vertragliche Anforderungen an Kundenprojekte:**
- Auftragsverarbeitungsvertrag (AVV) mit Anthropic/OpenAI abschließen
  - Anthropic: https://privacy.anthropic.com/en/articles/8325884-anthropic-data-processing-addendum
  - OpenAI: https://platform.openai.com/docs/guides/your-data
- Im Kundenvertrag explizit dokumentieren: "NL2SQL sendet keine personenbezogenen Daten
  oder Produktionsdaten an externe APIs"
- Audit-Log in `nl2sql.query.history` als Nachweis (welche Fragen wurden gestellt)
- Optional: Lokales LLM (Ollama + llama3) als DSGVO-freie Alternative für sensitive Kunden

**Lokales LLM als Option (für maximale Datensouveränität):**
```yaml
# docker-compose.prod.yml — optionale Erweiterung für sensitive Kunden
ollama:
  image: ollama/ollama:latest
  container_name: odoo_ollama
  volumes:
    - ollama_models:/root/.ollama
  environment:
    - OLLAMA_NUM_PARALLEL=2
  networks:
    - internal   # nur intern, kein Internet-Zugang
  deploy:
    resources:
      limits:
        memory: 6G   # llama3:8b benötigt ~5 GB
```

---

## Abgeleitete Architekturentscheidungen

Durch D1 + D3 + D6 sind folgende Architekturdetails **verbindlich festgelegt**:

### A1 — Kommunikation Odoo ↔ aifw_service: HTTP-REST (kein Python-Import)

```
mfg_nl2sql (Odoo Controller)
    │
    │  POST http://aifw_service:8001/api/nl2sql/query
    │  { "question": "...", "schema": "casting_foundry", "api_key": "..." }
    ▼
aifw_service (Django)
    │
    │  sync_completion() → Anthropic/OpenAI API
    │  nl2sql_ro → PostgreSQL (READ ONLY)
    ▼
    Response: { "sql": "...", "columns": [...], "rows": [...], "chart_type": "..." }
```

**Gelöste ADR-001-REVIEW Befunde durch A1:**
- C2 (`asyncio.run()` in Odoo) → **eliminiert** (kein Python-Import mehr)
- C4 (Stack-Mismatch Django+Odoo) → **eliminiert** (klare Service-Trennung)
- H3 (8 Verantwortlichkeiten im Controller) → **stark reduziert** (Controller nur HTTP-Proxy)

### A2 — SQL-Execution: nl2sql_ro-Role mit DB-seitigen Guards

```sql
-- Verbindlich für alle Deployments (docker/db/init.sql):
ALTER ROLE nl2sql_ro SET statement_timeout      = '30s';
ALTER ROLE nl2sql_ro SET lock_timeout           = '5s';
ALTER ROLE nl2sql_ro SET default_transaction_read_only = on;
```

**Gelöste ADR-001-REVIEW Befunde durch A2:**
- C1 (`cr.rollback()`) → **irrelevant** (aifw_service nutzt eigene DB-Connection, nicht Odoo-Cursor)
- C3 (`SET LOCAL statement_timeout` + pgbouncer) → **eliminiert** (Role-Level-Setting)
- H6 (kein Read-Only-User) → **gelöst**

### A3 — LLM-Prompt: Schema-only (DSGVO-konform per D6)

Technisch erzwungen durch `SchemaSource.schema_xml` — enthält nur DDL und Beschreibungen,
keine Query-Ergebnisse. `aifw_service` hat keine Möglichkeit, Datenbankwerte in den
Prompt einzubauen (Architektur verhindert es, nicht nur Konvention).

---

## Sprint 1 — Autorisierte Änderungen (sofort starten)

Alle Items sind durch D1/D3/D6 + A1/A2/A3 autorisiert. Aufwand ~20h.

### 1a. `mfg_nl2sql`: Controller zu HTTP-Proxy refactoren

**Ziel-Zustand `nl2sql_controller.py`:**
```python
class NL2SQLController(http.Controller):

    @http.route('/mfg_nl2sql/query', type='json', auth='user', methods=['POST'])
    def query(self, question: str, **kw):
        """HTTP-Proxy zu aifw_service. Kein LLM-Call, kein SQL-Execution hier."""
        config = self._get_aifw_config()          # URL + API-Key aus ir.config_parameter
        response = requests.post(                  # sync HTTP-Call (kein asyncio!)
            f"{config['url']}/api/nl2sql/query",
            json={
                'question': question,
                'schema': config['schema_source'],
                'max_rows': config['max_rows'],
            },
            headers={'Authorization': f"Bearer {config['api_key']}"},
            timeout=35,
        )
        result = response.json()
        self._write_audit_log(question, result)    # Odoo ORM — sauber, kein rollback-Risk
        return result

    def _get_aifw_config(self) -> dict:
        ICP = request.env['ir.config_parameter'].sudo()
        url = ICP.get_param('mfg_nl2sql.aifw_url')
        if not url:
            raise UserError('mfg_nl2sql.aifw_url ist nicht konfiguriert.')
        return {
            'url':           url,
            'api_key':       ICP.get_param('mfg_nl2sql.aifw_api_key', ''),
            'schema_source': ICP.get_param('mfg_nl2sql.schema_source', 'casting_foundry'),
            'max_rows':      int(ICP.get_param('mfg_nl2sql.max_rows', '500')),
        }

    def _write_audit_log(self, question: str, result: dict):
        request.env['nl2sql.query.history'].create({
            'name':          f"QH-{fields.Datetime.now().strftime('%Y%m%d%H%M%S')}",
            'question':      question,
            'generated_sql': result.get('sql'),
            'state':         'success' if 'rows' in result else 'error',
            'error_message': result.get('error'),
            'result_row_count': len(result.get('rows', [])),
        })
```

**Gelöschte Verantwortlichkeiten aus Controller (nach Refactoring):**
- `_call_anthropic()` → in `aifw_service`
- `_call_openai()` → in `aifw_service`
- `_build_system_prompt()` → in `aifw_service`
- `_execute_sql()` → in `aifw_service` (nl2sql_ro)
- `sanitize_sql()` → in `aifw_service`
- `detect_chart_type()` → in `aifw_service`
- `build_chart_config()` → in `aifw_service`

Controller verbleibt: HTTP-Routing + Config-Lesen + Audit-Log = ~60 Zeilen.

### 1b. `docker-compose.prod.yml`: aifw_service ergänzen

```yaml
# Ergänzung zu bestehender docker-compose.prod.yml
aifw_service:
  image: odoo-hub-aifw_service   # bereits vorhanden laut docker ps
  container_name: aifw_service
  restart: unless-stopped
  env_file: .env.prod
  environment:
    - AIFW_ALLOWED_HOSTS=odoo_web    # nur Odoo-Container darf anfragen
    - AIFW_NL2SQL_DB_HOST=odoo_db
    - AIFW_NL2SQL_DB_USER=nl2sql_user
    - AIFW_NL2SQL_DB_NAME=odoo
  expose:
    - "8001"           # NUR intern — kein ports: Mapping
  networks:
    - internal         # nicht im proxy-Netzwerk → kein Traefik, kein Internet
  depends_on:
    - db
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8001/api/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

### 1c. `docker/db/init.sql`: nl2sql_ro für casting_* erweitern

```sql
-- Ergänzung zu bestehender docker/db/init.sql
-- DSGVO-konform: nl2sql_ro darf nur casting_* lesen (Produktionsdaten intern)

-- Grants nach Odoo-Modulinstallation (casting_foundry muss installiert sein)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_name = 'casting_order') THEN
        GRANT SELECT ON TABLE
            casting_order,
            casting_order_line,
            casting_machine,
            casting_alloy,
            casting_mold,
            casting_quality_check,
            casting_defect_type,
            casting_material,
            casting_defect_type_casting_quality_check_rel
        TO nl2sql_ro;
        RAISE NOTICE 'casting_* GRANTs für nl2sql_ro gesetzt';
    ELSE
        RAISE NOTICE 'casting_foundry noch nicht installiert — GRANTs ausstehend';
    END IF;
END $$;
```

### 1d. `mfg_nl2sql` Modell-Fixes

```python
# models/query_history.py — verbindliche Änderungen

# Vor: fields.Text (JSON als String — kein DB-Constraint)
result_data    = fields.Text(...)
result_columns = fields.Text(...)
chart_config   = fields.Text(...)

# Nach: fields.Json (PostgreSQL jsonb — DB-validiert)
result_data    = fields.Json(string='Ergebnis', readonly=True)
result_columns = fields.Json(string='Spalten', readonly=True)
chart_config   = fields.Json(string='Chart Config', readonly=True)

# State-Constraints (neu):
_sql_constraints = [
    ('success_requires_sql',
     "CHECK(state != 'success' OR generated_sql IS NOT NULL)",
     'Erfolgreiche Abfragen müssen SQL enthalten.'),
    ('error_requires_message',
     "CHECK(state != 'error' OR error_message IS NOT NULL)",
     'Fehlerhafte Abfragen müssen eine Fehlermeldung enthalten.'),
    ('row_count_non_negative',
     "CHECK(result_row_count IS NULL OR result_row_count >= 0)",
     'Zeilenanzahl muss >= 0 sein.'),
]
```

---

---

## Neue Entscheidungen (2026-03-03, durch ADR-005 entschieden)

### D7 — Konfigurator: eigenständiges Addon `iil_configurator` ✅ ENTSCHIEDEN

**Entscheidung:** Der Produktkonfigurator wird als eigenständiges Odoo-Addon `iil_configurator`
implementiert. Er ist **nicht** Teil von `mfg_management`.

**Konsequenzen:**
- `mfg_management` `depends` auf `iil_configurator`
- `iil_configurator` enthält: `iil.product.feature` (Feature-Registry), `iil.seed.engine` (Demo-Daten-Generator), `iil.configurator.wizard` (5-Schritt-Fragebogen)
- Der Konfigurator ist **proprietäres IP** — kein Open-Source-Release ohne explizite Entscheidung
- Ermöglicht späteren SaaS-Onboarding-Flow (Sprint 5)

---

### D8 — Zweite Vertikale: Werkzeugmaschinen/CNC (`mfg_machining`) ✅ ENTSCHIEDEN

**Entscheidung:** `mfg_machining` wird als zweite Branchenvertikale nach `casting_foundry`
entwickelt. Zielsegment: Werkzeugmaschinenbau (VDMA: ~€14 Mrd Umsatz DE).

**Konsequenzen:**
- `casting_foundry`-Pattern (~70% Code-Reuse) wird direkt übertragen
- Neue Models: `machining_tool`, `machining_nc_program`, `machining_setup_sheet`, `machining_order`, `machining_quality_check`
- Konfigurator-Wizard enthält Branche `machining` ab Sprint 3
- Sprint-Zuordnung: Sprint 3 (Grundgerüst), Sprint 4 (vollständig)

---

### D9 — Demo-Daten: Pflichtbestandteil des Konfigurators ✅ ENTSCHIEDEN

**Entscheidung:** Demo-Daten-Generierung (`iil.seed.engine`) ist Standardbestandteil des
Wizard-Abschlusses (`generate_demo_data=True` als Default). Ohne Demo-Daten kein Go-Live.

**Konsequenzen:**
- `_generate_casting_data()`: ~200 Aufträge mit realistischen Trends (Volumen, Ausschuss, Saison)
- `_generate_machining_data()`: CNC-Aufträge, Maßprotokolle, Werkzeugverschleiß (Sprint 4)
- Idempotenz: `clear_existing=True` verhindert Datenmüll bei wiederholtem Durchlauf
- NL2SQL-Schema-Metadaten werden automatisch nach Demo-Daten aktiviert

---

## Offene Entscheidungen (noch nicht getroffen)

| # | Frage | Bis Sprint | Optionen |
|---|-------|-----------|---------|
| D2 | LLM-Default: claude-3-5-sonnet oder claude-3-haiku? | Sprint 1 | Haiku: günstiger, schneller; Sonnet: besser für komplexes SQL |
| D4 | Pricing NL2SQL Add-on: €149/€349? | Sprint 4 | Markttest mit Pilot-Kunden |
| D5 | Erster Pilot-Kunde: Gießerei-Branche? | Sprint 3 | `casting_foundry` = sofort demo-ready |

---

## Änderungshistorie ADR-Dokumente

| Dokument | Datum | Status | Inhalt |
|----------|-------|--------|--------|
| `ADR-001-REVIEW.md` | 2026-03-02 | Abgeschlossen | 7 kritische Befunde, 8 Empfehlungen |
| `ADR-001-DECISIONS.md` | 2026-03-02 | Abgeschlossen | F1/F2/F3 Analyse + Empfehlungen |
| `ADR-002-PRODUCT-STRATEGY.md` | 2026-03-03 | Abgeschlossen | Produktbewertung + 5-Sprint-Plan |
| **`ADR-003-DECISIONS-UPDATE.md`** | **2026-03-03** | **Aktiv** | **D1/D3/D6 bestätigt, A1/A2/A3 festgelegt, D7/D8/D9 ergänzt** |
| `ADR-005-KONFIGURATOR.md` | 2026-03-03 | Abgeschlossen | D7 (Konfigurator-Addon), D8 (Werkzeugmaschinen), D9 (Demo-Daten Pflicht) |

---

## Nächster Schritt

**Sprint 1 starten.** Reihenfolge (unverändert, Blocker für alle weiteren Sprints):

1. `mfg_nl2sql` Controller refactoren (1c → A1, ~6h)
2. `models/query_history.py` Fixes (fields.Json + _sql_constraints, ~3h)
3. `docker/db/init.sql` casting_* GRANTs (A2, ~1h)
4. `docker-compose.prod.yml` aifw_service ergänzen (D3, ~2h)
5. End-to-End-Test: Frage → aifw_service → SQL → Ergebnis in Odoo Dashboard

**Definition of Done Sprint 1:**
- [ ] Kein `cr.rollback()` im `mfg_nl2sql`-Codebase
- [ ] Kein `asyncio.run()` im `mfg_nl2sql`-Codebase
- [ ] Kein direkter LLM-API-Call in Odoo-Controller
- [ ] `nl2sql_ro` hat SELECT auf alle `casting_*`-Tabellen
- [ ] `aifw_service` antwortet auf `GET /api/health` mit HTTP 200
- [ ] End-to-End-Query funktioniert: "Welche Maschine hatte letzten Monat den höchsten Ausschuss?"

**Sprint 2 (nach Sprint 1):**
- `iil_configurator` Addon-Grundgerüst, `iil.product.feature` Model
- OWL-Panel-Registry in `mfg_management`
- `iil_mrp` + `iil_stock` Grundgerüst (depends: mrp, stock)

**Sprint 3 (Konfigurator-Kern):**
- Konfigurator-Wizard vollständig (5 Schritte)
- Demo-Daten-Generator Gießerei (`iil.seed.engine`)
- `mfg_machining` Grundgerüst
- Vollständige Gießerei-Demo in < 1h ab Leer-Instanz

**Für vollständigen Sprint-Plan: siehe ADR-005 Abschnitt 9.**
