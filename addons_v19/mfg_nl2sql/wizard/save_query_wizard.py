# -*- coding: utf-8 -*-
"""Wizard to save a query history entry as a reusable saved query."""
from odoo import fields, models


class SaveQueryWizard(models.TransientModel):
    _name = 'nl2sql.save.query.wizard'
    _description = 'Save NL2SQL Query'

    name = fields.Char(
        string='Name',
        required=True,
        help='Short descriptive name',
    )
    query_text = fields.Text(
        string='Abfrage',
        required=True,
        readonly=True,
    )
    generated_sql = fields.Text(
        string='SQL',
        readonly=True,
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
        default='bar',
    )
    is_dashboard_tile = fields.Boolean(
        string='Als Dashboard-Kachel',
        default=False,
    )
    is_shared = fields.Boolean(
        string='Mit Team teilen',
        default=False,
    )
    history_id = fields.Many2one(
        'nl2sql.query.history',
        string='History Entry',
    )

    def action_save(self):
        """Create saved query from wizard data."""
        self.ensure_one()
        saved = self.env['nl2sql.saved.query'].create({
            'name': self.name,
            'query_text': self.query_text,
            'generated_sql': self.generated_sql,
            'domain_filter': self.domain_filter,
            'chart_type': self.chart_type,
            'is_dashboard_tile': self.is_dashboard_tile,
            'is_shared': self.is_shared,
        })
        # Link history entry
        if self.history_id:
            self.history_id.saved_query_id = saved.id
        return {'type': 'ir.actions.act_window_close'}
