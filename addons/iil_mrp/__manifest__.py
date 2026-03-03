# -*- coding: utf-8 -*-
{
    'name': 'IIL MRP Integration',
    'version': '18.0.1.0.0',
    'summary': 'IIL-spezifische Erweiterungen für Odoo MRP (Fertigungsplanung)',
    'author': 'IIL',
    'license': 'OPL-1',
    'category': 'Manufacturing',
    'depends': ['mrp', 'iil_configurator'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
