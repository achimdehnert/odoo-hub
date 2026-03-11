/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";

export class CastingPanel extends Component {
    static template = "casting_foundry.CastingPanel";
    static components = {};

    setup() {
        this.actionService = useService("action");
        this.state = useState({ loading: true, kpis: null, error: null });
        onWillStart(() => this.loadKpis());
    }

    async loadKpis() {
        this.state.loading = true;
        try {
            this.state.kpis = await rpc("/casting_foundry/kpis");
        } catch (e) {
            this.state.error = String(e);
        } finally {
            this.state.loading = false;
        }
    }

    activeOrders() {
        const s = this.state.kpis.order_states;
        return (s.confirmed || 0) + (s.in_production || 0) + (s.quality_check || 0);
    }

    totalMachines() {
        const m = this.state.kpis.machine_states;
        return (m.operational || 0) + (m.maintenance || 0) + (m.breakdown || 0) + (m.decommissioned || 0);
    }

    machineAvailabilityPct() {
        const total = this.totalMachines();
        return total ? Math.round((this.state.kpis.machine_states.operational || 0) / total * 100) : 0;
    }

    qcTrend() {
        const cur  = this.state.kpis.qc_rate || 0;
        const prev = this.state.kpis.qc_rate_last_month || 0;
        if (!prev) return "neutral";
        return cur >= prev ? "good" : "bad";
    }

    scrapTrend() {
        const cur  = this.state.kpis.scrap_avg || 0;
        const prev = this.state.kpis.scrap_avg_lm || 0;
        if (!prev) return "neutral";
        return cur <= prev ? "good" : "bad";
    }

    machineStateColor(state) {
        return { operational: "#22c55e", maintenance: "#f59e0b", breakdown: "#ef4444", decommissioned: "#94a3b8" }[state] || "#94a3b8";
    }

    orderStates() {
        const s = this.state.kpis.order_states;
        return [
            { key: "draft",         count: s.draft || 0,         hex: "#94a3b8", label: "Entwurf" },
            { key: "confirmed",     count: s.confirmed || 0,     hex: "#3b82f6", label: "Bestätigt" },
            { key: "in_production", count: s.in_production || 0, hex: "#f59e0b", label: "In Fertigung" },
            { key: "quality_check", count: s.quality_check || 0, hex: "#8b5cf6", label: "QS-Prüfung" },
            { key: "done",          count: s.done || 0,          hex: "#22c55e", label: "Abgeschlossen" },
        ].filter(s => s.count > 0);
    }

    openOrders(domain) {
        if (!Array.isArray(domain)) domain = [];
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Gießaufträge",
            res_model: "casting.order",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain,
        });
    }

    openActiveOrders() {
        this.openOrders([["state", "in", ["confirmed", "in_production", "quality_check"]]]);
    }

    openOrdersByStateEv(ev) {
        const state = ev.currentTarget.dataset.orderState;
        if (state) this.openOrders([["state", "=", state]]);
    }

    openMachineOrdersEv(ev) {
        const el = ev.currentTarget;
        const machineId = parseInt(el.dataset.machineId, 10);
        const machineName = el.dataset.machineName || String(machineId);
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Auftr\u00e4ge: " + machineName,
            res_model: "casting.order",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["machine_id", "=", machineId], ["state", "in", ["confirmed", "in_production", "quality_check"]]],
        });
    }
}

registry.category("iil_panels").add("casting", {
    component: CastingPanel,
    label: "Gießerei",
    sequence: 10,
});
