/** @odoo-module **/
/**
 * DynamicDashboard — Feature-Registry-gesteuerter Dashboard-Container.
 *
 * Liest aktive Features aus iil.product.feature via RPC und rendert
 * nur die konfigurierten Panels. Fällt graceful zurück auf den
 * statischen MfgDashboard wenn iil_configurator nicht installiert ist.
 *
 * Self-contained: keine Cross-Modul-JS-Imports.
 * (Odoo 18 Bundler transformiert relative Imports zu @modul/-Namespace
 * und kann diese dann nicht über Modulgrenzen auflösen.)
 */

import { Component, useState, onWillStart, onError } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { getPanelComponent } from "./panel_registry";
import { MfgDashboard } from "./mfg_dashboard";

/**
 * PanelErrorBoundary — fängt Render-Fehler einzelner Panels ab.
 * Ein crashendes Panel zeigt eine Fehlermeldung statt die gesamte
 * OWL-App einzufrieren und Navigation zu blockieren.
 */
export class PanelErrorBoundary extends Component {
    static template = "mfg_management.PanelErrorBoundary";
    static props = ["*"];

    setup() {
        this.state = useState({ hasError: false, errorMsg: "" });
        onError((err) => {
            console.error("[IIL Panel Error]", err);
            this.state.hasError = true;
            this.state.errorMsg = err && err.message ? err.message : String(err);
        });
    }
}

export class DynamicDashboard extends Component {
    static template = "mfg_management.DynamicDashboard";
    static components = { PanelErrorBoundary };

    static PANEL_ICONS = {
        casting:    "fire",
        machining:  "cogs",
        machines:   "tachometer",
        quality:    "check-circle",
        stock:      "cubes",
        scm:        "truck",
        mrp:        "sitemap",
        nl2sql:     "magic",
        default:    "bar-chart",
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            panels: [],
            loading: true,
            fallback: false,
        });
        onWillStart(async () => {
            await this._loadFeatures();
        });
    }

    async _loadFeatures() {
        try {
            const features = await this.orm.call(
                "iil.product.feature",
                "get_active_features",
                []
            );

            if (!features || features.length === 0) {
                this.state.fallback = true;
                return;
            }

            this.state.panels = features
                .map(f => ({
                    code:      f.code,
                    label:     f.label,
                    config:    f.config || {},
                    component: getPanelComponent(f.code),
                    icon:      this.constructor.PANEL_ICONS[f.code]
                                || this.constructor.PANEL_ICONS.default,
                }))
                .filter(p => p.component !== null);

            if (this.state.panels.length === 0) {
                this.state.fallback = true;
            }
        } catch (_e) {
            this.state.fallback = true;
        } finally {
            this.state.loading = false;
        }
    }

    get dashboardTitle() {
        return "IIL Manufacturing Cockpit";
    }

    get FallbackComponent() {
        return MfgDashboard;
    }
}

registry.category("actions").add("mfg_management.Dashboard", DynamicDashboard, { force: true });
