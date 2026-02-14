from odoo import models, fields, api


class ScmPurchaseOrder(models.Model):
    _name = "scm.purchase.order"
    _description = "Bestellung / Purchase Order"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_order desc, name desc"

    name = fields.Char(
        string="Bestellnummer", required=True, copy=False,
        readonly=True, default="Neu",
    )
    partner_id = fields.Many2one(
        "res.partner", string="Lieferant", required=True,
        domain=[("is_company", "=", True)], tracking=True,
    )
    warehouse_id = fields.Many2one(
        "scm.warehouse", string="Ziellager", tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Entwurf"),
            ("sent", "Versendet"),
            ("confirmed", "Bestätigt"),
            ("received", "Eingegangen"),
            ("done", "Abgeschlossen"),
            ("cancelled", "Storniert"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )
    date_order = fields.Date(
        string="Bestelldatum", default=fields.Date.today, tracking=True,
    )
    date_expected = fields.Date(string="Erwartetes Lieferdatum")
    date_received = fields.Date(string="Eingangsdatum")
    incoterm = fields.Selection(
        [
            ("exw", "EXW - Ab Werk"),
            ("fca", "FCA - Frei Frachtführer"),
            ("cpt", "CPT - Fracht bezahlt"),
            ("cip", "CIP - Fracht/Versich. bezahlt"),
            ("dap", "DAP - Geliefert benannter Ort"),
            ("ddp", "DDP - Geliefert verzollt"),
        ],
        string="Incoterm",
    )
    line_ids = fields.One2many(
        "scm.purchase.line", "order_id", string="Positionen",
    )
    inspection_ids = fields.One2many(
        "scm.incoming.inspection", "purchase_id", string="Prüfungen",
    )
    total_amount = fields.Float(
        compute="_compute_total", string="Gesamtbetrag (EUR)",
        store=True, digits=(12, 2),
    )
    notes = fields.Html(string="Bemerkungen")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Neu") == "Neu":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code(
                        "scm.purchase.order"
                    ) or "Neu"
                )
        return super().create(vals_list)

    @api.depends("line_ids.subtotal")
    def _compute_total(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped("subtotal"))

    def action_send(self):
        self.write({"state": "sent"})

    def action_confirm(self):
        self.write({"state": "confirmed"})

    def action_receive(self):
        self.write({
            "state": "received",
            "date_received": fields.Date.today(),
        })

    def action_done(self):
        self.write({"state": "done"})

    def action_cancel(self):
        self.write({"state": "cancelled"})


class ScmPurchaseLine(models.Model):
    _name = "scm.purchase.line"
    _description = "Bestellposition / Purchase Line"
    _order = "order_id, sequence"

    sequence = fields.Integer(default=10)
    order_id = fields.Many2one(
        "scm.purchase.order", string="Bestellung",
        required=True, ondelete="cascade",
    )
    part_id = fields.Many2one(
        "scm.part", string="Teil", required=True,
    )
    quantity = fields.Float(
        string="Menge", required=True, default=1.0, digits=(10, 2),
    )
    unit_price = fields.Float(
        string="Stückpreis (EUR)", digits=(10, 4),
    )
    subtotal = fields.Float(
        compute="_compute_subtotal", string="Summe (EUR)",
        store=True, digits=(12, 2),
    )
    date_expected = fields.Date(string="Erwartetes Lieferdatum")
    qty_received = fields.Float(
        string="Menge eingegangen", digits=(10, 2),
    )

    @api.depends("quantity", "unit_price")
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = rec.quantity * rec.unit_price
