# -*- coding: utf-8 -*-
"""Dashboard layout configuration per user."""
from odoo import api, fields, models


class DashboardConfig(models.Model):
    _name = 'nl2sql.dashboard.config'
    _description = 'NL2SQL Dashboard Configuration'
    _rec_name = 'user_id'

    user_id = fields.Many2one(
        'res.users',
        string='Benutzer',
        required=True,
        default=lambda self: self.env.user,
        index=True,
    )
    layout = fields.Text(
        string='Layout (JSON)',
        default='{}',
        help='Dashboard widget layout configuration as JSON',
    )
    default_domain = fields.Selection(
        selection=[
            ('all', 'Alle Bereiche'),
            ('supply_chain', 'Supply Chain'),
            ('production', 'Produktion'),
            ('quality', 'Qualität'),
        ],
        string='Standard-Domäne',
        default='all',
    )
    show_sql = fields.Boolean(
        string='SQL anzeigen',
        default=False,
        help='Show generated SQL in query results',
    )
    max_results = fields.Integer(
        string='Max. Ergebnisse',
        default=500,
        help='Maximum number of rows returned per query',
    )
    theme = fields.Selection(
        selection=[
            ('light', 'Hell'),
            ('dark', 'Dunkel'),
        ],
        string='Theme',
        default='light',
    )

    _sql_constraints = [
        ('unique_user', 'UNIQUE(user_id)', 'Each user can have only one dashboard config.'),
    ]

    @api.model
    def get_or_create(self):
        """Get current user's config, creating default if needed."""
        config = self.search([('user_id', '=', self.env.user.id)], limit=1)
        if not config:
            config = self.create({'user_id': self.env.user.id})
        return {
            'id': config.id,
            'default_domain': config.default_domain,
            'show_sql': config.show_sql,
            'max_results': config.max_results,
            'theme': config.theme,
        }
