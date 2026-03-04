/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";

export class MachinesPanel extends Component {
    static template = "casting_foundry.MachinesPanel";
    static components = {};

    setup() {
        this.actionService = useService("action");
        this.state = useState({ loading: true, kpis: null, error: null, filter: "all" });
        onWillStart(() => this.loadKpis());
    }

    async loadKpis() {
        this.state.loading = true;
        try {
            this.state.kpis = await rpc("/casting_foundry/machines_kpis");
        } catch (e) {
            this.state.error = String(e);
        } finally {
            this.state.loading = false;
        }
    }

    setFilter(f) { this.state.filter = f; }

    filteredMachines() {
        const k = this.state.kpis;
        const all = [...(k.casting_machines || []), ...(k.machining_machines || [])];
        if (this.state.filter === "all") return all;
        return all.filter(m => m.state === this.state.filter);
    }

    stateColor(s) {
        return { operational: "#22c55e", maintenance: "#f59e0b", breakdown: "#ef4444", decommissioned: "#94a3b8" }[s] || "#94a3b8";
    }

    stateLabel(s) {
        return { operational: "Betrieb", maintenance: "Wartung", breakdown: "Störung", decommissioned: "Stillgelegt" }[s] || s;
    }

    domainIcon(d) {
        return d === "machining" ? "fa-cogs" : "fa-fire";
    }

    availClass() {
        const p = this.state.kpis.availability_pct;
        if (p >= 90) return "iil-trend-good";
        if (p >= 70) return "";
        return "iil-trend-bad";
    }

    openMachines(domain) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Maschinenpark",
            res_model: "casting.machine",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: domain || [],
        });
    }

    openMachinesByState(state) {
        this.openMachines([["state", "=", state]]);
    }

    openMachinesByStateEv(ev) {
        const state = ev.currentTarget.dataset.machineState;
        if (state) this.openMachinesByState(state);
    }

    setFilterEv(ev) {
        const f = ev.currentTarget.dataset.filter;
        if (f) this.setFilter(f);
    }

    openMachineDetailEv(ev) {
        const el = ev.currentTarget;
        const domain = el.dataset.domain;
        const model = domain === "machining" ? "machining.machine" : "casting.machine";
        const machineId = parseInt(el.dataset.machineId, 10);
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: el.dataset.machineName || "Maschine",
            res_model: model,
            view_mode: "form",
            views: [[false, "form"]],
            res_id: machineId,
        });
    }
}

registry.category("iil_panels").add("machines", {
    component: MachinesPanel,
    label: "Maschinenpark",
    sequence: 25,
});
