/** @odoo-module **/
import { Component, useState, onWillStart, onPatched } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const STEPS = [
    { key: "step1", label: "Branche",    icon: "fa-industry" },
    { key: "step2", label: "Prozesse",   icon: "fa-cogs" },
    { key: "step3", label: "KI",         icon: "fa-robot" },
    { key: "step4", label: "Dashboard",  icon: "fa-th-large" },
    { key: "step5", label: "Demo-Daten", icon: "fa-database" },
];

const INDUSTRY_PREVIEW = {
    casting:   { label: "Gießerei / Druckguss",         icon: "fa-fire",         modules: ["Gießaufträge", "Maschinen", "Qualitätsprüfung", "Legierungen"] },
    machining: { label: "CNC-Fertigung",                icon: "fa-wrench",       modules: ["Fertigungsaufträge", "CNC-Maschinen", "Werkzeuge", "Messprotokolle"] },
    both:      { label: "Gießerei + CNC",               icon: "fa-industry",     modules: ["Gießaufträge", "CNC-Fertigung", "Qualitätsprüfung", "Maschinenpark"] },
    scm:       { label: "Supply Chain",                  icon: "fa-truck",        modules: ["Einkauf", "Lagerverwaltung", "Lieferanten", "Produktionsplanung"] },
    all:       { label: "Vollständig",                   icon: "fa-star",         modules: ["Gießerei", "CNC", "SCM", "Qualität", "Instandhaltung"] },
    generic:   { label: "Sonstige Fertigung",            icon: "fa-cog",          modules: ["Fertigungsplanung", "Lagerverwaltung", "Produktion"] },
};

export class ConfiguratorProgress extends Component {
    static template = "iil_configurator.ConfiguratorProgress";
    static props = {
        record: { type: Object },
    };

    setup() {
        this.state = useState({
            currentStep: "step1",
            industry: "casting",
        });

        onWillStart(() => this._syncFromRecord());
        onPatched(() => this._syncFromRecord());
    }

    _syncFromRecord() {
        const rec = this.props.record;
        if (rec?.data) {
            this.state.currentStep = rec.data.state || "step1";
            this.state.industry   = rec.data.industry || "casting";
        }
    }

    get steps() {
        const current = this.state.currentStep;
        const currentIdx = STEPS.findIndex(s => s.key === current);
        return STEPS.map((s, i) => ({
            ...s,
            done:    i < currentIdx,
            active:  i === currentIdx,
            pending: i > currentIdx,
        }));
    }

    get industryPreview() {
        return INDUSTRY_PREVIEW[this.state.industry] || INDUSTRY_PREVIEW.generic;
    }
}

registry.category("view_widgets").add("configurator_progress", {
    component: ConfiguratorProgress,
});
