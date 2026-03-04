/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

export class QualityPanel extends Component {
    static template = "casting_foundry.QualityPanel";
    static components = {};

    setup() {
        this.state = useState({ loading: true, kpis: null, error: null });
        onWillStart(() => this.loadKpis());
    }

    async loadKpis() {
        this.state.loading = true;
        try {
            this.state.kpis = await rpc("/casting_foundry/quality_kpis");
        } catch (e) {
            this.state.error = String(e);
        } finally {
            this.state.loading = false;
        }
    }

    qcTrendClass() {
        const c = this.state.kpis.qc_rate, p = this.state.kpis.qc_rate_lm;
        if (!p) return "";
        return c >= p ? "iil-trend-good" : "iil-trend-bad";
    }

    severityColor(s) {
        return { critical: "#dc2626", major: "#f59e0b", minor: "#3b82f6" }[s] || "#94a3b8";
    }

    maxTrendCount() {
        if (!this.state.kpis.trend.length) return 1;
        return Math.max(...this.state.kpis.trend.map(d => d.pass + d.fail), 1);
    }

    trendBarHeight(val) {
        return Math.round((val / this.maxTrendCount()) * 40);
    }
}

registry.category("iil_panels").add("quality", {
    component: QualityPanel,
    label: "Qualitätssicherung",
    sequence: 60,
});
