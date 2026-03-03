# -*- coding: utf-8 -*-
"""Query history for NL2SQL dashboard.

Stores every natural language query, the generated SQL,
execution results, and visualization metadata.
"""
import json
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class QueryHistory(models.Model):
    _name = 'nl2sql.query.history'
    _description = 'NL2SQL Query History'
    _order = 'create_date desc'
    _inherit = ['mail.thread']

    _sql_constraints = [
        ('error_needs_message',
         "CHECK(state != 'error' OR error_message IS NOT NULL)",
         'Fehlerhafte Abfragen müssen eine Fehlermeldung enthalten.'),
        ('row_count_non_negative',
         'CHECK(result_row_count IS NULL OR result_row_count >= 0)',
         'Zeilenanzahl muss >= 0 sein.'),
    ]

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
    result_data = fields.Json(
        string='Ergebnis (JSON)',
        readonly=True,
        help='Query results as JSON array',
    )
    result_columns = fields.Json(
        string='Spalten (JSON)',
        readonly=True,
        help='Column names and types as JSON',
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
        help='Auto-detected or manually chosen visualization type',
    )
    chart_config = fields.Json(
        string='Chart Config (JSON)',
        readonly=True,
        help='Chart.js configuration as JSON',
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
        help='Pinned queries appear at top of history',
    )
    saved_query_id = fields.Many2one(
        'nl2sql.saved.query',
        string='Gespeicherte Abfrage',
        readonly=True,
    )

    def action_rerun(self):
        """Re-execute the query with current data."""
        self.ensure_one()
        if not self.name:
            raise UserError("Keine Abfrage vorhanden.")
        # Trigger NL2SQL pipeline via controller
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
                'default_query_text': self.name,
                'default_generated_sql': self.generated_sql,
                'default_domain_filter': self.domain_filter,
                'default_chart_type': self.chart_type,
                'default_history_id': self.id,
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
