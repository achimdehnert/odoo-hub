/** @odoo-module **/
/**
 * DynamicDashboard — Feature-Registry-gesteuerter Dashboard-Container.
 *
 * Liest aktive Features aus iil.product.feature via RPC und rendert
 * nur die konfigurierten Panels. Fällt graceful zurück auf den
 * statischen MfgDashboard wenn iil_configurator nicht installiert ist.
 *
 * OWL-18-konform: useService("orm") statt this.env.services.orm.
 */

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { PANEL_REGISTRY } from "./panel_registry";
import { MfgDashboard } from "./mfg_dashboard";

export class DynamicDashboard extends Component {
    static template = "mfg_management.DynamicDashboard";

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
                // Keine Features konfiguriert → statischen Dashboard zeigen
                this.state.fallback = true;
            } else {
                this.state.panels = features
                    .filter(f => PANEL_REGISTRY[f.code])
                    .map(f => ({
                        code:      f.code,
                        label:     f.label,
                        config:    f.config || {},
                        component: PANEL_REGISTRY[f.code],
                    }));

                // Keine registrierten Panels gefunden → Fallback
                if (this.state.panels.length === 0) {
                    this.state.fallback = true;
                }
            }
        } catch (e) {
            // iil_configurator nicht installiert oder Access Denied → Fallback
            this.state.fallback = true;
        } finally {
            this.state.loading = false;
        }
    }

    get FallbackComponent() {
        return MfgDashboard;
    }
}

// Als "mfg_management.Dashboard" registrieren — überschreibt den bisherigen Eintrag.
// Bestehender MfgDashboard bleibt als Fallback-Komponente erhalten.
registry.category("actions").add("mfg_management.Dashboard", DynamicDashboard, { force: true });
