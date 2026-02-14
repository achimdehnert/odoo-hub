# -*- coding: utf-8 -*-
{
    "name": "SCM Manufacturing",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "summary": "Supply Chain Management with BOM, purchasing, production, warehousing, and delivery",
    "description": """
        SCM Manufacturing
        =================
        Full supply chain management:
        - Parts & BOM management
        - Supplier info & purchasing
        - Production orders & work steps
        - Warehouse & stock moves
        - Deliveries & incoming inspections
    """,
    "author": "IIL",
    "website": "",
    "license": "LGPL-3",
    "depends": ["base", "mail"],
    "data": [
        # Security
        "security/scm_security.xml",
        "security/ir.model.access.csv",
        # Data
        "data/scm_sequence.xml",
        # Views
        "views/scm_part_views.xml",
        "views/scm_bom_views.xml",
        "views/scm_supplier_views.xml",
        "views/scm_purchase_views.xml",
        "views/scm_production_views.xml",
        "views/scm_warehouse_views.xml",
        "views/scm_delivery_views.xml",
        "views/scm_inspection_views.xml",
        "views/scm_menus.xml",
    ],
    "demo": [
        "demo/demo_data.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
