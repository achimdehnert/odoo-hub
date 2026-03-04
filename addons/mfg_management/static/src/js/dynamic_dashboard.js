/** @odoo-module **/
/**
 * DynamicDashboard — MFG-spezifischer Dashboard-Container.
 *
 * Subklasse von IilDynamicDashboard (iil_dashboard_core).
 * Steuert Features aus iil.product.feature (iil_configurator).
 * Fällt auf MfgDashboard zurück wenn keine Features konfiguriert sind.
 */

import { registry } from "@web/core/registry";
import { IilDynamicDashboard } from "@iil_dashboard_core/js/iil_dynamic_dashboard";
import { MfgDashboard } from "./mfg_dashboard";

export class DynamicDashboard extends IilDynamicDashboard {
    static template = "mfg_management.DynamicDashboard";

    get dashboardTitle() {
        return "IIL Manufacturing Cockpit";
    }

    get fallbackComponent() {
        return MfgDashboard;
    }
}

registry.category("actions").add("mfg_management.Dashboard", DynamicDashboard, { force: true });
