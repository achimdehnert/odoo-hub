/** @odoo-module **/
/**
 * NL2SQL Query-Bar — wiederverwendbare OWL-Komponente.
 *
 * Verwendung in jedem Panel:
 *   <NL2SqlQueryBar sourceCode="'odoo_mfg'" suggestQueries="suggestQueries()"/>
 *
 * Props:
 *   sourceCode   {string}   NL2SQL-SchemaSource-Code (z.B. 'odoo_mfg')
 *   suggestQueries {Array}  Optional: Liste von Vorschlägen
 *   title        {string}   Optional: Überschrift (Default: 'KI-Assistent')
 */

import { Component, useState } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class NL2SqlQueryBar extends Component {
    static template = "mfg_management.NL2SqlQueryBar";
    static props = {
        sourceCode:     { type: String },
        suggestQueries: { type: Array, optional: true },
        title:          { type: String, optional: true },
    };
    static defaultProps = {
        suggestQueries: [],
        title: "KI-Assistent",
    };

    setup() {
        this.state = useState({
            open:    false,
            query:   "",
            loading: false,
            result:  null,
            error:   null,
            sql:     null,
        });
    }

    toggle() { this.state.open = !this.state.open; }

    onInput(ev) { this.state.query = ev.target.value; }

    applySuggest(q) { this.state.query = q; }

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
                source_code: this.props.sourceCode,
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
                    columns:          cols,
                    rows,
                    row_count:        res.row_count || rows.length,
                    execution_time_ms: res.execution_time_ms || 0,
                    truncated:        res.truncated || false,
                    sql:              res.sql || "",
                    summary:          res.summary || "",
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

    onKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.runQuery();
        }
    }

    clearResult() {
        this.state.result = null;
        this.state.error  = null;
        this.state.sql    = null;
        this.state.query  = "";
    }
}
