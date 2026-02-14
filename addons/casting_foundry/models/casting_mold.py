from odoo import models, fields, api


class CastingMold(models.Model):
    _name = "casting.mold"
    _description = "Gussform / Mold"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char(string="Formbezeichnung", required=True, tracking=True)
    code = fields.Char(string="Form-Nr.", required=True, index=True, copy=False)
    mold_type = fields.Selection(
        [
            ("permanent", "Kokille / Dauerform"),
            ("sand", "Sandform"),
            ("die_cast", "Druckgussform"),
            ("investment", "Feingussform"),
            ("centrifugal", "Schleudergussform"),
            ("shell", "Maskenform"),
        ],
        string="Formtyp",
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("new", "Neu"),
            ("active", "Im Einsatz"),
            ("maintenance", "In Wartung"),
            ("retired", "Ausgemustert"),
        ],
        string="Status",
        default="new",
        required=True,
        tracking=True,
    )
    alloy_ids = fields.Many2many("casting.alloy", string="Geeignete Legierungen")
    # Dimensions
    cavity_count = fields.Integer(string="Anz. Kavitäten", default=1)
    part_weight_kg = fields.Float(string="Teilegewicht (kg)", digits=(8, 3))
    cycle_time_min = fields.Float(string="Zykluszeit (min)", digits=(6, 1))
    max_shots = fields.Integer(string="Max. Abgüsse (Lebensdauer)")
    current_shots = fields.Integer(string="Bisherige Abgüsse", tracking=True)
    # Costs
    acquisition_cost = fields.Float(string="Anschaffungskosten (€)", digits=(10, 2))
    maintenance_cost = fields.Float(string="Wartungskosten kum. (€)", digits=(10, 2))
    # Relations
    machine_id = fields.Many2one("casting.machine", string="Zugeordnete Maschine")
    order_line_ids = fields.One2many("casting.order.line", "mold_id", string="Auftragszeilen")
    notes = fields.Html(string="Notizen")
    active = fields.Boolean(default=True)

    remaining_shots = fields.Integer(
        compute="_compute_remaining_shots", string="Restliche Abgüsse", store=True,
    )
    utilization_pct = fields.Float(
        compute="_compute_remaining_shots", string="Auslastung (%)", store=True,
    )

    _sql_constraints = [
        ("code_uniq", "unique(code)", "Die Form-Nr. muss eindeutig sein."),
    ]

    @api.depends("max_shots", "current_shots")
    def _compute_remaining_shots(self):
        for rec in self:
            if rec.max_shots:
                rec.remaining_shots = max(rec.max_shots - rec.current_shots, 0)
                rec.utilization_pct = round(rec.current_shots / rec.max_shots * 100, 1)
            else:
                rec.remaining_shots = 0
                rec.utilization_pct = 0.0
