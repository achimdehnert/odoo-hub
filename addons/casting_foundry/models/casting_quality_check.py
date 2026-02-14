from odoo import models, fields


class CastingQualityCheck(models.Model):
    _name = "casting.quality.check"
    _description = "Qualitätsprüfung / Quality Check"
    _inherit = ["mail.thread"]
    _order = "check_date desc"

    name = fields.Char(string="Prüf-Nr.", required=True, copy=False, readonly=True, default="Neu")
    order_id = fields.Many2one("casting.order", string="Auftrag", required=True, ondelete="cascade")
    order_line_id = fields.Many2one("casting.order.line", string="Position")
    inspector_id = fields.Many2one("res.users", string="Prüfer", default=lambda self: self.env.user)
    check_date = fields.Datetime(string="Prüfzeitpunkt", default=fields.Datetime.now)
    check_type = fields.Selection(
        [
            ("visual", "Sichtprüfung"),
            ("dimensional", "Maßprüfung"),
            ("xray", "Röntgenprüfung"),
            ("ultrasonic", "Ultraschallprüfung"),
            ("hardness", "Härteprüfung"),
            ("tensile", "Zugversuch"),
            ("spectrometry", "Spektrometrie"),
            ("leak", "Dichtheitsprüfung"),
            ("cmm", "3D-Koordinatenmessung"),
        ],
        string="Prüfart",
        required=True,
        tracking=True,
    )
    result = fields.Selection(
        [
            ("pass", "Bestanden (i.O.)"),
            ("conditional", "Bedingt bestanden"),
            ("fail", "Nicht bestanden (n.i.O.)"),
        ],
        string="Ergebnis",
        tracking=True,
    )
    defect_type_ids = fields.Many2many("casting.defect.type", string="Festgestellte Fehler")
    sample_size = fields.Integer(string="Stichprobengröße")
    defect_count = fields.Integer(string="Fehleranzahl")
    # Measurement values
    measured_value = fields.Float(string="Messwert", digits=(10, 3))
    nominal_value = fields.Float(string="Sollwert", digits=(10, 3))
    tolerance_plus = fields.Float(string="Toleranz + (mm)", digits=(6, 3))
    tolerance_minus = fields.Float(string="Toleranz - (mm)", digits=(6, 3))
    notes = fields.Text(string="Prüfbericht / Bemerkungen")
    corrective_action = fields.Text(string="Korrekturmaßnahme")

    def create(self, vals_list):
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        for vals in vals_list:
            if vals.get("name", "Neu") == "Neu":
                vals["name"] = self.env["ir.sequence"].next_by_code("casting.quality.check") or "Neu"
        return super().create(vals_list)
