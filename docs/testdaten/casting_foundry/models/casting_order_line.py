from odoo import models, fields, api


class CastingOrderLine(models.Model):
    _name = "casting.order.line"
    _description = "Auftragsposition / Order Line"
    _order = "order_id, sequence"

    sequence = fields.Integer(default=10)
    order_id = fields.Many2one(
        "casting.order", string="Auftrag", required=True, ondelete="cascade",
    )
    order_state = fields.Selection(related="order_id.state", string="Auftragsstatus", store=True)
    part_name = fields.Char(string="Teilebezeichnung", required=True)
    part_number = fields.Char(string="Zeichnungsnummer")
    alloy_id = fields.Many2one("casting.alloy", string="Legierung", required=True)
    mold_id = fields.Many2one("casting.mold", string="Gussform")
    machine_id = fields.Many2one("casting.machine", string="Maschine")
    casting_process = fields.Selection(
        [
            ("gravity", "Schwerkraftguss"),
            ("die_cast_hot", "Warmkammer-Druckguss"),
            ("die_cast_cold", "Kaltkammer-Druckguss"),
            ("sand", "Sandguss"),
            ("investment", "Feinguss"),
            ("centrifugal", "Schleuderguss"),
            ("continuous", "Strangguss"),
        ],
        string="Gießverfahren",
        required=True,
    )
    # Quantities
    quantity = fields.Integer(string="Stückzahl", required=True, default=1)
    scrap_qty = fields.Integer(string="Ausschuss (Stk)")
    good_qty = fields.Integer(compute="_compute_good_qty", string="Gutteile", store=True)
    piece_weight_kg = fields.Float(string="Stückgewicht (kg)", digits=(8, 3))
    total_weight_kg = fields.Float(
        compute="_compute_total_weight", string="Gesamtgewicht (kg)", store=True, digits=(10, 2),
    )
    # Pouring
    pouring_temp_c = fields.Float(string="Gießtemperatur (°C)", digits=(6, 1))
    mold_temp_c = fields.Float(string="Formtemperatur (°C)", digits=(6, 1))
    cycle_time_min = fields.Float(string="Zykluszeit (min)", digits=(6, 1))
    # Heat treatment
    heat_treatment = fields.Selection(
        [
            ("none", "Keine"),
            ("t4", "T4 - Lösungsglühen"),
            ("t5", "T5 - Warmauslagern"),
            ("t6", "T6 - Lösungsglühen + Warmauslagern"),
            ("t7", "T7 - Überaltern"),
            ("annealing", "Glühen"),
            ("normalizing", "Normalisieren"),
            ("quench_temper", "Vergüten"),
        ],
        string="Wärmebehandlung",
        default="none",
    )
    notes = fields.Text(string="Bemerkungen")

    @api.depends("quantity", "scrap_qty")
    def _compute_good_qty(self):
        for rec in self:
            rec.good_qty = rec.quantity - rec.scrap_qty

    @api.depends("quantity", "piece_weight_kg")
    def _compute_total_weight(self):
        for rec in self:
            rec.total_weight_kg = rec.quantity * rec.piece_weight_kg
