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

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { getPanelComponent } from "./panel_registry";

export class DynamicDashboard extends Component {
    static template = "mfg_management.DynamicDashboard";
    static components = {};

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
        // NOTE: Component classes must NOT be stored in useState() — OWL 2 wraps
        // state in a Proxy which corrupts class objects and breaks event binding.
        // Only store plain serializable data (codes, labels, icons) in state.
        this._panelComponents = {};
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

            const panels = [];
            for (const f of features) {
                const component = getPanelComponent(f.code);
                if (component) {
                    // Store component class outside of reactive state
                    this._panelComponents[f.code] = component;
                    panels.push({
                        code:  f.code,
                        label: f.label,
                        icon:  this.constructor.PANEL_ICONS[f.code]
                                || this.constructor.PANEL_ICONS.default,
                    });
                }
            }

            if (panels.length === 0) {
                this.state.fallback = true;
            } else {
                this.state.panels = panels;
            }
        } catch (_e) {
            this.state.fallback = true;
        } finally {
            this.state.loading = false;
        }
    }

    getPanelComponent(code) {
        return this._panelComponents[code] || null;
    }

    getNl2sqlComponent() {
        return this._panelComponents["nl2sql"] || null;
    }

    get dashboardTitle() {
        return "IIL Manufacturing Cockpit";
    }

    get FallbackComponent() {
        return null;
    }
}

registry.category("actions").add("mfg_management.Dashboard", DynamicDashboard, { force: true });
