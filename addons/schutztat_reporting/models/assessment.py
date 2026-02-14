"""Schutztat Assessment model (synced from Django risk-hub)."""

from odoo import fields, models


class SchutztatAssessment(models.Model):
    _name = "schutztat.assessment"
    _description = "Risk Assessment"
    _order = "synced_at desc"
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
    title = fields.Char(string="Title", required=True)
    description = fields.Text(string="Description")
    category = fields.Char(string="Category")
    status = fields.Selection(
        [
            ("draft", "Draft"),
            ("in_review", "In Review"),
            ("approved", "Approved"),
            ("archived", "Archived"),
        ],
        string="Status",
        default="draft",
    )
    site_id = fields.Char(string="Site ID")
    created_by_id = fields.Char(string="Created By ID")
    approved_by_id = fields.Char(string="Approved By ID")
    approved_at = fields.Datetime(string="Approved At")
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

    hazard_ids = fields.One2many(
        "schutztat.hazard",
        "assessment_id",
        string="Hazards",
    )
    action_ids = fields.One2many(
        "schutztat.action.item",
        "assessment_id",
        string="Actions",
    )
    hazard_count = fields.Integer(
        string="Hazards",
        compute="_compute_hazard_count",
    )
    action_count = fields.Integer(
        string="Actions",
        compute="_compute_action_count",
    )

    _sql_constraints = [
        (
            "django_id_unique",
            "UNIQUE(django_id)",
            "Django ID must be unique.",
        ),
    ]

    def _compute_hazard_count(self):
        for rec in self:
            rec.hazard_count = len(rec.hazard_ids)

    def _compute_action_count(self):
        for rec in self:
            rec.action_count = len(rec.action_ids)
