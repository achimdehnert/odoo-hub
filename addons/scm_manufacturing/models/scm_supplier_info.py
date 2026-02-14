from odoo import models, fields


class ScmSupplierInfo(models.Model):
    _name = "scm.supplier.info"
    _description = "Lieferanteninformation / Supplier Info"
    _inherit = ["mail.thread"]
    _order = "priority, partner_id"

    part_id = fields.Many2one(
        "scm.part", string="Teil", required=True,
        ondelete="cascade", tracking=True,
    )
    partner_id = fields.Many2one(
        "res.partner", string="Lieferant", required=True,
        domain=[("is_company", "=", True)], tracking=True,
    )
    priority = fields.Selection(
        [
            ("1", "Hauptlieferant"),
            ("2", "Zweitlieferant"),
            ("3", "Ersatzlieferant"),
        ],
        string="Priorität",
        default="2",
        required=True,
    )
    rating = fields.Selection(
        [
            ("a", "A - Bevorzugt"),
            ("b", "B - Qualifiziert"),
            ("c", "C - Bedingt"),
            ("d", "D - Gesperrt"),
        ],
        string="Bewertung",
        default="b",
    )
    supplier_part_number = fields.Char(
        string="Lieferanten-Teilenr.",
    )
    price = fields.Float(
        string="Einkaufspreis (EUR)", digits=(10, 4), tracking=True,
    )
    min_order_qty = fields.Float(
        string="Mindestbestellmenge", digits=(10, 2),
    )
    lead_time_days = fields.Integer(
        string="Lieferzeit (Tage)", tracking=True,
    )
    on_time_delivery_pct = fields.Float(
        string="Liefertreue (%)", digits=(5, 1),
    )
    currency = fields.Char(string="Währung", default="EUR")
    notes = fields.Text(string="Bemerkungen")
    active = fields.Boolean(default=True)
