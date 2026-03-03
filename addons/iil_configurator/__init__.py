# -*- coding: utf-8 -*-
import logging
import os

from odoo import api, SUPERUSER_ID

from . import models
from . import wizard

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Lädt NL2SQL-Schema-Metadaten — nur wenn mfg_nl2sql installiert ist.

    Wird nach dem vollständigen Modul-Install ausgeführt, wenn alle
    abhängigen Modelle (inkl. nl2sql.schema.table) bereits registriert sind.
    Falls mfg_nl2sql nicht installiert ist, wird der Hook still übersprungen.
    """
    if not env['ir.module.module'].search([
        ('name', '=', 'mfg_nl2sql'),
        ('state', '=', 'installed'),
    ]):
        _logger.info(
            "iil_configurator post_init_hook: mfg_nl2sql nicht installiert "
            "— NL2SQL-Schema-Daten werden übersprungen."
        )
        return

    addon_path = os.path.dirname(__file__)
    schema_files = [
        os.path.join(addon_path, 'data', 'nl2sql_schema_casting.xml'),
        os.path.join(addon_path, 'data', 'nl2sql_schema_machining.xml'),
    ]

    from odoo.tools import convert_file

    for xml_path in schema_files:
        if not os.path.exists(xml_path):
            _logger.warning("iil_configurator: Schema-Datei nicht gefunden: %s", xml_path)
            continue
        try:
            convert_file(
                env,
                'iil_configurator',
                os.path.basename(xml_path),
                {},
                mode='init',
                noupdate=True,
                kind='data',
            )
            _logger.info("iil_configurator post_init_hook: %s geladen.", os.path.basename(xml_path))
        except Exception as e:
            _logger.error(
                "iil_configurator post_init_hook: Fehler beim Laden von %s: %s",
                os.path.basename(xml_path), e,
            )
