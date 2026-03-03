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
        gaugeValue: { type: Number, optional: true },
        gaugeMax: { type: Number, optional: true },
        gaugeColor: { type: String, optional: true },
    };

    onClick() {
        if (this.props.onDrilldown && this.props.drilldownKey) {
            this.props.onDrilldown(this.props.drilldownKey);
        }
    }

    get hasGauge() {
        return this.props.gaugeValue !== undefined && this.props.gaugeValue !== null;
    }

    get gaugeArcPath() {
        const pct = Math.min(100, Math.max(0, this.props.gaugeValue || 0)) / (this.props.gaugeMax || 100);
        const r = 28;
        const cx = 36, cy = 36;
        const startAngle = -210;
        const sweepAngle = 240;
        const endAngle = startAngle + sweepAngle * pct;
        const toRad = (d) => d * Math.PI / 180;
        const x1 = cx + r * Math.cos(toRad(startAngle));
        const y1 = cy + r * Math.sin(toRad(startAngle));
        const x2 = cx + r * Math.cos(toRad(endAngle));
        const y2 = cy + r * Math.sin(toRad(endAngle));
        const largeArc = sweepAngle * pct > 180 ? 1 : 0;
        if (pct <= 0) return "";
        return `M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}`;
    }

    get gaugeTrackPath() {
        const r = 28;
        const cx = 36, cy = 36;
        const startAngle = -210;
        const endAngle = startAngle + 240;
        const toRad = (d) => d * Math.PI / 180;
        const x1 = cx + r * Math.cos(toRad(startAngle));
        const y1 = cy + r * Math.sin(toRad(startAngle));
        const x2 = cx + r * Math.cos(toRad(endAngle));
        const y2 = cy + r * Math.sin(toRad(endAngle));
        return `M ${x1} ${y1} A ${r} ${r} 0 1 1 ${x2} ${y2}`;
    }

    get gaugeStrokeColor() {
        if (this.props.gaugeColor) return this.props.gaugeColor;
        const v = this.props.gaugeValue || 0;
        if (v >= 85) return "#22c55e";
        if (v >= 65) return "#f59e0b";
        return "#ef4444";
    }
}
