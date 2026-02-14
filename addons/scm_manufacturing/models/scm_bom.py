from odoo import models, fields, api


class ScmBom(models.Model):
    _name = "scm.bom"
    _description = "Stückliste / Bill of Materials"
    _inherit = ["mail.thread"]
    _order = "part_id, revision desc"

    part_id = fields.Many2one(
        "scm.part", string="Fertigteil", required=True,
        ondelete="cascade", tracking=True,
    )
    revision = fields.Char(
        string="Revision", required=True, default="A", tracking=True,
    )
    bom_type = fields.Selection(
        [
            ("standard", "Standard"),
            ("phantom", "Phantom / Kit"),
            ("variant", "Variante"),
        ],
        string="Stücklistentyp",
        required=True,
        default="standard",
    )
    state = fields.Selection(
        [
            ("draft", "Entwurf"),
            ("active", "Aktiv"),
            ("obsolete", "Veraltet"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )
    line_ids = fields.One2many(
        "scm.bom.line", "bom_id", string="Positionen",
    )
    line_count = fields.Integer(
        compute="_compute_line_count", string="Positionen",
    )
    total_material_cost = fields.Float(
        compute="_compute_total_cost",
        string="Materialkosten (EUR)",
        store=True,
        digits=(10, 2),
    )
    notes = fields.Text(string="Bemerkungen")

    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    @api.depends("line_ids.subtotal_cost")
    def _compute_total_cost(self):
        for rec in self:
            rec.total_material_cost = sum(
                rec.line_ids.mapped("subtotal_cost")
            )

    def action_activate(self):
        self.write({"state": "active"})

    def action_obsolete(self):
        self.write({"state": "obsolete"})


class ScmBomLine(models.Model):
    _name = "scm.bom.line"
    _description = "Stücklistenposition / BOM Line"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    bom_id = fields.Many2one(
        "scm.bom", string="Stückliste", required=True,
        ondelete="cascade",
    )
    component_id = fields.Many2one(
        "scm.part", string="Komponente", required=True,
    )
    quantity = fields.Float(
        string="Menge", required=True, default=1.0, digits=(10, 3),
    )
    unit = fields.Char(
        related="component_id.unit", string="Einheit", readonly=True,
    )
    subtotal_cost = fields.Float(
        compute="_compute_subtotal",
        string="Kosten (EUR)",
        store=True,
        digits=(10, 2),
    )
    notes = fields.Char(string="Bemerkung")

    @api.depends("component_id.standard_cost", "quantity")
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal_cost = (
                rec.quantity * rec.component_id.standard_cost
            )
