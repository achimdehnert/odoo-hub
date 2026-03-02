/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class MachineStatus extends Component {
    static template = "mfg_management.MachineStatus";
    static components = {};

    setup() {
        this.rpc = useService("rpc");
        this.state = useState({ loading: true, machines: [], filter: "" });
        onWillStart(() => this.loadData());
    }

    async loadData() {
        this.state.loading = true;
        try {
            const result = await this.rpc("/mfg_management/machine_status", {});
            this.state.machines = result.machines || [];
        } finally {
            this.state.loading = false;
        }
    }

    onFilterChange(ev) {
        this.state.filter = ev.target.value;
    }

    filteredMachines() {
        if (!this.state.filter) return this.state.machines;
        return this.state.machines.filter(m => m.machine_type === this.state.filter);
    }

    machineSummary() {
        const machines = this.state.machines;
        const counts = { operational: 0, maintenance: 0, breakdown: 0, decommissioned: 0 };
        machines.forEach(m => { if (counts[m.state] !== undefined) counts[m.state]++; });
        return [
            { state: "operational",   label: "Betrieb",     count: counts.operational },
            { state: "maintenance",   label: "Wartung",     count: counts.maintenance },
            { state: "breakdown",     label: "Störung",     count: counts.breakdown },
            { state: "decommissioned",label: "Stillgelegt", count: counts.decommissioned },
        ];
    }

    stateLabel(state) {
        const map = {
            operational: "Betrieb",
            maintenance: "Wartung",
            breakdown: "Störung",
            decommissioned: "Stillgelegt",
        };
        return map[state] || state;
    }

    machineTypeLabel(type) {
        const map = {
            melting_furnace:  "Schmelzofen",
            holding_furnace:  "Warmhalteofen",
            die_casting:      "Druckguss",
            gravity_casting:  "Schwerkraft-Kokillen",
            sand_molding:     "Formanlage (Sand)",
            centrifugal:      "Schleuderguss",
            heat_treatment:   "Wärmebehandlung",
            finishing:        "Nachbearbeitung / Putzerei",
            xray:             "Röntgenprüfanlage",
        };
        return map[type] || type;
    }
}

registry.category("actions").add("mfg_management.MachineStatus", MachineStatus);
