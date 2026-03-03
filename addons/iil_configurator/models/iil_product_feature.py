# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class IilProductFeature(models.Model):
    _name = 'iil.product.feature'
    _description = 'IIL Produkt-Feature'
    _order = 'sequence, code'

    code = fields.Char(
        string='Code',
        required=True,
        index=True,
        help='Technischer Bezeichner (z.B. casting, mrp, nl2sql)',
    )
    label = fields.Char(
        string='Bezeichnung',
        required=True,
    )
    is_active = fields.Boolean(
        string='Aktiv',
        default=True,
        index=True,
        help='Nur aktive Features werden im OWL-Dashboard gerendert.',
    )
    sequence = fields.Integer(
        string='Reihenfolge',
        default=10,
    )
    config = fields.Json(
        string='Konfiguration',
        default=dict,
        help='Optionale JSON-Konfiguration (Farbe, Provider, etc.)',
    )
    depends_module = fields.Char(
        string='Odoo-Modul',
        help='Odoo-Modulname — wird vor Panel-Render auf Installation geprüft.',
    )

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Feature-Code muss eindeutig sein.'),
    ]

    @api.model
    def get_active_features(self):
        """RPC-Endpoint für OWL-Dashboard.

        Gibt alle aktiven Features sortiert nach sequence zurück.

        ACL: ir.model.access.csv muss 'read'-Recht auf iil.product.feature
        für base.group_user enthalten, sonst Access Denied beim Dashboard-Load.
        """
        features = self.search([('is_active', '=', True)], order='sequence, code')
        return [{
            'code':     f.code,
            'label':    f.label,
            'sequence': f.sequence,
            'config':   f.config or {},
        } for f in features]
