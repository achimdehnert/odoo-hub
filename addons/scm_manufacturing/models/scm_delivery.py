from odoo import models, fields, api


class ScmDelivery(models.Model):
    _name = "scm.delivery"
    _description = "Lieferung / Delivery"
    _inherit = ["mail.thread"]
    _order = "date_shipped desc, name desc"

    name = fields.Char(
        string="Lieferschein-Nr.", required=True, copy=False,
        readonly=True, default="Neu",
    )
    partner_id = fields.Many2one(
        "res.partner", string="Empfänger", required=True, tracking=True,
    )
    part_id = fields.Many2one(
        "scm.part", string="Teil", required=True,
    )
    quantity = fields.Float(
        string="Menge", required=True, digits=(10, 2),
    )
    carrier = fields.Char(string="Spediteur", tracking=True)
    tracking_number = fields.Char(string="Sendungsnummer")
    total_weight_kg = fields.Float(
        string="Gesamtgewicht (kg)", digits=(10, 2),
    )
    state = fields.Selection(
        [
            ("draft", "Entwurf"),
            ("ready", "Versandbereit"),
            ("shipped", "Versendet"),
            ("delivered", "Zugestellt"),
            ("cancelled", "Storniert"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )
    date_shipped = fields.Date(string="Versanddatum")
    date_delivered = fields.Date(string="Zustelldatum")
    stock_move_ids = fields.One2many(
        "scm.stock.move", "delivery_id", string="Lagerbewegungen",
    )
    notes = fields.Html(string="Bemerkungen")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Neu") == "Neu":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code(
                        "scm.delivery"
                    ) or "Neu"
                )
        return super().create(vals_list)

    def action_ready(self):
        self.write({"state": "ready"})

    def action_ship(self):
        self.write({
            "state": "shipped",
            "date_shipped": fields.Date.today(),
        })

    def action_deliver(self):
        self.write({
            "state": "delivered",
            "date_delivered": fields.Date.today(),
        })

    def action_cancel(self):
        self.write({"state": "cancelled"})
