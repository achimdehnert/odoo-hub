/** @odoo-module **/
/**
 * Panel-Registry für das dynamische IIL-Dashboard.
 *
 * Jeder Feature-Code aus iil.product.feature wird hier auf eine
 * OWL-Komponente gemappt. Nicht registrierte Codes werden still übersprungen.
 *
 * Sprint 2: Nur casting + nl2sql registriert (bestehende Komponenten).
 * Sprint 3+: machining, mrp, stock, scm, quality, maintenance, sales, accounting.
 */

import { MfgDashboard } from "./mfg_dashboard";

/**
 * PANEL_REGISTRY — einzige Quelle der Wahrheit für Feature-Code → Komponente.
 *
 * Hinweis: MfgDashboard ist der bestehende monolithische Dashboard-Container.
 * In Sprint 3 wird er in dedizierte Panel-Komponenten aufgespalten.
 * Bis dahin: casting + nl2sql zeigen den vollen Dashboard-Container.
 */
export const PANEL_REGISTRY = {
    casting:  MfgDashboard,
    nl2sql:   MfgDashboard,
    // machining:   MachiningPanel,     // Sprint 4
    // mrp:         MrpOverviewPanel,   // Sprint 3
    // stock:       StockOverviewPanel, // Sprint 3
    // scm:         ScmOverviewPanel,   // Sprint 3
    // quality:     QualityPanel,       // Sprint 3
    // maintenance: MaintenancePanel,   // Sprint 4
    // sales:       SalesPanel,         // Sprint 4
    // accounting:  AccountingPanel,    // Sprint 4
};
