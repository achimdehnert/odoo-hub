/** @odoo-module **/
import { Component, useState, onWillStart, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { KpiCard } from "./kpi_card";

export class MfgDashboard extends Component {
    static template = "mfg_management.Dashboard";
    static components = { KpiCard };

    setup() {
        this.state = useState({ loading: true, data: null });
        onWillStart(() => this.loadData());
    }

    async loadData() {
        this.state.loading = true;
        try {
            this.state.data = await rpc("/mfg_management/kpis");
        } finally {
            this.state.loading = false;
        }
    }

    activecastingOrders() {
        const d = this.state.data.casting_orders;
        return (d.draft || 0) + (d.confirmed || 0) + (d.in_production || 0) + (d.quality_check || 0);
    }

    openPurchases() {
        const d = this.state.data.purchases;
        return (d.draft || 0) + (d.sent || 0) + (d.confirmed || 0);
    }

    totalMachines() {
        const m = this.state.data.machines;
        return (m.operational || 0) + (m.maintenance || 0) + (m.breakdown || 0) + (m.decommissioned || 0);
    }

    machPct(state) {
        const total = this.totalMachines();
        if (!total) return 0;
        return Math.round((this.state.data.machines[state] || 0) / total * 100);
    }

    castingOrderStates() {
        const d = this.state.data.casting_orders;
        const total = Object.values(d).reduce((a, b) => a + b, 0) || 1;
        return [
            { key: "draft",        label: "Entwurf",          count: d.draft || 0,        hex: "#94a3b8", pct: Math.round((d.draft || 0) / total * 100) },
            { key: "confirmed",    label: "Bestätigt",        count: d.confirmed || 0,    hex: "#3b82f6", pct: Math.round((d.confirmed || 0) / total * 100) },
            { key: "in_production",label: "In Fertigung",     count: d.in_production || 0,hex: "#f59e0b", pct: Math.round((d.in_production || 0) / total * 100) },
            { key: "quality_check",label: "Qualitätsprüfung", count: d.quality_check || 0,hex: "#8b5cf6", pct: Math.round((d.quality_check || 0) / total * 100) },
            { key: "done",         label: "Abgeschlossen",    count: d.done || 0,         hex: "#22c55e", pct: Math.round((d.done || 0) / total * 100) },
            { key: "cancelled",    label: "Storniert",        count: d.cancelled || 0,    hex: "#ef4444", pct: Math.round((d.cancelled || 0) / total * 100) },
        ];
    }

    scmOrderStates() {
        const d = this.state.data.scm_production;
        const total = Object.values(d).reduce((a, b) => a + b, 0) || 1;
        return [
            { key: "draft",      label: "Entwurf",       count: d.draft || 0,       hex: "#94a3b8", pct: Math.round((d.draft || 0) / total * 100) },
            { key: "confirmed",  label: "Bestätigt",     count: d.confirmed || 0,   hex: "#3b82f6", pct: Math.round((d.confirmed || 0) / total * 100) },
            { key: "in_progress",label: "In Fertigung",  count: d.in_progress || 0, hex: "#f59e0b", pct: Math.round((d.in_progress || 0) / total * 100) },
            { key: "done",       label: "Abgeschlossen", count: d.done || 0,        hex: "#22c55e", pct: Math.round((d.done || 0) / total * 100) },
            { key: "cancelled",  label: "Storniert",     count: d.cancelled || 0,   hex: "#ef4444", pct: Math.round((d.cancelled || 0) / total * 100) },
        ];
    }

    deliveryStates() {
        const d = this.state.data.deliveries;
        const total = Object.values(d).reduce((a, b) => a + b, 0) || 1;
        return [
            { key: "draft",     label: "Entwurf",        count: d.draft || 0,     hex: "#94a3b8", pct: Math.round((d.draft || 0) / total * 100) },
            { key: "ready",     label: "Versandbereit",  count: d.ready || 0,     hex: "#3b82f6", pct: Math.round((d.ready || 0) / total * 100) },
            { key: "shipped",   label: "Versendet",      count: d.shipped || 0,   hex: "#f59e0b", pct: Math.round((d.shipped || 0) / total * 100) },
            { key: "delivered", label: "Zugestellt",     count: d.delivered || 0, hex: "#22c55e", pct: Math.round((d.delivered || 0) / total * 100) },
            { key: "cancelled", label: "Storniert",      count: d.cancelled || 0, hex: "#ef4444", pct: Math.round((d.cancelled || 0) / total * 100) },
        ];
    }
}

registry.category("actions").add("mfg_management.Dashboard", MfgDashboard);
