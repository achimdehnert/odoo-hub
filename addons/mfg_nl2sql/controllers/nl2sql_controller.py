# -*- coding: utf-8 -*-
"""NL2SQL Controller — API endpoints for the OWL dashboard.

Handles:
1. Natural language → SQL translation via LLM
2. SQL sanitization & execution
3. Result → chart-config mapping
4. Dashboard tile data refresh
"""
import json
import logging
import re
import time

import requests
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SQL safety
# ---------------------------------------------------------------------------
FORBIDDEN_KEYWORDS = {
    'DROP', 'TRUNCATE', 'ALTER', 'CREATE', 'GRANT', 'REVOKE',
    'COPY', 'EXECUTE', 'DO', 'IMPORT', 'LOAD', 'VACUUM',
    'CLUSTER', 'REINDEX', 'COMMENT', 'SECURITY', 'OWNER',
}
WRITE_KEYWORDS = {'INSERT', 'UPDATE', 'DELETE', 'MERGE', 'UPSERT'}


def sanitize_sql(sql, allow_write=False):
    """Validate and sanitize SQL for safe execution.

    Returns:
        tuple: (sanitized_sql, error_message)
            sanitized_sql is None if validation fails
    """
    if not sql or not sql.strip():
        return None, "Leere SQL-Abfrage"

    cleaned = sql.strip().rstrip(';')

    # Remove any comments
    cleaned = re.sub(r'--.*$', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
    cleaned = cleaned.strip()

    upper = cleaned.upper()

    # Check for forbidden DDL/admin keywords
    for kw in FORBIDDEN_KEYWORDS:
        pattern = rf'\b{kw}\b'
        if re.search(pattern, upper):
            return None, f"Verbotenes Schlüsselwort: {kw}"

    # Check write operations
    if not allow_write:
        for kw in WRITE_KEYWORDS:
            pattern = rf'\b{kw}\b'
            if re.search(pattern, upper):
                return None, f"Schreiboperation nicht erlaubt: {kw}"

    # Must start with SELECT or WITH
    if not re.match(r'^(SELECT|WITH)\b', upper):
        return None, "Nur SELECT/WITH Abfragen erlaubt"

    # Block multiple statements
    # Split by semicolons that are not inside strings
    statements = re.split(r';(?=(?:[^\']*\'[^\']*\')*[^\']*$)', cleaned)
    statements = [s.strip() for s in statements if s.strip()]
    if len(statements) > 1:
        return None, "Nur eine Abfrage gleichzeitig erlaubt"

    return cleaned, None


def detect_chart_type(columns, rows):
    """Auto-detect best chart type from result shape.

    Heuristics:
    - 1 row, 1 column → KPI card
    - 1 row, 2+ numeric columns → KPI multi-card
    - 2+ rows, 1 label + 1 numeric → bar chart
    - 2+ rows, 1 label + 2+ numeric → grouped bar
    - Date/time column + numeric → line chart
    - 1 label + 1 numeric, ≤8 rows → pie chart
    - Everything else → table
    """
    if not columns or not rows:
        return 'table'

    col_count = len(columns)
    row_count = len(rows)

    # Classify columns
    numeric_cols = []
    text_cols = []
    date_cols = []
    for col in columns:
        ctype = col.get('type', 'text')
        cname = col.get('name', '').lower()
        if ctype in ('integer', 'float', 'numeric', 'decimal', 'int4',
                      'int8', 'float4', 'float8', 'int', 'real',
                      'double precision', 'bigint', 'smallint'):
            numeric_cols.append(col)
        elif ctype in ('date', 'timestamp', 'timestamptz', 'datetime') or \
                any(k in cname for k in ('date', 'datum', 'monat', 'month',
                                          'year', 'jahr', 'zeit', 'time')):
            date_cols.append(col)
        else:
            text_cols.append(col)

    # Single value → KPI
    if row_count == 1 and col_count == 1:
        return 'kpi'

    # Single row, multiple numeric → KPI cards
    if row_count == 1 and len(numeric_cols) >= 2:
        return 'kpi'

    # Has date column + numeric → line chart
    if date_cols and numeric_cols:
        return 'line'

    # Label + numeric, small set → pie
    if len(text_cols) == 1 and len(numeric_cols) == 1 and row_count <= 8:
        return 'pie'

    # Label + numeric(s) → bar
    if text_cols and numeric_cols and row_count > 1:
        return 'bar'

    return 'table'


def build_chart_config(chart_type, columns, rows):
    """Build Chart.js-compatible configuration."""
    if not rows or not columns:
        return {}

    col_names = [c['name'] for c in columns]

    if chart_type == 'kpi':
        # Return raw values for KPI cards
        if len(rows) == 1:
            return {
                'type': 'kpi',
                'values': [
                    {'label': col_names[i], 'value': rows[0][i]}
                    for i in range(len(col_names))
                ],
            }

    # Identify label and value columns
    numeric_cols = []
    text_cols = []
    for i, col in enumerate(columns):
        ctype = col.get('type', 'text')
        if ctype in ('integer', 'float', 'numeric', 'decimal', 'int4',
                      'int8', 'float4', 'float8', 'int', 'real',
                      'double precision', 'bigint', 'smallint'):
            numeric_cols.append(i)
        else:
            text_cols.append(i)

    label_idx = text_cols[0] if text_cols else 0
    value_idxs = numeric_cols or [i for i in range(len(columns)) if i != label_idx]

    labels = [str(row[label_idx]) for row in rows]

    colors = [
        'rgba(59, 130, 246, 0.8)',   # blue
        'rgba(16, 185, 129, 0.8)',   # green
        'rgba(245, 158, 11, 0.8)',   # amber
        'rgba(239, 68, 68, 0.8)',    # red
        'rgba(139, 92, 246, 0.8)',   # purple
        'rgba(6, 182, 212, 0.8)',    # cyan
    ]

    datasets = []
    for di, vi in enumerate(value_idxs):
        datasets.append({
            'label': col_names[vi],
            'data': [row[vi] for row in rows],
            'backgroundColor': colors[di % len(colors)],
            'borderColor': colors[di % len(colors)].replace('0.8', '1'),
            'borderWidth': 1,
        })

    config = {
        'type': chart_type if chart_type in ('bar', 'line', 'pie') else 'bar',
        'data': {
            'labels': labels,
            'datasets': datasets,
        },
        'options': {
            'responsive': True,
            'maintainAspectRatio': False,
            'plugins': {
                'legend': {'display': len(datasets) > 1},
            },
        },
    }

    if chart_type == 'hbar':
        config['type'] = 'bar'
        config['options']['indexAxis'] = 'y'

    return config


class NL2SQLController(http.Controller):
    """HTTP controller for NL2SQL dashboard API."""

    # -------------------------------------------------------------------
    # LLM communication
    # -------------------------------------------------------------------
    def _get_llm_config(self):
        """Read LLM configuration from ir.config_parameter."""
        ICP = request.env['ir.config_parameter'].sudo()
        return {
            'provider': ICP.get_param('mfg_nl2sql.llm_provider', 'anthropic'),
            'api_key': ICP.get_param('mfg_nl2sql.api_key', ''),
            'model': ICP.get_param('mfg_nl2sql.model_name',
                                    'claude-sonnet-4-5-20250929'),
            'max_tokens': int(ICP.get_param('mfg_nl2sql.max_tokens', 2048)),
            'temperature': float(ICP.get_param('mfg_nl2sql.temperature', 0.0)),
            'timeout': int(ICP.get_param('mfg_nl2sql.query_timeout', 30)),
            'max_rows': int(ICP.get_param('mfg_nl2sql.max_rows', 1000)),
            'allow_write': ICP.get_param('mfg_nl2sql.allow_write', 'False')
                            == 'True',
        }

    def _build_system_prompt(self, schema_context):
        """Build the system prompt for NL2SQL translation."""
        return f"""Du bist ein SQL-Experte für PostgreSQL-Datenbanken.
Deine Aufgabe: Übersetze natürlichsprachliche Fragen in korrektes PostgreSQL SQL.

REGELN:
1. Generiere NUR eine einzige SELECT-Abfrage (oder WITH ... SELECT).
2. KEINE DDL (CREATE, ALTER, DROP), DML (INSERT, UPDATE, DELETE) oder Admin-Befehle.
3. Verwende LIMIT wenn sinnvoll (max 1000 Zeilen).
4. Benutze aussagekräftige Aliase für Spalten (deutsch).
5. Formatiere Zahlen sinnvoll (ROUND für Dezimalwerte).
6. Bei Datumsfiltern: Nutze CURRENT_DATE, INTERVAL etc.
7. Gib NUR das SQL zurück, keine Erklärungen, kein Markdown.

VERFÜGBARES SCHEMA:
{schema_context}

WICHTIG:
- Tabellen- und Spaltennamen exakt wie im Schema verwenden
- Bei Aggregationen immer GROUP BY verwenden
- Verwende JOINs um Fremdschlüssel aufzulösen
- Antworte NUR mit dem SQL-Statement, nichts anderes"""

    def _call_anthropic(self, config, system_prompt, user_query):
        """Call Anthropic Claude API."""
        resp = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key': config['api_key'],
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json',
            },
            json={
                'model': config['model'],
                'max_tokens': config['max_tokens'],
                'temperature': config['temperature'],
                'system': system_prompt,
                'messages': [{'role': 'user', 'content': user_query}],
            },
            timeout=config['timeout'],
        )
        resp.raise_for_status()
        data = resp.json()
        # Extract text from content blocks
        text_parts = [
            block['text']
            for block in data.get('content', [])
            if block.get('type') == 'text'
        ]
        sql = '\n'.join(text_parts).strip()
        # Strip markdown code fences if present
        sql = re.sub(r'^```(?:sql)?\s*', '', sql)
        sql = re.sub(r'\s*```$', '', sql)
        tokens = data.get('usage', {}).get('input_tokens', 0) + \
                 data.get('usage', {}).get('output_tokens', 0)
        return sql.strip(), tokens

    def _call_openai(self, config, system_prompt, user_query):
        """Call OpenAI API."""
        resp = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Authorization': f"Bearer {config['api_key']}",
                'Content-Type': 'application/json',
            },
            json={
                'model': config['model'],
                'max_tokens': config['max_tokens'],
                'temperature': config['temperature'],
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_query},
                ],
            },
            timeout=config['timeout'],
        )
        resp.raise_for_status()
        data = resp.json()
        sql = data['choices'][0]['message']['content'].strip()
        sql = re.sub(r'^```(?:sql)?\s*', '', sql)
        sql = re.sub(r'\s*```$', '', sql)
        tokens = data.get('usage', {}).get('total_tokens', 0)
        return sql.strip(), tokens

    def _translate_nl_to_sql(self, query_text, domain_filter='all'):
        """Full NL → SQL pipeline."""
        config = self._get_llm_config()
        if not config['api_key']:
            return None, 0, "API Key nicht konfiguriert. Bitte unter Einstellungen hinterlegen."

        # Build schema context
        SchemaTable = request.env['nl2sql.schema.table'].sudo()
        domain = None if domain_filter == 'all' else domain_filter
        schema_ctx = SchemaTable.get_schema_context(domain=domain)

        if not schema_ctx:
            return None, 0, "Kein Schema konfiguriert. Bitte Schema-Metadaten anlegen."

        system_prompt = self._build_system_prompt(schema_ctx)

        try:
            if config['provider'] == 'anthropic':
                sql, tokens = self._call_anthropic(config, system_prompt, query_text)
            elif config['provider'] == 'openai':
                sql, tokens = self._call_openai(config, system_prompt, query_text)
            else:
                return None, 0, f"Unbekannter Provider: {config['provider']}"

            return sql, tokens, None

        except requests.Timeout:
            return None, 0, "LLM API Timeout"
        except requests.HTTPError as exc:
            _logger.error("LLM API error: %s", exc.response.text if exc.response else exc)
            return None, 0, f"LLM API Fehler: {exc.response.status_code if exc.response else str(exc)}"
        except Exception as exc:
            _logger.exception("NL2SQL translation error")
            return None, 0, f"Übersetzungsfehler: {str(exc)}"

    def _execute_sql(self, sql, max_rows=1000):
        """Execute sanitized SQL and return structured results.

        Wrapped in a savepoint so a failing SQL statement does not roll back
        unrelated ORM writes on the shared request cursor (fixes ADR-004 C1).
        """
        config = self._get_llm_config()
        timeout_ms = config['timeout'] * 1000

        start = time.time()
        cr = request.env.cr
        try:
            with cr.savepoint():
                cr.execute(f"SET LOCAL statement_timeout = '{timeout_ms}'")
                limited_sql = f"SELECT * FROM ({sql}) AS _q LIMIT {max_rows}"
                cr.execute(limited_sql)

                columns = []
                if cr.description:
                    for desc in cr.description:
                        pg_type = desc.type_code
                        type_name = 'text'
                        if pg_type in (20, 21, 23):  # int8, int2, int4
                            type_name = 'integer'
                        elif pg_type in (700, 701, 1700):  # float4, float8, numeric
                            type_name = 'float'
                        elif pg_type == 16:  # bool
                            type_name = 'boolean'
                        elif pg_type == 1082:  # date
                            type_name = 'date'
                        elif pg_type in (1114, 1184):  # timestamp, timestamptz
                            type_name = 'datetime'
                        columns.append({'name': desc.name, 'type': type_name})

                rows = cr.fetchall()
                elapsed = int((time.time() - start) * 1000)

                serializable_rows = [
                    [v.isoformat() if hasattr(v, 'isoformat') else v for v in row]
                    for row in rows
                ]
                return {
                    'columns': columns,
                    'rows': serializable_rows,
                    'row_count': len(serializable_rows),
                    'execution_time_ms': elapsed,
                }

        except Exception as exc:
            elapsed = int((time.time() - start) * 1000)
            _logger.error("SQL execution error: %s\nSQL: %s", exc, sql)
            return {
                'columns': [],
                'rows': [],
                'row_count': 0,
                'execution_time_ms': elapsed,
                'error': str(exc),
            }

    # -------------------------------------------------------------------
    # HTTP Endpoints
    # -------------------------------------------------------------------
    @http.route('/mfg_nl2sql/query', type='json', auth='user', methods=['POST'])
    def execute_query(self, query_text, domain_filter='all', chart_type=None,
                      saved_query_id=None):
        """Main NL2SQL endpoint: translate + execute + visualize."""
        config = self._get_llm_config()

        # 1. Translate NL → SQL
        generated_sql, tokens, error = self._translate_nl_to_sql(
            query_text, domain_filter
        )

        if error:
            # Save failed attempt
            request.env['nl2sql.query.history'].create({
                'name': query_text,
                'domain_filter': domain_filter,
                'state': 'error',
                'error_message': error,
                'llm_tokens_used': tokens,
                'saved_query_id': saved_query_id,
            })
            return {'error': error}

        # 2. Sanitize SQL
        sanitized, san_error = sanitize_sql(generated_sql, config['allow_write'])
        if san_error:
            request.env['nl2sql.query.history'].create({
                'name': query_text,
                'generated_sql': generated_sql,
                'domain_filter': domain_filter,
                'state': 'error',
                'error_message': f"SQL Validierung: {san_error}",
                'llm_tokens_used': tokens,
                'saved_query_id': saved_query_id,
            })
            return {'error': f"SQL Validierung: {san_error}", 'sql': generated_sql}

        # 3. Execute SQL
        result = self._execute_sql(sanitized, config['max_rows'])

        if result.get('error'):
            request.env['nl2sql.query.history'].create({
                'name': query_text,
                'generated_sql': generated_sql,
                'sanitized_sql': sanitized,
                'domain_filter': domain_filter,
                'state': 'error',
                'error_message': result['error'],
                'execution_time_ms': result['execution_time_ms'],
                'llm_tokens_used': tokens,
                'saved_query_id': saved_query_id,
            })
            return {'error': result['error'], 'sql': sanitized}

        # 4. Detect chart type
        detected_chart = chart_type or detect_chart_type(
            result['columns'], result['rows']
        )

        # 5. Build chart config
        chart_config = build_chart_config(
            detected_chart, result['columns'], result['rows']
        )

        # 6. Save to history
        history = request.env['nl2sql.query.history'].create({
            'name': query_text,
            'generated_sql': generated_sql,
            'sanitized_sql': sanitized,
            'domain_filter': domain_filter,
            'state': 'success',
            'result_data': json.dumps(result['rows']),
            'result_columns': json.dumps(result['columns']),
            'result_row_count': result['row_count'],
            'chart_type': detected_chart,
            'chart_config': json.dumps(chart_config),
            'execution_time_ms': result['execution_time_ms'],
            'llm_tokens_used': tokens,
            'saved_query_id': saved_query_id,
        })

        # 7. Update saved query if applicable
        if saved_query_id:
            saved = request.env['nl2sql.saved.query'].browse(saved_query_id)
            if saved.exists():
                saved.write({
                    'last_result_data': json.dumps(result['rows'][:50]),
                    'last_run': history.create_date,
                    'generated_sql': sanitized,
                })

        return {
            'history_id': history.id,
            'sql': sanitized,
            'columns': result['columns'],
            'rows': result['rows'],
            'row_count': result['row_count'],
            'chart_type': detected_chart,
            'chart_config': chart_config,
            'execution_time_ms': result['execution_time_ms'],
            'tokens_used': tokens,
        }

    @http.route('/mfg_nl2sql/dashboard_data', type='json', auth='user',
                methods=['POST'])
    def get_dashboard_data(self):
        """Return initial dashboard data: tiles, config, recent history."""
        SavedQuery = request.env['nl2sql.saved.query']
        History = request.env['nl2sql.query.history']
        Config = request.env['nl2sql.dashboard.config']

        tiles = SavedQuery.get_dashboard_tiles()
        config = Config.get_or_create()

        recent = History.search([
            ('user_id', '=', request.env.user.id),
            ('state', '=', 'success'),
        ], limit=20, order='create_date desc')

        history = [{
            'id': h.id,
            'name': h.name,
            'chart_type': h.chart_type,
            'row_count': h.result_row_count,
            'execution_time_ms': h.execution_time_ms,
            'create_date': h.create_date.isoformat() if h.create_date else None,
            'is_pinned': h.is_pinned,
        } for h in recent]

        schema = request.env['nl2sql.schema.table'].sudo().get_schema_json()

        return {
            'tiles': tiles,
            'config': config,
            'history': history,
            'schema': schema,
            'user_name': request.env.user.name,
        }

    @http.route('/mfg_nl2sql/schema', type='json', auth='user',
                methods=['POST'])
    def get_schema(self, domain=None):
        """Return schema metadata for frontend display."""
        return request.env['nl2sql.schema.table'].sudo().get_schema_json(
            domain=domain
        )

    @http.route('/mfg_nl2sql/history', type='json', auth='user',
                methods=['POST'])
    def get_history(self, limit=20, offset=0):
        """Return paginated query history."""
        History = request.env['nl2sql.query.history']
        records = History.search(
            [('user_id', '=', request.env.user.id)],
            limit=limit,
            offset=offset,
            order='create_date desc',
        )
        return [{
            'id': h.id,
            'name': h.name,
            'state': h.state,
            'chart_type': h.chart_type,
            'row_count': h.result_row_count,
            'domain_filter': h.domain_filter,
            'execution_time_ms': h.execution_time_ms,
            'create_date': h.create_date.isoformat() if h.create_date else None,
            'is_pinned': h.is_pinned,
        } for h in records]

    @http.route('/mfg_nl2sql/history/<int:history_id>/result', type='json',
                auth='user', methods=['POST'])
    def get_history_result(self, history_id):
        """Return full result data for a history entry."""
        history = request.env['nl2sql.query.history'].browse(history_id)
        if not history.exists() or history.user_id != request.env.user:
            return {'error': 'Nicht gefunden'}
        return {
            'id': history.id,
            'name': history.name,
            'sql': history.sanitized_sql,
            'columns': json.loads(history.result_columns or '[]'),
            'rows': json.loads(history.result_data or '[]'),
            'row_count': history.result_row_count,
            'chart_type': history.chart_type,
            'chart_config': json.loads(history.chart_config or '{}'),
        }
