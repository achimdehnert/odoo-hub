from odoo import models, fields, api


class CastingAlloy(models.Model):
    _name = "casting.alloy"
    _description = "Legierung / Alloy"
    _inherit = ["mail.thread"]
    _order = "din_number, name"

    name = fields.Char(string="Legierungsbezeichnung", required=True, tracking=True)
    din_number = fields.Char(string="DIN/EN Werkstoffnummer", index=True)
    base_material_id = fields.Many2one(
        "casting.material",
        string="Grundwerkstoff",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    alloy_type = fields.Selection(
        [
            ("cast_iron", "Gusseisen"),
            ("cast_steel", "Stahlguss"),
            ("aluminum", "Aluminium-Guss"),
            ("bronze", "Bronzeguss"),
            ("zinc", "Zinkguss"),
            ("magnesium", "Magnesiumguss"),
            ("copper", "Kupferguss"),
            ("other", "Sonstiges"),
        ],
        string="Gusstyp",
        required=True,
        tracking=True,
    )
    # Mechanical properties
    tensile_strength = fields.Float(string="Zugfestigkeit Rm (MPa)", digits=(8, 1))
    yield_strength = fields.Float(string="Streckgrenze Rp0.2 (MPa)", digits=(8, 1))
    elongation = fields.Float(string="Bruchdehnung A (%)", digits=(5, 1))
    hardness_brinell = fields.Float(string="Härte HB", digits=(6, 1))
    # Casting properties
    pouring_temp_min = fields.Float(string="Gießtemperatur min (°C)", digits=(6, 1))
    pouring_temp_max = fields.Float(string="Gießtemperatur max (°C)", digits=(6, 1))
    shrinkage_rate = fields.Float(string="Schwindmaß (%)", digits=(5, 2))
    fluidity_rating = fields.Selection(
        [("low", "Gering"), ("medium", "Mittel"), ("high", "Hoch")],
        string="Fließfähigkeit",
    )
    cost_per_kg = fields.Float(string="Legierungspreis (€/kg)", digits=(8, 2))
    description = fields.Text(string="Technische Beschreibung")
    active = fields.Boolean(default=True)

    display_name = fields.Char(compute="_compute_display_name", store=True)

    @api.depends("name", "din_number")
    def _compute_display_name(self):
        for rec in self:
            if rec.din_number:
                rec.display_name = f"{rec.name} ({rec.din_number})"
            else:
                rec.display_name = rec.name
