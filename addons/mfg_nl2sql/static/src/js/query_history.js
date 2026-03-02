/** @odoo-module **/
import { Component } from "@odoo/owl";

export class QueryHistory extends Component {
    static template = "mfg_nl2sql.QueryHistory";
    static props = {
        history: { type: Array },
        onSelect: { type: Function },
    };

    formatDate(isoStr) {
        if (!isoStr) return "";
        const d = new Date(isoStr);
        return d.toLocaleString("de-DE", {
            day: "2-digit",
            month: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
        });
    }

    chartIcon(chartType) {
        const icons = {
            table: "fa-table",
            bar: "fa-bar-chart",
            line: "fa-line-chart",
            pie: "fa-pie-chart",
            kpi: "fa-dashboard",
            hbar: "fa-align-left",
        };
        return icons[chartType] || "fa-question";
    }

    onSelect(historyId) {
        this.props.onSelect(historyId);
    }
}
