/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

export class Nl2sqlPanel extends Component {
    static template = "mfg_management.Nl2sqlPanel";
    static components = {};

    setup() {
        this.state = useState({
            query:   "",
            loading: false,
            result:  null,
            error:   null,
            sql:     null,
        });
    }

    onInput(ev) { this.state.query = ev.target.value; }

    onKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.runQuery();
        }
    }

    applySuggestEv(ev) {
        const q = ev.currentTarget.dataset.query;
        if (q) this.state.query = q;
    }

    async runQuery() {
        const q = this.state.query.trim();
        if (!q) return;
        this.state.loading = true;
        this.state.result  = null;
        this.state.error   = null;
        this.state.sql     = null;
        try {
            const res = await rpc("/mfg_management/nl2sql", {
                query:       q,
                source_code: "odoo_mfg",
            });
            if (res.error || res.success === false) {
                this.state.error = res.error || "Unbekannter Fehler";
                if (res.sql) this.state.sql = res.sql;
            } else {
                const cols     = (res.columns || []).map(c => typeof c === "object" ? c : { name: c });
                const colNames = cols.map(c => c.name);
                const rows     = (res.rows || []).map(row =>
                    Array.isArray(row) ? row : colNames.map(n => row[n] ?? null)
                );
                this.state.result = {
                    columns:           cols,
                    rows,
                    row_count:         res.row_count || rows.length,
                    execution_time_ms: res.execution_time_ms || 0,
                    truncated:         res.truncated || false,
                    sql:               res.sql || "",
                    summary:           res.summary || "",
                };
                this.state.sql = res.sql || "";
            }
        } catch (e) {
            this.state.error = String(e);
        } finally {
            this.state.loading = false;
        }
    }

    hasRows() {
        return this.state.result && this.state.result.rows && this.state.result.rows.length > 0;
    }

    clearResult() {
        this.state.result = null;
        this.state.error  = null;
        this.state.sql    = null;
        this.state.query  = "";
    }

    suggestQueries() {
        return [
            "Welche Maschinen sind gerade in Störung?",
            "Zeige Aufträge mit Ausschuss > 5%",
            "Top 5 Maschinen nach aktiven Aufträgen",
            "Wie viele Aufträge sind diese Woche fällig?",
            "Kritische Teile mit Nullbestand",
        ];
    }
}

registry.category("iil_panels").add("nl2sql", {
    component: Nl2sqlPanel,
    label: "KI-Assistent",
    sequence: 90,
});
