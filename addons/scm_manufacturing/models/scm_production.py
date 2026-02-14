from odoo import models, fields, api


class ScmProductionOrder(models.Model):
    _name = "scm.production.order"
    _description = "Fertigungsauftrag / Production Order"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_planned desc, name desc"

    name = fields.Char(
        string="Fertigungsnummer", required=True, copy=False,
        readonly=True, default="Neu",
    )
    part_id = fields.Many2one(
        "scm.part", string="Fertigteil", required=True, tracking=True,
    )
    bom_id = fields.Many2one(
        "scm.bom", string="Stückliste", tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Entwurf"),
            ("confirmed", "Bestätigt"),
            ("in_progress", "In Fertigung"),
            ("done", "Abgeschlossen"),
            ("cancelled", "Storniert"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )
    date_planned = fields.Date(
        string="Geplantes Datum", tracking=True,
    )
    date_start = fields.Datetime(string="Produktionsstart")
    date_done = fields.Datetime(string="Fertigstellung")
    planned_qty = fields.Float(
        string="Geplante Menge", digits=(10, 2), required=True,
    )
    produced_qty = fields.Float(
        string="Produzierte Menge", digits=(10, 2), tracking=True,
    )
    scrap_qty = fields.Float(
        string="Ausschuss", digits=(10, 2),
    )
    yield_pct = fields.Float(
        compute="_compute_yield", string="Ausbeute (%)",
        store=True, digits=(5, 1),
    )
    total_cost = fields.Float(
        string="Gesamtkosten (EUR)", digits=(12, 2),
    )
    work_step_ids = fields.One2many(
        "scm.work.step", "production_id", string="Arbeitsschritte",
    )
    stock_move_ids = fields.One2many(
        "scm.stock.move", "production_id", string="Lagerbewegungen",
    )
    notes = fields.Html(string="Bemerkungen")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Neu") == "Neu":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code(
                        "scm.production.order"
                    ) or "Neu"
                )
        return super().create(vals_list)

    @api.depends("planned_qty", "produced_qty")
    def _compute_yield(self):
        for rec in self:
            if rec.planned_qty:
                rec.yield_pct = round(
                    rec.produced_qty / rec.planned_qty * 100, 1
                )
            else:
                rec.yield_pct = 0.0

    def action_confirm(self):
        self.write({"state": "confirmed"})

    def action_start(self):
        self.write({
            "state": "in_progress",
            "date_start": fields.Datetime.now(),
        })

    def action_done(self):
        self.write({
            "state": "done",
            "date_done": fields.Datetime.now(),
        })

    def action_cancel(self):
        self.write({"state": "cancelled"})


class ScmWorkStep(models.Model):
    _name = "scm.work.step"
    _description = "Arbeitsschritt / Work Step"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    production_id = fields.Many2one(
        "scm.production.order", string="Fertigungsauftrag",
        required=True, ondelete="cascade",
    )
    name = fields.Char(string="Bezeichnung", required=True)
    work_center = fields.Char(string="Arbeitsplatz")
    planned_duration_min = fields.Float(
        string="Geplante Dauer (min)", digits=(8, 1),
    )
    actual_duration_min = fields.Float(
        string="Ist-Dauer (min)", digits=(8, 1),
    )
    efficiency_pct = fields.Float(
        compute="_compute_efficiency",
        string="Effizienz (%)",
        store=True,
        digits=(5, 1),
    )
    state = fields.Selection(
        [
            ("pending", "Offen"),
            ("in_progress", "In Bearbeitung"),
            ("done", "Abgeschlossen"),
        ],
        string="Status",
        default="pending",
    )
    notes = fields.Text(string="Bemerkungen")

    @api.depends("planned_duration_min", "actual_duration_min")
    def _compute_efficiency(self):
        for rec in self:
            if rec.actual_duration_min:
                rec.efficiency_pct = round(
                    rec.planned_duration_min
                    / rec.actual_duration_min * 100, 1
                )
            else:
                rec.efficiency_pct = 0.0
