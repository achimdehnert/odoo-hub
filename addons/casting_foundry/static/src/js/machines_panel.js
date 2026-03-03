/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { NL2SqlQueryBar } from "@mfg_management/js/nl2sql_query_bar";

export class MachinesPanel extends Component {
    static template = "casting_foundry.MachinesPanel";
    static components = { NL2SqlQueryBar };

    suggestQueries() {
        return [
            "Welche Maschinen sind aktuell in Störung?",
            "Durchschnittliche Wartungszeit pro Maschinentyp",
            "Wie viele Maschinen sind pro Halle verfügbar?",
        ];
    }

    setup() {
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
}

registry.category("iil_panels").add("machines", {
    component: MachinesPanel,
    label: "Maschinenpark",
    sequence: 25,
});
