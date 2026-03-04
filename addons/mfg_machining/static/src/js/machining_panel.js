/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
export class MachiningPanel extends Component {
    static template = "mfg_machining.MachiningPanel";

    setup() {
        this.actionService = useService("action");
        this.state = useState({
            loading: true,
            kpis: null,
            error: null,
        });
        onWillStart(() => this.loadKpis());
    }

    async loadKpis() {
        this.state.loading = true;
        this.state.error = null;
        try {
            this.state.kpis = await rpc("/mfg_machining/kpis");
        } catch (e) {
            this.state.error = String(e);
        } finally {
            this.state.loading = false;
        }
    }

    totalMachines() {
        const m = this.state.kpis.machine_states;
        return (m.operational || 0) + (m.maintenance || 0) + (m.breakdown || 0) + (m.decommissioned || 0);
    }

    machineAvailabilityPct() {
        const total = this.totalMachines();
        if (!total) return 0;
        return Math.round((this.state.kpis.machine_states.operational || 0) / total * 100);
    }

    activeOrders() {
        const s = this.state.kpis.order_states;
        return (s.confirmed || 0) + (s.in_production || 0) + (s.quality_check || 0);
    }

    scrapTrend() {
        const cur  = this.state.kpis.scrap_pct || 0;
        const prev = this.state.kpis.scrap_pct_last_month || 0;
        if (!prev) return "neutral";
        return cur < prev ? "good" : cur > prev ? "bad" : "neutral";
    }

    producedTrend() {
        const cur  = this.state.kpis.produced_this_month || 0;
        const prev = this.state.kpis.produced_last_month || 0;
        if (!prev) return "neutral";
        return cur >= prev ? "good" : "bad";
    }

    machineStateColor(state) {
        return {
            operational:   "#22c55e",
            maintenance:   "#f59e0b",
            breakdown:     "#ef4444",
            decommissioned:"#94a3b8",
        }[state] || "#94a3b8";
    }

    orderStateLabel(state) {
        return {
            draft:         "Entwurf",
            confirmed:     "Bestätigt",
            in_production: "In Fertigung",
            quality_check: "Qualitätsprüfung",
            done:          "Abgeschlossen",
            cancelled:     "Storniert",
        }[state] || state;
    }

    orderStates() {
        const s = this.state.kpis.order_states;
        return [
            { key: "draft",         count: s.draft || 0,         hex: "#94a3b8" },
            { key: "confirmed",     count: s.confirmed || 0,     hex: "#3b82f6" },
            { key: "in_production", count: s.in_production || 0, hex: "#f59e0b" },
            { key: "quality_check", count: s.quality_check || 0, hex: "#8b5cf6" },
            { key: "done",          count: s.done || 0,          hex: "#22c55e" },
        ].filter(s => s.count > 0);
    }

    openOrders(domain) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Fertigungsaufträge",
            res_model: "mrp.production",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: domain || [],
        });
    }

    openOrdersByState(state) {
        this.openOrders([["state", "=", state]]);
    }

    openActiveOrders() {
        this.openOrders([["state", "in", ["confirmed", "progress", "to_close"]]]);
    }

    openMachines() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Maschinen",
            res_model: "maintenance.equipment",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
        });
    }
}

// Panel-Registry: wird vom DynamicDashboard geladen wenn Feature 'machining' aktiv
const panelRegistry = registry.category("iil_panels");
if (panelRegistry) {
    panelRegistry.add("machining", {
        component: MachiningPanel,
        label: "CNC-Fertigung",
        sequence: 20,
    });
}
