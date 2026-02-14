from . import models


def _post_init_hook(env):
    """Create scheduled actions after module install."""
    model = env["ir.model"].search(
        [("model", "=", "schutztat.sync.log")], limit=1,
    )
    if not model:
        return

    crons = [
        {
            "name": "Schutztat: Sync Assessments",
            "code": "model.action_sync_assessments()",
        },
        {
            "name": "Schutztat: Sync Hazards",
            "code": "model.action_sync_hazards()",
        },
        {
            "name": "Schutztat: Sync Action Items",
            "code": "model.action_sync_actions()",
        },
    ]
    for cron in crons:
        existing = env["ir.cron"].search(
            [("name", "=", cron["name"])], limit=1,
        )
        if not existing:
            env["ir.cron"].create(
                {
                    "name": cron["name"],
                    "model_id": model.id,
                    "state": "code",
                    "code": cron["code"],
                    "interval_number": 15,
                    "interval_type": "minutes",
                    "active": True,
                }
            )
