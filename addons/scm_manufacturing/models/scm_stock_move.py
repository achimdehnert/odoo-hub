from odoo import models, fields


class ScmStockMove(models.Model):
    _name = "scm.stock.move"
    _description = "Lagerbewegung / Stock Move"
    _order = "date desc, id desc"

    part_id = fields.Many2one(
        "scm.part", string="Teil", required=True, index=True,
    )
    warehouse_id = fields.Many2one(
        "scm.warehouse", string="Lager", required=True, index=True,
    )
    move_type = fields.Selection(
        [
            ("in", "Zugang"),
            ("out", "Abgang"),
            ("transfer", "Umbuchung"),
            ("adjust", "Korrektur"),
            ("scrap", "Verschrottung"),
        ],
        string="Bewegungsart",
        required=True,
    )
    quantity = fields.Float(
        string="Menge", required=True, digits=(10, 2),
    )
    lot_number = fields.Char(string="Losnummer / Charge")
    date = fields.Datetime(
        string="Datum", default=fields.Datetime.now, required=True,
    )
    reference = fields.Char(string="Referenz")
    production_id = fields.Many2one(
        "scm.production.order", string="Fertigungsauftrag",
    )
    delivery_id = fields.Many2one(
        "scm.delivery", string="Lieferung",
    )
    notes = fields.Text(string="Bemerkungen")
