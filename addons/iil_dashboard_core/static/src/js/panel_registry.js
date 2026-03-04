/** @odoo-module **/
/**
 * IIL Dashboard Core — Panel Registry
 *
 * Single source of truth for feature-code → OWL component resolution.
 *
 * Consuming modules register their panels via:
 *   registry.category("iil_panels").add("my_code", {
 *       component: MyPanelComponent,
 *       label: "My Panel",      // optional, display label
 *       sequence: 10,           // optional, sort order
 *   });
 *
 * getPanelComponent(featureCode) returns the component or null.
 * DynamicDashboard filters out null entries — unknown codes are silently skipped.
 *
 * IMPORTANT: Never add full Action components (ir.actions.client targets) to
 * iil_panels. They lack the panel-grid context and will crash the OWL app.
 * Panel components must be self-contained widgets that receive props:
 *   { featureCode, featureConfig, featureLabel }
 */

import { registry } from "@web/core/registry";

/**
 * getPanelComponent
 * @param {string} featureCode — matches iil.product.feature.code in DB
 * @returns {Component|null}
 */
export function getPanelComponent(featureCode) {
    const iilPanels = registry.category("iil_panels");
    if (iilPanels.contains(featureCode)) {
        return iilPanels.get(featureCode).component;
    }
    return null;
}

/**
 * getPanelMeta — returns the full registry entry { component, label, sequence }
 * @param {string} featureCode
 * @returns {Object|null}
 */
export function getPanelMeta(featureCode) {
    const iilPanels = registry.category("iil_panels");
    if (iilPanels.contains(featureCode)) {
        return iilPanels.get(featureCode);
    }
    return null;
}
