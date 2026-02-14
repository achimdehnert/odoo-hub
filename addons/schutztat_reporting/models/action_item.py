"""Schutztat ActionItem model (synced from Django risk-hub)."""

from odoo import fields, models


class SchutztatActionItem(models.Model):
    _name = "schutztat.action.item"
    _description = "Action Item"
    _order = "due_date asc, priority desc"
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
    status = fields.Selection(
        [
            ("open", "Open"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="open",
    )
    priority = fields.Integer(string="Priority", default=2)
    due_date = fields.Date(string="Due Date")
    assigned_to_id = fields.Char(string="Assigned To ID")
    assessment_id = fields.Many2one(
        "schutztat.assessment",
        string="Assessment",
        ondelete="set null",
    )
    assessment_django_id = fields.Char(
        string="Assessment Django ID",
        index=True,
    )
    hazard_id = fields.Many2one(
        "schutztat.hazard",
        string="Hazard",
        ondelete="set null",
    )
    hazard_django_id = fields.Char(
        string="Hazard Django ID",
        index=True,
    )
    completed_at = fields.Datetime(string="Completed At")
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
    is_overdue = fields.Boolean(
        string="Overdue",
        compute="_compute_is_overdue",
    )

    _sql_constraints = [
        (
            "django_id_unique",
            "UNIQUE(django_id)",
            "Django ID must be unique.",
        ),
    ]

    def _compute_is_overdue(self):
        today = fields.Date.today()
        for rec in self:
            rec.is_overdue = (
                rec.due_date
                and rec.due_date < today
                and rec.status in ("open", "in_progress")
            )
