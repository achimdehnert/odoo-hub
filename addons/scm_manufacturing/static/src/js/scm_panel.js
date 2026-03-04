/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

export class ScmPanel extends Component {
    static template = "scm_manufacturing.ScmPanel";
    static components = {};

    setup() {
        this.state = useState({ loading: true, kpis: null, error: null });
        onWillStart(() => this.loadKpis());
    }

    async loadKpis() {
        this.state.loading = true;
        try {
            this.state.kpis = await rpc("/scm_manufacturing/kpis");
        } catch (e) {
            this.state.error = String(e);
        } finally {
            this.state.loading = false;
        }
    }

    activeProduction() {
        const s = this.state.kpis.prod_states;
        return (s.confirmed || 0) + (s.in_progress || 0);
    }

    stockHealthPct() {
        const total = this.state.kpis.parts_total || 0;
        const low   = this.state.kpis.parts_low_stock || 0;
        if (!total) return 100;
        return Math.round((total - low) / total * 100);
    }

    throughputTrend() {
        const cur  = this.state.kpis.done_this_month || 0;
        const prev = this.state.kpis.done_last_month || 0;
        if (!prev) return "neutral";
        return cur >= prev ? "good" : "bad";
    }

    overdueClass() {
        return (this.state.kpis.overdue_purchases || 0) > 0 ? "iil-trend-bad" : "";
    }

    prodStateColor(state) {
        return { draft: "#94a3b8", confirmed: "#3b82f6", in_progress: "#f59e0b", done: "#22c55e", cancelled: "#ef4444" }[state] || "#94a3b8";
    }

    prodStates() {
        const s = this.state.kpis.prod_states;
        return [
            { key: "draft",       count: s.draft || 0,       hex: "#94a3b8", label: "Entwurf" },
            { key: "confirmed",   count: s.confirmed || 0,   hex: "#3b82f6", label: "Bestätigt" },
            { key: "in_progress", count: s.in_progress || 0, hex: "#f59e0b", label: "In Fertigung" },
            { key: "done",        count: s.done || 0,        hex: "#22c55e", label: "Abgeschlossen" },
        ].filter(s => s.count > 0);
    }

    formatDate(d) {
        if (!d) return "–";
        return d.substring(0, 10);
    }
}

registry.category("iil_panels").add("scm", {
    component: ScmPanel,
    label: "Supply Chain",
    sequence: 50,
});
