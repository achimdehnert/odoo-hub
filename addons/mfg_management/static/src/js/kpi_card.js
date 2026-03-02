/** @odoo-module **/
import { Component } from "@odoo/owl";

export class KpiCard extends Component {
    static template = "mfg_management.KpiCard";
    static props = {
        icon: { type: String, optional: true },
        label: String,
        value: [String, Number],
        sublabel: { type: String, optional: true },
        colorClass: { type: String, optional: true },
    };
}
