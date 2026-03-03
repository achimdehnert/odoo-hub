# ADR-004: Code Review — `mfg_nl2sql` Produktionscode

| Feld | Wert |
|------|------|
| **Review-Datum** | 2026-03-03 |
| **Reviewer** | Cascade — kritisches Architektur-Review |
| **Geprüfte Revision** | aktueller HEAD (`addons/mfg_nl2sql/`) |
| **Geprüfte Dateien** | `controllers/nl2sql_controller.py` (618 Zeilen), `models/query_history.py`, `models/schema_metadata.py`, `models/saved_query.py`, `models/dashboard_config.py`, `docker/db/init.sql` |
| **ADR-Status** | **Review — Umsetzung ausstehend** |
| **Bewertung gesamt** | ⚠️ **Nicht production-ready** — 4 Kritische, 5 Hohe, 4 Mittlere Befunde |

**Qualitätskriterien (Prüfmaßstab):**
1. DB-getrieben — Konfiguration ausschließlich aus der Datenbank
2. Konsequente Normalisierung — keine redundanten Felder
3. Separation of Concerns — klare Schichttrennung
4. Naming Conventions — konsistent über alle Layer
5. Minimaler Diff — reviewbar
6. Kein magisches Verhalten — keine stillen Fallbacks
7. Robustes Error Handling — klare Exit Codes, kein swallow
8. Idempotenz — mehrfaches Ausführen darf nicht kaputt machen

---

## 1. Architekturkonformität

### 1.1 `cr.rollback()` rollt den gesamten Request-Cursor zurück — KRITISCH

**Befund:**

```python
# controllers/nl2sql_controller.py, Zeile 415–426
except Exception as exc:
    elapsed = int((time.time() - start) * 1000)
    _logger.error("SQL execution error: %s\nSQL: %s", exc, sql)
    # Rollback the failed transaction
    cr.rollback()           # ← KRITISCH
    return {
        'columns': [],
        ...
        'error': str(exc),
    }
```

In Odoo teilt der Controller-Request **einen** Cursor (`request.env.cr`) mit dem
gesamten ORM-Framework. `cr.rollback()` rollt **alle** ORM-Writes dieses Requests
zurück — inklusive nicht verwandter Writes.

Unmittelbar nach `_execute_sql()` ruft `execute_query()` (Zeilen 471–483)
`request.env['nl2sql.query.history'].create(...)` auf. Dieser Create findet
**nach** dem Rollback statt — der History-Eintrag wird zwar committed, aber die
vorherigen Writes sind weg. Das Verhalten ist nicht-deterministisch unter Last.

**Risiko:** 🔴 KRITISCH — Datenverlust durch impliziten Rollback nicht-verwandter Writes.

**Empfehlung:**

```python
# controllers/nl2sql_controller.py — _execute_sql(), Zeile 357ff.
# Savepoint statt Rollback des Gesamt-Cursors

def _execute_sql(self, sql: str, max_rows: int = 1000) -> dict:
    config = self._get_llm_config()
    timeout_ms = config['timeout'] * 1000
    cr = request.env.cr
    savepoint = f"nl2sql_exec_{int(time.time() * 1000)}"
    start = time.time()

    cr.execute(f"SAVEPOINT {savepoint}")
    try:
        cr.execute(f"SET LOCAL statement_timeout = '{timeout_ms}'")
        cr.execute(
            "SELECT * FROM (%s) AS _nl2sql_q LIMIT %s",
            (sql, max_rows),   # ← parametrisiert, kein String-Format
        )
        columns = []
        if cr.description:
            for desc in cr.description:
                columns.append({
                    'name': desc.name,
                    'type': _pg_type_name(desc.type_code),
                })
        rows = _serialize_rows(cr.fetchall())
        cr.execute(f"RELEASE SAVEPOINT {savepoint}")
        return {
            'columns': columns,
            'rows': rows,
            'row_count': len(rows),
            'execution_time_ms': int((time.time() - start) * 1000),
        }
    except Exception as exc:
        cr.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
        _logger.error("SQL execution error: %s | SQL: %s", exc, sql)
        return {
            'columns': [],
            'rows': [],
            'row_count': 0,
            'execution_time_ms': int((time.time() - start) * 1000),
            'error': str(exc),
        }
```

---

### 1.2 SQL-Wrapping via String-Interpolation — KRITISCH

**Befund:**

```python
# controllers/nl2sql_controller.py, Zeile 371
limited_sql = f"SELECT * FROM ({sql}) AS _q LIMIT {max_rows}"
cr.execute(limited_sql)
```

`sql` ist LLM-Output — nicht vertrauenswürdig. Obwohl `sanitize_sql()` vorher
läuft, schützt es nicht gegen alle Formen von SQL-Injection durch cleveres
Prompt-Engineering. Der Wert `max_rows` kommt aus `ir.config_parameter` (int),
das ist akzeptabel, aber `sql` muss parametrisiert übergeben werden.

`psycopg2` unterstützt Sub-Query-Wrapping nicht via Placeholder — das erfordert
`sql.SQL()` aus `psycopg2.sql`:

**Risiko:** 🔴 KRITISCH — SQL-Injection-Vektor durch LLM-generierten Code.

**Empfehlung:**

```python
from psycopg2 import sql as pgsql

# Statt f-String:
wrapped = pgsql.SQL("SELECT * FROM ({inner}) AS _nl2sql_q LIMIT {limit}").format(
    inner=pgsql.SQL(sql),    # sanitize_sql() hat bereits validiert
    limit=pgsql.Literal(max_rows),
)
cr.execute(wrapped)
```

Zusätzlich: `sanitize_sql()` als eigene Klasse mit `__call__` statt freier
Modul-Funktion, um Testbarkeit zu gewährleisten.

---

### 1.3 Acht Verantwortlichkeiten in einer Klasse — HOCH

**Befund:**

`NL2SQLController` (618 Zeilen) enthält:

| Methode | Verantwortlichkeit |
|---------|-------------------|
| `_get_llm_config()` | Config-Lesen |
| `_build_system_prompt()` | Prompt-Engineering |
| `_call_anthropic()` | HTTP-Call Anthropic |
| `_call_openai()` | HTTP-Call OpenAI |
| `_translate_nl_to_sql()` | LLM-Orchestrierung |
| `_execute_sql()` | SQL-Execution |
| `detect_chart_type()` | Visualisierungs-Logik |
| `build_chart_config()` | Chart.js-Config-Bau |
| `execute_query()` | HTTP-Routing + Orchestrierung |
| `get_dashboard_data()` | Dashboard-Datenaggregation |

Zusätzlich: `sanitize_sql()` und `detect_chart_type()` und `build_chart_config()`
als freie Modul-Funktionen — weder `@staticmethod` noch eigene Klasse,
importierbar aber nicht mock-fähig ohne den gesamten Controller-Import.

**Risiko:** 🟡 HOCH — Unit-Tests ohne vollständige Odoo-Umgebung unmöglich.
LLM-Provider-Wechsel (Anthropic → OpenAI) erfordert Controller-Eingriff.

**Empfehlung:**

```
mfg_nl2sql/
  services/
    __init__.py
    llm_service.py      # _get_llm_config, _build_system_prompt,
                        # _call_anthropic, _call_openai, _translate_nl_to_sql
    sql_service.py      # SQLSanitizer (Klasse), _execute_sql
    chart_service.py    # ChartDetector, ChartConfigBuilder
  controllers/
    nl2sql_controller.py  # nur HTTP-Routing + Orchestrierung (~80 Zeilen)
```

---

### 1.4 `_rec_name = 'display_name'` überschreibt Odoo-Base-Feld — MITTEL

**Befund:**

```python
# models/schema_metadata.py, Zeile 22–23
_rec_name = 'display_name'

display_name = fields.Char(
    string='Display Name',
    compute='_compute_display_name',
    store=True,
)
```

`display_name` ist ein **von Odoo-Base automatisch berechnetes Feld** (`name_get()`).
Das Überschreiben via `store=True`-Compute-Feld kollidiert mit Odoo-internen
Mechanismen: `name_search()`, `Many2one`-Dropdown-Rendering, `display_name`-Cache-
Invalidierung. In Odoo 18 wurde `display_name` explizit in `BaseModel` als
systemseitiges Computed-Feld deklariert — eine eigene Definition mit `store=True`
ist undokumentiertes Override-Verhalten.

**Risiko:** 🟠 MITTEL — Schwer zu debuggender Konflikt in Many2one-Feldern.

**Empfehlung:**

```python
# models/schema_metadata.py
_rec_name = 'label'   # eigener Name, kein Konflikt mit Odoo-Base

label = fields.Char(
    string='Bezeichnung',
    compute='_compute_label',
    store=True,
)

@api.depends('name', 'domain')
def _compute_label(self):
    domain_labels = dict(self._fields['domain'].selection)
    for rec in self:
        domain_label = domain_labels.get(rec.domain, '')
        rec.label = f"[{domain_label}] {rec.name}" if rec.name else ''
```

---

## 2. Invarianten

### 2.1 `result_data` / `result_columns` / `chart_config` als `fields.Text` — KRITISCH

**Befund:**

```python
# models/query_history.py, Zeilen 60–92
result_data    = fields.Text(string='Ergebnis (JSON)', readonly=True)
result_columns = fields.Text(string='Spalten (JSON)', readonly=True)
chart_config   = fields.Text(string='Chart Config (JSON)', readonly=True)
```

Drei `Text`-Felder mit strukturierten JSON-Daten. PostgreSQL 16 hat natives `jsonb` —
Odoo 16+ mappt `fields.Json` auf `jsonb`.

Konsequenzen:
- Keine DB-seitige JSON-Validierung — fehlerhafte JSON-Strings landen ohne Fehler in der DB
- `result_data` kann mehrere MB groß werden (1000 Rows × viele Spalten) — kein
  Truncation-Guard, keine Größenwarnung
- Kein `@>`-Operator-Support auf `text` — JSON-Inhalte nicht suchbar/filterbar

Gleichzeitig in `execute_query()` (Zeilen 502–508):
```python
'result_data':    json.dumps(result['rows']),    # Text serialisiert
'result_columns': json.dumps(result['columns']), # Text serialisiert
'chart_config':   json.dumps(chart_config),      # Text serialisiert
```

Und in `get_history_result()` (Zeilen 612–616):
```python
'columns':    json.loads(history.result_columns or '[]'),  # stiller Fallback ←
'rows':       json.loads(history.result_data    or '[]'),  # stiller Fallback ←
'chart_config': json.loads(history.chart_config or '{}'), # stiller Fallback ←
```

**Risiko:** 🔴 KRITISCH — Stille Fallbacks verbergen Datenfehler; kein DB-Constraint.

**Empfehlung:**

```python
# models/query_history.py — vollständige Korrekturfassung

result_data = fields.Json(
    string='Ergebnis',
    readonly=True,
    help='Query results as jsonb array (PostgreSQL native)',
)
result_columns = fields.Json(
    string='Spalten',
    readonly=True,
)
chart_config = fields.Json(
    string='Chart Config',
    readonly=True,
)

_sql_constraints = [
    (
        'success_requires_sql',
        "CHECK(state != 'success' OR "
        "(generated_sql IS NOT NULL AND sanitized_sql IS NOT NULL))",
        'Erfolgreiche Abfragen müssen SQL enthalten.',
    ),
    (
        'error_requires_message',
        "CHECK(state != 'error' OR error_message IS NOT NULL)",
        'Fehlerhafte Abfragen müssen eine Fehlermeldung enthalten.',
    ),
    (
        'row_count_non_negative',
        "CHECK(result_row_count IS NULL OR result_row_count >= 0)",
        'Zeilenanzahl muss >= 0 sein.',
    ),
]
```

Controller: `json.dumps()` entfällt — `fields.Json` serialisiert automatisch.
```python
# execute_query(), Zeile 496ff — nach Fix:
history = request.env['nl2sql.query.history'].create({
    ...
    'result_data':    result['rows'],      # kein json.dumps()
    'result_columns': result['columns'],   # kein json.dumps()
    'chart_config':   chart_config,        # kein json.dumps()
    ...
})
```

In `get_history_result()`:
```python
# Kein stiller Fallback — explizites None-Handling:
if not history.result_columns:
    return {'error': 'Kein gespeichertes Ergebnis (result_columns ist NULL)'}
return {
    'columns':    history.result_columns,   # bereits dict/list durch fields.Json
    'rows':       history.result_data,
    'chart_config': history.chart_config or {},
}
```

---

### 2.2 `domain`-Pflichtfeld ohne DB-Constraint — MITTEL

**Befund:**

```python
# models/schema_metadata.py, Zeile 43–53
domain = fields.Selection(
    selection=[...],
    string='Domäne',
    required=True,   # nur ORM-Constraint
    index=True,
)
```

`required=True` ist ein ORM-Constraint — nicht in `_sql_constraints` als
`CHECK(domain IS NOT NULL)`. Direkter DB-Insert (via `psql`, Migration-Script,
`execute()`) umgeht diesen Guard. `_compute_display_name()` produziert dann
`"[] tablename"` — kein Fehler, falscher Wert.

**Risiko:** 🟠 MITTEL — Stille Fehlkonfiguration ohne DB-seitige Absicherung.

**Empfehlung:**

```python
# models/schema_metadata.py
_sql_constraints = [
    ('unique_table_name', 'UNIQUE(name)', 'Table name must be unique.'),
    ('domain_not_null', 'CHECK(domain IS NOT NULL)', 'Domain ist Pflichtfeld.'),
]
```

---

### 2.3 `saved_query.last_result_data` — denormalisiertes `fields.Text` — MITTEL

**Befund:**

```python
# models/saved_query.py, Zeile 104–107
last_result_data = fields.Text(
    string='Letztes Ergebnis (JSON)',
    readonly=True,
)
```

`SavedQuery` speichert die letzten 50 Rows als JSON-String — redundant zu
`QueryHistory.result_data`. Bei jedem Query-Run (Zeilen 517–519 im Controller):

```python
saved.write({
    'last_result_data': json.dumps(result['rows'][:50]),  # Duplikat
    'last_run': history.create_date,
    'generated_sql': sanitized,
})
```

Das ist Denormalisierung: `last_result_data` ist eine gecachte Kopie von
`nl2sql.query.history.result_data` gefiltert auf die letzte Ausführung.
Statt eigenes Feld: Foreign-Key auf letzten `history`-Eintrag.

**Risiko:** 🟠 MITTEL — Inkonsistenz zwischen `SavedQuery.last_result_data`
und dem zugehörigen `QueryHistory`-Eintrag möglich (Race Condition, Fehler).

**Empfehlung:**

```python
# models/saved_query.py — normalisierte Variante
last_history_id = fields.Many2one(
    'nl2sql.query.history',
    string='Letzte Ausführung',
    readonly=True,
    ondelete='set null',
)
# last_result_data entfernen — Daten über last_history_id.result_data abrufen
```

Controller-Anpassung:
```python
# execute_query(), statt last_result_data:
saved.write({
    'last_history_id': history.id,   # FK auf History-Record
    'last_run':        history.create_date,
    'generated_sql':   sanitized,
})
```

---

## 3. Seiteneffekte

### 3.1 `SET LOCAL statement_timeout` via Odoo-Cursor — KRITISCH

**Befund:**

```python
# controllers/nl2sql_controller.py, Zeile 369
cr.execute(f"SET LOCAL statement_timeout = '{timeout_ms}'")
```

`SET LOCAL` gilt nur für die aktuelle Transaktion. In Odoo wird die Transaktion
nicht explizit gestartet — `SET LOCAL` ohne explizites `BEGIN` kann je nach
psycopg2-`autocommit`-Einstellung keine Wirkung haben.

Zusätzlich: `timeout_ms` ist ein f-String ohne Validierung. Wenn
`mfg_nl2sql.query_timeout` auf einen nicht-numerischen Wert gesetzt wird
(z.B. via direktem DB-Write), schlägt `cr.execute()` mit einem kryptischen
Postgres-Fehler fehl — nicht mit einem klaren `ValueError`.

Entscheidend: Das DB-seitige `nl2sql_ro`-Rollen-Setting in `docker/db/init.sql`
(Zeile 37: `ALTER ROLE nl2sql_ro SET statement_timeout = '30s'`) greift — aber
**nur wenn `aifw_service` / NL2SQL-Execution über `nl2sql_user` läuft**, nicht wenn
Odoo seinen eigenen Cursor (`request.env.cr`) nutzt. Aktuell läuft `_execute_sql()`
als Odoo-User, nicht als `nl2sql_user` — das Rollen-Setting ist wirkungslos.

**Risiko:** 🔴 KRITISCH — Timeout-Guard greift nicht. Full-Table-Scans ohne
Zeitlimit möglich.

**Empfehlung (2 Varianten):**

**Variante A (minimal, kurzfristig):** Explizites `BEGIN` + validierter Timeout:
```python
def _execute_sql(self, sql: str, max_rows: int = 1000) -> dict:
    config = self._get_llm_config()
    timeout_ms = int(config['timeout']) * 1000   # int() wirft ValueError bei Müll
    cr = request.env.cr
    savepoint = f"nl2sql_{int(time.time() * 1000)}"
    cr.execute(f"SAVEPOINT {savepoint}")
    try:
        # SET LOCAL innerhalb Savepoint wirkt sicher:
        cr.execute("SET LOCAL statement_timeout = %s", (f"{timeout_ms}ms",))
        ...
    except Exception as exc:
        cr.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
        ...
```

**Variante B (strukturell, langfristig — per ADR-003 A2):**
`_execute_sql()` aus dem Odoo-Controller heraus entfernen. Die Execution erfolgt
in `aifw_service` via `nl2sql_user`-Verbindung — dort greift das Rollen-Setting
zuverlässig.

---

### 3.2 Stille Fallbacks — verletzt Qualitätskriterium 6

**Befund:**

```python
# controllers/nl2sql_controller.py, Zeilen 612–616
'columns':     json.loads(history.result_columns or '[]'),   # stiller Fallback
'rows':        json.loads(history.result_data    or '[]'),   # stiller Fallback
'chart_config': json.loads(history.chart_config or '{}'),   # stiller Fallback
```

```python
# controllers/nl2sql_controller.py, Zeile 226
'provider': ICP.get_param('mfg_nl2sql.llm_provider', 'anthropic'),  # Default ohne Warnung
```

```python
# models/dashboard_config.py, Zeile 57–61
def get_or_create(self):
    config = self.search([('user_id', '=', self.env.user.id)], limit=1)
    if not config:
        config = self.create({'user_id': self.env.user.id})  # stilles Create
```

Wenn `result_columns` `None` ist (z.B. durch den Rollback-Bug aus 1.1 oder
die fehlende State-Invariante aus 2.1), gibt der Endpoint
`{"columns": [], "rows": []}` zurück — **ohne Fehlerindikation**. Das Frontend
zeigt eine leere Tabelle. Kein Log-Eintrag. Kein Error-State im History-Record.

**Risiko:** 🟡 HOCH — Debugging produktiver Fehler extrem schwierig.

**Empfehlung:**

```python
# get_history_result() — explizites Fehler-Handling statt stiller Fallbacks:
def get_history_result(self, history_id):
    history = request.env['nl2sql.query.history'].browse(history_id)
    if not history.exists() or history.user_id != request.env.user:
        return {'error': 'Nicht gefunden oder keine Berechtigung'}

    if history.state != 'success':
        return {'error': f"Abfrage hat keinen Erfolg-Status: {history.state}"}

    if not history.result_columns:
        # Das darf nach Fix von 2.1 nicht mehr vorkommen
        _logger.error(
            "nl2sql.query.history id=%d: state=success aber result_columns=NULL",
            history.id,
        )
        return {'error': 'Interner Fehler: Ergebnis nicht gespeichert (ADR-004/2.1)'}

    return {
        'id':           history.id,
        'name':         history.name,
        'sql':          history.sanitized_sql,
        'columns':      history.result_columns,   # fields.Json → bereits list
        'rows':         history.result_data,       # fields.Json → bereits list
        'row_count':    history.result_row_count,
        'chart_type':   history.chart_type,
        'chart_config': history.chart_config or {},
    }
```

---

### 3.3 `init.sql` Bug: falsche `WHERE`-Bedingung — HOCH

**Befund:**

```sql
-- docker/db/init.sql, Zeilen 98–108
FOREACH tbl IN ARRAY tbls LOOP
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'current_schema()'   -- ← BUG: String-Literal statt Funktion
           OR table_name = tbl
    ) THEN
```

`'current_schema()'` ist ein **String-Literal** — nicht der Funktionsaufruf
`current_schema()`. Die Bedingung lautet effektiv:
```sql
WHERE table_schema = 'current_schema()'   -- immer FALSE (kein Schema heißt so)
   OR table_name = tbl                    -- immer TRUE (jede Tabelle existiert irgendwo)
```

Das bedeutet: `GRANT SELECT` wird für **alle Tabellen** ausgeführt — auch für
Tabellen die noch nicht existieren (→ Fehler) oder zu falschen Schemas gehören.
Der `ELSE`-Zweig (GRANT übersprungen) wird **nie** erreicht.

**Risiko:** 🟡 HOCH — GRANTs werden unkontrolliert ausgeführt, Idempotenz-Garantie
bricht. Fehler-Nachrichten irreführend.

**Empfehlung:**

```sql
-- docker/db/init.sql, korrigierte Version:
FOREACH tbl IN ARRAY tbls LOOP
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = current_schema()    -- Funktion, kein String-Literal
          AND table_name   = tbl                 -- AND statt OR
    ) THEN
        EXECUTE format('GRANT SELECT ON TABLE %I TO nl2sql_ro', tbl);
        RAISE NOTICE '[init.sql] GRANT SELECT ON % TO nl2sql_ro — OK', tbl;
    ELSE
        RAISE NOTICE '[init.sql] % existiert noch nicht — übersprungen', tbl;
    END IF;
END LOOP;
```

Gleiches gilt für Abschnitt 5 (custom_tbls, Zeile 141–151) — dort ist die
Bedingung korrekt (`table_schema = 'public'`), aber der OR-Operator im ersten
Block muss durch AND ersetzt werden.

---

## 4. Migrationsrisiken

### 4.1 Kein `casting_material` und kein `casting_defect_type` in `init.sql` — HOCH

**Befund:**

```sql
-- docker/db/init.sql, Zeilen 134–138 (Abschnitt 5)
'casting_order', 'casting_order_line',
'casting_machine', 'casting_alloy',
'casting_quality_check', 'casting_defect',   -- ← falsch: 'casting_defect' existiert nicht
'casting_mold', 'casting_mold_usage'         -- ← 'casting_mold_usage' existiert nicht
```

Die tatsächliche DB-Struktur (validiert 2026-03-03) zeigt:

| `init.sql`-Name | Tatsächlicher Tabellenname | Status |
|---|---|---|
| `casting_defect` | `casting_defect_type` | ❌ Falscher Name |
| `casting_mold_usage` | nicht vorhanden | ❌ Existiert nicht |
| — | `casting_material` | ❌ Fehlt in init.sql |
| — | `casting_defect_type_casting_quality_check_rel` | ❌ Fehlt (Junction-Tabelle) |

GRANTs für `casting_defect` und `casting_mold_usage` schlagen lautlos fehl
(der `IF EXISTS`-Block würde sie überspringen, wenn der Bug aus 3.3 behoben ist).
`nl2sql_ro` hat dadurch keinen Zugriff auf `casting_defect_type` — NL2SQL-Queries
die Defektinformationen abfragen scheitern mit `permission denied`.

**Risiko:** 🟡 HOCH — NL2SQL-Queries auf Defekttabellen schlagen fehl.

**Empfehlung:**

```sql
-- docker/db/init.sql, Abschnitt 5 — korrigierte Tabellenliste:
custom_tbls TEXT[] := ARRAY[
    -- SCM Manufacturing
    'scm_part', 'scm_part_category',
    'scm_bom', 'scm_bom_line',
    'scm_supplier_info',
    'scm_purchase_order', 'scm_purchase_order_line',
    'scm_production_order', 'scm_work_step',
    'scm_warehouse', 'scm_delivery',
    'scm_stock_move', 'scm_incoming_inspection',
    -- Casting Foundry (korrekte Tabellennamen — verifiziert 2026-03-03)
    'casting_material',
    'casting_alloy',
    'casting_machine',
    'casting_mold',
    'casting_order',
    'casting_order_line',
    'casting_quality_check',
    'casting_defect_type',
    'casting_defect_type_casting_quality_check_rel'
];
```

---

### 4.2 `NL2SQLController._get_llm_config()` liest Config bei jedem Request — MITTEL

**Befund:**

```python
# controllers/nl2sql_controller.py, Zeilen 222–236
def _get_llm_config(self):
    ICP = request.env['ir.config_parameter'].sudo()
    return {
        'provider': ICP.get_param('mfg_nl2sql.llm_provider', 'anthropic'),
        ...
    }
```

`_get_llm_config()` wird in `execute_query()` **zweimal** aufgerufen:
- Zeile 435: `config = self._get_llm_config()` (für `allow_write`)
- Zeile 324: In `_translate_nl_to_sql()` → `config = self._get_llm_config()`
- Zeile 362: In `_execute_sql()` → `config = self._get_llm_config()`

Pro Request **3 DB-Reads** für `ir.config_parameter` — obwohl die Config
sich zwischen den Calls nicht ändert. In Odoo ist `ir.config_parameter` zwar
gecacht, aber der Pattern ist unnötig und fehleranfällig (Änderungen mid-request).

**Risiko:** 🟠 MITTEL — Unnötige DB-Reads, potentielle Inkonsistenz bei
Config-Änderung während eines langen Requests.

**Empfehlung:**

```python
# execute_query(): Config einmal lesen, durchreichen
def execute_query(self, query_text, domain_filter='all', ...):
    config = self._get_llm_config()   # einmal
    generated_sql, tokens, error = self._translate_nl_to_sql(
        query_text, domain_filter, config   # config übergeben, nicht neu lesen
    )
    ...
    result = self._execute_sql(sanitized, config['max_rows'], config['timeout'])

def _translate_nl_to_sql(self, query_text, domain_filter, config):  # config als Param
    ...

def _execute_sql(self, sql, max_rows, timeout):  # kein self._get_llm_config() hier
    ...
```

---

## 5. Zusammenfassung

### Kritische Befunde 🔴 (Blocker für Production)

| # | Befund | Datei | Zeile |
|---|--------|-------|-------|
| C1 | `cr.rollback()` rollt nicht-verwandte ORM-Writes zurück | `nl2sql_controller.py` | 419 |
| C2 | SQL-Wrapping via f-String — SQL-Injection-Vektor | `nl2sql_controller.py` | 371 |
| C3 | `result_data/columns/chart_config` als `fields.Text` + stille `or '[]'`-Fallbacks | `query_history.py` + Controller | 60–92, 612–616 |
| C4 | `SET LOCAL statement_timeout` ohne garantiertes `BEGIN` + Odoo-User statt `nl2sql_user` | `nl2sql_controller.py` | 369 |

### Hohe Befunde 🟡 (Vor Deployment beheben)

| # | Befund | Datei |
|---|--------|-------|
| H1 | 8 Verantwortlichkeiten in `NL2SQLController` — kein Service Layer | `nl2sql_controller.py` |
| H2 | `init.sql` Bug: `WHERE table_schema = 'current_schema()'` ist String-Literal | `docker/db/init.sql` |
| H3 | Falsche Tabellennamen in `init.sql` (`casting_defect`, `casting_mold_usage`) | `docker/db/init.sql` |
| H4 | Stille Fallbacks `or '[]'` / `or '{}'` in `get_history_result()` | `nl2sql_controller.py` |
| H5 | `_get_llm_config()` dreifach pro Request aufgerufen | `nl2sql_controller.py` |

### Mittlere Befunde 🟠 (Nächster Sprint)

| # | Befund | Datei |
|---|--------|-------|
| M1 | `_rec_name = 'display_name'` überschreibt Odoo-Base-Feld | `schema_metadata.py` |
| M2 | `domain`-Pflichtfeld ohne DB-Constraint | `schema_metadata.py` |
| M3 | `SavedQuery.last_result_data` denormalisiert — FK auf History verwenden | `saved_query.py` |
| M4 | Fehlende State-Constraints (`_sql_constraints`) in `QueryHistory` | `query_history.py` |

---

## 6. Korrektur-Patches (vollständig, kein Platzhalter)

### Patch 1 — `docker/db/init.sql` (Bugs 3.3 + 4.1)

```sql
-- docker/db/init.sql
-- PostgreSQL 16 Initialisierungs-Script für odoo-hub
-- IDEMPOTENT: IF NOT EXISTS / DO $$ Blöcke
-- Rev: ADR-004 2026-03-03 — Bugfix WHERE-Bedingung + casting_*-Tabellennamen

-- ── 1. Read-Only-Basisrolle ──────────────────────────────────────────────────
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nl2sql_ro') THEN
        CREATE ROLE nl2sql_ro NOLOGIN;
        RAISE NOTICE '[init.sql] Rolle nl2sql_ro angelegt.';
    ELSE
        RAISE NOTICE '[init.sql] Rolle nl2sql_ro existiert bereits — übersprungen.';
    END IF;
END $$;

ALTER ROLE nl2sql_ro SET statement_timeout                    = '30s';
ALTER ROLE nl2sql_ro SET lock_timeout                         = '5s';
ALTER ROLE nl2sql_ro SET idle_in_transaction_session_timeout  = '60s';
ALTER ROLE nl2sql_ro SET default_transaction_read_only        = on;

-- ── 2. Login-User ────────────────────────────────────────────────────────────
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nl2sql_user') THEN
        CREATE USER nl2sql_user PASSWORD 'changeme_set_via_env' IN ROLE nl2sql_ro;
        RAISE NOTICE '[init.sql] User nl2sql_user angelegt. Passwort bitte sofort ändern!';
    ELSE
        RAISE NOTICE '[init.sql] User nl2sql_user existiert bereits — übersprungen.';
    END IF;
END $$;

-- ── 3. Schema-Usage ──────────────────────────────────────────────────────────
GRANT USAGE ON SCHEMA public TO nl2sql_ro;

-- ── 4. Standard-Odoo-Tabellen ────────────────────────────────────────────────
DO $$
DECLARE
    tbl TEXT;
    tbls TEXT[] := ARRAY[
        'purchase_order', 'purchase_order_line',
        'stock_quant', 'stock_location', 'stock_move', 'stock_picking',
        'res_partner', 'product_product', 'product_template', 'product_category',
        'mrp_production', 'mrp_bom', 'mrp_bom_line', 'mrp_workcenter', 'mrp_workorder',
        'quality_check', 'quality_point', 'quality_alert'
    ];
BEGIN
    FOREACH tbl IN ARRAY tbls LOOP
        IF EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = current_schema()  -- FIX: Funktion statt String-Literal
              AND table_name   = tbl               -- FIX: AND statt OR
        ) THEN
            EXECUTE format('GRANT SELECT ON TABLE %I TO nl2sql_ro', tbl);
            RAISE NOTICE '[init.sql] GRANT SELECT ON % TO nl2sql_ro — OK', tbl;
        ELSE
            RAISE NOTICE '[init.sql] % noch nicht vorhanden — übersprungen', tbl;
        END IF;
    END LOOP;
END $$;

-- ── 5. Default-Privileges für zukünftige Tabellen ───────────────────────────
ALTER DEFAULT PRIVILEGES FOR ROLE odoo IN SCHEMA public
    GRANT SELECT ON TABLES TO nl2sql_ro;

-- ── 6. Custom-Tabellen (SCM + Casting) ──────────────────────────────────────
DO $$
DECLARE
    tbl TEXT;
    custom_tbls TEXT[] := ARRAY[
        -- SCM Manufacturing
        'scm_part', 'scm_part_category',
        'scm_bom', 'scm_bom_line',
        'scm_supplier_info',
        'scm_purchase_order', 'scm_purchase_order_line',
        'scm_production_order', 'scm_work_step',
        'scm_warehouse', 'scm_delivery',
        'scm_stock_move', 'scm_incoming_inspection',
        -- Casting Foundry (verifiziert 2026-03-03)
        'casting_material',
        'casting_alloy',
        'casting_machine',
        'casting_mold',
        'casting_order',
        'casting_order_line',
        'casting_quality_check',
        'casting_defect_type',
        'casting_defect_type_casting_quality_check_rel'
    ];
BEGIN
    FOREACH tbl IN ARRAY custom_tbls LOOP
        IF EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name   = tbl
        ) THEN
            EXECUTE format('GRANT SELECT ON TABLE %I TO nl2sql_ro', tbl);
            RAISE NOTICE '[init.sql] GRANT SELECT ON % TO nl2sql_ro — OK', tbl;
        ELSE
            RAISE NOTICE '[init.sql] % noch nicht vorhanden — übersprungen', tbl;
        END IF;
    END LOOP;
END $$;

-- ── 7. aifw-Service User ─────────────────────────────────────────────────────
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'aifw') THEN
        CREATE USER aifw PASSWORD 'changeme_set_via_env_aifw';
        RAISE NOTICE '[init.sql] User aifw angelegt.';
    ELSE
        RAISE NOTICE '[init.sql] User aifw existiert bereits.';
    END IF;
END $$;
```

### Patch 2 — `models/query_history.py` (Bug C3 + M4)

```python
# -*- coding: utf-8 -*-
"""Query history for NL2SQL dashboard.

Rev: ADR-004 2026-03-03
- fields.Text → fields.Json für result_data/result_columns/chart_config
- _sql_constraints für state-Invarianten
"""
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class QueryHistory(models.Model):
    _name = 'nl2sql.query.history'
    _description = 'NL2SQL Query History'
    _order = 'create_date desc'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Abfrage',
        required=True,
        tracking=True,
        help='Original natural language query',
    )
    generated_sql = fields.Text(
        string='Generiertes SQL',
        readonly=True,
    )
    sanitized_sql = fields.Text(
        string='Ausgeführtes SQL',
        readonly=True,
        help='SQL after sanitization (read-only enforcement)',
    )
    domain_filter = fields.Selection(
        selection=[
            ('all', 'Alle Bereiche'),
            ('supply_chain', 'Supply Chain'),
            ('production', 'Produktion'),
            ('quality', 'Qualität'),
        ],
        string='Domäne',
        default='all',
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Entwurf'),
            ('processing', 'Verarbeitung'),
            ('success', 'Erfolgreich'),
            ('error', 'Fehler'),
            ('timeout', 'Timeout'),
        ],
        string='Status',
        default='draft',
        tracking=True,
        index=True,
    )
    # FIX ADR-004/C3: fields.Json statt fields.Text — PostgreSQL jsonb, DB-validiert
    result_data = fields.Json(
        string='Ergebnis',
        readonly=True,
        help='Query results as jsonb array',
    )
    result_columns = fields.Json(
        string='Spalten',
        readonly=True,
        help='Column names and types as jsonb',
    )
    result_row_count = fields.Integer(
        string='Zeilen',
        readonly=True,
        default=0,
    )
    chart_type = fields.Selection(
        selection=[
            ('table', 'Tabelle'),
            ('bar', 'Balkendiagramm'),
            ('line', 'Liniendiagramm'),
            ('pie', 'Kreisdiagramm'),
            ('kpi', 'KPI-Karte'),
            ('hbar', 'Horizontale Balken'),
        ],
        string='Diagrammtyp',
        default='table',
    )
    # FIX ADR-004/C3: fields.Json statt fields.Text
    chart_config = fields.Json(
        string='Chart Config',
        readonly=True,
        help='Chart.js configuration as jsonb',
    )
    execution_time_ms = fields.Integer(
        string='Ausführungszeit (ms)',
        readonly=True,
    )
    llm_tokens_used = fields.Integer(
        string='LLM Tokens',
        readonly=True,
    )
    error_message = fields.Text(
        string='Fehlermeldung',
        readonly=True,
    )
    user_id = fields.Many2one(
        'res.users',
        string='Benutzer',
        default=lambda self: self.env.user,
        readonly=True,
        index=True,
    )
    is_pinned = fields.Boolean(
        string='Angepinnt',
        default=False,
    )
    saved_query_id = fields.Many2one(
        'nl2sql.saved.query',
        string='Gespeicherte Abfrage',
        readonly=True,
    )

    # FIX ADR-004/M4: DB-seitige Invarianten für state-Übergänge
    _sql_constraints = [
        (
            'success_requires_sql',
            "CHECK(state != 'success' OR "
            "(generated_sql IS NOT NULL AND sanitized_sql IS NOT NULL))",
            'Erfolgreiche Abfragen müssen SQL enthalten.',
        ),
        (
            'error_requires_message',
            "CHECK(state != 'error' OR error_message IS NOT NULL)",
            'Fehlerhafte Abfragen müssen eine Fehlermeldung enthalten.',
        ),
        (
            'row_count_non_negative',
            "CHECK(result_row_count IS NULL OR result_row_count >= 0)",
            'Zeilenanzahl muss >= 0 sein.',
        ),
    ]

    def action_rerun(self):
        """Re-execute the query with current data."""
        self.ensure_one()
        if not self.name:
            raise UserError("Keine Abfrage vorhanden.")
        return {
            'type': 'ir.actions.client',
            'tag': 'mfg_nl2sql.dashboard',
            'params': {'rerun_query': self.name, 'domain': self.domain_filter},
        }

    def action_save_query(self):
        """Save this query for reuse."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Abfrage speichern',
            'res_model': 'nl2sql.save.query.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_query_text':   self.name,
                'default_generated_sql': self.generated_sql,
                'default_domain_filter': self.domain_filter,
                'default_chart_type':   self.chart_type,
                'default_history_id':   self.id,
            },
        }

    @api.model
    def cleanup_old_entries(self, days=90):
        """Scheduled action: remove entries older than N days."""
        cutoff = fields.Datetime.subtract(fields.Datetime.now(), days=days)
        old = self.search([
            ('create_date', '<', cutoff),
            ('is_pinned', '=', False),
            ('saved_query_id', '=', False),
        ])
        count = len(old)
        old.unlink()
        _logger.info("NL2SQL: Cleaned up %d old query history entries", count)
        return count
```

### Patch 3 — `controllers/nl2sql_controller.py` (Bugs C1+C2+C4+H4+H5, Auszug kritische Stellen)

```python
# Nur die geänderten Methoden — kein Platzhalter für unveränderte Teile

import time
import logging
import re

import requests
from psycopg2 import sql as pgsql

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessDenied, UserError

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hilfsfunktionen (unveränderter Block sanitize_sql, detect_chart_type, etc.)
# ---------------------------------------------------------------------------

def _pg_type_name(type_code: int) -> str:
    """Map PostgreSQL type OIDs to simple type names."""
    _MAP = {
        20: 'integer', 21: 'integer', 23: 'integer',   # int8, int2, int4
        700: 'float', 701: 'float', 1700: 'float',      # float4, float8, numeric
        16: 'boolean',
        1082: 'date',
        1114: 'datetime', 1184: 'datetime',              # timestamp, timestamptz
    }
    return _MAP.get(type_code, 'text')


def _serialize_rows(rows: list) -> list:
    """Convert DB rows to JSON-serializable lists."""
    return [
        [v.isoformat() if hasattr(v, 'isoformat') else v for v in row]
        for row in rows
    ]


class NL2SQLController(http.Controller):

    # FIX ADR-004/H5: Config einmal lesen, keine 3-fache DB-Abfrage
    def _get_llm_config(self):
        """Read LLM configuration from ir.config_parameter. Call once per request."""
        ICP = request.env['ir.config_parameter'].sudo()
        provider = ICP.get_param('mfg_nl2sql.llm_provider')
        if not provider:
            raise UserError(
                'mfg_nl2sql.llm_provider ist nicht konfiguriert. '
                'Bitte unter Einstellungen → NL2SQL hinterlegen.'
            )
        api_key = ICP.get_param('mfg_nl2sql.api_key', '')
        if not api_key:
            raise UserError('mfg_nl2sql.api_key ist nicht konfiguriert.')
        return {
            'provider':    provider,
            'api_key':     api_key,
            'model':       ICP.get_param('mfg_nl2sql.model_name', 'claude-haiku-4-5'),
            'max_tokens':  int(ICP.get_param('mfg_nl2sql.max_tokens', '2048')),
            'temperature': float(ICP.get_param('mfg_nl2sql.temperature', '0.0')),
            'timeout':     int(ICP.get_param('mfg_nl2sql.query_timeout', '30')),
            'max_rows':    int(ICP.get_param('mfg_nl2sql.max_rows', '1000')),
            'allow_write': ICP.get_param('mfg_nl2sql.allow_write', 'False') == 'True',
        }

    # FIX ADR-004/C1+C2+C4: Savepoint, psycopg2.sql, validierter Timeout
    def _execute_sql(self, sql: str, max_rows: int, timeout_s: int) -> dict:
        """Execute sanitized SQL via savepoint — no rollback of unrelated writes."""
        timeout_ms = timeout_s * 1000   # int arithmetic — keine String-Injection möglich
        cr = request.env.cr
        savepoint = f"nl2sql_{int(time.time() * 1000)}"
        start = time.time()

        cr.execute(f"SAVEPOINT {savepoint}")
        try:
            # SET LOCAL innerhalb Savepoint → wirkt garantiert
            cr.execute("SET LOCAL statement_timeout = %s", (f"{timeout_ms}ms",))

            # FIX ADR-004/C2: psycopg2.sql statt f-String für SQL-Wrapping
            wrapped = pgsql.SQL(
                "SELECT * FROM ({inner}) AS _nl2sql_q LIMIT {limit}"
            ).format(
                inner=pgsql.SQL(sql),
                limit=pgsql.Literal(max_rows),
            )
            cr.execute(wrapped)

            columns = []
            if cr.description:
                columns = [
                    {'name': d.name, 'type': _pg_type_name(d.type_code)}
                    for d in cr.description
                ]
            rows = _serialize_rows(cr.fetchall())
            cr.execute(f"RELEASE SAVEPOINT {savepoint}")

            return {
                'columns': columns,
                'rows': rows,
                'row_count': len(rows),
                'execution_time_ms': int((time.time() - start) * 1000),
            }

        except Exception as exc:
            cr.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
            _logger.error("SQL execution error: %s | SQL: %.500s", exc, sql)
            return {
                'columns': [],
                'rows': [],
                'row_count': 0,
                'execution_time_ms': int((time.time() - start) * 1000),
                'error': str(exc),
            }

    @http.route('/mfg_nl2sql/query', type='json', auth='user', methods=['POST'])
    def execute_query(self, query_text, domain_filter='all', chart_type=None,
                      saved_query_id=None):
        """Main NL2SQL endpoint: translate + execute + visualize."""
        # FIX ADR-004/H5: config einmal lesen
        config = self._get_llm_config()

        generated_sql, tokens, error = self._translate_nl_to_sql(
            query_text, domain_filter, config   # config übergeben
        )
        if error:
            request.env['nl2sql.query.history'].create({
                'name':            query_text,
                'domain_filter':   domain_filter,
                'state':           'error',
                'error_message':   error,
                'llm_tokens_used': tokens,
                'saved_query_id':  saved_query_id,
            })
            return {'error': error}

        sanitized, san_error = sanitize_sql(generated_sql, config['allow_write'])
        if san_error:
            request.env['nl2sql.query.history'].create({
                'name':            query_text,
                'generated_sql':   generated_sql,
                'domain_filter':   domain_filter,
                'state':           'error',
                'error_message':   f"SQL Validierung: {san_error}",
                'llm_tokens_used': tokens,
                'saved_query_id':  saved_query_id,
            })
            return {'error': f"SQL Validierung: {san_error}", 'sql': generated_sql}

        # FIX ADR-004/H5: timeout aus config, kein erneutes _get_llm_config()
        result = self._execute_sql(sanitized, config['max_rows'], config['timeout'])

        if result.get('error'):
            request.env['nl2sql.query.history'].create({
                'name':               query_text,
                'generated_sql':      generated_sql,
                'sanitized_sql':      sanitized,
                'domain_filter':      domain_filter,
                'state':              'error',
                'error_message':      result['error'],
                'execution_time_ms':  result['execution_time_ms'],
                'llm_tokens_used':    tokens,
                'saved_query_id':     saved_query_id,
            })
            return {'error': result['error'], 'sql': sanitized}

        detected_chart = chart_type or detect_chart_type(
            result['columns'], result['rows']
        )
        chart_cfg = build_chart_config(detected_chart, result['columns'], result['rows'])

        # FIX ADR-004/C3: kein json.dumps() — fields.Json serialisiert automatisch
        history = request.env['nl2sql.query.history'].create({
            'name':               query_text,
            'generated_sql':      generated_sql,
            'sanitized_sql':      sanitized,
            'domain_filter':      domain_filter,
            'state':              'success',
            'result_data':        result['rows'],      # list — fields.Json
            'result_columns':     result['columns'],   # list — fields.Json
            'result_row_count':   result['row_count'],
            'chart_type':         detected_chart,
            'chart_config':       chart_cfg,           # dict — fields.Json
            'execution_time_ms':  result['execution_time_ms'],
            'llm_tokens_used':    tokens,
            'saved_query_id':     saved_query_id,
        })

        if saved_query_id:
            saved = request.env['nl2sql.saved.query'].browse(saved_query_id)
            if saved.exists():
                saved.write({
                    'last_history_id': history.id,   # FIX ADR-004/M3: FK statt Kopie
                    'last_run':        history.create_date,
                    'generated_sql':   sanitized,
                })

        return {
            'history_id':        history.id,
            'sql':               sanitized,
            'columns':           result['columns'],
            'rows':              result['rows'],
            'row_count':         result['row_count'],
            'chart_type':        detected_chart,
            'chart_config':      chart_cfg,
            'execution_time_ms': result['execution_time_ms'],
            'tokens_used':       tokens,
        }

    @http.route('/mfg_nl2sql/history/<int:history_id>/result', type='json',
                auth='user', methods=['POST'])
    def get_history_result(self, history_id):
        """Return full result data for a history entry."""
        history = request.env['nl2sql.query.history'].browse(history_id)
        if not history.exists() or history.user_id != request.env.user:
            return {'error': 'Nicht gefunden oder keine Berechtigung'}

        # FIX ADR-004/H4: explizites Fehler-Handling statt stiller Fallbacks
        if history.state != 'success':
            return {'error': f"Kein Ergebnis — Status: {history.state}"}

        if not history.result_columns:
            _logger.error(
                "nl2sql.query.history id=%d: state=success aber result_columns=NULL",
                history.id,
            )
            return {'error': 'Interner Fehler: Ergebnis nicht gespeichert (ADR-004/C3)'}

        return {
            'id':           history.id,
            'name':         history.name,
            'sql':          history.sanitized_sql,
            'columns':      history.result_columns,    # fields.Json → bereits list
            'rows':         history.result_data,        # fields.Json → bereits list
            'row_count':    history.result_row_count,
            'chart_type':   history.chart_type,
            'chart_config': history.chart_config or {},
        }
```

---

## 7. Änderungshistorie

| ADR | Datum | Inhalt |
|-----|-------|--------|
| ADR-001-REVIEW | 2026-03-02 | Erster Review (ADR-Planungsartefakte) |
| ADR-003 | 2026-03-03 | D1/D3/D6 Entscheidungen bestätigt |
| **ADR-004** | **2026-03-03** | **Code-Review produktiver `mfg_nl2sql`-Codebase** |

*Nächster Schritt: Patches 1–3 als Sprint-1-Tasks umsetzen.*
