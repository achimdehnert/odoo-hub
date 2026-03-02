# -*- coding: utf-8 -*-
"""Saved queries for NL2SQL dashboard.

Named, reusable queries that can be shared across users
and pinned to the dashboard as KPI tiles.
"""
from odoo import api, fields, models


class SavedQuery(models.Model):
    _name = 'nl2sql.saved.query'
    _description = 'NL2SQL Saved Query'
    _order = 'sequence, name'

    name = fields.Char(
        string='Name',
        required=True,
        help='Short descriptive name for this query',
    )
    query_text = fields.Text(
        string='Abfrage (NL)',
        required=True,
        help='Natural language query text',
    )
    generated_sql = fields.Text(
        string='SQL (cached)',
        help='Cached SQL from last execution',
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
        string='Dashboard-Kachel',
        default=False,
        help='Show as tile on main dashboard',
    )
    tile_color = fields.Selection(
        selection=[
            ('blue', 'Blau'),
            ('green', 'Grün'),
            ('orange', 'Orange'),
            ('red', 'Rot'),
            ('purple', 'Violett'),
            ('teal', 'Teal'),
        ],
        string='Kachel-Farbe',
        default='blue',
    )
    tile_icon = fields.Char(
        string='Kachel-Icon',
        default='fa-bar-chart',
        help='Font Awesome icon class (e.g. fa-bar-chart)',
    )
    refresh_interval = fields.Selection(
        selection=[
            ('0', 'Manuell'),
            ('60', '1 Minute'),
            ('300', '5 Minuten'),
            ('900', '15 Minuten'),
            ('3600', '1 Stunde'),
        ],
        string='Auto-Refresh',
        default='0',
    )
    is_shared = fields.Boolean(
        string='Geteilt',
        default=False,
        help='Shared queries are visible to all users',
    )
    user_id = fields.Many2one(
        'res.users',
        string='Ersteller',
        default=lambda self: self.env.user,
        readonly=True,
    )
    sequence = fields.Integer(
        string='Reihenfolge',
        default=10,
    )
    history_ids = fields.One2many(
        'nl2sql.query.history',
        'saved_query_id',
        string='Ausführungsverlauf',
    )
    last_result_data = fields.Text(
        string='Letztes Ergebnis (JSON)',
        readonly=True,
    )
    last_run = fields.Datetime(
        string='Letzte Ausführung',
        readonly=True,
    )

    def action_run(self):
        """Execute this saved query."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'mfg_nl2sql.dashboard',
            'params': {
                'run_saved_query': self.id,
                'query_text': self.query_text,
                'domain': self.domain_filter,
            },
        }

    @api.model
    def get_dashboard_tiles(self):
        """Return saved queries configured as dashboard tiles."""
        domain = [('is_dashboard_tile', '=', True)]
        # Include shared tiles + user's own tiles
        domain = [
            ('is_dashboard_tile', '=', True),
            '|',
            ('is_shared', '=', True),
            ('user_id', '=', self.env.user.id),
        ]
        tiles = self.search(domain, order='sequence')
        return [{
            'id': t.id,
            'name': t.name,
            'query_text': t.query_text,
            'domain_filter': t.domain_filter,
            'chart_type': t.chart_type,
            'tile_color': t.tile_color,
            'tile_icon': t.tile_icon,
            'refresh_interval': int(t.refresh_interval),
            'last_result_data': t.last_result_data,
            'last_run': t.last_run and t.last_run.isoformat() or None,
        } for t in tiles]
