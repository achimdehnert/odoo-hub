# -*- coding: utf-8 -*-
"""
nl2sql.example — Few-Shot Examples für den NL2SQL LLM-Prompt.

Proxy-Modell: Daten leben in aifw_service (Django DB).
Odoo-Modell synchronisiert via REST-API beim Lesen/Schreiben.
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


class NL2SQLExample(models.Model):
    _name = 'nl2sql.example'
    _description = 'NL2SQL Few-Shot Beispiel'
    _order = 'domain, difficulty, id'
    _rec_name = 'question'

    aifw_id = fields.Integer(string='aifw ID', readonly=True, index=True)
    source_code = fields.Char(
        string='Schema Source', default='odoo_mfg', required=True,
    )
    question = fields.Text(string='Frage', required=True)
    sql = fields.Text(string='Verifiziertes SQL', required=True)
    domain = fields.Selection([
        ('machines',  'Maschinen'),
        ('casting',   'Gießaufträge / Qualität'),
        ('scm',       'Einkauf / SCM'),
        ('products',  'Produkte / Lager'),
        ('general',   'Allgemein'),
    ], string='Domäne', default='general')
    difficulty = fields.Selection([
        ('1', 'Einfach'),
        ('2', 'Mittel'),
        ('3', 'Komplex'),
    ], string='Schwierigkeitsgrad', default='1')
    is_active = fields.Boolean(string='Aktiv', default=True)
    created_at = fields.Datetime(string='Erstellt am', readonly=True)
    synced = fields.Boolean(string='Mit aifw synchronisiert', default=False, readonly=True)

    def _aifw_headers(self):
        token = self.env['ir.config_parameter'].sudo().get_param(
            'mfg_nl2sql.aifw_api_token', ''
        )
        h = {'Content-Type': 'application/json'}
        if token:
            h['Authorization'] = f'Bearer {token}'
        return h

    def action_sync_to_aifw(self):
        """Sendet dieses Beispiel an aifw_service POST /nl2sql/examples/."""
        base_url = _get_aifw_url(self.env)
        url = f"{base_url}/nl2sql/examples/"
        for rec in self:
            payload = {
                'source_code': rec.source_code,
                'question': rec.question,
                'sql': rec.sql,
                'domain': rec.domain or '',
                'difficulty': int(rec.difficulty or 1),
                'is_active': rec.is_active,
            }
            try:
                resp = requests.post(
                    url, json=payload,
                    headers=rec._aifw_headers(), timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()
                rec.write({'aifw_id': data.get('id', 0), 'synced': True})
                _logger.info("NL2SQLExample synced to aifw: id=%s", data.get('id'))
            except Exception as exc:
                _logger.warning("NL2SQLExample sync fehlgeschlagen: %s", exc)
                raise UserError(
                    f"Sync zu aifw_service fehlgeschlagen:\n{exc}\n\n"
                    "Bitte prüfe ob aifw_service erreichbar ist."
                ) from exc
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Sync erfolgreich',
                'message': f'{len(self)} Beispiel(e) zu aifw_service übertragen.',
                'type': 'success',
            },
        }

    def action_sync_from_aifw(self):
        """Lädt alle Beispiele von aifw_service und aktualisiert lokale Einträge."""
        base_url = _get_aifw_url(self.env)
        url = f"{base_url}/nl2sql/examples/"
        try:
            resp = requests.get(url, headers=self._aifw_headers(), timeout=15)
            resp.raise_for_status()
            examples = resp.json().get('results', [])
        except Exception as exc:
            raise UserError(
                f"Laden von aifw_service fehlgeschlagen:\n{exc}"
            ) from exc

        created = updated = 0
        for ex in examples:
            existing = self.search([('aifw_id', '=', ex['id'])], limit=1)
            vals = {
                'aifw_id': ex['id'],
                'source_code': ex.get('source_code', 'odoo_mfg'),
                'question': ex['question'],
                'sql': ex['sql'],
                'domain': ex.get('domain', 'general') or 'general',
                'difficulty': str(ex.get('difficulty', 1)),
                'is_active': ex.get('is_active', True),
                'synced': True,
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
                'title': 'Import abgeschlossen',
                'message': f'{created} neu, {updated} aktualisiert.',
                'type': 'success',
            },
        }
