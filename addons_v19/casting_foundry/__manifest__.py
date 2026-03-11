# -*- coding: utf-8 -*-
{
    "name": "Casting & Foundry Management",
    "version": "19.0.1.0.0",
    "category": "Manufacturing",
    "summary": "Industrial casting and foundry management with molds, materials, and quality control",
    "description": """
        Casting & Foundry Management
        ============================
        Manage your foundry operations:
        - Materials (alloys, metals, compounds)
        - Molds and tooling
        - Casting orders and production
        - Quality checks and defect tracking
        - Machines and work centers
    """,
    "author": "IIL",
    "website": "",
    "license": "LGPL-3",
    "depends": ["base", "mail", "product"],
    "data": [
        # Security
        "security/casting_security.xml",
        "security/ir.model.access.csv",
        # Data
        "data/casting_sequence.xml",
        "data/casting_data.xml",
        # Views
        "views/casting_alloy_views.xml",
        "views/casting_material_views.xml",
        "views/casting_mold_views.xml",
        "views/casting_machine_views.xml",
        "views/casting_order_views.xml",
        "views/casting_quality_views.xml",
        "views/casting_defect_views.xml",
        "views/casting_menus.xml",
    ],
    "demo": [
        "demo/demo_materials.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "casting_foundry/static/src/js/casting_panel.js",
            "casting_foundry/static/src/xml/casting_panel.xml",
            "casting_foundry/static/src/js/quality_panel.js",
            "casting_foundry/static/src/xml/quality_panel.xml",
            "casting_foundry/static/src/js/machines_panel.js",
            "casting_foundry/static/src/xml/machines_panel.xml",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}
