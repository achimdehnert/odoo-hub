from odoo import models, fields


class ScmWarehouse(models.Model):
    _name = "scm.warehouse"
    _description = "Lager / Warehouse"
    _inherit = ["mail.thread"]
    _order = "code"

    name = fields.Char(string="Lagername", required=True, tracking=True)
    code = fields.Char(string="Lagercode", required=True, index=True)
    warehouse_type = fields.Selection(
        [
            ("raw", "Rohstofflager"),
            ("wip", "Zwischenlager (WIP)"),
            ("finished", "Fertigwarenlager"),
            ("quarantine", "Sperrlager"),
            ("shipping", "Versandlager"),
        ],
        string="Lagertyp",
        required=True,
        default="raw",
        tracking=True,
    )
    address = fields.Text(string="Adresse")
    capacity_pallets = fields.Integer(
        string="Kapazität (Paletten)",
    )
    manager_id = fields.Many2one(
        "res.users", string="Lagerleiter",
    )
    active = fields.Boolean(default=True)
    notes = fields.Text(string="Bemerkungen")

    stock_move_ids = fields.One2many(
        "scm.stock.move", "warehouse_id", string="Lagerbewegungen",
    )

    _sql_constraints = [
        ("code_uniq", "unique(code)",
         "Der Lagercode muss eindeutig sein."),
    ]
