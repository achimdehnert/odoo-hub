# -*- coding: utf-8 -*-
{
    'name': 'IIL Produktkonfigurator',
    'version': '18.0.1.0.0',
    'summary': 'Branchenspezifischer Onboarding-Wizard mit Demo-Daten-Generator',
    'author': 'IIL',
    'license': 'OPL-1',
    'category': 'Manufacturing',
    'depends': ['base', 'mail', 'casting_foundry'],
    # mfg_nl2sql optional — kein hard depends, Schema-Daten via post_init_hook
    'data': [
        'security/iil_security.xml',
        'security/ir.model.access.csv',
        'data/feature_defaults.xml',
        'views/iil_product_feature_views.xml',
        'views/iil_configurator_wizard_views.xml',
        'views/iil_menus.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'assets': {
        'web.assets_backend': [
            'iil_configurator/static/src/js/configurator_wizard.js',
            'iil_configurator/static/src/xml/configurator_wizard.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}
