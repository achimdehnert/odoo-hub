# -*- coding: utf-8 -*-
{
    "name": "IIL Dashboard Core",
    "version": "18.0.1.0.0",
    "category": "Technical",
    "summary": "Reusable OWL 2 plugin-registry dashboard engine for Odoo 18",
    "description": """
        IIL Dashboard Core
        ==================
        Generic, reusable foundation for feature-registry-driven dashboards.

        Provides:
        - iil_panels OWL registry (plugin pattern — modules register their own panels)
        - getPanelComponent() — resolves feature code → OWL component
        - PanelErrorBoundary — isolates crashing panels, prevents OWL-app freeze
        - IilDynamicDashboard — feature-list-driven grid container (model-agnostic)
        - IilDashboardMixin — base class for panel components with loading/error state

        Usage in consuming modules:
            1. Add "iil_dashboard_core" to depends
            2. Register panels:
               registry.category("iil_panels").add("my_code", {
                   component: MyPanel, label: "My Panel", sequence: 10
               });
            3. Mount IilDynamicDashboard as ir.actions.client with your feature-loader.

        This module has NO domain-specific code. It does not depend on
        casting_foundry, scm_manufacturing, mfg_management, or iil_configurator.
    """,
    "author": "IIL",
    "website": "https://github.com/achimdehnert/odoo-hub",
    "license": "LGPL-3",
    "depends": ["base", "web"],
    "data": [],
    "assets": {},
    "installable": True,
    "application": False,
    "auto_install": False,
}
