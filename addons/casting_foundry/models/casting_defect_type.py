from odoo import models, fields


class CastingDefectType(models.Model):
    _name = "casting.defect.type"
    _description = "Fehlerart / Defect Type"
    _order = "category, name"

    name = fields.Char(string="Fehlerbezeichnung", required=True)
    code = fields.Char(string="Fehlercode", required=True, index=True)
    category = fields.Selection(
        [
            ("porosity", "Porosität / Lunker"),
            ("surface", "Oberflächenfehler"),
            ("dimensional", "Maßabweichung"),
            ("crack", "Riss / Bruch"),
            ("inclusion", "Einschlüsse"),
            ("cold_shut", "Kaltlauf / Kaltschweißung"),
            ("misrun", "Formfüllung unvollständig"),
            ("shrinkage", "Schwindung"),
            ("distortion", "Verzug"),
            ("other", "Sonstiges"),
        ],
        string="Fehlerkategorie",
        required=True,
    )
    severity = fields.Selection(
        [
            ("minor", "Gering (kosmetisch)"),
            ("major", "Erheblich (funktionsrelevant)"),
            ("critical", "Kritisch (sicherheitsrelevant)"),
        ],
        string="Schweregrad",
        required=True,
        default="minor",
    )
    description = fields.Text(string="Beschreibung / Ursache")
    remedy = fields.Text(string="Abhilfemaßnahme")
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("code_uniq", "unique(code)", "Der Fehlercode muss eindeutig sein."),
    ]
