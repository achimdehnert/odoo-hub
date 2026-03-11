/** @odoo-module **/
import { Component } from "@odoo/owl";

export class KpiCard extends Component {
    static template = "mfg_nl2sql.KpiCard";
    static props = {
        label: { type: String },
        value: { type: [Number, String, { value: null }] },
        icon: { type: String, optional: true },
        color: { type: String, optional: true },
        onClick: { type: Function, optional: true },
    };

    get formattedValue() {
        const val = this.props.value;
        if (val == null) return "—";
        if (typeof val === "number") {
            if (Number.isInteger(val)) {
                return val.toLocaleString("de-DE");
            }
            return val.toLocaleString("de-DE", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
            });
        }
        return String(val);
    }

    get colorClass() {
        const colors = {
            blue: "nl2sql-kpi--blue",
            green: "nl2sql-kpi--green",
            orange: "nl2sql-kpi--orange",
            red: "nl2sql-kpi--red",
            purple: "nl2sql-kpi--purple",
            teal: "nl2sql-kpi--teal",
        };
        return colors[this.props.color] || colors.blue;
    }

    onClick() {
        if (this.props.onClick) {
            this.props.onClick();
        }
    }
}
