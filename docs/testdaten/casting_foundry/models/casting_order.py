from odoo import models, fields, api


class CastingOrder(models.Model):
    _name = "casting.order"
    _description = "Gießauftrag / Casting Order"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_planned desc, name desc"

    name = fields.Char(
        string="Auftragsnummer",
        required=True,
        copy=False,
        readonly=True,
        default="Neu",
    )
    partner_id = fields.Many2one("res.partner", string="Kunde", tracking=True)
    customer_reference = fields.Char(string="Kunden-Referenz")
    state = fields.Selection(
        [
            ("draft", "Entwurf"),
            ("confirmed", "Bestätigt"),
            ("in_production", "In Fertigung"),
            ("quality_check", "Qualitätsprüfung"),
            ("done", "Abgeschlossen"),
            ("cancelled", "Storniert"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )
    priority = fields.Selection(
        [("0", "Normal"), ("1", "Dringend"), ("2", "Sehr dringend")],
        string="Priorität",
        default="0",
    )
    date_planned = fields.Date(string="Geplantes Datum", tracking=True)
    date_start = fields.Datetime(string="Produktionsstart")
    date_done = fields.Datetime(string="Fertigstellung")
    # Lines
    line_ids = fields.One2many("casting.order.line", "order_id", string="Auftragspositionen")
    line_count = fields.Integer(compute="_compute_line_count", string="Positionen")
    # Totals
    total_pieces = fields.Integer(compute="_compute_totals", string="Gesamtstückzahl", store=True)
    total_weight_kg = fields.Float(
        compute="_compute_totals", string="Gesamtgewicht (kg)", store=True, digits=(10, 2),
    )
    total_scrap_pct = fields.Float(
        compute="_compute_totals", string="Ausschuss (%)", store=True, digits=(5, 1),
    )
    # Quality
    quality_check_ids = fields.One2many("casting.quality.check", "order_id", string="Prüfungen")
    quality_check_count = fields.Integer(
        compute="_compute_quality_count", string="Prüfungen",
    )
    notes = fields.Html(string="Bemerkungen")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Neu") == "Neu":
                vals["name"] = self.env["ir.sequence"].next_by_code("casting.order") or "Neu"
        return super().create(vals_list)

    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    @api.depends("line_ids.quantity", "line_ids.piece_weight_kg", "line_ids.scrap_qty")
    def _compute_totals(self):
        for rec in self:
            lines = rec.line_ids
            total_qty = sum(lines.mapped("quantity"))
            total_scrap = sum(lines.mapped("scrap_qty"))
            rec.total_pieces = total_qty
            rec.total_weight_kg = sum(l.quantity * l.piece_weight_kg for l in lines)
            rec.total_scrap_pct = (
                round(total_scrap / total_qty * 100, 1) if total_qty else 0.0
            )

    def _compute_quality_count(self):
        for rec in self:
            rec.quality_check_count = len(rec.quality_check_ids)

    def action_confirm(self):
        self.write({"state": "confirmed"})

    def action_start_production(self):
        self.write({"state": "in_production", "date_start": fields.Datetime.now()})

    def action_quality_check(self):
        self.write({"state": "quality_check"})

    def action_done(self):
        self.write({"state": "done", "date_done": fields.Datetime.now()})

    def action_cancel(self):
        self.write({"state": "cancelled"})
