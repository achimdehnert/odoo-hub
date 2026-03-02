# ADR-001: aifw NL2SQL Extension

| Feld | Wert |
|------|------|
| **Status** | Proposed |
| **Datum** | 2026-03-02 |
| **Package** | `aifw` v0.4.0 → v0.5.0 |
| **Autor** | Achim Dehnert |
| **Scope** | Neues Subpackage `aifw.nl2sql` |
| **Consumer** | `mfg_nl2sql` (Odoo), perspektivisch alle Django-Projekte |

---

## 1. Kontext & Problemstellung

### 1.1 Ausgangslage

`aifw` (v0.4.0) ist ein Django AI Services Framework mit DB-gesteuertem LLM-Routing via LiteLLM. Es bietet:

- **4 Django-Models:** `LLMProvider`, `LLMModel`, `AIActionType`, `AIUsageLog`
- **Service-Layer:** `completion()`, `sync_completion()`, `completion_stream()`, `completion_with_fallback()`
- **Schema:** `LLMResult` (mit `tool_calls`), `RenderedPromptProtocol`, `ToolCall`
- **Infrastruktur:** TTL-Config-Cache, Tenacity-Retry (nur transiente Fehler), Signal-basierte Cache-Invalidierung, Budget-Tracking pro `AIActionType`

### 1.2 Anforderung

Für das Odoo-Projekt `mfg_nl2sql` (SCM Manufacturing, Casting Foundry) wird eine NL2SQL-Fähigkeit benötigt: Natürlichsprachliche Fragen → SQL → Ergebnis → Visualisierung. Die 28 definierten Management-Use-Cases (UC-1.1 bis UC-6.3) sollen über ein NL-Interface abfragbar sein.

### 1.3 Warum aifw und nicht Vanna.ai / LangChain / Custom?

| Kriterium | Vanna.ai 2.0 | LangChain SQL | Custom Package | **aifw Extension** |
|-----------|-------------|---------------|----------------|-------------------|
| Provider-Routing | ❌ Hardcoded | ⚠️ Eigene Abstraktion | ❌ Neu bauen | ✅ Bestehendes DB-Routing |
| Budget/Cost-Tracking | ❌ Fehlt | ❌ Fehlt | ❌ Neu bauen | ✅ `AIUsageLog` vorhanden |
| Retry/Fallback | ❌ Fehlt | ⚠️ LangChain Retry | ❌ Neu bauen | ✅ `completion_with_fallback()` |
| Django-Integration | ❌ Flask-only UI | ❌ Framework-agnostisch | ⚠️ Manuell | ✅ Native Django-App |
| Streaming | ⚠️ Flask SSE | ⚠️ LangChain Callbacks | ❌ Neu bauen | ✅ `completion_stream()` |
| Multi-Tenant | ❌ Fehlt | ❌ Fehlt | ⚠️ Manuell | ✅ `tenant_id` in `AIUsageLog` |
| Dependency-Footprint | chromadb, flask, plotly | langchain, sqlalchemy | Minimal | ✅ Nur psycopg2 + pandas |
| Tool-Use Support | ❌ Fehlt | ⚠️ Agent-basiert | ❌ Neu bauen | ✅ `ToolCall` + `LLMResult.tool_calls` |

**Entscheidung: aifw erweitern** — 80% der benötigten Infrastruktur existiert bereits. NL2SQL als Subpackage `aifw.nl2sql` hält die Abhängigkeiten sauber und den Kern schlank.

---

## 2. Ist-Zustand: aifw v0.4.0

```
src/aifw/
├── __init__.py          # Public API: completion, sync_completion, LLMResult, ...
├── apps.py              # AifwConfig (signal wiring in ready())
├── admin.py             # 4 ModelAdmins
├── models.py            # LLMProvider, LLMModel, AIActionType, AIUsageLog
├── schema.py            # LLMResult, RenderedPromptProtocol, ToolCall
├── service.py           # completion(), streaming, fallback, config cache
└── signals.py           # Cache-Invalidierung bei Model-Änderungen
```

**Stärken für NL2SQL:**

1. `AIActionType(code="nl2sql")` → DB-gesteuert welches LLM-Modell für SQL-Generierung verwendet wird
2. `completion(action_code="nl2sql", messages=[...], tools=[...])` → Tool-Use für Chart-Empfehlungen
3. `AIUsageLog` mit `tenant_id`, `object_id`, `metadata` → Audit-Trail pro NL2SQL-Query
4. `completion_with_fallback()` → Claude → GPT-4o Fallback wenn Rate-Limit
5. `RenderedPromptProtocol` → Integration mit promptfw für komplexe Schema-Prompts
6. Budget-Tracking via `AIActionType.budget_per_day` → Cost-Control für NL2SQL

**Identifizierte Gaps (1 Minor):**

`LLMResult` hat bereits `tool_calls: list[ToolCall]` und `finish_reason` — das ist ausreichend. Kein Gap im Adapter wie bei `bfagent-llm`, da aifw LiteLLM nutzt, das Tool-Use nativ unterstützt.

---

## 3. Soll-Zustand: aifw v0.5.0

### 3.1 Neue Struktur

```
src/aifw/
├── __init__.py              # + nl2sql re-exports
├── apps.py                  # unverändert
├── admin.py                 # + SchemaSource Admin
├── models.py                # + SchemaSource Model
├── schema.py                # unverändert
├── service.py               # unverändert
├── signals.py               # unverändert
└── nl2sql/                  # ← NEU
    ├── __init__.py          # Public API
    ├── registry.py          # SchemaRegistry: lädt & cached DB-Metadaten
    ├── generator.py         # SQLGenerator: NL → SQL via aifw.completion()
    ├── validator.py         # SQLValidator: Safety (read-only, Injection)
    ├── executor.py          # SQLExecutor: SQL → DataFrame (read-only)
    └── formatter.py         # ResultFormatter: DataFrame → Chart-Config
```

### 3.2 Abhängigkeitsgraph

```
aifw.service.completion()
       ↑
aifw.nl2sql.generator ──→ aifw.nl2sql.registry (Schema-Context)
       ↓
aifw.nl2sql.validator ──→ aifw.nl2sql.executor ──→ aifw.nl2sql.formatter
```

Keine Rückwärts-Abhängigkeiten. `nl2sql` importiert `aifw.service` und `aifw.schema`, nicht umgekehrt. Der Kern bleibt unberührt.

### 3.3 Neue Dependencies

```toml
[project.optional-dependencies]
nl2sql = [
    "psycopg2-binary>=2.9",
    "pandas>=2.0",
]
```

Installation: `pip install "aifw[nl2sql]"` — wer NL2SQL nicht braucht, zahlt keinen Dependency-Overhead.

---

## 4. Technische Spezifikation

### 4.1 `models.py` — SchemaSource (neues Model)

```python
class SchemaSource(models.Model):
    """Registrierte Datenquellen für NL2SQL Schema-Context."""

    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    db_alias = models.CharField(
        max_length=100, default="default",
        help_text="Django DB-Alias (settings.DATABASES key)",
    )
    schema_xml = models.TextField(
        blank=True,
        help_text="Schema-Metadaten als XML (DDL, Beschreibungen, Beispiel-Queries)",
    )
    table_prefix = models.CharField(
        max_length=50, blank=True,
        help_text="Erlaubter Tabellen-Prefix (z.B. 'scm_' für SCM Manufacturing)",
    )
    max_rows = models.IntegerField(
        default=500,
        help_text="Max Zeilen pro Query-Ergebnis",
    )
    timeout_seconds = models.IntegerField(
        default=30,
        help_text="Query-Timeout in Sekunden",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "aifw"
        db_table = "aifw_schema_sources"
        verbose_name = "NL2SQL Schema Source"
        verbose_name_plural = "NL2SQL Schema Sources"

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"
```

### 4.2 `nl2sql/registry.py` — SchemaRegistry

```python
"""Schema Registry: Lädt und cached DB-Metadaten für NL2SQL-Prompts."""

from __future__ import annotations

import logging
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_registry_cache: dict[str, tuple["SchemaContext", float]] = {}
_CACHE_TTL: int = 300  # 5 Minuten


@dataclass(frozen=True)
class FieldInfo:
    """Feld-Metadaten für Prompt-Context."""
    name: str
    db_column: str
    field_type: str
    description: str
    selection_values: str = ""


@dataclass(frozen=True)
class TableInfo:
    """Tabellen-Metadaten für Prompt-Context."""
    model_name: str
    db_table: str
    description: str
    fields: tuple[FieldInfo, ...] = ()


@dataclass(frozen=True)
class SampleQuery:
    """Beispiel-Query für Few-Shot-Prompting."""
    question: str
    sql: str
    domain: str = ""


@dataclass
class SchemaContext:
    """Gesamter Schema-Context für eine SchemaSource."""
    tables: list[TableInfo] = field(default_factory=list)
    sample_queries: list[SampleQuery] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)

    def to_prompt_text(self) -> str:
        """Rendert Schema-Context als Text für System-Prompt."""
        parts = ["## Datenbank-Schema\n"]
        for table in self.tables:
            parts.append(f"### {table.db_table} — {table.description}")
            for f in table.fields:
                sel = f" [{f.selection_values}]" if f.selection_values else ""
                parts.append(f"  - {f.db_column} ({f.field_type}): {f.description}{sel}")
            parts.append("")

        if self.sample_queries:
            parts.append("## Beispiel-Queries\n")
            for sq in self.sample_queries:
                parts.append(f"Frage: {sq.question}")
                parts.append(f"SQL: {sq.sql}\n")

        return "\n".join(parts)


class SchemaRegistry:
    """Lädt SchemaSource-Einträge und baut SchemaContext auf."""

    @staticmethod
    def get_context(source_code: str) -> SchemaContext:
        """Lade SchemaContext für eine SchemaSource (mit TTL-Cache)."""
        now = time.monotonic()
        cached = _registry_cache.get(source_code)
        if cached and (now - cached[1]) < _CACHE_TTL:
            return cached[0]

        from aifw.models import SchemaSource
        source = SchemaSource.objects.filter(code=source_code, is_active=True).first()
        if not source or not source.schema_xml:
            return SchemaContext()

        ctx = SchemaRegistry._parse_xml(source.schema_xml)
        _registry_cache[source_code] = (ctx, now)
        return ctx

    @staticmethod
    def invalidate(source_code: str | None = None) -> None:
        if source_code:
            _registry_cache.pop(source_code, None)
        else:
            _registry_cache.clear()

    @staticmethod
    def _parse_xml(xml_text: str) -> SchemaContext:
        """Parst schema_scm_manufacturing.xml-Format in SchemaContext."""
        root = ET.fromstring(xml_text)
        tables, queries, domains = [], [], []

        for model_el in root.findall(".//model"):
            fields = []
            for f_el in model_el.findall("field"):
                fields.append(FieldInfo(
                    name=f_el.get("name", ""),
                    db_column=f_el.get("db_column", f_el.get("name", "")),
                    field_type=f_el.get("type", ""),
                    description=f_el.get("description", ""),
                    selection_values=f_el.get("selection", ""),
                ))
            tables.append(TableInfo(
                model_name=model_el.get("name", ""),
                db_table=model_el.get("table", ""),
                description=model_el.get("description", ""),
                fields=tuple(fields),
            ))

        for q_el in root.findall(".//sample_query"):
            queries.append(SampleQuery(
                question=q_el.findtext("question", ""),
                sql=q_el.findtext("sql", ""),
                domain=q_el.get("domain", ""),
            ))

        for d_el in root.findall(".//domain"):
            domains.append(d_el.get("name", ""))

        return SchemaContext(tables=tables, sample_queries=queries, domains=domains)
```

### 4.3 `nl2sql/generator.py` — SQLGenerator

```python
"""SQL Generator: Natural Language → SQL via aifw.completion()."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from aifw.schema import LLMResult
from aifw.nl2sql.registry import SchemaContext, SchemaRegistry

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """\
Du bist ein SQL-Experte für PostgreSQL. Du generierst ausschließlich
SELECT-Statements basierend auf folgendem Datenbank-Schema.

Regeln:
1. NUR SELECT-Statements — kein INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE
2. Verwende nur Tabellen und Spalten aus dem Schema unten
3. Nutze PostgreSQL-Syntax (z.B. DATE_TRUNC, EXTRACT, COALESCE)
4. Limitiere Ergebnisse auf maximal {max_rows} Zeilen
5. Kommentiere das SQL mit -- zur Erklärung
6. Antworte NUR mit dem SQL, kein umschließender Text

{schema_context}
"""

USER_PROMPT_TEMPLATE = """\
Frage: {question}

Generiere das passende SQL-Statement.
"""


@dataclass
class GenerationResult:
    """Ergebnis der SQL-Generierung."""
    success: bool
    sql: str = ""
    explanation: str = ""
    llm_result: LLMResult | None = None
    error: str = ""


class SQLGenerator:
    """Generiert SQL aus natürlichsprachlichen Fragen."""

    def __init__(
        self,
        action_code: str = "nl2sql",
        max_rows: int = 500,
    ):
        self.action_code = action_code
        self.max_rows = max_rows

    async def generate(
        self,
        question: str,
        source_code: str,
        conversation_history: list[dict[str, Any]] | None = None,
        user=None,
        **overrides,
    ) -> GenerationResult:
        """Generiert SQL für eine natürlichsprachliche Frage."""
        from aifw.service import completion

        schema_ctx = SchemaRegistry.get_context(source_code)
        if not schema_ctx.tables:
            return GenerationResult(
                success=False,
                error=f"Kein Schema gefunden für source_code='{source_code}'",
            )

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            max_rows=self.max_rows,
            schema_context=schema_ctx.to_prompt_text(),
        )

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
        ]

        # Few-Shot: Beispiel-Queries als User/Assistant-Turns
        for sq in schema_ctx.sample_queries[:5]:
            messages.append({"role": "user", "content": sq.question})
            messages.append({"role": "assistant", "content": sq.sql})

        # Conversation-History für Follow-up-Fragen
        if conversation_history:
            messages.extend(conversation_history)

        messages.append({"role": "user", "content": question})

        result: LLMResult = await completion(
            action_code=self.action_code,
            messages=messages,
            user=user,
            **overrides,
        )

        if not result.success:
            return GenerationResult(
                success=False,
                error=result.error,
                llm_result=result,
            )

        sql = self._extract_sql(result.content)
        return GenerationResult(
            success=True,
            sql=sql,
            explanation=result.content,
            llm_result=result,
        )

    @staticmethod
    def _extract_sql(content: str) -> str:
        """Extrahiert SQL aus LLM-Antwort (mit oder ohne Code-Block)."""
        # Code-Block-Format: ```sql ... ```
        match = re.search(r"```sql\s*(.*?)\s*```", content, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Fallback: Suche nach SELECT
        match = re.search(r"(SELECT\s.+)", content, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip().rstrip(";") + ";"

        return content.strip()
```

### 4.4 `nl2sql/validator.py` — SQLValidator

```python
"""SQL Validator: Safety-Checks bevor SQL ausgeführt wird."""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Verbotene SQL-Patterns
_FORBIDDEN_PATTERNS = [
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE)\b",
    r"\b(COPY|LOAD|IMPORT|EXPORT)\b",
    r"\b(pg_read_file|pg_ls_dir|pg_stat_file)\b",
    r"\bINTO\s+OUTFILE\b",
    r"\bEXEC(UTE)?\b",
    r";\s*(INSERT|UPDATE|DELETE|DROP)",  # Statement-Chaining
]

# Sensible Odoo-Tabellen (nie abfragbar)
_BLOCKED_TABLES = {
    "ir_config_parameter",
    "res_users",
    "ir_cron",
    "ir_mail_server",
    "auth_totp_device",
    "base_import_mapping",
}


@dataclass
class ValidationResult:
    """Ergebnis der SQL-Validierung."""
    is_valid: bool
    sql: str = ""
    error: str = ""
    warnings: list[str] | None = None


class SQLValidator:
    """Validiert generiertes SQL bevor es ausgeführt wird."""

    def __init__(
        self,
        allowed_prefixes: list[str] | None = None,
        blocked_tables: set[str] | None = None,
        max_query_length: int = 5000,
    ):
        self.allowed_prefixes = allowed_prefixes or []
        self.blocked_tables = blocked_tables or _BLOCKED_TABLES
        self.max_query_length = max_query_length

    def validate(self, sql: str) -> ValidationResult:
        """Validiert SQL-Statement gegen Safety-Regeln."""
        warnings = []

        # 1. Längenbegrenzung
        if len(sql) > self.max_query_length:
            return ValidationResult(
                is_valid=False,
                error=f"SQL überschreitet Maximallänge ({len(sql)} > {self.max_query_length})",
            )

        # 2. Muss mit SELECT beginnen
        normalized = sql.strip().upper()
        if not normalized.startswith("SELECT") and not normalized.startswith("WITH"):
            return ValidationResult(
                is_valid=False,
                error="Nur SELECT- und WITH-Statements erlaubt",
            )

        # 3. Verbotene Patterns
        for pattern in _FORBIDDEN_PATTERNS:
            if re.search(pattern, sql, re.IGNORECASE):
                return ValidationResult(
                    is_valid=False,
                    error=f"Verbotenes SQL-Pattern erkannt: {pattern}",
                )

        # 4. Blocked Tables
        sql_lower = sql.lower()
        for table in self.blocked_tables:
            if table in sql_lower:
                return ValidationResult(
                    is_valid=False,
                    error=f"Zugriff auf Tabelle '{table}' nicht erlaubt",
                )

        # 5. Tabellen-Prefix-Check (optional)
        if self.allowed_prefixes:
            tables = self._extract_table_names(sql)
            for table in tables:
                if not any(table.startswith(p) for p in self.allowed_prefixes):
                    return ValidationResult(
                        is_valid=False,
                        error=f"Tabelle '{table}' hat keinen erlaubten Prefix "
                              f"({', '.join(self.allowed_prefixes)})",
                    )

        # 6. Subquery-Warnung
        if sql_lower.count("select") > 3:
            warnings.append("Viele verschachtelte Subqueries — Performance prüfen")

        return ValidationResult(
            is_valid=True,
            sql=sql,
            warnings=warnings or None,
        )

    @staticmethod
    def _extract_table_names(sql: str) -> list[str]:
        """Extrahiert Tabellennamen aus FROM und JOIN Klauseln."""
        pattern = r"(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)"
        return [m.lower() for m in re.findall(pattern, sql, re.IGNORECASE)]
```

### 4.5 `nl2sql/executor.py` — SQLExecutor

```python
"""SQL Executor: Führt validiertes SQL read-only gegen PostgreSQL aus."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """Ergebnis einer SQL-Ausführung."""
    success: bool
    columns: list[str] = field(default_factory=list)
    rows: list[list[Any]] = field(default_factory=list)
    row_count: int = 0
    truncated: bool = False
    execution_ms: int = 0
    error: str = ""

    def to_dataframe(self):
        """Konvertiert zu pandas DataFrame (lazy import)."""
        import pandas as pd
        return pd.DataFrame(self.rows, columns=self.columns)


class SQLExecutor:
    """Führt validiertes SQL read-only aus."""

    def __init__(
        self,
        db_alias: str = "default",
        max_rows: int = 500,
        timeout_seconds: int = 30,
    ):
        self.db_alias = db_alias
        self.max_rows = max_rows
        self.timeout_seconds = timeout_seconds

    def execute(self, sql: str) -> QueryResult:
        """Führt SQL read-only aus mit Timeout und Row-Limit."""
        from django.db import connections

        start = time.perf_counter()

        try:
            connection = connections[self.db_alias]
            with connection.cursor() as cursor:
                # Read-only Transaction + Timeout
                cursor.execute("SET LOCAL statement_timeout = %s",
                               [self.timeout_seconds * 1000])
                cursor.execute("SET TRANSACTION READ ONLY")

                # SQL mit LIMIT-Absicherung
                safe_sql = self._ensure_limit(sql)
                cursor.execute(safe_sql)

                columns = [desc[0] for desc in cursor.description or []]
                rows = cursor.fetchmany(self.max_rows + 1)

                truncated = len(rows) > self.max_rows
                if truncated:
                    rows = rows[:self.max_rows]

                elapsed = int((time.perf_counter() - start) * 1000)

                return QueryResult(
                    success=True,
                    columns=columns,
                    rows=[list(row) for row in rows],
                    row_count=len(rows),
                    truncated=truncated,
                    execution_ms=elapsed,
                )

        except Exception as e:
            elapsed = int((time.perf_counter() - start) * 1000)
            logger.exception("SQL execution failed")
            return QueryResult(
                success=False,
                error=str(e),
                execution_ms=elapsed,
            )

    def _ensure_limit(self, sql: str) -> str:
        """Stellt sicher, dass ein LIMIT vorhanden ist."""
        if "LIMIT" not in sql.upper():
            sql = sql.rstrip().rstrip(";")
            sql = f"{sql}\nLIMIT {self.max_rows};"
        return sql
```

### 4.6 `nl2sql/formatter.py` — ResultFormatter

```python
"""Result Formatter: DataFrame → Chart-Empfehlung."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from aifw.nl2sql.executor import QueryResult

logger = logging.getLogger(__name__)


@dataclass
class ChartRecommendation:
    """Empfehlung für Chart-Typ basierend auf Datenstruktur."""
    chart_type: str            # bar, line, pie, table, heatmap, gauge
    x_column: str = ""
    y_columns: list[str] = field(default_factory=list)
    group_by: str = ""
    title: str = ""
    reasoning: str = ""


@dataclass
class FormattedResult:
    """Formatiertes Ergebnis mit Chart-Empfehlung."""
    query_result: QueryResult
    chart: ChartRecommendation | None = None
    summary: str = ""


class ResultFormatter:
    """Analysiert QueryResult und empfiehlt Visualisierung."""

    def format(self, result: QueryResult, question: str = "") -> FormattedResult:
        """Formatiert QueryResult mit Chart-Empfehlung."""
        if not result.success or not result.rows:
            return FormattedResult(
                query_result=result,
                summary="Keine Ergebnisse gefunden." if result.success else result.error,
            )

        chart = self._recommend_chart(result)
        summary = self._build_summary(result)

        return FormattedResult(
            query_result=result,
            chart=chart,
            summary=summary,
        )

    def _recommend_chart(self, result: QueryResult) -> ChartRecommendation:
        """Heuristik-basierte Chart-Empfehlung."""
        cols = result.columns
        rows = result.rows
        num_cols = self._detect_numeric_columns(cols, rows)
        date_cols = [c for c in cols if any(k in c.lower() for k in
                     ("date", "datum", "month", "monat", "week", "year", "jahr"))]
        cat_cols = [c for c in cols if c not in num_cols and c not in date_cols]

        # Einzelwert → Gauge/KPI
        if len(rows) == 1 and len(num_cols) == 1:
            return ChartRecommendation(
                chart_type="gauge",
                y_columns=num_cols,
                title=cols[0] if cols else "",
                reasoning="Einzelner numerischer Wert → KPI-Anzeige",
            )

        # Zeitreihe → Line Chart
        if date_cols and num_cols:
            return ChartRecommendation(
                chart_type="line",
                x_column=date_cols[0],
                y_columns=num_cols[:3],
                reasoning="Zeitliche Dimension + numerische Werte → Liniendiagramm",
            )

        # Kategorien + 1 Wert → Bar Chart
        if cat_cols and len(num_cols) >= 1 and len(rows) <= 20:
            return ChartRecommendation(
                chart_type="bar",
                x_column=cat_cols[0],
                y_columns=num_cols[:2],
                reasoning="Kategorien + numerische Werte → Balkendiagramm",
            )

        # Wenige Kategorien + 1 Prozentwert → Pie
        if cat_cols and len(num_cols) == 1 and len(rows) <= 8:
            return ChartRecommendation(
                chart_type="pie",
                x_column=cat_cols[0],
                y_columns=num_cols,
                reasoning="Wenige Kategorien + einzelner Wert → Kreisdiagramm",
            )

        # Default → Tabelle
        return ChartRecommendation(
            chart_type="table",
            reasoning="Keine eindeutige Visualisierung → Tabellenanzeige",
        )

    @staticmethod
    def _detect_numeric_columns(cols: list[str], rows: list[list]) -> list[str]:
        """Erkennt numerische Spalten anhand der Daten."""
        numeric = []
        if not rows:
            return numeric
        for i, col in enumerate(cols):
            values = [row[i] for row in rows[:10] if row[i] is not None]
            if values and all(isinstance(v, (int, float)) for v in values):
                numeric.append(col)
        return numeric

    @staticmethod
    def _build_summary(result: QueryResult) -> str:
        """Baut Text-Zusammenfassung."""
        if result.truncated:
            return f"{result.row_count} Zeilen (limitiert, weitere vorhanden)"
        return f"{result.row_count} Zeilen"
```

### 4.7 `nl2sql/__init__.py` — Public API

```python
"""
aifw.nl2sql — Natural Language to SQL Extension.

Erweitert aifw um NL2SQL-Fähigkeit:
  Frage (DE/EN) → SQL → Ergebnis → Chart-Empfehlung

Benötigt: pip install "aifw[nl2sql]"
"""

from aifw.nl2sql.registry import SchemaRegistry, SchemaContext
from aifw.nl2sql.generator import SQLGenerator, GenerationResult
from aifw.nl2sql.validator import SQLValidator, ValidationResult
from aifw.nl2sql.executor import SQLExecutor, QueryResult
from aifw.nl2sql.formatter import ResultFormatter, FormattedResult, ChartRecommendation


class NL2SQLEngine:
    """
    High-Level Facade: Frage → SQL → Ergebnis → Visualisierung.

    Usage::

        from aifw.nl2sql import NL2SQLEngine

        engine = NL2SQLEngine(source_code="scm_manufacturing")
        result = await engine.ask("Welcher Lieferant hatte die beste Liefertreue?")

        print(result.sql)                    # SELECT ...
        print(result.formatted.summary)      # "8 Zeilen"
        print(result.formatted.chart.type)   # "bar"
        df = result.query_result.to_dataframe()  # pandas DataFrame
    """

    def __init__(
        self,
        source_code: str,
        action_code: str = "nl2sql",
        allowed_prefixes: list[str] | None = None,
    ):
        from aifw.models import SchemaSource

        self.source_code = source_code
        source = SchemaSource.objects.filter(code=source_code, is_active=True).first()

        self.generator = SQLGenerator(action_code=action_code,
                                      max_rows=source.max_rows if source else 500)
        self.validator = SQLValidator(
            allowed_prefixes=allowed_prefixes or ([source.table_prefix] if source and source.table_prefix else []),
        )
        self.executor = SQLExecutor(
            db_alias=source.db_alias if source else "default",
            max_rows=source.max_rows if source else 500,
            timeout_seconds=source.timeout_seconds if source else 30,
        )
        self.formatter = ResultFormatter()

    async def ask(
        self,
        question: str,
        user=None,
        conversation_history: list | None = None,
        **overrides,
    ) -> "NL2SQLResult":
        """Kompletter NL2SQL-Pipeline: Frage → SQL → Ergebnis → Chart."""
        # 1. Generate SQL
        gen_result = await self.generator.generate(
            question=question,
            source_code=self.source_code,
            conversation_history=conversation_history,
            user=user,
            **overrides,
        )
        if not gen_result.success:
            return NL2SQLResult(success=False, error=gen_result.error,
                                generation=gen_result)

        # 2. Validate SQL
        val_result = self.validator.validate(gen_result.sql)
        if not val_result.is_valid:
            return NL2SQLResult(success=False, error=val_result.error,
                                generation=gen_result, validation=val_result)

        # 3. Execute SQL
        query_result = self.executor.execute(gen_result.sql)
        if not query_result.success:
            return NL2SQLResult(success=False, error=query_result.error,
                                generation=gen_result, validation=val_result,
                                query_result=query_result)

        # 4. Format & Chart-Empfehlung
        formatted = self.formatter.format(query_result, question)

        return NL2SQLResult(
            success=True,
            sql=gen_result.sql,
            generation=gen_result,
            validation=val_result,
            query_result=query_result,
            formatted=formatted,
        )


from dataclasses import dataclass

@dataclass
class NL2SQLResult:
    """Gesamtergebnis der NL2SQL-Pipeline."""
    success: bool
    sql: str = ""
    error: str = ""
    generation: GenerationResult | None = None
    validation: ValidationResult | None = None
    query_result: QueryResult | None = None
    formatted: FormattedResult | None = None


__all__ = [
    "NL2SQLEngine",
    "NL2SQLResult",
    "SchemaRegistry",
    "SchemaContext",
    "SQLGenerator",
    "GenerationResult",
    "SQLValidator",
    "ValidationResult",
    "SQLExecutor",
    "QueryResult",
    "ResultFormatter",
    "FormattedResult",
    "ChartRecommendation",
]
```

---

## 5. Integration: Odoo mfg_nl2sql

Der Odoo-Consumer nutzt `aifw.nl2sql` über einen minimalen Wrapper:

```python
# mfg_nl2sql/controllers/nl2sql_controller.py
from aifw.nl2sql import NL2SQLEngine

class NL2SQLController(http.Controller):

    @http.route("/nl2sql/ask", type="json", auth="user")
    def ask(self, question, source_code="scm_manufacturing"):
        engine = NL2SQLEngine(source_code=source_code)
        result = asyncio.run(engine.ask(question, user=request.env.user))
        return {
            "success": result.success,
            "sql": result.sql,
            "columns": result.query_result.columns if result.query_result else [],
            "rows": result.query_result.rows if result.query_result else [],
            "chart": vars(result.formatted.chart) if result.formatted and result.formatted.chart else None,
            "error": result.error,
        }
```

---

## 6. AIActionType-Konfiguration

Über Django Admin oder `init_aifw_config`:

```python
AIActionType.objects.create(
    code="nl2sql",
    name="NL2SQL Query Generation",
    description="Natürlichsprachliche Fragen in SQL übersetzen",
    default_model=claude_sonnet,      # Claude Sonnet 4.5 (günstig, schnell)
    fallback_model=gpt4o_mini,        # GPT-4o-mini als Fallback
    max_tokens=2000,
    temperature=0.1,                  # Niedrig für präzise SQL
    budget_per_day=Decimal("5.00"),   # $5/Tag Budget
)
```

---

## 7. Betrachtete Alternativen

### Option A: Vanna.ai als Dependency

**Verworfen.** Vanna bringt Flask, ChromaDB und Plotly als Dependencies mit (~150MB). Der RAG-Ansatz von Vanna ist mächtiger, aber für den Use Case mit vordefinierten Schema-XMLs Overkill. Vanna hat keine Django-Integration und kein DB-gesteuertes Model-Routing.

### Option B: Eigenes PyPI-Package `nl2sql`

**Verworfen.** Würde die gesamte LLM-Infrastruktur (Retry, Fallback, Streaming, Cost-Tracking) duplizieren oder als Dependency von `aifw` abhängen. Ein Subpackage vermeidet beides.

### Option C: LangChain SQL Agent

**Verworfen.** LangChain bringt massive Dependency-Chain mit und der Agent-Ansatz ist für deterministische SQL-Generierung überdimensioniert. Die Few-Shot-Prompt-Strategie mit Schema-Context ist einfacher und kontrollierbarer.

---

## 8. Migration & Rollout

| Tag | Aufgabe | Deliverable |
|-----|---------|-------------|
| **1** | `SchemaSource` Model + Migration | `0002_schema_source.py` |
| **1** | `nl2sql/` Subpackage (5 Module) | Funktionsfähige Pipeline |
| **2** | Unit-Tests (registry, validator, executor) | ≥90% Coverage auf nl2sql |
| **2** | Integration-Test mit SCM-Schema-XML | End-to-End NL → SQL → DataFrame |
| **3** | `pyproject.toml` Update (`[nl2sql]` Extra) | v0.5.0 Release |
| **3** | Odoo `mfg_nl2sql` Controller-Integration | Deployable auf Hetzner |

---

## 9. Risiken & Mitigierung

| Risiko | Wahrscheinlichkeit | Impact | Mitigierung |
|--------|-------------------|--------|-------------|
| SQL Injection via LLM | Mittel | Hoch | `SQLValidator` mit Whitelist-Prefixes + Blocklist |
| Teure Queries (Full Table Scan) | Mittel | Mittel | `SET LOCAL statement_timeout`, LIMIT-Absicherung |
| Halluzinierte Tabellennamen | Niedrig | Niedrig | Validator prüft gegen Schema-Registry |
| LLM generiert nicht-SQL | Niedrig | Niedrig | `_extract_sql()` + Validator fängt ab |
| Read-Only Verletzung | Sehr niedrig | Hoch | `SET TRANSACTION READ ONLY` auf DB-Ebene |

---

## 10. Akzeptanzkriterien

| # | Kriterium | Methode |
|---|-----------|---------|
| A1 | `NL2SQLEngine.ask("Liefertreue pro Lieferant")` → valides SQL | Integration-Test |
| A2 | Verbotenes SQL (DROP, DELETE) wird von Validator blockiert | Unit-Test |
| A3 | Ergebnis enthält Chart-Empfehlung (bar/line/pie/table) | Unit-Test |
| A4 | `AIUsageLog` wird pro NL2SQL-Query geschrieben | Integration-Test |
| A5 | Budget-Limit in `AIActionType` wirkt für nl2sql | Unit-Test |
| A6 | Query-Timeout nach konfigurierter Sekunden-Zahl | Integration-Test |
| A7 | `pip install aifw` ohne `[nl2sql]` importiert kein pandas | Import-Test |
