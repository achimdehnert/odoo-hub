# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class MachiningOrder(models.Model):
    _name = 'machining.order'
    _description = 'CNC-Fertigungsauftrag'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_planned desc, name desc'

    name = fields.Char(
        string='Auftragsnummer',
        required=True,
        copy=False,
        readonly=True,
        default='Neu',
    )
    state = fields.Selection([
        ('draft',         'Entwurf'),
        ('confirmed',     'Bestätigt'),
        ('in_production', 'In Fertigung'),
        ('quality_check', 'Qualitätsprüfung'),
        ('done',          'Abgeschlossen'),
        ('cancelled',     'Storniert'),
    ], string='Status', default='draft', required=True, tracking=True)

    partner_id = fields.Many2one('res.partner', string='Kunde', tracking=True)
    machine_id = fields.Many2one('machining.machine', string='Maschine', tracking=True)

    date_planned  = fields.Date(string='Geplantes Datum', tracking=True)
    date_start    = fields.Datetime(string='Fertigungsstart')
    date_done     = fields.Datetime(string='Fertigstellung')

    # Mengen
    planned_qty   = fields.Integer(string='Geplante Stückzahl', default=1)
    produced_qty  = fields.Integer(string='Produzierte Stückzahl', default=0)
    scrap_qty     = fields.Integer(string='Ausschuss (Stk)', default=0)

    # Material / Werkzeug
    material      = fields.Char(string='Werkstoff')
    drawing_no    = fields.Char(string='Zeichnungsnummer')
    cycle_time_min = fields.Float(string='Zykluszeit (min)', digits=(6, 1))

    notes         = fields.Text(string='Bemerkungen')
    is_demo_data  = fields.Boolean(
        string='Demo-Datensatz',
        default=False,
        index=True,
        help='Vom IIL-Seed-Engine generiert — in Produktivabfragen ausschließen.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Neu') == 'Neu':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('machining.order') or 'Neu'
                )
        return super().create(vals_list)

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_start(self):
        self.write({'state': 'in_production', 'date_start': fields.Datetime.now()})

    def action_done(self):
        self.write({'state': 'done', 'date_done': fields.Datetime.now()})

    def action_cancel(self):
        self.write({'state': 'cancelled'})
