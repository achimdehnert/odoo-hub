from odoo import models, fields, api


class ScmPartCategory(models.Model):
    _name = "scm.part.category"
    _description = "Teilekategorie / Part Category"
    _order = "name"

    name = fields.Char(string="Bezeichnung", required=True)
    code = fields.Char(string="Kurzzeichen", index=True)
    parent_id = fields.Many2one(
        "scm.part.category", string="Übergeordnet", ondelete="cascade",
    )
    child_ids = fields.One2many(
        "scm.part.category", "parent_id", string="Unterkategorien",
    )
    part_count = fields.Integer(
        compute="_compute_part_count", string="Anz. Teile",
    )

    def _compute_part_count(self):
        for rec in self:
            rec.part_count = self.env["scm.part"].search_count(
                [("category_id", "=", rec.id)]
            )


class ScmPart(models.Model):
    _name = "scm.part"
    _description = "Teil / Part"
    _inherit = ["mail.thread"]
    _order = "part_number"

    part_number = fields.Char(
        string="Teilenummer", required=True, index=True, tracking=True,
    )
    name = fields.Char(string="Bezeichnung", required=True, tracking=True)
    category_id = fields.Many2one(
        "scm.part.category", string="Kategorie", tracking=True,
    )
    part_type = fields.Selection(
        [
            ("raw", "Rohmaterial"),
            ("semi", "Halbfertigteil"),
            ("finished", "Fertigteil"),
            ("consumable", "Verbrauchsmaterial"),
        ],
        string="Teiletyp",
        required=True,
        default="raw",
        tracking=True,
    )
    material = fields.Char(string="Werkstoff")
    make_or_buy = fields.Selection(
        [("make", "Eigenfertigung"), ("buy", "Fremdbezug")],
        string="Make/Buy",
        required=True,
        default="buy",
    )
    standard_cost = fields.Float(
        string="Standardkosten (EUR)", digits=(10, 2),
    )
    stock_qty = fields.Float(
        string="Lagerbestand", digits=(10, 2),
    )
    unit = fields.Char(string="Einheit", default="Stk")
    weight_kg = fields.Float(string="Gewicht (kg)", digits=(8, 3))
    description = fields.Text(string="Beschreibung")
    active = fields.Boolean(default=True)

    bom_ids = fields.One2many("scm.bom", "part_id", string="Stücklisten")
    supplier_ids = fields.One2many(
        "scm.supplier.info", "part_id", string="Lieferanten",
    )
    bom_count = fields.Integer(
        compute="_compute_counts", string="Stücklisten",
    )
    supplier_count = fields.Integer(
        compute="_compute_counts", string="Lieferanten",
    )

    _sql_constraints = [
        ("part_number_uniq", "unique(part_number)",
         "Die Teilenummer muss eindeutig sein."),
    ]

    @api.depends("bom_ids", "supplier_ids")
    def _compute_counts(self):
        for rec in self:
            rec.bom_count = len(rec.bom_ids)
            rec.supplier_count = len(rec.supplier_ids)

    def action_view_boms(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Stücklisten",
            "res_model": "scm.bom",
            "view_mode": "list,form",
            "domain": [("part_id", "=", self.id)],
            "context": {"default_part_id": self.id},
        }

    def action_view_suppliers(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Lieferanten",
            "res_model": "scm.supplier.info",
            "view_mode": "list,form",
            "domain": [("part_id", "=", self.id)],
            "context": {"default_part_id": self.id},
        }
