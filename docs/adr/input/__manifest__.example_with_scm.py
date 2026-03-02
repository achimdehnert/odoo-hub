# -*- coding: utf-8 -*-
{
    'name': 'NL2SQL Management Dashboard',
    'version': '18.0.1.0.0',
    'category': 'Manufacturing/Reporting',
    'summary': 'Natural Language SQL queries with visual dashboard for manufacturing data',
    'description': """
        NL2SQL Management Dashboard
        ===========================
        Query manufacturing, supply chain, production, and quality data
        using natural language. Results are automatically visualized as
        charts, tables, and KPI cards.

        Features:
        - Natural language to SQL translation via LLM API
        - Auto-visualization (bar, line, pie, table)
        - Schema introspection with safe query generation
        - Query history and saved queries
        - Configurable dashboard with KPI tiles
        - Multi-domain: Supply Chain, Production, Quality
    """,
    'author': 'Achim Dehnert',
    'website': 'https://github.com/achimdehnert/odoo-hub',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'mail',
        'scm_manufacturing',
    ],
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/schema_metadata.xml',
        'data/schema_scm_manufacturing.xml',
        'data/demo_data.xml',
        # Views
        'views/query_history_views.xml',
        'views/saved_query_views.xml',
        'views/schema_metadata_views.xml',
        'views/dashboard_config_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu.xml',
        'views/dashboard_action.xml',
        # Wizards
        'wizard/save_query_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'mfg_nl2sql/static/src/css/dashboard.css',
            'mfg_nl2sql/static/src/js/nl2sql_service.js',
            'mfg_nl2sql/static/src/js/dashboard.js',
            'mfg_nl2sql/static/src/js/query_input.js',
            'mfg_nl2sql/static/src/js/result_chart.js',
            'mfg_nl2sql/static/src/js/result_table.js',
            'mfg_nl2sql/static/src/js/kpi_card.js',
            'mfg_nl2sql/static/src/js/query_history.js',
            'mfg_nl2sql/static/src/xml/dashboard_templates.xml',
        ],
    },
    'demo': [
        'data/demo_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 5,
}
