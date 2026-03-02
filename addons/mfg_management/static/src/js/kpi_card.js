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
        drilldownKey: { type: String, optional: true },
        onDrilldown: { type: Function, optional: true },
    };

    onClick() {
        if (this.props.onDrilldown && this.props.drilldownKey) {
            this.props.onDrilldown(this.props.drilldownKey);
        }
    }
}
