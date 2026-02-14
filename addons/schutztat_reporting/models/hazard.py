"""Schutztat Hazard model (synced from Django risk-hub)."""

from odoo import fields, models


class SchutztatHazard(models.Model):
    _name = "schutztat.hazard"
    _description = "Hazard"
    _order = "risk_score desc, synced_at desc"
    _rec_name = "title"

    django_id = fields.Char(
        string="Django UUID",
        required=True,
        index=True,
        readonly=True,
    )
    tenant_id = fields.Char(
        string="Tenant ID",
        readonly=True,
        index=True,
    )
    assessment_id = fields.Many2one(
        "schutztat.assessment",
        string="Assessment",
        ondelete="cascade",
    )
    assessment_django_id = fields.Char(
        string="Assessment Django ID",
        index=True,
    )
    title = fields.Char(string="Title", required=True)
    description = fields.Text(string="Description")
    severity = fields.Integer(string="Severity", default=1)
    probability = fields.Integer(string="Probability", default=1)
    risk_score = fields.Integer(
        string="Risk Score",
        readonly=True,
    )
    mitigation = fields.Text(string="Mitigation")
    django_created_at = fields.Datetime(
        string="Created (Django)",
        readonly=True,
    )
    django_updated_at = fields.Datetime(
        string="Updated (Django)",
        readonly=True,
    )
    synced_at = fields.Datetime(
        string="Last Synced",
        readonly=True,
    )

    risk_level = fields.Selection(
        [
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("critical", "Critical"),
        ],
        string="Risk Level",
        compute="_compute_risk_level",
        store=True,
    )

    _sql_constraints = [
        (
            "django_id_unique",
            "UNIQUE(django_id)",
            "Django ID must be unique.",
        ),
    ]

    def _compute_risk_level(self):
        for rec in self:
            score = rec.risk_score or 0
            if score >= 15:
                rec.risk_level = "critical"
            elif score >= 9:
                rec.risk_level = "high"
            elif score >= 4:
                rec.risk_level = "medium"
            else:
                rec.risk_level = "low"
