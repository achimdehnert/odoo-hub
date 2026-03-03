# ADR-005: Produktkonfigurator — Architektur & Implementierung

| Feld | Wert |
|------|------|
| **Datum** | 2026-03-03 |
| **Status** | **ENTSCHIEDEN — Rev. 2 (kritischer Review eingearbeitet, 2026-03-03)** |
| **Entscheidungsträger** | Achim Dehnert |
| **Reviewer** | Cascade |
| **Basis** | PRODUCT-STRATEGY-VERTICAL.md, ADR-003 D1, Strategiegespräch 2026-03-03 |
| **Supersedes** | — |

---

## 0. Kernentscheidung

> **Der Produktkonfigurator ist das Kernprodukt — nicht die einzelnen Module.**

Statt klassischer Odoo-Implementierung (6–12 Wochen Handarbeit pro Kunde) liefert ein
interaktiver Fragebogen-Assistent eine **branchenspezifisch konfigurierte Instanz inkl.
Demo-Daten in < 1 Stunde**. Das transformiert das Geschäftsmodell von Dienstleistung zu
skalierbarlem Software-Produkt (SaaS-Pfad).

---

## 1. Strategische Einordnung

### 1.1 Problem des Status quo

Jeder Odoo-Implementierungspartner liefert heute:

```
Anforderungsworkshop (1–2 Tage)
  → manuelle Konfiguration (2–4 Wochen)
    → manuelle Datenmigration (1–2 Wochen)
      → Schulung (1 Woche)
        → Go-Live (Woche 6–12)
```

**Kosten:** €18.000–35.000 einmalig. **Nicht skalierbar.**

### 1.2 Zielzustand mit Konfigurator

```
Fragebogen ausfüllen (20 Minuten)
  → Feature-Flags in DB (automatisch, sofort)
    → OWL-Dashboard konfiguriert sich (automatisch)
      → Demo-Daten passend zur Branche generiert (automatisch)
        → Erste produktive Demo läuft (< 1 Stunde)
```

**Kosten:** €0 Konfigurationsaufwand. **Beliebig skalierbar.**

### 1.3 Wettbewerbsdifferenzierung

| | Klassischer Odoo-Partner | Wir mit Konfigurator |
|---|---|---|
| Konfigurationsaufwand | 6–12 Wochen Handarbeit | 20 Minuten Fragebogen |
| Skalierbarkeit | 1 Entwickler = 1–2 Projekte/Jahr | 1 Konfigurator = ∞ Kunden |
| Demo-Vorbereitung | Stunden bis Tage | Minuten |
| Branchenanpassung | Immer neu | Registry: 1 Eintrag = neue Branche |
| Preismodell | Einmalig €18k–35k | SaaS-Modell möglich |

---

## 2. Architektur: 3 Schichten

```
┌──────────────────────────────────────────────────────────────────┐
│ SCHICHT 3: iil_configurator (Addon)                              │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ iil.configurator.wizard (TransientModel, 5 Schritte)    │    │
│  │  Fragebogen → Branche, Prozesse, KI, Layout, Demo-Daten │    │
│  │  action_apply() → Savepoint → Feature-Flags + Seed      │    │
│  └────────────────────┬───────────────────┬────────────────┘    │
│                       │ schreibt          │ triggert            │
│  ┌────────────────────▼──────┐  ┌─────────▼──────────────────┐  │
│  │ iil.product.feature       │  │ iil.seed.engine            │  │
│  │ (Feature-Registry)        │  │ (TransientModel, Subsystem) │  │
│  │ code, is_active, sequence │  │ Branchenspezifische Daten  │  │
│  │ config (JSON)             │  │ Idempotent, is_demo_data   │  │
│  └────────────────────┬──────┘  └────────────────────────────┘  │
└───────────────────────┼──────────────────────────────────────────┘
                        │ liest (RPC)
┌───────────────────────▼──────────────────────────────────────────┐
│ SCHICHT 1: Dynamisches OWL-Cockpit (mfg_management)              │
│  useService('orm').call → get_active_features()                  │
│  PANEL_REGISTRY: feature_code → OWL-Komponente                   │
│  Nur aktivierte Features → nur diese Panels rendern              │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Schicht 3 — Konfigurator-Wizard

### 3.1 `__manifest__.py`

```python
# addons/iil_configurator/__manifest__.py
{
    'name': 'IIL Produktkonfigurator',
    'version': '18.0.1.0.0',
    'summary': 'Branchenspezifischer Onboarding-Wizard mit Demo-Daten-Generator',
    'author': 'IIL',
    'license': 'OPL-1',
    'category': 'Manufacturing',
    'depends': ['base', 'mail', 'casting_foundry'],
    # mfg_nl2sql optional — kein hard depends, Feature-Flag steuert Aktivierung
    'data': [
        'security/iil_security.xml',
        'security/ir.model.access.csv',
        'data/feature_defaults.xml',
        'views/iil_product_feature_views.xml',
        'views/iil_configurator_wizard_views.xml',
        'views/iil_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'iil_configurator/static/src/js/configurator_wizard.js',
            'iil_configurator/static/src/xml/configurator_wizard.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}
```

### 3.2 Modulstruktur

```
addons/iil_configurator/
  __manifest__.py
  __init__.py
  models/
    __init__.py
    iil_product_feature.py      ← Feature-Registry Model
    iil_seed_engine.py          ← Demo-Daten-Generator
  wizard/
    __init__.py
    iil_configurator_wizard.py  ← 5-Schritt-Fragebogen (TransientModel)
  data/
    feature_defaults.xml        ← Seed-Einträge für alle Feature-Codes
  views/
    iil_configurator_wizard_views.xml
    iil_product_feature_views.xml
    iil_menus.xml
  security/
    iil_security.xml
    ir.model.access.csv
  static/src/
    js/configurator_wizard.js   ← OWL-Wrapper für mehrstufigen Wizard
    xml/configurator_wizard.xml
```

### 3.3 Wizard — Fragebogen-Schritte

```python
# addons/iil_configurator/wizard/iil_configurator_wizard.py

class IilConfiguratorWizard(models.TransientModel):
    _name = 'iil.configurator.wizard'
    _description = 'IIL Produktkonfigurator'

    # state steuert Wizard-Navigation (Odoo-konform: Selection + statusbar)
    # Integer-Felder erlauben step=99 ohne Fehler — Selection ist typsicher
    state = fields.Selection([
        ('step1', '1. Branche'),
        ('step2', '2. Prozesse'),
        ('step3', '3. KI-Features'),
        ('step4', '4. Dashboard'),
        ('step5', '5. Demo-Daten'),
    ], default='step1', required=True)

    # ── Schritt 1: Branche ─────────────────────────────────────────
    industry = fields.Selection([
        ('casting',   'Gießerei / Druckguss'),
        ('machining', 'Werkzeugmaschinen / CNC-Fertigung'),
        ('both',      'Gießerei + CNC-Nachbearbeitung'),
        ('generic',   'Sonstige Fertigung'),
    ], required=True, default='casting')

    company_size = fields.Selection([
        ('small',  'Klein (< 20 Mitarbeiter)'),
        ('medium', 'Mittel (20–100 Mitarbeiter)'),
        ('large',  'Groß (> 100 Mitarbeiter)'),
    ], default='medium')
    # company_size beeinflusst: Demo-Auftragsanzahl (small→50, medium→200, large→500)
    # und Dashboard-Layout (small→kpi_first, large→split)

    # ── Schritt 2: Prozesse ────────────────────────────────────────
    has_mrp            = fields.Boolean('Fertigungsplanung (MRP)', default=True)
    has_stock          = fields.Boolean('Lagerverwaltung', default=True)
    has_procurement    = fields.Boolean('Einkauf / Beschaffung', default=True)
    has_quality        = fields.Boolean('Qualitätsmanagement', default=True)
    has_maintenance    = fields.Boolean('Instandhaltung', default=False)
    has_sales          = fields.Boolean('Verkauf / Auftragsabwicklung', default=False)
    has_accounting     = fields.Boolean('Finanzbuchhaltung', default=False)

    # ── Schritt 3: KI-Features ─────────────────────────────────────
    has_nl2sql         = fields.Boolean('KI-Analyse (NL2SQL)', default=True)
    nl2sql_provider    = fields.Selection([
        ('anthropic', 'Anthropic Claude (Cloud, DSGVO-AVV)'),
        ('openai',    'OpenAI GPT-4 (Cloud, DSGVO-AVV)'),
        ('ollama',    'Lokales LLM (Hetzner, maximale Datensouveränität)'),
    ], default='anthropic')
    # View-Hinweis: nl2sql_provider in XML-View mit invisible="not has_nl2sql"
    # ausblenden — sonst erscheint das Provider-Dropdown auch wenn KI deaktiviert

    # ── Schritt 4: Dashboard-Layout ────────────────────────────────
    dashboard_layout   = fields.Selection([
        ('kanban_first', 'Kanban-Board oben, KPIs unten'),
        ('kpi_first',    'KPIs oben, Kanban unten'),
        ('nl2sql_focus', 'KI-Analyse im Vordergrund'),
        ('split',        'Gleichgewichtete Panels'),
    ], default='kanban_first')

    # ── Schritt 5: Demo-Daten ──────────────────────────────────────
    generate_demo_data = fields.Boolean('Demo-Daten generieren', default=True)
    demo_months        = fields.Integer('Historische Monate', default=12)
    demo_order_count   = fields.Integer('Anzahl Demo-Aufträge', default=200)
    demo_clear_existing = fields.Boolean(
        'Vorhandene Demo-Daten ersetzen', default=True
    )

    # _sql_constraints auf TransientModel sind unzuverlässig (ir.autovacuum truncated
    # die Tabelle periodisch, Constraints werden nicht immer neu angelegt).
    # @api.constrains ist die Odoo-konforme Lösung für Wizard-Validierung.
    @api.constrains('demo_months', 'demo_order_count')
    def _check_demo_params(self):
        for rec in self:
            if rec.demo_months <= 0:
                raise ValidationError('Historische Monate müssen > 0 sein.')
            if rec.demo_order_count <= 0:
                raise ValidationError('Auftragsanzahl muss > 0 sein.')

    def action_apply(self):
        """Konfigurator anwenden: Feature-Flags setzen + Demo-Daten generieren.

        Transaktional gesichert: Wenn _generate_demo_data() fehlschlägt,
        werden auch Feature-Flags zurückgerollt → kein halbkonfiguriertes Dashboard.
        ir.config_parameter (Dashboard-Layout) ist bewusst außerhalb des Savepoints:
        kein Rollback nötig, da kein inkonsistenter Zustand bei Layout-Fehler.
        """
        self.ensure_one()
        with self.env.cr.savepoint():
            self._apply_feature_flags()
            if self.generate_demo_data:
                self._generate_demo_data()
        self._apply_dashboard_layout()
        return {
            'type': 'ir.actions.client',
            'tag':  'mfg_management.dashboard',
            'params': {'reconfigure': True},
        }

    def _generate_demo_data(self):
        """Delegiert an IilSeedEngine. company_size steuert Auftragsanzahl."""
        count_by_size = {'small': 50, 'medium': 200, 'large': 500}
        count = count_by_size.get(self.company_size, self.demo_order_count)
        self.env['iil.seed.engine'].generate(
            industry=self.industry,
            months=self.demo_months,
            order_count=count,
            clear_existing=self.demo_clear_existing,
        )

    def _apply_feature_flags(self):
        Feature = self.env['iil.product.feature']
        mapping = [
            # (condition, code, sequence, config)
            (self.industry in ('casting', 'both'),
                'casting',     10, {'color': 'orange'}),
            (self.industry in ('machining', 'both'),
                'machining',   20, {'color': 'blue'}),
            (self.industry != 'generic',
                'machines',    25, {}),
            (self.has_mrp,
                'mrp',         30, {}),
            (self.has_stock,
                'stock',       40, {}),
            (self.has_procurement,
                'scm',         50, {}),
            (self.has_quality,
                'quality',     60, {}),
            (self.has_maintenance,
                'maintenance', 70, {}),
            (self.has_sales,
                'sales',       75, {}),
            (self.has_accounting,
                'accounting',  78, {}),
            (self.has_nl2sql,
                'nl2sql',      80,
                {'provider': self.nl2sql_provider}),
        ]
        for is_active, code, seq, config in mapping:
            rec = Feature.search([('code', '=', code)], limit=1)
            vals = {'is_active': is_active, 'sequence': seq, 'config': config}
            if rec:
                rec.write(vals)
            else:
                Feature.create({**vals, 'code': code, 'label': code.title()})

    def _apply_dashboard_layout(self):
        # company_size überschreibt das gewählte Layout wenn es noch auf dem
        # Default 'kanban_first' ist — hier, nicht in _apply_feature_flags()
        layout = self.dashboard_layout
        if layout == 'kanban_first' and self.company_size == 'small':
            layout = 'kpi_first'
        elif layout == 'kanban_first' and self.company_size == 'large':
            layout = 'split'
        self.env['ir.config_parameter'].sudo().set_param(
            'iil.dashboard.layout', layout
        )

```

---

## 4. Schicht 2 — Feature-Registry

### 4.1 Model

```python
# addons/iil_configurator/models/iil_product_feature.py

class IilProductFeature(models.Model):
    _name = 'iil.product.feature'
    _description = 'IIL Produkt-Feature'
    _order = 'sequence'

    code           = fields.Char(required=True, index=True)
    label          = fields.Char(required=True)
    is_active      = fields.Boolean(default=True, index=True)
    sequence       = fields.Integer(default=10)
    config         = fields.Json(default=dict)
    depends_module = fields.Char(
        help='Odoo-Modulname — wird vor Panel-Render auf Installation geprüft'
    )

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Feature-Code muss eindeutig sein.'),
    ]

    @api.model
    def get_active_features(self):
        """RPC-Endpoint für OWL-Dashboard.

        ACL-Anforderung: ir.model.access.csv muss 'read'-Recht auf
        iil.product.feature für die Gruppe 'base.group_user' (alle angemeldeten
        User) vergeben. Fehlt dieses Recht, wirft Odoo 'Access Denied' beim
        Dashboard-Load für normale User.

        ir.model.access.csv Eintrag:
          access_iil_product_feature_user,iil.product.feature,model_iil_product_feature,base.group_user,1,0,0,0
        """
        features = self.search([('is_active', '=', True)], order='sequence')
        return [{
            'code':     f.code,
            'label':    f.label,
            'sequence': f.sequence,
            'config':   f.config or {},
        } for f in features]
```

### 4.2 Standard-Feature-Codes

| Code | Label | Zugehöriges Modul | Panel-Komponente |
|------|-------|------------------|-----------------|
| `casting` | Gießerei | `casting_foundry` | `CastingKanbanPanel` |
| `machining` | Werkzeugmaschinen | `mfg_machining` | `MachiningKanbanPanel` |
| `machines` | Maschinenpark | `casting_foundry` / `mfg_machining` | `MachineStatusPanel` |
| `mrp` | Fertigungsplanung | `iil_mrp` (Odoo `mrp`) | `MrpOverviewPanel` |
| `stock` | Lagerverwaltung | `iil_stock` (Odoo `stock`) | `StockOverviewPanel` |
| `scm` | Einkauf | `scm_manufacturing` | `ScmOverviewPanel` |
| `quality` | Qualität | `casting_foundry` / `mfg_machining` | `QualityPanel` |
| `maintenance` | Instandhaltung | Odoo `maintenance` | `MaintenancePanel` |
| `sales` | Verkauf | Odoo `sale` | `SalesPanel` |
| `accounting` | Buchhaltung | Odoo `account` | `AccountingPanel` |
| `nl2sql` | KI-Analyse | `mfg_nl2sql` | `NL2SQLPanel` |

---

## 5. Schicht 1 — Dynamisches OWL-Cockpit

### 5.1 Panel-Registry Pattern

```javascript
// addons/mfg_management/static/src/js/mfg_dashboard.js

// useService ist die Odoo-18-konforme API — this.env.services.orm ist Odoo-16-API
// und in Odoo 18 deprecated. useService() muss im setup()-Hook aufgerufen werden.
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";

import { CastingKanbanPanel }   from "./panels/casting_kanban";
import { MachiningKanbanPanel } from "./panels/machining_kanban";
import { MachineStatusPanel }   from "./panels/machine_status";
import { MrpOverviewPanel }     from "./panels/mrp_overview";
import { StockOverviewPanel }   from "./panels/stock_overview";
import { ScmOverviewPanel }     from "./panels/scm_overview";
import { QualityPanel }         from "./panels/quality_panel";
import { MaintenancePanel }     from "./panels/maintenance_panel";
import { SalesPanel }           from "./panels/sales_panel";
import { AccountingPanel }      from "./panels/accounting_panel";
import { NL2SQLPanel }          from "./panels/nl2sql_panel";

const PANEL_REGISTRY = {
    casting:     CastingKanbanPanel,
    machining:   MachiningKanbanPanel,
    machines:    MachineStatusPanel,
    mrp:         MrpOverviewPanel,
    stock:       StockOverviewPanel,
    scm:         ScmOverviewPanel,
    quality:     QualityPanel,
    maintenance: MaintenancePanel,
    sales:       SalesPanel,
    accounting:  AccountingPanel,
    nl2sql:      NL2SQLPanel,
};

export class MfgDashboard extends Component {
    static template = "mfg_management.Dashboard";

    setup() {
        this.orm = useService("orm");  // Odoo-18-konform
        this.state = useState({ panels: [], loading: true });
        onWillStart(async () => {
            const features = await this.orm.call(
                "iil.product.feature", "get_active_features", []
            );
            this.state.panels = features
                .filter(f => PANEL_REGISTRY[f.code])
                .map(f => ({
                    code:      f.code,
                    component: PANEL_REGISTRY[f.code],
                    config:    f.config,
                    label:     f.label,
                }));
            this.state.loading = false;
        });
    }
}
```

### 5.2 Dashboard-Template

```xml
<!-- addons/mfg_management/static/src/xml/dashboard.xml -->
<templates>
  <t t-name="mfg_management.Dashboard">
    <div class="iil-mfg-dashboard o_view_controller">
      <t t-if="state.loading">
        <div class="iil-loading">
          <i class="fa fa-spinner fa-spin"/> Cockpit wird geladen…
        </div>
      </t>
      <t t-elif="state.panels.length === 0">
        <div class="iil-empty-state">
          <i class="fa fa-cogs fa-3x"/>
          <h3>Keine Module konfiguriert</h3>
          <p>Starten Sie den Einrichtungsassistenten um Ihr Cockpit zu konfigurieren.</p>
          <button class="btn btn-primary" t-on-click="openConfigurator">
            Konfigurator starten
          </button>
        </div>
      </t>
      <t t-else="">
        <div class="iil-dashboard-grid">
          <t t-foreach="state.panels" t-as="panel" t-key="panel.code">
            <div t-attf-class="iil-panel iil-panel-{{ panel.code }}">
              <t t-component="panel.component"
                 config="panel.config"
                 label="panel.label"/>
            </div>
          </t>
        </div>
      </t>
    </div>
  </t>
</templates>
```

---

## 6. Seed-Engine — Demo-Daten-Generator (Subsystem von Schicht 3)

Das ist das **entscheidende Feature** für schnelle Demos und schnellen Piloten-Onboarding.

### 6.1 Architektur des Seed-Engines

```python
# addons/iil_configurator/models/iil_seed_engine.py

# Imports am Dateikopf (kein Import in Methodenrümpfen)
import random
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta  # korrekte Monatsberechnung

_logger = logging.getLogger(__name__)


class IilSeedEngine(models.AbstractModel):
    """Demo-Daten-Generator — branchenspezifisch, parametrisiert, idempotent.

    AbstractModel (nicht TransientModel): Alle Methoden sind @api.model —
    es werden keine Instanz-Records benötigt, keine eigene DB-Tabelle.
    Aufruf: self.env['iil.seed.engine'].generate(...)
    AbstractModel ist die korrekte Basisklasse für reine Service-Objekte in Odoo.

    Schutz gegen Produktivdaten-Löschung: ausschließlich über
    is_demo_data=True gefiltert — kein Name-Prefix-Match.
    """
    _name = 'iil.seed.engine'
    _description = 'IIL Demo-Daten-Generator'

    GENERATORS = {
        'casting':   '_generate_casting_data',
        'machining': '_generate_machining_data',
        'both':      '_generate_casting_and_machining_data',
        'generic':   '_generate_generic_data',
    }

    @api.model
    def generate(self, industry: str, months: int = 12,
                 order_count: int = 200, clear_existing: bool = True):
        """Einstiegspunkt — dispatcht an branchenspezifischen Generator."""
        if clear_existing:
            self._clear_demo_data(industry)

        method = self.GENERATORS.get(industry, '_generate_generic_data')
        getattr(self, method)(months=months, order_count=order_count)

        self._activate_nl2sql_schema(industry)

        _logger.info(
            "IIL Seed Engine: %d Aufträge für Branche '%s' über %d Monate generiert.",
            order_count, industry, months
        )

    @api.model
    def _clear_demo_data(self, industry: str):
        """Bestehende Demo-Daten entfernen — nur is_demo_data=True Records.

        Name-Prefix ('DEMO-') ist kein ausreichender Schutz: User können
        echte Aufträge mit diesem Prefix anlegen. is_demo_data-Flag ist
        die einzige zuverlässige Unterscheidung.
        """
        if industry in ('casting', 'both'):
            self.env['casting.order'].sudo().search(
                [('is_demo_data', '=', True)]
            ).unlink()
            self.env['casting.quality.check'].sudo().search(
                [('is_demo_data', '=', True)]
            ).unlink()
        if industry in ('machining', 'both'):
            # analog für mfg_machining-Models (Sprint 4)
            pass

    @api.model
    def _generate_casting_data(self, months: int, order_count: int):
        """Gießerei-Demo-Daten: Aufträge, Qualitätsprüfungen, Maschinenzuweisungen.

        Realistische Trends:
        - Auftragsvolumen: leicht wachsend (+5%/Monat)
        - Ausschussrate: saisonale Schwankung (Winter höher)
        - Maschinenauslastung: 70–95%, eine Maschine mit Störung im letzten Monat
        """
        env = self.env

        alloys   = env['casting.alloy'].search([])
        machines = env['casting.machine'].search([])
        molds    = env['casting.mold'].search([])

        if not (alloys and machines and molds):
            raise UserError(
                'casting_foundry Stammdaten fehlen. '
                'Bitte zuerst casting_foundry-Modul-Demo-Daten laden.'
            )

        base_date = date.today().replace(day=1)
        orders_per_month = max(1, order_count // months)

        for month_offset in range(months, 0, -1):
            # relativedelta statt timedelta(days=30): exakte Monatsberechnung
            # timedelta(days=30*12) = 360 Tage != 12 Monate
            month_start = base_date - relativedelta(months=month_offset)

            volume_factor = 1.0 + (months - month_offset) * 0.05
            actual_orders = int(orders_per_month * volume_factor * random.uniform(0.9, 1.1))

            is_winter = month_start.month in (11, 12, 1, 2)
            base_scrap = 0.06 if is_winter else 0.03

            for i in range(actual_orders):
                order_date = month_start + timedelta(days=random.randint(0, 28))
                planned_qty = random.choice([50, 100, 200, 500, 1000])
                scrap_pct   = max(0.0, random.gauss(base_scrap, 0.01))
                scrap_qty   = int(planned_qty * scrap_pct)
                produced    = planned_qty - scrap_qty

                order = env['casting.order'].create({
                    'name':          f"DEMO-{order_date.strftime('%Y%m')}-{i+1:04d}",
                    'alloy_id':      random.choice(alloys).id,
                    'machine_id':    random.choice(machines).id,
                    'mold_id':       random.choice(molds).id,
                    'state':         'done',
                    'order_date':    order_date,
                    'planned_qty':   planned_qty,
                    'produced_qty':  produced,
                    'scrap_qty':     scrap_qty,
                    'is_demo_data':  True,  # Pflichtfeld für sauberes Cleanup
                })

                env['casting.quality.check'].create({
                    'name':         f"DEMO-QC-{order.name}",
                    'order_id':     order.id,
                    'state':        'pass' if scrap_pct < 0.05 else 'fail',
                    'checked_by':   env.ref('base.user_admin').id,
                    'check_date':   order_date + timedelta(days=1),
                    'is_demo_data': True,
                })

    @api.model
    def _activate_nl2sql_schema(self, industry: str):
        """NL2SQL Schema-Metadaten für die gewählte Branche aktivieren.

        Alle Domains die zur Branche gehören aktivieren —
        keine fehleranfällige domain_map + separater if-Block mehr.
        """
        SchemaTable = self.env['nl2sql.schema.table']
        # Einzige Quelle der Wahrheit: domains-Dict statt domain_map + if-Block
        domains = {
            'casting':   ['casting'],
            'machining': ['machining'],
            'both':      ['casting', 'machining'],
            'generic':   ['generic'],
        }
        for domain in domains.get(industry, ['generic']):
            SchemaTable.search([('domain', '=', domain)]).write({'active': True})
```

### 6.2 Was der Generator produziert (Gießerei-Beispiel)

Nach Wizard-Abschluss (Branche: Gießerei, 12 Monate, 200 Aufträge):

```
casting.order:         ~200 Aufträge mit realistischen Trends
  - Auftragsvolumen wächst ~5%/Monat
  - Ausschuss Winter höher (6%) als Sommer (3%)
  - Alle 4 Maschinen belegt, eine mit Häufung im letzten Monat

casting.quality.check: ~200 Prüfprotokolle (pass/fail korreliert mit Ausschuss)

NL2SQL-Schema:         casting_* Tabellen aktiviert, LLM-Kontext geladen

Sofort beantwortbare Fragen:
  "Welche Maschine hatte letzten Monat den höchsten Ausschuss?"
  "Zeige mir den Ausschuss-Trend der letzten 6 Monate nach Legierung"
  "Wie viele Aufträge wurden in Q4 2025 fertiggestellt?"
  "Welche Legierung hat die beste Ausbeute?"
```

### 6.3 Demo-Daten für Werkzeugmaschinen (Sprint 4)

```python
@api.model
def _generate_machining_data(self, months: int, order_count: int):
    """Werkzeugmaschinen-Demo: CNC-Aufträge, Maßprotokolle, Werkzeugverschleiß.

    Realistische Trends:
    - Rüstzeiten: variabel, Lernkurve (sinkt über Zeit)
    - Werkzeugstandzeit: Verschleiß-Pattern (alle N Teile Werkzeugwechsel)
    - Maßgenauigkeit: ±0.01mm Normalverteilung, gelegentliche Ausreißer
    """
    # Implementierung in Sprint 4 (mfg_machining-Modul)
    pass
```

---

## 7. Entscheidungen (D7–D9)

### D7 — Konfigurator: eigenständiges Odoo-Addon `iil_configurator` ✅ ENTSCHIEDEN

**Entscheidung:** Der Konfigurator wird als eigenständiges Odoo-Addon `iil_configurator`
implementiert. Er ist **nicht** Teil von `mfg_management`.

**Begründung:**
- Klare Separation of Concerns: Konfiguration ≠ Dashboard
- `iil_configurator` kann auch ohne `mfg_management` installiert werden
- Ermöglicht spätere Extraktion als eigenständiges SaaS-Onboarding-Tool
- `mfg_management` bleibt reines UI-Modul ohne Business-Logik

**Abhängigkeit:** `mfg_management` `depends` auf `iil_configurator`.

---

### D8 — Zweite Vertikale: Werkzeugmaschinen/CNC ✅ ENTSCHIEDEN

**Entscheidung:** `mfg_machining` wird als zweite Branchenvertikale nach `casting_foundry`
entwickelt. Zielsegment: Werkzeugmaschinenbau (VDMA: ~€14 Mrd Umsatz DE).

**Begründung:**
- Höchstes Reuse-Potential aus `casting_foundry` (~70% Code-Reuse)
- Strukturähnlichkeit: Make-to-Order, Maschinenpark, Qualitätsprüfung
- Gießereien liefern an Werkzeugmaschinenbauer → Cross-Selling-Potential
- Konfigurator-Architektur macht neue Branchen zu Registrierungs-Einträgen

**Sprint-Zuordnung:** Sprint 3 (Grundgerüst), Sprint 4 (vollständig).

---

### D9 — Demo-Daten: Pflichtbestandteil des Konfigurators ✅ ENTSCHIEDEN

**Entscheidung:** Demo-Daten-Generierung ist **kein optionales Feature** — sie ist
Standardbestandteil des Wizard-Abschlusses (`generate_demo_data=True` als Default).

**Begründung:**
- Ohne Demo-Daten ist das Dashboard nach Konfiguration leer → schlechter Ersteindruck
- Mit Demo-Daten können NL2SQL-Fragen sofort gestellt werden → "Aha-Moment" in Minuten
- Idempotenz (clear_existing=True) verhindert Datenmüll bei wiederholtem Durchlauf
- Demo-Daten-Qualität ist Verkaufsargument: realistische Trends > zufällige Zahlen

---

## 8. Technische Constraints

| Constraint | Detail |
|---|---|
| **Wizard installiert keine Module** | `iil_configurator` setzt Feature-Flags, installiert aber keine Odoo-Module zur Laufzeit. Alle Module müssen im `addons/`-Ordner deployed sein. |
| **Module-Check vor Panel-Render** | OWL prüft `depends_module` aus Feature-Registry — fehlt das Modul, wird der Panel übersprungen statt zu crashen. |
| **Demo-Daten erfordern Stammdaten** | `_generate_casting_data()` benötigt `casting.alloy`, `casting.machine`, `casting.mold` — diese kommen aus `casting_foundry`-Demo-XML, müssen vor Seed-Engine vorhanden sein. |
| **Idempotenz** | `action_apply()` ist Savepoint-geschützt. Feature-Flags werden aktualisiert, nicht dupliziert. Demo-Daten werden ersetzt (`is_demo_data=True` Filter). |
| **is_demo_data Pflichtfeld** | `casting.order` und `casting.quality.check` (sowie künftig alle Seed-fähigen Models) benötigen `is_demo_data = fields.Boolean(default=False)`. Dieses Feld muss in `casting_foundry` ergänzt werden — **Migrations-Task Sprint 2**. |
| **Multi-Tenant** | `iil.product.feature` erhält `company_id`-Feld in Sprint 4. Bis dahin: eine Konfiguration pro Instanz. |
| **ACL für get_active_features()** | `ir.model.access.csv` muss `read`-Recht auf `iil.product.feature` für `base.group_user` (alle User) enthalten. Fehlt diese Zeile → `Access Denied` beim Dashboard-Load für Nicht-Admins. |

---

## 9. Sprint-Plan (Konfigurator-fokussiert)

| Sprint | Aufgaben | Definition of Done |
|--------|---------|-------------------|
| **1** | ADR-004 Bugfixes (`mfg_nl2sql` C1–C4, `init.sql` H2+H3) | Kein `cr.rollback()`, kein `asyncio.run()`, `nl2sql_ro` funktionsfähig |
| **2** | `iil_configurator`: Addon-Grundgerüst, `iil.product.feature` Model, Feature-Defaults-XML, OWL-Panel-Registry in `mfg_management`, `iil_mrp`+`iil_stock` Grundgerüst | Wizard läuft durch, Dashboard zeigt konfigurierte Panels |
| **3** | Konfigurator-Wizard vollständig (5 Schritte), Demo-Daten-Generator Gießerei, `mfg_machining` Grundgerüst, NL2SQL-Schema-Metadaten Gießerei | Vollständige Gießerei-Demo in < 1h ab Leer-Instanz |
| **4** | `mfg_machining` vollständig (NC-Programme, Rüstblatt, Maßprotokoll), Demo-Daten-Generator Werkzeugmaschinen, Multi-Tenant Feature-Flags (`company_id`) | Vollständige Werkzeugmaschinen-Demo in < 1h ab Leer-Instanz |
| **5** | Self-Service-Provisionierung (Skript: Instanz + Konfigurator-API), 2 Demo-Instanzen live, GTM-Material aktualisiert | SaaS-Onboarding-Flow funktionsfähig, Produktvorschlag enthält Konfigurator als USP |

---

## 10. Vollständiges Abhängigkeitsdiagramm (Zielzustand)

```
Odoo 18 CE/Enterprise
  mrp   stock   purchase   maintenance   sale   account
   │      │        │            │          │        │
   └──────┴────────┴────────────┴──────────┴────────┘
                        │
              ┌──────────┴──────────┐
              │                     │
           iil_mrp              iil_stock
       (MRP-Erweiterung)    (Lager-Erweiterung)
              │                     │
              └──────────┬──────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
  casting_foundry   mfg_machining   iil_configurator
  (Gießerei V1)    (CNC V2, Spr.3)  (Feature-Registry
                                     + Seed-Engine)
         │               │               │
         └───────────────┼───────────────┘
                         │
              ┌──────────┴──────────┐
              │                     │
       mfg_management           mfg_nl2sql
      (OWL-Cockpit, dynamisch)  (KI-Layer)
              │                     │
              └──────────┬──────────┘
                         │ HTTP
                   aifw_service
                  (Django, intern)
                         │
                   PostgreSQL 16
                   (nl2sql_ro)
```

---

## 11. Änderungshistorie

| Datum | Änderung |
|-------|----------|
| 2026-03-03 | Dokument erstellt. D7 (Konfigurator-Addon), D8 (Werkzeugmaschinen), D9 (Demo-Daten Pflicht) entschieden. |
| 2026-03-03 | **Rev. 2:** Kritischer Review (13 Befunde) eingearbeitet. C1: `AbstractModel`→`TransientModel`; C2: Imports an Dateikopf; C3: `is_demo_data`-Flag statt Name-Prefix; C4: `_activate_nl2sql_schema()` domains-Dict-Pattern; H1: `state = Selection` statt `step = Integer`; H2: `savepoint()` in `action_apply()`; H3: ACL-Anforderung dokumentiert; H4: OWL-18 `useService("orm")` statt `this.env.services.orm`; H5: Architekturdiagramm Seed-Engine als Subsystem; M1: `relativedelta` statt `timedelta(days=30)`; M2: `company_size` ausgewertet; M3: `__manifest__.py` ergänzt; M4: `_sql_constraints` für Integer-Felder. |
| 2026-03-03 | **Rev. 3:** Zweiter Review (4 neue Befunde) eingearbeitet. N1: `_sql_constraints`→`@api.constrains` (TransientModel-Limitation); N2: `_generate_demo_data()`-Delegationsstub im Wizard ergänzt; N3: `company_size`-Layout-Logik aus `_apply_feature_flags()` nach `_apply_dashboard_layout()` verschoben; N4: `IilSeedEngine` zurück zu `AbstractModel` (korrekt für reine `@api.model`-Service-Klassen ohne eigene DB-Records). |
| 2026-03-03 | **Rev. 4:** 3 verbleibende View-Kleinigkeiten eingearbeitet: `industry` Default `'casting'`; `nl2sql_provider` View-Hinweis `invisible="not has_nl2sql"`; `@api.model` auf `_clear_demo_data()` ergänzt. Dokument vollständig — implementierungsreif. |
