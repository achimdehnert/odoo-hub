/** @odoo-module **/
/**
 * Panel-Registry für das dynamische IIL-Dashboard.
 *
 * Jeder Feature-Code aus iil.product.feature wird hier auf eine
 * OWL-Komponente gemappt. Nicht registrierte Codes werden still übersprungen.
 *
 * Sprint 2: Nur casting + nl2sql registriert (bestehende Komponenten).
 * Sprint 3+: machining, mrp, stock, scm, quality, maintenance, sales, accounting.
 */

import { MfgDashboard } from "./mfg_dashboard";
import { registry } from "@web/core/registry";

/**
 * PANEL_REGISTRY — einzige Quelle der Wahrheit für Feature-Code → Komponente.
 *
 * Casting + NL2SQL → monolithischer MfgDashboard (Sprint 2 Baseline).
 * Machining → MachiningPanel aus iil_panels-Registry (wenn mfg_machining installiert).
 * Fallback: MfgDashboard wenn Panel nicht registriert.
 *
 * Andere Module registrieren ihre Panels selbst via:
 *   registry.category("iil_panels").add("code", { component, label, sequence })
 */
export function getPanelComponent(featureCode) {
    const iilPanels = registry.category("iil_panels");
    if (iilPanels.contains(featureCode)) {
        return iilPanels.get(featureCode).component;
    }
    return PANEL_REGISTRY_STATIC[featureCode] || null;
}

const PANEL_REGISTRY_STATIC = {
    casting:   MfgDashboard,
    nl2sql:    MfgDashboard,
    // machining: via iil_panels-Registry (mfg_machining)
    // quality:   via iil_panels-Registry (casting_foundry/quality_panel.js)
    // machines:  via iil_panels-Registry (casting_foundry/machines_panel.js)
    // stock:     via iil_panels-Registry (scm_manufacturing/stock_panel.js)
    // scm:       via iil_panels-Registry (scm_manufacturing/scm_panel.js)
};

export const PANEL_REGISTRY = PANEL_REGISTRY_STATIC;
