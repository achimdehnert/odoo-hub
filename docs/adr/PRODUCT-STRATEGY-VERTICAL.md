# Produkt-Strategie: Vertikalen + Konfigurator-Architektur

| Feld | Wert |
|------|------|
| **Datum** | 2026-03-03 |
| **Basis** | PRODUCT-MODULES.md, ADR-003 D1, Maschinenbau-Analyse |
| **Status** | Entwurf — Review ausstehend |

---

## Teil 1 — Maschinenbau als zweite Vertikale

### Markteinordnung: Welcher Bereich des Maschinenbaus?

Der Maschinenbau ist heterogen. Die umsatzstärksten Segmente nach VDMA 2025:

| Segment | Umsatz DE | Odoo-Relevanz | Unser Reuse-Potential |
|---|---|---|---|
| **Werkzeugmaschinen** (Drehen, Fräsen, Schleifen) | ~€14 Mrd | ★★★★★ | Höchstes: `casting_foundry`-Pattern direkt übertragbar |
| **Antriebstechnik** (Getriebe, Motoren, Kupplungen) | ~€12 Mrd | ★★★★☆ | Hoch: Serienfertigung, BOM-intensiv |
| **Fördertechnik** (Fließbänder, Krane, Stapler) | ~€8 Mrd | ★★★☆☆ | Mittel: MRO-lastig |
| **Druckmaschinen / Verpackung** | ~€7 Mrd | ★★★☆☆ | Mittel |
| **Landtechnik** | ~€5 Mrd | ★★☆☆☆ | Gering (Saisonalität) |

**Empfehlung: Werkzeugmaschinen als zweite Vertikale** — aus drei Gründen:

1. **Strukturähnlichkeit zu Gießerei**: Auftragstypen (Make-to-Order, Losgröße 1–50), Maschinenpark-Verwaltung, Qualitätsprüfungen, Rüstzeiten — identisches Pattern wie `casting_foundry`
2. **Höchstes Reuse-Potential**: ~70% der `casting_foundry`-Logik wiederverwendbar
3. **Gießerei als Lieferant**: Gießereien beliefern oft Werkzeugmaschinenbauer — gemeinsame Kunden möglich, Cross-Selling

---

### Modul: `mfg_machining` — Werkzeugmaschinen-Vertikale

#### Kernprozesse im Werkzeugmaschinenbau

```
Kundenauftrag (Make-to-Order)
  └─ Arbeitsvorbereitung (Zeichnungen, NC-Programme, Werkzeugplan)
       └─ Fertigungsauftrag mit Arbeitsplänen
            ├─ Rüsten: Werkzeuge, Spannmittel, NC-Programme laden
            ├─ Bearbeitung: CNC-Drehen / -Fräsen / -Schleifen
            ├─ Zwischenmessung: Maßhaltigkeitsprüfung
            └─ Endprüfung: Qualitätsprotokoll, Abnahme
```

#### Neue Models (analog `casting_foundry`-Pattern)

```python
# addons/mfg_machining/models/

machining_material.py        # Werkstoffe: Stahl 1.0503, Aluminium 7075, ...
machining_tool.py            # Werkzeuge: Fräser, Wendeplatten, Bohrer
machining_fixture.py         # Spannmittel: Schraubstock, Spannturm, Magnetplatte
machining_nc_program.py      # NC-Programme: Maschine, Material, Revision, Datei-Ref
machining_machine.py         # CNC-Maschinen: Typ (Drehen/Fräsen), Achsen, max. Verfahrweg
machining_order.py           # Fertigungsauftrag mit Arbeitsplänen
machining_order_operation.py # Operationen: Op10 Drehen, Op20 Fräsen, Op30 Messen
machining_quality_check.py   # Maßprotokoll: Sollmaß, Istmaß, Toleranz, Ergebnis
machining_defect_type.py     # Fehlertypen: Maßabweichung, Rauheit, Riss, ...
machining_setup_sheet.py     # Rüstblatt: Werkzeuge, Spannmittel, Nullpunkt
```

#### Wiederverwendung aus `casting_foundry`

| `casting_foundry` | `mfg_machining` | Strategie |
|---|---|---|
| `casting_material` | `machining_material` | Neues Model, gleiche Struktur |
| `casting_machine` | `machining_machine` | `_inherit`-Pattern + Maschinentyp CNC |
| `casting_order` | `machining_order` | Neues Model, identisches State-Pattern |
| `casting_quality_check` | `machining_quality_check` | Erweitert um Maßprotokoll (Soll/Ist/Toleranz) |
| `casting_defect_type` | `machining_defect_type` | Neues Model, gleiche Struktur |
| — | `machining_tool` | **Neu** — kein Pendant in Gießerei |
| — | `machining_nc_program` | **Neu** — kein Pendant in Gießerei |
| — | `machining_setup_sheet` | **Neu** — kein Pendant in Gießerei |

#### `mfg_machining` Manifest (Zielstruktur)

```python
# addons/mfg_machining/__manifest__.py
{
    "name": "IIL Machining — CNC/Werkzeugmaschinen",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "summary": "CNC-Fertigung: Aufträge, Werkzeuge, NC-Programme, Maßprotokolle",
    "author": "IIL",
    "license": "LGPL-3",
    "depends": [
        "base", "mail",
        "iil_mrp",          # Odoo-MRP-Basis (mrp.production, mrp.workcenter)
        "product",          # Fertigteil als Odoo-Produkt
    ],
    "data": [
        "security/machining_security.xml",
        "security/ir.model.access.csv",
        "data/machining_sequence.xml",
        "data/machining_defect_types.xml",
        "views/machining_machine_views.xml",
        "views/machining_tool_views.xml",
        "views/machining_order_views.xml",
        "views/machining_quality_views.xml",
        "views/machining_menus.xml",
    ],
    "installable": True,
    "application": True,
}
```

---

### Produktmatrix: Gießerei vs. Werkzeugmaschinen vs. Gemeinsam

```
                    GEMEINSAME BASIS (immer installiert)
┌───────────────────────────────────────────────────────────────┐
│  iil_mrp       iil_stock      mfg_nl2sql     mfg_management  │
│  (MRP-Basis)   (Lager-Basis)  (KI-Layer)     (Cockpit-UI)    │
└───────────────────────────────────────────────────────────────┘
              │                           │
    ┌─────────┘                           └──────────┐
    ▼                                                ▼
VERTIKAL: Gießerei                      VERTIKAL: Werkzeugmaschinen
┌──────────────────────┐               ┌──────────────────────────┐
│  casting_foundry     │               │  mfg_machining           │
│  - casting_material  │               │  - machining_material    │
│  - casting_alloy     │               │  - machining_tool        │
│  - casting_mold      │               │  - machining_nc_program  │
│  - casting_machine   │               │  - machining_machine     │
│  - casting_order     │               │  - machining_order       │
│  - casting_quality   │               │  - machining_quality     │
└──────────────────────┘               └──────────────────────────┘
```

**Ein Kunde = eine Vertikale + gemeinsame Basis.** Beide Vertikalen gleichzeitig nur bei Betrieben die beides machen (Gießen + Bearbeiten — gibt es, z.B. Aluminium-Druckguss mit CNC-Nachbearbeitung).

---

## Teil 2 — Konfigurator-Architektur: Dynamische OWL-Views

### Ist das möglich? — **Ja, vollständig.**

Odoo 18 + OWL 3 bieten alle notwendigen Primitiven. Das Konzept nennt sich in Odoo **"Module as Feature Flags"** kombiniert mit **dynamischem OWL-Component-Registry**.

---

### Architektur: 3 Schichten

```
┌─────────────────────────────────────────────────────────────┐
│ SCHICHT 3: Konfigurator-UI (Onboarding-Wizard)              │
│  → Fragebogen → feature_flags → Odoo ir.config_parameter   │
└──────────────────────────┬──────────────────────────────────┘
                           │ schreibt
┌──────────────────────────▼──────────────────────────────────┐
│ SCHICHT 2: Feature-Registry (Odoo Model)                    │
│  iil.product.feature — DB-Tabelle der aktivierten Features  │
│  { feature_code: "casting", "machining", "nl2sql", ... }   │
└──────────────────────────┬──────────────────────────────────┘
                           │ liest
┌──────────────────────────▼──────────────────────────────────┐
│ SCHICHT 1: Dynamisches OWL-Cockpit (mfg_management)         │
│  ComponentRegistry.add() — nur aktivierte Komponenten laden │
│  Dashboard baut sich aus Feature-Flags zusammen             │
└─────────────────────────────────────────────────────────────┘
```

---

### Schicht 1 — Dynamisches OWL-Cockpit

```javascript
// addons/mfg_management/static/src/js/mfg_dashboard.js

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";

// Alle verfügbaren Panel-Komponenten registrieren
// (werden nur gerendert wenn Feature aktiv)
import { CastingKanbanPanel }   from "./panels/casting_kanban";
import { MachiningKanbanPanel } from "./panels/machining_kanban";
import { MachineStatusPanel }   from "./panels/machine_status";
import { StockOverviewPanel }   from "./panels/stock_overview";
import { NL2SQLPanel }          from "./panels/nl2sql_panel";
import { ScmOverviewPanel }     from "./panels/scm_overview";

// Panel-Registry: feature_code → Komponente
const PANEL_REGISTRY = {
    casting:    CastingKanbanPanel,
    machining:  MachiningKanbanPanel,
    machines:   MachineStatusPanel,
    stock:      StockOverviewPanel,
    nl2sql:     NL2SQLPanel,
    scm:        ScmOverviewPanel,
};

export class MfgDashboard extends Component {
    static template = "mfg_management.Dashboard";

    setup() {
        this.state = useState({ activeFeatures: [], panels: [] });
        onWillStart(async () => {
            // Feature-Flags aus DB laden (einmaliger RPC-Call)
            const features = await this.env.services.orm.call(
                "iil.product.feature",
                "get_active_features",
                [],
            );
            // Nur aktivierte Panels in Render-Liste aufnehmen
            this.state.activeFeatures = features;
            this.state.panels = features
                .filter(f => PANEL_REGISTRY[f.code])
                .sort((a, b) => a.sequence - b.sequence)
                .map(f => ({
                    code:      f.code,
                    label:     f.label,
                    component: PANEL_REGISTRY[f.code],
                    config:    f.config,   // JSON-Konfiguration aus DB
                }));
        });
    }
}
```

```xml
<!-- addons/mfg_management/static/src/xml/dashboard.xml -->
<templates>
  <t t-name="mfg_management.Dashboard">
    <div class="iil-mfg-dashboard">
      <!-- Nur aktivierte Panels rendern — vollständig dynamisch -->
      <t t-foreach="state.panels" t-as="panel" t-key="panel.code">
        <t t-component="panel.component"
           config="panel.config"
           label="panel.label"/>
      </t>
      <!-- Leerer Zustand wenn keine Features aktiv -->
      <t t-if="state.panels.length === 0">
        <div class="iil-empty-state">
          Keine Module konfiguriert. Bitte den Einrichtungsassistenten starten.
        </div>
      </t>
    </div>
  </t>
</templates>
```

---

### Schicht 2 — Feature-Registry (Odoo Model)

```python
# addons/mfg_management/models/iil_product_feature.py

from odoo import api, fields, models
import json


class IilProductFeature(models.Model):
    """DB-Tabelle der aktivierten Produkt-Features pro Instanz.

    Wird durch den Konfigurator-Wizard befüllt.
    Steuert welche OWL-Panels im Dashboard gerendert werden.
    """
    _name = 'iil.product.feature'
    _description = 'IIL Produkt-Feature'
    _order = 'sequence'

    code = fields.Char(
        string='Feature-Code',
        required=True,
        index=True,
        help='Technischer Code: casting, machining, stock, nl2sql, scm, machines',
    )
    label = fields.Char(string='Bezeichnung', required=True)
    is_active = fields.Boolean(string='Aktiv', default=True, index=True)
    sequence = fields.Integer(string='Reihenfolge', default=10)
    config = fields.Json(
        string='Konfiguration',
        default=dict,
        help='Feature-spezifische JSON-Konfiguration (Farben, Limits, etc.)',
    )
    depends_module = fields.Char(
        string='Odoo-Modul',
        help='Technischer Modulname — wird geprüft ob installiert',
    )

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Feature-Code muss eindeutig sein.'),
    ]

    @api.model
    def get_active_features(self):
        """RPC-Endpoint für OWL-Dashboard: gibt aktive Features zurück."""
        features = self.search([('is_active', '=', True)], order='sequence')
        return [
            {
                'code':     f.code,
                'label':    f.label,
                'sequence': f.sequence,
                'config':   f.config or {},
            }
            for f in features
        ]

    @api.model
    def activate_feature(self, code: str, config: dict = None):
        """Aktiviert ein Feature — idempotent."""
        existing = self.search([('code', '=', code)], limit=1)
        if existing:
            existing.write({'is_active': True, 'config': config or existing.config})
        # Wenn nicht vorhanden: wird durch Wizard-XML angelegt
        return True

    @api.model
    def deactivate_feature(self, code: str):
        """Deaktiviert ein Feature — Daten bleiben erhalten."""
        self.search([('code', '=', code)]).write({'is_active': False})
        return True
```

---

### Schicht 3 — Konfigurator-Wizard (Onboarding-Fragebogen)

```python
# addons/mfg_management/wizard/iil_configurator_wizard.py

from odoo import api, fields, models


class IilConfiguratorWizard(models.TransientModel):
    """Schritt-für-Schritt Konfigurations-Assistent.

    Fragebogen → Feature-Flags → Dashboard-Aufbau.
    Kann jederzeit erneut ausgeführt werden (idempotent).
    """
    _name = 'iil.configurator.wizard'
    _description = 'IIL Produkt-Konfigurator'

    # ── Schritt 1: Branche ──────────────────────────────────────────────────
    industry = fields.Selection(
        selection=[
            ('casting',   'Gießerei / Druckguss'),
            ('machining', 'Werkzeugmaschinen / CNC-Fertigung'),
            ('both',      'Gießerei + CNC-Nachbearbeitung'),
            ('generic',   'Sonstige Fertigung'),
        ],
        string='Branche',
        required=True,
        help='Bestimmt welche Branchenmodule aktiviert werden',
    )

    # ── Schritt 2: Prozesse ──────────────────────────────────────────────────
    has_stock_management = fields.Boolean(
        string='Lagerverwaltung',
        default=True,
        help='Mehrlager, Chargen, Seriennummern, Barcode',
    )
    has_procurement = fields.Boolean(
        string='Einkauf / Beschaffung',
        default=True,
        help='Bestellwesen, Lieferantenmanagement, Rahmenverträge',
    )
    has_mrp = fields.Boolean(
        string='Fertigungsplanung (MRP)',
        default=True,
        help='Stücklisten, Kapazitätsplanung, Fertigungsaufträge',
    )
    has_quality = fields.Boolean(
        string='Qualitätsmanagement',
        default=True,
        help='Prüfpläne, Abweichungen, Qualitätsprotokolle',
    )
    has_maintenance = fields.Boolean(
        string='Instandhaltung',
        default=False,
        help='Wartungspläne, Störmeldungen, Ersatzteile',
    )

    # ── Schritt 3: KI-Features ───────────────────────────────────────────────
    has_nl2sql = fields.Boolean(
        string='KI-Analyse (NL2SQL)',
        default=True,
        help='Natürlichsprachliche Datenabfragen per KI',
    )
    nl2sql_llm_provider = fields.Selection(
        selection=[
            ('anthropic', 'Anthropic Claude (Cloud)'),
            ('openai',    'OpenAI GPT-4 (Cloud)'),
            ('ollama',    'Lokales LLM (DSGVO-maximal, Hetzner)'),
        ],
        string='KI-Anbieter',
        default='anthropic',
    )

    # ── Schritt 4: Dashboard-Layout ──────────────────────────────────────────
    dashboard_layout = fields.Selection(
        selection=[
            ('kanban_first',  'Kanban-Board oben, KPIs unten'),
            ('kpi_first',     'KPIs oben, Kanban unten'),
            ('nl2sql_focus',  'KI-Analyse im Vordergrund'),
            ('split',         'Gleichgewichtete Panels'),
        ],
        string='Dashboard-Layout',
        default='kanban_first',
    )

    # ── Schritt 5: Benutzerrollen ─────────────────────────────────────────────
    setup_roles = fields.Boolean(
        string='Benutzerrollen einrichten',
        default=True,
        help='Manager, Planer, Shopfloor-User, Analyst',
    )

    def action_apply(self):
        """Konfigurations-Fragebogen anwenden — Feature-Flags schreiben."""
        self.ensure_one()
        Feature = self.env['iil.product.feature']

        # Feature-Map: Fragebogen-Feld → Feature-Code + Sequenz
        feature_map = [
            # Branche
            (self.industry in ('casting', 'both'),   'casting',   10, {'color': 'orange'}),
            (self.industry in ('machining', 'both'),  'machining', 20, {'color': 'blue'}),
            # Prozesse
            (self.has_mrp,              'mrp',         30, {}),
            (self.has_stock_management, 'stock',       40, {}),
            (self.has_procurement,      'scm',         50, {}),
            (self.has_quality,          'quality',     60, {}),
            (self.has_maintenance,      'maintenance', 70, {}),
            # Maschinen-Panel immer wenn Branche aktiv
            (self.industry != 'generic', 'machines',  25, {}),
            # KI
            (self.has_nl2sql,           'nl2sql',      80,
             {'provider': self.nl2sql_llm_provider}),
        ]

        for is_active, code, sequence, config in feature_map:
            existing = Feature.search([('code', '=', code)], limit=1)
            vals = {
                'is_active': is_active,
                'sequence':  sequence,
                'config':    config,
            }
            if existing:
                existing.write(vals)
            else:
                existing.create({**vals, 'code': code, 'label': code.title()})

        # Dashboard-Layout als ir.config_parameter speichern
        self.env['ir.config_parameter'].sudo().set_param(
            'iil.dashboard.layout', self.dashboard_layout
        )

        # Wizard schließen + Dashboard neu laden
        return {
            'type': 'ir.actions.client',
            'tag':  'mfg_management.dashboard',
            'params': {'reconfigure': True},
        }
```

---

### Fragebogen — visueller Ablauf

```
┌─────────────────────────────────────────────────────────────┐
│  IIL Produktions-Konfigurator                               │
│  ══════════════════════════════                             │
│                                                             │
│  Schritt 1/5 — Branche                                      │
│  ○ Gießerei / Druckguss                                     │
│  ● Werkzeugmaschinen / CNC-Fertigung           ← ausgewählt │
│  ○ Gießerei + CNC-Nachbearbeitung                           │
│  ○ Sonstige Fertigung                                       │
│                                                             │
│  Schritt 2/5 — Prozesse aktivieren                          │
│  ☑ Lagerverwaltung (Mehrlager, Chargen, Barcode)            │
│  ☑ Einkauf / Beschaffung                                    │
│  ☑ Fertigungsplanung (MRP)                                  │
│  ☑ Qualitätsmanagement                                      │
│  ☐ Instandhaltung                                           │
│                                                             │
│  Schritt 3/5 — KI-Analyse                                   │
│  ☑ NL2SQL aktivieren                                        │
│    Anbieter: ● Anthropic Claude  ○ OpenAI  ○ Lokal          │
│                                                             │
│  Schritt 4/5 — Dashboard-Layout                             │
│  ● Kanban-Board oben, KPIs unten                            │
│  ○ KPIs oben, Kanban unten                                  │
│  ○ KI-Analyse im Vordergrund                                │
│                                                             │
│  Schritt 5/5 — Benutzerrollen                               │
│  ☑ Manager, Planer, Shopfloor-User, Analyst einrichten      │
│                                                             │
│  [ Zurück ]                    [ Konfiguration anwenden ] ► │
└─────────────────────────────────────────────────────────────┘
```

---

### Was nach dem Wizard passiert

```
Konfigurator schreibt:
  iil.product.feature:
    casting   → is_active=False  (Werkzeugmaschinen-Kunde)
    machining → is_active=True
    mrp       → is_active=True
    stock     → is_active=True
    nl2sql    → is_active=True, config={provider: "anthropic"}
    machines  → is_active=True

OWL-Dashboard lädt:
  get_active_features() → [machining, mrp, stock, machines, nl2sql]

Dashboard rendert:
  ┌──────────────────┬──────────────────┐
  │ MachiningKanban  │ MachineStatus    │
  │ (CNC-Aufträge)   │ (Live-Zustand)   │
  ├──────────────────┴──────────────────┤
  │ StockOverview (Lager + Einkauf)     │
  ├─────────────────────────────────────┤
  │ NL2SQLPanel (KI-Abfragen)           │
  └─────────────────────────────────────┘

  → casting_foundry-Panels: NICHT gerendert (is_active=False)
  → kein if/else im JS — reine Registry-Steuerung
```

---

### Technische Machbarkeit — Bewertung

| Anforderung | Machbar? | Aufwand |
|---|---|---|
| Feature-Flags in DB | ✅ `iil.product.feature` Model | 1 Tag |
| OWL-Panels dynamisch laden | ✅ `PANEL_REGISTRY` + `t-component` | 2 Tage |
| Konfigurator-Wizard | ✅ `models.TransientModel` | 2 Tage |
| Neue Branche (`mfg_machining`) | ✅ Pattern von `casting_foundry` | 1–2 Wochen |
| NL2SQL-Schema für neue Branche | ✅ XML-Daten in `mfg_nl2sql` | 1 Tag je Branche |
| **Gesamt Sprint 2+3** | ✅ | **~3 Wochen** |

---

### Einschränkungen + Risiken

| Punkt | Detail |
|---|---|
| **Odoo-Module installieren** | `iil.product.feature` steuert nur OWL-Visibility, nicht ob Odoo-Module installiert sind. Wenn `casting_foundry` nicht installiert ist, crasht `CastingKanbanPanel` beim RPC-Call. → Lösung: `depends_module`-Feld prüfen vor Panel-Render |
| **Wizard ist kein App-Store** | Der Wizard aktiviert/deaktiviert Features in der DB — er installiert keine Odoo-Module zur Laufzeit. Module müssen vorher deployed sein (in `addons/`). |
| **Multi-Tenant** | Pro-Kunde-Konfiguration erfordert company-abhängige Feature-Flags (`company_id` auf `iil.product.feature`). Für Sprint 4 vorgesehen. |

---

## Erweiterter Sprint-Plan

| Sprint | Aufgaben |
|--------|---------|
| **Sprint 1** | ADR-004 Bugfixes (C1–C4), init.sql Fix (H2+H3) |
| **Sprint 2** | `iil_mrp` + `iil_stock` Grundgerüst, `iil.product.feature` Model, OWL-Panel-Registry |
| **Sprint 3** | Konfigurator-Wizard, `mfg_machining` Grundgerüst (Pattern von `casting_foundry`), Schema-Metadaten |
| **Sprint 4** | `mfg_machining` vollständig (NC-Programme, Rüstblatt, Maßprotokoll), Multi-Tenant Feature-Flags |
| **Sprint 5** | GTM: 2 Demo-Instanzen (Gießerei + Werkzeugmaschinen), Produktvorschlag aktualisieren |
