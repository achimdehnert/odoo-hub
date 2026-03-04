/** @odoo-module **/
/**
 * IIL Dashboard Core — PanelErrorBoundary
 *
 * OWL error boundary that catches render errors of individual panel components.
 * Prevents a single crashing panel from freezing the entire OWL application
 * and blocking router navigation.
 *
 * Usage in templates:
 *   <PanelErrorBoundary>
 *       <t t-component="panel.component" t-props="..."/>
 *   </PanelErrorBoundary>
 *
 * On error: shows a non-blocking warning card with the error message.
 * On success: renders the default slot transparently.
 */

import { Component, useState, onError } from "@odoo/owl";

export class PanelErrorBoundary extends Component {
    static template = "iil_dashboard_core.PanelErrorBoundary";
    static props = ["*"];

    setup() {
        this.state = useState({ hasError: false, errorMsg: "" });
        onError((err) => {
            console.error("[IIL Dashboard Core] Panel render error:", err);
            this.state.hasError = true;
            this.state.errorMsg = err && err.message ? err.message : String(err);
        });
    }
}
