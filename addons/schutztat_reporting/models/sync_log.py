"""Schutztat SyncLog model — orchestrates Django API sync."""

import logging
from datetime import datetime

import requests

from odoo import fields, models

_logger = logging.getLogger(__name__)

DJANGO_API_BASE = "https://demo.schutztat.de/api/v1"

DATETIME_FIELDS = {
    "approved_at",
    "completed_at",
    "django_created_at",
    "django_updated_at",
}


def _parse_dt(value):
    """Convert ISO 8601 datetime string to Odoo format."""
    if not value:
        return False
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, AttributeError):
        return False


class SchutztatSyncLog(models.Model):
    _name = "schutztat.sync.log"
    _description = "Sync Log"
    _order = "started_at desc"

    model_name = fields.Char(string="Model", required=True)
    started_at = fields.Datetime(string="Started")
    finished_at = fields.Datetime(string="Finished")
    records_created = fields.Integer(string="Created", default=0)
    records_updated = fields.Integer(string="Updated", default=0)
    status = fields.Selection(
        [
            ("running", "Running"),
            ("done", "Done"),
            ("error", "Error"),
        ],
        string="Status",
        default="running",
    )
    error_message = fields.Text(string="Error")

    def action_sync_assessments(self):
        """Cron: sync assessments from Django."""
        self._sync_model(
            "schutztat.assessment",
            "/risk/assessments",
            {
                "id": "django_id",
                "tenant_id": "tenant_id",
                "title": "title",
                "description": "description",
                "category": "category",
                "status": "status",
                "site_id": "site_id",
                "created_by_id": "created_by_id",
                "approved_by_id": "approved_by_id",
                "approved_at": "approved_at",
                "created_at": "django_created_at",
                "updated_at": "django_updated_at",
            },
        )

    def action_sync_hazards(self):
        """Cron: sync hazards from Django."""
        self._sync_model(
            "schutztat.hazard",
            "/risk/hazards",
            {
                "id": "django_id",
                "tenant_id": "tenant_id",
                "assessment_id": "assessment_django_id",
                "title": "title",
                "description": "description",
                "severity": "severity",
                "probability": "probability",
                "risk_score": "risk_score",
                "mitigation": "mitigation",
                "created_at": "django_created_at",
                "updated_at": "django_updated_at",
            },
        )
        self._link_hazard_assessments()

    def action_sync_actions(self):
        """Cron: sync action items from Django."""
        self._sync_model(
            "schutztat.action.item",
            "/actions",
            {
                "id": "django_id",
                "tenant_id": "tenant_id",
                "title": "title",
                "description": "description",
                "status": "status",
                "priority": "priority",
                "due_date": "due_date",
                "assigned_to_id": "assigned_to_id",
                "assessment_id": "assessment_django_id",
                "hazard_id": "hazard_django_id",
                "completed_at": "completed_at",
                "created_at": "django_created_at",
                "updated_at": "django_updated_at",
            },
        )
        self._link_action_relations()

    def _sync_model(self, model_name, endpoint, field_mapping):
        """Generic sync: pull data from Django Ninja API (offset/limit)."""
        api_url = self.env["ir.config_parameter"].sudo().get_param(
            "schutztat.django_api_url",
            default=DJANGO_API_BASE,
        )
        api_key = self.env["ir.config_parameter"].sudo().get_param(
            "schutztat.django_api_key",
        )
        if not api_key:
            _logger.warning("schutztat.django_api_key not configured")
            return

        log = self.create(
            {
                "model_name": model_name,
                "started_at": fields.Datetime.now(),
            }
        )
        target = self.env[model_name].sudo()
        created, updated = 0, 0
        batch_size = 100

        try:
            offset = 0
            while True:
                resp = requests.get(
                    f"{api_url}{endpoint}",
                    headers={"Authorization": f"Bearer {api_key}"},
                    params={"limit": batch_size, "offset": offset},
                    timeout=30,
                )
                resp.raise_for_status()
                items = resp.json()

                if not items:
                    break

                for item in items:
                    vals = {}
                    for django_field, odoo_field in field_mapping.items():
                        value = item.get(django_field)
                        if odoo_field in DATETIME_FIELDS:
                            value = _parse_dt(value)
                        elif value is None:
                            value = False
                        vals[odoo_field] = value
                    vals["synced_at"] = fields.Datetime.now()

                    existing = target.search(
                        [("django_id", "=", vals["django_id"])],
                        limit=1,
                    )
                    if existing:
                        existing.write(vals)
                        updated += 1
                    else:
                        target.create(vals)
                        created += 1

                offset += batch_size
                if len(items) < batch_size:
                    break

            log.write(
                {
                    "finished_at": fields.Datetime.now(),
                    "records_created": created,
                    "records_updated": updated,
                    "status": "done",
                }
            )
            _logger.info(
                "Sync %s: %d created, %d updated",
                model_name,
                created,
                updated,
            )
        except Exception as exc:
            log.write(
                {
                    "finished_at": fields.Datetime.now(),
                    "status": "error",
                    "error_message": str(exc),
                }
            )
            _logger.exception("Sync failed for %s", model_name)

    def _link_hazard_assessments(self):
        """Link hazards to their assessment records via django_id."""
        hazards = (
            self.env["schutztat.hazard"]
            .sudo()
            .search(
                [
                    ("assessment_id", "=", False),
                    ("assessment_django_id", "!=", False),
                ]
            )
        )
        for hazard in hazards:
            assessment = (
                self.env["schutztat.assessment"]
                .sudo()
                .search(
                    [("django_id", "=", hazard.assessment_django_id)],
                    limit=1,
                )
            )
            if assessment:
                hazard.write({"assessment_id": assessment.id})

    def _link_action_relations(self):
        """Link action items to assessment and hazard records."""
        actions = (
            self.env["schutztat.action.item"]
            .sudo()
            .search(
                [
                    "|",
                    "&",
                    ("assessment_id", "=", False),
                    ("assessment_django_id", "!=", False),
                    "&",
                    ("hazard_id", "=", False),
                    ("hazard_django_id", "!=", False),
                ]
            )
        )
        for action in actions:
            vals = {}
            if not action.assessment_id and action.assessment_django_id:
                assessment = (
                    self.env["schutztat.assessment"]
                    .sudo()
                    .search(
                        [("django_id", "=", action.assessment_django_id)],
                        limit=1,
                    )
                )
                if assessment:
                    vals["assessment_id"] = assessment.id
            if not action.hazard_id and action.hazard_django_id:
                hazard = (
                    self.env["schutztat.hazard"]
                    .sudo()
                    .search(
                        [("django_id", "=", action.hazard_django_id)],
                        limit=1,
                    )
                )
                if hazard:
                    vals["hazard_id"] = hazard.id
            if vals:
                action.write(vals)
