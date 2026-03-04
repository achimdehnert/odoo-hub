# -*- coding: utf-8 -*-
{
    "name": "Manufacturing Management Frontend",
    "version": "18.0.1.2.0",
    "category": "Manufacturing",
    "summary": "Unified management dashboard for Production (Casting) and Supply Chain",
    "description": """
        Manufacturing Management Frontend
        ==================================
        Cross-module management cockpit for:
        - Production Kanban Board (casting.order + scm.production.order)
        - Machine Status Board (live operational state)
        - SCM Overview (purchasing pipeline, deliveries, warehouse KPIs)
        - Unified KPI tiles combining both modules
    """,
    "author": "IIL",
    "website": "https://github.com/achimdehnert/odoo-hub",
    "license": "LGPL-3",
    "depends": [
        "base",
        "web",
        "mail",
        "iil_dashboard_core",
        "casting_foundry",
        "scm_manufacturing",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/dashboard_action.xml",
        "views/menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mfg_management/static/src/css/dashboard.css",
            "mfg_management/static/src/xml/dashboard.xml",
            "mfg_management/static/src/js/kpi_card.js",
            "mfg_management/static/src/js/mfg_dashboard.js",
            "mfg_management/static/src/js/production_board.js",
            "mfg_management/static/src/js/machine_status.js",
            "mfg_management/static/src/js/scm_overview.js",
            "mfg_management/static/src/js/panel_registry.js",
            "mfg_management/static/src/js/dynamic_dashboard.js",
            "mfg_management/static/src/js/nl2sql_query_bar.js",
            "mfg_management/static/src/xml/nl2sql_query_bar.xml",
            "mfg_management/static/src/js/nl2sql_panel.js",
            "mfg_management/static/src/xml/nl2sql_panel.xml",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
    "sequence": 4,
}
