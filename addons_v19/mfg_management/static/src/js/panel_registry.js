/** @odoo-module **/
/**
 * Panel-Registry für mfg_management.
 *
 * getPanelComponent sucht ausschließlich in iil_panels-Registry.
 * Gibt null zurück wenn kein Panel registriert → DynamicDashboard filtert.
 *
 * HINWEIS: Odoo 18 kennt keine @module/-Import-Aliase außer @web/ und @odoo/.
 * Daher direkte Implementierung statt Re-Export aus iil_dashboard_core.
 */
import { registry } from "@web/core/registry";

export function getPanelComponent(featureCode) {
    const iilPanels = registry.category("iil_panels");
    if (iilPanels.contains(featureCode)) {
        return iilPanels.get(featureCode).component;
    }
    return null;
}

export function getPanelMeta(featureCode) {
    const iilPanels = registry.category("iil_panels");
    if (iilPanels.contains(featureCode)) {
        return iilPanels.get(featureCode);
    }
    return null;
}

export const PANEL_REGISTRY = {};
