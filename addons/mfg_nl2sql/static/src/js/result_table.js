/** @odoo-module **/
import { Component, useState } from "@odoo/owl";

export class ResultTable extends Component {
    static template = "mfg_nl2sql.ResultTable";
    static props = {
        columns: { type: Array },
        rows: { type: Array },
        rowCount: { type: Number },
    };

    setup() {
        this.state = useState({
            sortCol: null,
            sortDir: "asc",
            page: 0,
            pageSize: 50,
        });
    }

    get sortedRows() {
        let rows = [...this.props.rows];
        if (this.state.sortCol !== null) {
            const idx = this.state.sortCol;
            const dir = this.state.sortDir === "asc" ? 1 : -1;
            rows.sort((a, b) => {
                const va = a[idx];
                const vb = b[idx];
                if (va == null) return 1;
                if (vb == null) return -1;
                if (typeof va === "number" && typeof vb === "number") {
                    return (va - vb) * dir;
                }
                return String(va).localeCompare(String(vb)) * dir;
            });
        }
        return rows;
    }

    get paginatedRows() {
        const start = this.state.page * this.state.pageSize;
        return this.sortedRows.slice(start, start + this.state.pageSize);
    }

    get totalPages() {
        return Math.ceil(this.props.rows.length / this.state.pageSize);
    }

    get pageInfo() {
        const start = this.state.page * this.state.pageSize + 1;
        const end = Math.min(
            (this.state.page + 1) * this.state.pageSize,
            this.props.rows.length
        );
        return `${start}–${end} von ${this.props.rows.length}`;
    }

    sortBy(colIdx) {
        if (this.state.sortCol === colIdx) {
            this.state.sortDir = this.state.sortDir === "asc" ? "desc" : "asc";
        } else {
            this.state.sortCol = colIdx;
            this.state.sortDir = "asc";
        }
    }

    prevPage() {
        if (this.state.page > 0) this.state.page--;
    }

    nextPage() {
        if (this.state.page < this.totalPages - 1) this.state.page++;
    }

    formatCell(value, colType) {
        if (value == null) return "—";
        if (colType === "float" || colType === "numeric") {
            return Number(value).toLocaleString("de-DE", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
            });
        }
        if (colType === "integer" || colType === "int") {
            return Number(value).toLocaleString("de-DE");
        }
        return String(value);
    }
}
