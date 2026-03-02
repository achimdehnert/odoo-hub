/** @odoo-module **/
import { Component, useState, onWillStart, onMounted, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { QueryInput } from "./query_input";
import { ResultChart } from "./result_chart";
import { ResultTable } from "./result_table";
import { KpiCard } from "./kpi_card";
import { QueryHistory } from "./query_history";

export class NL2SQLDashboard extends Component {
    static template = "mfg_nl2sql.Dashboard";
    static components = { QueryInput, ResultChart, ResultTable, KpiCard, QueryHistory };

    setup() {
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            // Dashboard data
            tiles: [],
            history: [],
            schema: [],
            config: {},
            // Current query state
            isLoading: false,
            currentResult: null,
            currentError: null,
            currentSql: null,
            // UI state
            showHistory: false,
            showSchema: false,
            selectedDomain: "all",
            userName: "",
        });

        onWillStart(async () => {
            await this._loadDashboardData();
        });
    }

    async _loadDashboardData() {
        try {
            const data = await rpc("/mfg_nl2sql/dashboard_data", {});
            this.state.tiles = data.tiles || [];
            this.state.history = data.history || [];
            this.state.schema = data.schema || [];
            this.state.config = data.config || {};
            this.state.selectedDomain = data.config?.default_domain || "all";
            this.state.userName = data.user_name || "";
        } catch (err) {
            console.error("Failed to load dashboard data:", err);
            this.notification.add("Dashboard-Daten konnten nicht geladen werden.", {
                type: "danger",
            });
        }
    }

    async onQuerySubmit(queryText) {
        if (!queryText.trim()) return;

        this.state.isLoading = true;
        this.state.currentError = null;
        this.state.currentResult = null;
        this.state.currentSql = null;

        try {
            const result = await rpc("/mfg_nl2sql/query", {
                query_text: queryText,
                domain_filter: this.state.selectedDomain,
            });

            if (result.error) {
                this.state.currentError = result.error;
                this.state.currentSql = result.sql || null;
            } else {
                this.state.currentResult = result;
                this.state.currentSql = result.sql;
                // Prepend to local history
                this.state.history.unshift({
                    id: result.history_id,
                    name: queryText,
                    chart_type: result.chart_type,
                    row_count: result.row_count,
                    execution_time_ms: result.execution_time_ms,
                    create_date: new Date().toISOString(),
                    is_pinned: false,
                });
                // Trim local history to 20 entries
                if (this.state.history.length > 20) {
                    this.state.history = this.state.history.slice(0, 20);
                }
            }
        } catch (err) {
            console.error("Query execution failed:", err);
            this.state.currentError = "Verbindungsfehler. Bitte erneut versuchen.";
        } finally {
            this.state.isLoading = false;
        }
    }

    async onHistorySelect(historyId) {
        this.state.isLoading = true;
        try {
            const result = await rpc("/mfg_nl2sql/history/" + historyId + "/result", {});
            if (result.error) {
                this.state.currentError = result.error;
            } else {
                this.state.currentResult = result;
                this.state.currentSql = result.sql;
                this.state.currentError = null;
            }
        } catch (err) {
            this.state.currentError = "Ergebnis konnte nicht geladen werden.";
        } finally {
            this.state.isLoading = false;
        }
    }

    async onTileClick(tile) {
        await this.onQuerySubmit(tile.query_text);
    }

    onDomainChange(ev) {
        this.state.selectedDomain = ev.target.value;
    }

    toggleHistory() {
        this.state.showHistory = !this.state.showHistory;
    }

    toggleSchema() {
        this.state.showSchema = !this.state.showSchema;
    }

    get domainOptions() {
        return [
            { value: "all", label: "Alle Bereiche" },
            { value: "supply_chain", label: "Supply Chain" },
            { value: "production", label: "Produktion" },
            { value: "quality", label: "Qualität" },
        ];
    }

    get hasKpiResult() {
        return this.state.currentResult?.chart_type === "kpi";
    }

    get hasChartResult() {
        const t = this.state.currentResult?.chart_type;
        return t && ["bar", "line", "pie", "hbar"].includes(t);
    }

    get hasTableResult() {
        return this.state.currentResult?.columns?.length > 0;
    }

    get resultMeta() {
        const r = this.state.currentResult;
        if (!r) return null;
        return {
            rowCount: r.row_count,
            executionTime: r.execution_time_ms,
            tokensUsed: r.tokens_used,
            chartType: r.chart_type,
        };
    }
}

registry.category("actions").add("mfg_nl2sql.dashboard", NL2SQLDashboard);
