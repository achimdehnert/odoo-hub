# -*- coding: utf-8 -*-
{
    'name': 'IIL Werkzeugmaschinen / CNC-Fertigung',
    'version': '18.0.1.0.0',
    'summary': 'Vertikale für Werkzeugmaschinen-Betrieb und CNC-Nachbearbeitung',
    'author': 'IIL',
    'license': 'OPL-1',
    'category': 'Manufacturing',
    'depends': ['base', 'mail', 'iil_configurator', 'mfg_management'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'views/mfg_machining_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'mfg_machining/static/src/js/machining_panel.js',
            'mfg_machining/static/src/xml/machining_panel.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}
