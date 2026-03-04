/** @odoo-module **/
/**
 * Panel-Registry für das dynamische IIL-Dashboard.
 *
 * Jeder Feature-Code aus iil.product.feature wird hier auf eine
 * OWL-Komponente gemappt. Nicht registrierte Codes werden still übersprungen.
 *
 * Alle Panels registrieren sich selbst via:
 *   registry.category("iil_panels").add("code", { component, label, sequence })
 *
 * Diese Datei enthält keinen Fallback auf MfgDashboard mehr — MfgDashboard
 * ist eine vollständige Action-Komponente und darf nicht als Panel im Grid
 * gerendert werden (Crash durch doppelten rpc + fehlendem Action-Kontext).
 */

import { registry } from "@web/core/registry";

/**
 * getPanelComponent — sucht ausschließlich in iil_panels-Registry.
 * Gibt null zurück wenn kein Panel registriert → wird in DynamicDashboard gefiltert.
 */
export function getPanelComponent(featureCode) {
    const iilPanels = registry.category("iil_panels");
    if (iilPanels.contains(featureCode)) {
        return iilPanels.get(featureCode).component;
    }
    return null;
}

export const PANEL_REGISTRY = {};
