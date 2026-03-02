/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

export class ProductionBoard extends Component {
    static template = "mfg_management.ProductionBoard";
    static components = {};

    setup() {
        this.state = useState({ loading: true, data: null, tab: "casting" });
        onWillStart(() => this.loadData());
    }

    async loadData() {
        this.state.loading = true;
        try {
            this.state.data = await rpc("/mfg_management/production_board");
        } finally {
            this.state.loading = false;
        }
    }

    castingColumns() {
        const orders = this.state.data.casting_orders || [];
        const cols = [
            { key: "draft",         label: "Entwurf",          color: "#94a3b8" },
            { key: "confirmed",     label: "Bestätigt",        color: "#3b82f6" },
            { key: "in_production", label: "In Fertigung",     color: "#f59e0b" },
            { key: "quality_check", label: "Qualitätsprüfung", color: "#8b5cf6" },
        ];
        return cols.map(col => ({
            ...col,
            items: orders.filter(o => o.state === col.key),
        }));
    }

    scmColumns() {
        const orders = this.state.data.scm_orders || [];
        const cols = [
            { key: "draft",       label: "Entwurf",       color: "#94a3b8" },
            { key: "confirmed",   label: "Bestätigt",     color: "#3b82f6" },
            { key: "in_progress", label: "In Fertigung",  color: "#f59e0b" },
        ];
        return cols.map(col => ({
            ...col,
            items: orders.filter(o => o.state === col.key),
        }));
    }
}

registry.category("actions").add("mfg_management.ProductionBoard", ProductionBoard);
