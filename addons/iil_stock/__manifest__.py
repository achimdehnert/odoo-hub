# -*- coding: utf-8 -*-
{
    'name': 'IIL Stock Integration',
    'version': '18.0.1.0.0',
    'summary': 'IIL-spezifische Erweiterungen für Odoo Stock (Lagerverwaltung)',
    'author': 'IIL',
    'license': 'OPL-1',
    'category': 'Manufacturing',
    'depends': ['stock', 'iil_configurator'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
