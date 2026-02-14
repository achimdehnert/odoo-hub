from odoo import models, fields


class CastingMaterial(models.Model):
    _name = "casting.material"
    _description = "Base Material / Grundwerkstoff"
    _inherit = ["mail.thread"]
    _order = "name"

    name = fields.Char(string="Bezeichnung", required=True, tracking=True)
    code = fields.Char(string="Kurzzeichen", required=True, index=True)
    material_type = fields.Selection(
        [
            ("ferrous", "Eisenmetall"),
            ("non_ferrous", "Nichteisenmetall"),
            ("special", "Sonderwerkstoff"),
        ],
        string="Werkstoffgruppe",
        required=True,
        default="ferrous",
        tracking=True,
    )
    density = fields.Float(string="Dichte (g/cm³)", digits=(6, 3))
    melting_point = fields.Float(string="Schmelzpunkt (°C)", digits=(6, 1))
    cost_per_kg = fields.Float(string="Preis pro kg (€)", digits=(8, 2))
    description = fields.Text(string="Beschreibung")
    active = fields.Boolean(default=True)

    alloy_ids = fields.One2many("casting.alloy", "base_material_id", string="Legierungen")
    alloy_count = fields.Integer(compute="_compute_alloy_count", string="Anz. Legierungen")

    _sql_constraints = [
        ("code_uniq", "unique(code)", "Das Kurzzeichen muss eindeutig sein."),
    ]

    def _compute_alloy_count(self):
        for rec in self:
            rec.alloy_count = len(rec.alloy_ids)
