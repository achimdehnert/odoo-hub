{
    "name": "Schutztat Reporting",
    "version": "18.0.1.0.0",
    "category": "Safety/Reporting",
    "summary": "Risk assessment reporting synced from Django risk-hub",
    "description": """
        Odoo management module for Schutztat occupational safety platform.
        Syncs Assessment, Hazard, and ActionItem data from the Django risk-hub
        API for reporting, Kanban management, and approval workflows.

        See ADR-030 for architecture details.
    """,
    "author": "IIL",
    "website": "https://schutztat.iil.pet",
    "license": "LGPL-3",
    "depends": ["base"],
    "external_dependencies": {
        "python": ["requests"],
    },
    "data": [
        "security/ir.model.access.csv",
        "views/assessment_views.xml",
        "views/hazard_views.xml",
        "views/action_item_views.xml",
        "views/sync_log_views.xml",
        "views/menu_views.xml",
    ],
    "post_init_hook": "_post_init_hook",
    "installable": True,
    "application": True,
}
