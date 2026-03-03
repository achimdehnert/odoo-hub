# -*- coding: utf-8 -*-
{
    'name': 'IIL Werkzeugmaschinen / CNC-Fertigung',
    'version': '18.0.1.0.0',
    'summary': 'Vertikale für Werkzeugmaschinen-Betrieb und CNC-Nachbearbeitung',
    'author': 'IIL',
    'license': 'OPL-1',
    'category': 'Manufacturing',
    'depends': ['base', 'mail', 'iil_configurator'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'views/mfg_machining_menus.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
