/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { KpiCard } from "./kpi_card";

export class MfgDashboard extends Component {
    static template = "mfg_management.Dashboard";
    static components = { KpiCard };

    setup() {
        this.state = useState({
            loading: true,
            data: null,
            drilldown: null,
            drilldownData: null,
            drilldownLoading: false,
            nl2sql: {
                open: false,
                query: "",
                loading: false,
                result: null,
                error: null,
                sql: null,
            },
        });
        onWillStart(() => this.loadData());
    }

    async loadData() {
        this.state.loading = true;
        try {
            this.state.data = await rpc("/mfg_management/kpis");
        } finally {
            this.state.loading = false;
        }
    }

    // ── KPI helpers ───────────────────────────────────────────────
    activecastingOrders() {
        const d = this.state.data.casting_orders;
        return (d.draft || 0) + (d.confirmed || 0) + (d.in_production || 0) + (d.quality_check || 0);
    }

    openPurchases() {
        const d = this.state.data.purchases;
        return (d.draft || 0) + (d.sent || 0) + (d.confirmed || 0);
    }

    totalMachines() {
        const m = this.state.data.machines;
        return (m.operational || 0) + (m.maintenance || 0) + (m.breakdown || 0) + (m.decommissioned || 0);
    }

    machPct(state) {
        const total = this.totalMachines();
        if (!total) return 0;
        return Math.round((this.state.data.machines[state] || 0) / total * 100);
    }

    castingOrderStates() {
        const d = this.state.data.casting_orders;
        const total = Object.values(d).reduce((a, b) => a + b, 0) || 1;
        return [
            { key: "draft",         label: "Entwurf",          count: d.draft || 0,        hex: "#94a3b8", pct: Math.round((d.draft || 0) / total * 100) },
            { key: "confirmed",     label: "Bestätigt",        count: d.confirmed || 0,    hex: "#3b82f6", pct: Math.round((d.confirmed || 0) / total * 100) },
            { key: "in_production", label: "In Fertigung",     count: d.in_production || 0,hex: "#f59e0b", pct: Math.round((d.in_production || 0) / total * 100) },
            { key: "quality_check", label: "Qualitätsprüfung", count: d.quality_check || 0,hex: "#8b5cf6", pct: Math.round((d.quality_check || 0) / total * 100) },
            { key: "done",          label: "Abgeschlossen",    count: d.done || 0,         hex: "#22c55e", pct: Math.round((d.done || 0) / total * 100) },
            { key: "cancelled",     label: "Storniert",        count: d.cancelled || 0,    hex: "#ef4444", pct: Math.round((d.cancelled || 0) / total * 100) },
        ];
    }

    scmOrderStates() {
        const d = this.state.data.scm_production;
        const total = Object.values(d).reduce((a, b) => a + b, 0) || 1;
        return [
            { key: "draft",       label: "Entwurf",       count: d.draft || 0,       hex: "#94a3b8", pct: Math.round((d.draft || 0) / total * 100) },
            { key: "confirmed",   label: "Bestätigt",     count: d.confirmed || 0,   hex: "#3b82f6", pct: Math.round((d.confirmed || 0) / total * 100) },
            { key: "in_progress", label: "In Fertigung",  count: d.in_progress || 0, hex: "#f59e0b", pct: Math.round((d.in_progress || 0) / total * 100) },
            { key: "done",        label: "Abgeschlossen", count: d.done || 0,        hex: "#22c55e", pct: Math.round((d.done || 0) / total * 100) },
            { key: "cancelled",   label: "Storniert",     count: d.cancelled || 0,   hex: "#ef4444", pct: Math.round((d.cancelled || 0) / total * 100) },
        ];
    }

    deliveryStates() {
        const d = this.state.data.deliveries;
        const total = Object.values(d).reduce((a, b) => a + b, 0) || 1;
        return [
            { key: "draft",     label: "Entwurf",       count: d.draft || 0,     hex: "#94a3b8", pct: Math.round((d.draft || 0) / total * 100) },
            { key: "ready",     label: "Versandbereit", count: d.ready || 0,     hex: "#3b82f6", pct: Math.round((d.ready || 0) / total * 100) },
            { key: "shipped",   label: "Versendet",     count: d.shipped || 0,   hex: "#f59e0b", pct: Math.round((d.shipped || 0) / total * 100) },
            { key: "delivered", label: "Zugestellt",    count: d.delivered || 0, hex: "#22c55e", pct: Math.round((d.delivered || 0) / total * 100) },
            { key: "cancelled", label: "Storniert",     count: d.cancelled || 0, hex: "#ef4444", pct: Math.round((d.cancelled || 0) / total * 100) },
        ];
    }

    // ── Drilldown ─────────────────────────────────────────────────
    async openDrilldown(key) {
        this.state.drilldown = key;
        this.state.drilldownData = null;
        this.state.drilldownLoading = true;
        try {
            const result = await rpc("/mfg_management/drilldown", { key });
            this.state.drilldownData = result;
        } catch (e) {
            this.state.drilldownData = { error: String(e) };
        } finally {
            this.state.drilldownLoading = false;
        }
    }

    closeDrilldown() {
        this.state.drilldown = null;
        this.state.drilldownData = null;
    }

    drilldownTitle() {
        const titles = {
            casting_active:   "Aktive Gießaufträge",
            scm_in_progress:  "Fertigungsaufträge in Progress",
            machines_op:      "Maschinen – Betrieb",
            machines_fail:    "Maschinen – Störung",
            quality:          "Qualitätsprüfungen",
            purchases_open:   "Offene Bestellungen",
        };
        return titles[this.state.drilldown] || "Details";
    }

    // ── NL2SQL ────────────────────────────────────────────────────
    toggleNl2sql() {
        this.state.nl2sql.open = !this.state.nl2sql.open;
    }

    onNl2sqlInput(ev) {
        this.state.nl2sql.query = ev.target.value;
    }

    async runNl2sql() {
        const q = this.state.nl2sql.query.trim();
        if (!q) return;
        this.state.nl2sql.loading = true;
        this.state.nl2sql.result = null;
        this.state.nl2sql.error = null;
        this.state.nl2sql.sql = null;
        try {
            const res = await rpc("/mfg_management/nl2sql", { query: q });
            if (res.error || res.success === false) {
                this.state.nl2sql.error = res.error || "Unbekannter Fehler";
                if (res.sql) this.state.nl2sql.sql = res.sql;
            } else {
                // aifw_service returns rows as list[dict] — normalize to {columns, rows as list[list]}
                const cols = (res.columns || []).map(c => typeof c === "object" ? c : { name: c });
                const colNames = cols.map(c => c.name);
                const rowsAsLists = (res.rows || []).map(row =>
                    Array.isArray(row) ? row : colNames.map(name => row[name] ?? null)
                );
                this.state.nl2sql.result = {
                    columns: cols,
                    rows: rowsAsLists,
                    row_count: res.row_count || rowsAsLists.length,
                    execution_time_ms: res.execution_time_ms || 0,
                    truncated: res.truncated || false,
                    chart_type: res.chart_type || "table",
                    chart: res.chart || {},
                    summary: res.summary || "",
                };
                this.state.nl2sql.sql = res.sql || "";
            }
        } catch (e) {
            this.state.nl2sql.error = String(e);
        } finally {
            this.state.nl2sql.loading = false;
        }
    }

    nl2sqlHasRows() {
        return this.state.nl2sql.result &&
               this.state.nl2sql.result.rows &&
               this.state.nl2sql.result.rows.length > 0;
    }

    nl2sqlSuggestQueries() {
        return [
            "Wie viele Gießaufträge sind aktuell in Fertigung?",
            "Zeige alle Maschinen im Störungszustand",
            "Welche Aufträge haben den höchsten Ausschuss?",
            "Offene Bestellungen nach Lieferant sortiert",
            "QS-Ergebnisse der letzten 30 Tage",
        ];
    }

    applySuggest(q) {
        this.state.nl2sql.query = q;
    }
}

registry.category("actions").add("mfg_management.Dashboard", MfgDashboard);
