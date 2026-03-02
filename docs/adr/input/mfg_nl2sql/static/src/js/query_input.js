/** @odoo-module **/
import { Component, useState, useRef, onMounted } from "@odoo/owl";

export class QueryInput extends Component {
    static template = "mfg_nl2sql.QueryInput";
    static props = {
        onSubmit: { type: Function },
        isLoading: { type: Boolean },
        domainOptions: { type: Array },
        selectedDomain: { type: String },
        onDomainChange: { type: Function },
    };

    setup() {
        this.inputRef = useRef("queryInput");
        this.state = useState({
            queryText: "",
        });

        this.exampleQueries = [
            "Wie viele offene Fertigungsaufträge gibt es?",
            "Welcher Lieferant hat die meisten Bestellungen?",
            "Zeige die Ausschussrate nach Maschine",
            "Top 10 Artikel nach Lagerbestand",
            "Durchschnittliche Lieferzeit pro Lieferant",
            "Qualitätsprüfungen der letzten 30 Tage",
        ];

        onMounted(() => {
            if (this.inputRef.el) {
                this.inputRef.el.focus();
            }
        });
    }

    onKeyDown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.submitQuery();
        }
    }

    submitQuery() {
        const text = this.state.queryText.trim();
        if (text && !this.props.isLoading) {
            this.props.onSubmit(text);
        }
    }

    setExample(query) {
        this.state.queryText = query;
        if (this.inputRef.el) {
            this.inputRef.el.focus();
        }
    }
}
