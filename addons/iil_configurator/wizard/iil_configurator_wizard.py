# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class IilConfiguratorWizard(models.TransientModel):
    _name = 'iil.configurator.wizard'
    _description = 'IIL Produktkonfigurator'

    # state steuert Wizard-Navigation (Odoo-konform: Selection + statusbar)
    state = fields.Selection([
        ('step1', '1. Branche'),
        ('step2', '2. Prozesse'),
        ('step3', '3. KI-Features'),
        ('step4', '4. Dashboard'),
        ('step5', '5. Demo-Daten'),
    ], default='step1', required=True)

    # ── Schritt 1: Branche ─────────────────────────────────────────────────────
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
    # company_size → demo_order_count: small=50, medium=200, large=500
    # company_size → dashboard_layout override: small=kpi_first, large=split

    # ── Schritt 2: Prozesse ────────────────────────────────────────────────────
    has_mrp         = fields.Boolean('Fertigungsplanung (MRP)', default=True)
    has_stock       = fields.Boolean('Lagerverwaltung', default=True)
    has_procurement = fields.Boolean('Einkauf / Beschaffung', default=True)
    has_quality     = fields.Boolean('Qualitätsmanagement', default=True)
    has_maintenance = fields.Boolean('Instandhaltung', default=False)
    has_sales       = fields.Boolean('Verkauf / Auftragsabwicklung', default=False)
    has_accounting  = fields.Boolean('Finanzbuchhaltung', default=False)

    # ── Schritt 3: KI-Features ────────────────────────────────────────────────
    has_nl2sql     = fields.Boolean('KI-Analyse (NL2SQL)', default=True)
    nl2sql_provider = fields.Selection([
        ('anthropic', 'Anthropic Claude (Cloud, DSGVO-AVV)'),
        ('openai',    'OpenAI GPT-4 (Cloud, DSGVO-AVV)'),
        ('ollama',    'Lokales LLM (Hetzner, maximale Datensouveränität)'),
    ], default='anthropic')
    # View-Hinweis: nl2sql_provider mit invisible="not has_nl2sql" ausblenden

    # ── Schritt 4: Dashboard-Layout ───────────────────────────────────────────
    dashboard_layout = fields.Selection([
        ('kanban_first', 'Kanban-Board oben, KPIs unten'),
        ('kpi_first',    'KPIs oben, Kanban unten'),
        ('nl2sql_focus', 'KI-Analyse im Vordergrund'),
        ('split',        'Gleichgewichtete Panels'),
    ], default='kanban_first')

    # ── Schritt 5: Demo-Daten ─────────────────────────────────────────────────
    generate_demo_data  = fields.Boolean('Demo-Daten generieren', default=True)
    demo_months         = fields.Integer('Historische Monate', default=12)
    demo_order_count    = fields.Integer('Anzahl Demo-Aufträge', default=200)
    demo_clear_existing = fields.Boolean('Vorhandene Demo-Daten ersetzen', default=True)

    @api.constrains('demo_months', 'demo_order_count')
    def _check_demo_params(self):
        for rec in self:
            if rec.demo_months <= 0:
                raise ValidationError('Historische Monate müssen > 0 sein.')
            if rec.demo_order_count <= 0:
                raise ValidationError('Auftragsanzahl muss > 0 sein.')

    # ── Navigation ────────────────────────────────────────────────────────────
    def action_next(self):
        self.ensure_one()
        steps = ['step1', 'step2', 'step3', 'step4', 'step5']
        idx = steps.index(self.state)
        if idx < len(steps) - 1:
            self.state = steps[idx + 1]
        return self._reload()

    def action_back(self):
        self.ensure_one()
        steps = ['step1', 'step2', 'step3', 'step4', 'step5']
        idx = steps.index(self.state)
        if idx > 0:
            self.state = steps[idx - 1]
        return self._reload()

    def _reload(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    # ── Hauptaktion ───────────────────────────────────────────────────────────
    def action_apply(self):
        """Konfigurator anwenden: Feature-Flags setzen + Demo-Daten generieren.

        Transaktional gesichert: Wenn _generate_demo_data() fehlschlägt,
        werden auch Feature-Flags zurückgerollt → kein halbkonfiguriertes Dashboard.
        _apply_dashboard_layout() schreibt nur ir.config_parameter — außerhalb
        des Savepoints, kein inkonsistenter Zustand bei Layout-Fehler.
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
                'nl2sql',      80, {'provider': self.nl2sql_provider}),
        ]
        for is_active, code, seq, config in mapping:
            rec = Feature.search([('code', '=', code)], limit=1)
            vals = {'is_active': is_active, 'sequence': seq, 'config': config}
            if rec:
                rec.write(vals)
            else:
                Feature.create({**vals, 'code': code, 'label': code.title()})

    def _apply_dashboard_layout(self):
        layout = self.dashboard_layout
        if layout == 'kanban_first' and self.company_size == 'small':
            layout = 'kpi_first'
        elif layout == 'kanban_first' and self.company_size == 'large':
            layout = 'split'
        self.env['ir.config_parameter'].sudo().set_param(
            'iil.dashboard.layout', layout
        )
