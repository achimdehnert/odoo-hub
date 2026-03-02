/** @odoo-module **/
import { registry } from "@web/core/registry";

/**
 * NL2SQL Service — manages schema cache and query suggestions.
 */
const nl2sqlService = {
    dependencies: [],
    start() {
        let schemaCache = null;

        return {
            getSchema() {
                return schemaCache;
            },
            setSchema(schema) {
                schemaCache = schema;
            },
        };
    },
};

registry.category("services").add("nl2sql", nl2sqlService);
