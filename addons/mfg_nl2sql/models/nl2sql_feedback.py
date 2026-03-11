# -*- coding: utf-8 -*-
"""
nl2sql.feedback — Auto-captured SQL errors + manuelle Korrekturen.

Wird automatisch von NL2SQLEngine bei SQL-Ausführungsfehlern befüllt.
Manager kann corrected_sql setzen und via action_promote zu Example promoten.
"""
import logging

import requests
from odoo import fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


def _get_aifw_url(env):
    return env['ir.config_parameter'].sudo().get_param(
        'mfg_nl2sql.aifw_service_url', 'http://aifw_service:8001'
    )


class NL2SQLFeedback(models.Model):
    _name = 'nl2sql.feedback'
    _description = 'NL2SQL Feedback (SQL-Fehler & Korrekturen)'
    _order = 'created_at desc'
    _rec_name = 'question'

    aifw_id = fields.Integer(string='aifw ID', readonly=True, index=True)
    source_code = fields.Char(string='Schema Source', readonly=True)
    question = fields.Text(string='Original-Frage', readonly=True)
    bad_sql = fields.Text(string='Fehlerhaftes SQL', readonly=True)
    error_message = fields.Text(string='Fehlermeldung', readonly=True)
    error_type = fields.Selection([
        ('schema_error',  'Schema-Fehler (halluziniertes Feld)'),
        ('table_error',   'Tabellen-Fehler (halluzinierte Tabelle)'),
        ('join_error',    'Join-Fehler (falscher Join-Pfad)'),
        ('syntax_error',  'Syntax-Fehler'),
        ('timeout',       'Timeout'),
        ('unknown',       'Unbekannt'),
    ], string='Fehlertyp', readonly=True)
    corrected_sql = fields.Text(
        string='Korrigiertes SQL',
        help='Manuell korrigiertes SQL — wird beim Promote zu NL2SQLExample.',
    )
    promoted = fields.Boolean(
        string='Zu Example promoted', readonly=True, default=False,
    )
    created_at = fields.Datetime(string='Erfasst am', readonly=True)

    def _aifw_headers(self):
        token = self.env['ir.config_parameter'].sudo().get_param(
            'mfg_nl2sql.aifw_api_token', ''
        )
        h = {'Content-Type': 'application/json'}
        if token:
            h['Authorization'] = f'Bearer {token}'
        return h

    def action_sync_from_aifw(self):
        """Lädt alle Feedback-Einträge von aifw_service."""
        base_url = _get_aifw_url(self.env)
        url = f"{base_url}/nl2sql/feedback/"
        try:
            resp = requests.get(url, headers=self._aifw_headers(), timeout=15)
            resp.raise_for_status()
            items = resp.json().get('results', [])
        except Exception as exc:
            raise UserError(
                f"Laden von aifw_service fehlgeschlagen:\n{exc}"
            ) from exc

        created = updated = 0
        for item in items:
            existing = self.search([('aifw_id', '=', item['id'])], limit=1)
            vals = {
                'aifw_id': item['id'],
                'source_code': item.get('source_code', 'odoo_mfg'),
                'question': item['question'],
                'bad_sql': item.get('bad_sql', ''),
                'error_message': item.get('error_message', ''),
                'error_type': item.get('error_type', 'unknown'),
                'corrected_sql': item.get('corrected_sql', ''),
                'promoted': item.get('promoted', False),
                'created_at': item.get('created_at'),
            }
            if existing:
                existing.write(vals)
                updated += 1
            else:
                self.create(vals)
                created += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Feedback importiert',
                'message': f'{created} neu, {updated} aktualisiert.',
                'type': 'success',
            },
        }

    def action_promote_to_example(self):
        """Sendet corrected_sql als neues NL2SQLExample zu aifw_service."""
        for rec in self:
            if not rec.corrected_sql:
                raise UserError(
                    'Bitte zuerst "Korrigiertes SQL" ausfüllen.'
                )
            if rec.promoted:
                raise UserError(
                    f'Dieser Eintrag wurde bereits promoted (aifw_id={rec.aifw_id}).'
                )

        base_url = _get_aifw_url(self.env)
        url = f"{base_url}/nl2sql/feedback/{{}}/promote/"
        promoted_count = 0
        for rec in self:
            try:
                resp = requests.post(
                    url.format(rec.aifw_id),
                    json={'corrected_sql': rec.corrected_sql},
                    headers=rec._aifw_headers(),
                    timeout=10,
                )
                resp.raise_for_status()
                rec.write({'promoted': True})
                promoted_count += 1
            except Exception as exc:
                raise UserError(
                    f"Promote fehlgeschlagen für '{rec.question[:60]}':\n{exc}"
                ) from exc

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Promote erfolgreich',
                'message': (
                    f'{promoted_count} Feedback(s) als Few-Shot Example promoted.'
                ),
                'type': 'success',
            },
        }
