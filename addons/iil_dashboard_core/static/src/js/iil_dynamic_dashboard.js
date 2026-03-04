/** @odoo-module **/
/**
 * IIL Dashboard Core — IilDynamicDashboard
 *
 * Generic, model-agnostic dashboard container driven by a feature list.
 *
 * The component expects a "featureLoader" prop — a function that returns
 * a Promise resolving to an array of { code, label, config } objects.
 * It maps each code via getPanelComponent() and renders the matched panels
 * in a responsive grid, each wrapped in PanelErrorBoundary.
 *
 * If no featureLoader prop is provided, it defaults to loading features
 * from iil.product.feature.get_active_features (iil_configurator).
 *
 * Consuming modules register an ir.actions.client pointing to a subclass:
 *
 *   export class MyDashboard extends IilDynamicDashboard {
 *       static template = "my_module.MyDashboard";  // extends base template
 *       get fallbackComponent() { return MyStaticDashboard; }
 *   }
 *   registry.category("actions").add("my_module.Dashboard", MyDashboard);
 *
 * Or use the base component directly if no customisation is needed:
 *   registry.category("actions").add("my_module.Dashboard", IilDynamicDashboard);
 *
 * Panel icon mapping is configurable via PANEL_ICONS static property.
 */

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { getPanelComponent } from "./panel_registry";
import { PanelErrorBoundary } from "./panel_error_boundary";

export class IilDynamicDashboard extends Component {
    static template = "iil_dashboard_core.IilDynamicDashboard";
    static components = { PanelErrorBoundary };
    static props = {
        featureLoader: { type: Function, optional: true },
        title: { type: String, optional: true },
        fallbackComponent: { type: Function, optional: true },
    };

    /**
     * Icon mapping: feature code → FontAwesome icon name (without "fa-").
     * Consuming modules can override by subclassing and redefining PANEL_ICONS.
     */
    static PANEL_ICONS = {
        casting:   "fire",
        machining: "cogs",
        machines:  "tachometer",
        quality:   "check-circle",
        stock:     "cubes",
        scm:       "truck",
        mrp:       "sitemap",
        nl2sql:    "magic",
        sales:     "shopping-cart",
        accounting:"calculator",
        maintenance:"wrench",
        default:   "bar-chart",
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
            let features;
            if (this.props.featureLoader) {
                features = await this.props.featureLoader();
            } else {
                features = await this.orm.call(
                    "iil.product.feature",
                    "get_active_features",
                    []
                );
            }

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
        return this.props.title || "Dashboard";
    }

    /**
     * Override in subclass to provide a custom fallback component.
     * Must be an OWL Component class.
     */
    get fallbackComponent() {
        return this.props.fallbackComponent || null;
    }
}
