# -*- coding: utf-8 -*-
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class MachiningMachine(models.Model):
    _name = 'machining.machine'
    _description = 'CNC-Maschine / Bearbeitungszentrum'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(string='Maschinenbezeichnung', required=True, tracking=True)
    code = fields.Char(string='Maschinen-Nr.', required=True, index=True)

    machine_type = fields.Selection([
        ('lathe',          'Drehmaschine'),
        ('milling',        'Fräsmaschine'),
        ('machining_center', 'Bearbeitungszentrum (BAZ)'),
        ('grinding',       'Schleifmaschine'),
        ('drilling',       'Bohrmaschine'),
        ('edm',            'Erodiermaschine (EDM)'),
        ('laser',          'Laserbearbeitung'),
        ('measuring',      'Messmaschine (KMG)'),
    ], string='Maschinentyp', required=True, tracking=True)

    state = fields.Selection([
        ('operational',   'Betriebsbereit'),
        ('maintenance',   'In Wartung'),
        ('breakdown',     'Störung'),
        ('decommissioned','Stillgelegt'),
    ], string='Status', default='operational', required=True, tracking=True)

    manufacturer     = fields.Char(string='Hersteller')
    model            = fields.Char(string='Modell / Typ')
    year_built       = fields.Integer(string='Baujahr')
    axes             = fields.Integer(string='Achsanzahl', default=3)
    max_spindle_rpm  = fields.Integer(string='Max. Spindeldrehzahl (U/min)')
    travel_x_mm      = fields.Float(string='Verfahrweg X (mm)', digits=(8, 1))
    travel_y_mm      = fields.Float(string='Verfahrweg Y (mm)', digits=(8, 1))
    travel_z_mm      = fields.Float(string='Verfahrweg Z (mm)', digits=(8, 1))
    hall             = fields.Char(string='Halle')
    position         = fields.Char(string='Standplatz')
    last_maintenance = fields.Date(string='Letzte Wartung')
    next_maintenance = fields.Date(string='Nächste Wartung')
    notes            = fields.Text(string='Bemerkungen')
    active           = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_uniq', 'UNIQUE(code)', 'Die Maschinen-Nr. muss eindeutig sein.'),
    ]
