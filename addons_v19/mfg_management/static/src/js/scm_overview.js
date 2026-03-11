/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

export class ScmOverview extends Component {
    static template = "mfg_management.ScmOverview";
    static components = {};

    setup() {
        this.state = useState({ loading: true, data: null });
        onWillStart(() => this.loadData());
    }

    async loadData() {
        this.state.loading = true;
        try {
            this.state.data = await rpc("/mfg_management/scm_overview");
        } finally {
            this.state.loading = false;
        }
    }

    isOverdue(dateStr) {
        if (!dateStr) return false;
        return new Date(dateStr) < new Date();
    }

    formatAmount(amount) {
        if (!amount) return "—";
        return new Intl.NumberFormat("de-DE", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(amount);
    }

    purchaseStateLabel(state) {
        const map = {
            draft: "Entwurf", sent: "Versendet", confirmed: "Bestätigt",
            received: "Eingegangen", done: "Abgeschlossen", cancelled: "Storniert",
        };
        return map[state] || state;
    }

    deliveryStateLabel(state) {
        const map = {
            draft: "Entwurf", ready: "Versandbereit", shipped: "Versendet",
            delivered: "Zugestellt", cancelled: "Storniert",
        };
        return map[state] || state;
    }

    warehouseTypeLabel(type) {
        const map = {
            raw: "Rohstofflager", wip: "Zwischenlager (WIP)",
            finished: "Fertigwarenlager", quarantine: "Sperrlager", shipping: "Versandlager",
        };
        return map[type] || type;
    }
}

registry.category("actions").add("mfg_management.ScmOverview", ScmOverview);
