/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

export class StockPanel extends Component {
    static template = "scm_manufacturing.StockPanel";

    setup() {
        this.state = useState({ loading: true, kpis: null, error: null });
        onWillStart(() => this.loadKpis());
    }

    async loadKpis() {
        this.state.loading = true;
        try {
            this.state.kpis = await rpc("/scm_manufacturing/stock_kpis");
        } catch (e) {
            this.state.error = String(e);
        } finally {
            this.state.loading = false;
        }
    }

    stockHealthClass() {
        const pct = this.state.kpis.stock_health_pct || 0;
        if (pct >= 90) return "iil-trend-good";
        if (pct >= 70) return "";
        return "iil-trend-bad";
    }

    formatValue(v) {
        if (v >= 1000000) return (v / 1000000).toFixed(1) + " M";
        if (v >= 1000)    return (v / 1000).toFixed(1) + " K";
        return v.toFixed(0);
    }

    warehouseTypeLabel(t) {
        return { raw: "Rohstoff", wip: "WIP", finished: "Fertigware", quarantine: "Sperr", shipping: "Versand" }[t] || t;
    }

    warehouseTypeColor(t) {
        return { raw: "#3b82f6", wip: "#f59e0b", finished: "#22c55e", quarantine: "#ef4444", shipping: "#8b5cf6" }[t] || "#94a3b8";
    }

    partTypeLabel(t) {
        return { raw: "Rohstoff", semi: "Halbfertig", finished: "Fertigteil", consumable: "Verbr." }[t] || t;
    }
}

registry.category("iil_panels").add("stock", {
    component: StockPanel,
    label: "Lagerverwaltung",
    sequence: 40,
});
