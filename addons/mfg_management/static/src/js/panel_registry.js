/** @odoo-module **/
/**
 * Panel-Registry für mfg_management — delegiert an iil_dashboard_core.
 * Re-Export für Rückwärtskompatibilität mit anderen Modulen die
 * aus mfg_management importieren.
 */
export { getPanelComponent, getPanelMeta } from "@iil_dashboard_core/js/panel_registry";

export const PANEL_REGISTRY = {};
