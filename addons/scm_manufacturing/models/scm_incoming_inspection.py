from odoo import models, fields


class ScmIncomingInspection(models.Model):
    _name = "scm.incoming.inspection"
    _description = "Wareneingangsprüfung / Incoming Inspection"
    _inherit = ["mail.thread"]
    _order = "inspection_date desc"

    purchase_id = fields.Many2one(
        "scm.purchase.order", string="Bestellung",
        required=True, ondelete="cascade", tracking=True,
    )
    inspector_id = fields.Many2one(
        "res.users", string="Prüfer",
        default=lambda self: self.env.user,
    )
    inspection_date = fields.Datetime(
        string="Prüfdatum", default=fields.Datetime.now,
    )
    inspection_type = fields.Selection(
        [
            ("visual", "Sichtprüfung"),
            ("dimensional", "Maßprüfung"),
            ("functional", "Funktionsprüfung"),
            ("material", "Werkstoffprüfung"),
            ("documentation", "Dokumentenprüfung"),
        ],
        string="Prüfart",
        required=True,
    )
    result = fields.Selection(
        [
            ("accepted", "Angenommen"),
            ("conditional", "Bedingt angenommen"),
            ("rejected", "Abgelehnt"),
        ],
        string="Ergebnis",
        tracking=True,
    )
    sample_size = fields.Integer(string="Stichprobengröße")
    defect_count = fields.Integer(string="Fehleranzahl")
    acceptance_rate = fields.Float(
        string="Annahmequote (%)", digits=(5, 1),
    )
    certificate_type = fields.Selection(
        [
            ("none", "Kein Zeugnis"),
            ("2_1", "2.1 - Werkszeugnis"),
            ("2_2", "2.2 - Werkszeugnis"),
            ("3_1", "3.1 - Abnahmeprüfzeugnis"),
            ("3_2", "3.2 - Abnahmeprüfzeugnis"),
        ],
        string="Zeugnis nach EN 10204",
        default="none",
    )
    notes = fields.Text(string="Prüfbericht / Bemerkungen")
    corrective_action = fields.Text(string="Korrekturmaßnahme")
