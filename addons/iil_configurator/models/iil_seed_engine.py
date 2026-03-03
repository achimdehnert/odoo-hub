# -*- coding: utf-8 -*-
import logging
import random
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from odoo import api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class IilSeedEngine(models.AbstractModel):
    """Demo-Daten-Generator — branchenspezifisch, parametrisiert, idempotent.

    AbstractModel: Alle Methoden sind @api.model — keine eigene DB-Tabelle.
    Aufruf: self.env['iil.seed.engine'].generate(...)

    Datenschutz: Cleanup ausschließlich über is_demo_data=True gefiltert.
    Voraussetzung: casting_foundry muss is_demo_data-Feld auf casting.order
    und casting.quality.check haben (Migrations-Task Sprint 2).
    """
    _name = 'iil.seed.engine'
    _description = 'IIL Demo-Daten-Generator'

    GENERATORS = {
        'casting':   '_generate_casting_data',
        'machining': '_generate_machining_data',
        'both':      '_generate_casting_and_machining_data',
        'generic':   '_generate_generic_data',
    }

    @api.model
    def generate(self, industry, months=12, order_count=200, clear_existing=True):
        """Einstiegspunkt — dispatcht an branchenspezifischen Generator."""
        if clear_existing:
            self._clear_demo_data(industry)

        method = self.GENERATORS.get(industry, '_generate_generic_data')
        getattr(self, method)(months=months, order_count=order_count)

        self._activate_nl2sql_schema(industry)

        _logger.info(
            "IIL Seed Engine: %d Aufträge für Branche '%s' über %d Monate generiert.",
            order_count, industry, months,
        )

    @api.model
    def _clear_demo_data(self, industry):
        """Bestehende Demo-Daten entfernen — nur is_demo_data=True Records.

        Name-Prefix ist kein ausreichender Schutz: User können echte Aufträge
        mit gleichem Prefix anlegen. is_demo_data-Flag ist die einzige
        zuverlässige Unterscheidung.
        """
        if industry in ('casting', 'both'):
            self.env['casting.order'].sudo().search(
                [('is_demo_data', '=', True)]
            ).unlink()
            self.env['casting.quality.check'].sudo().search(
                [('is_demo_data', '=', True)]
            ).unlink()
        if industry in ('machining', 'both'):
            pass  # analog für mfg_machining-Models (Sprint 4)

    @api.model
    def _generate_casting_data(self, months, order_count):
        """Gießerei-Demo-Daten: Aufträge, Qualitätsprüfungen, Maschinenzuweisungen.

        Realistische Trends:
        - Auftragsvolumen: leicht wachsend (+5%/Monat)
        - Ausschussrate: saisonale Schwankung (Winter höher)
        """
        env = self.env

        alloys   = env['casting.alloy'].search([])
        machines = env['casting.machine'].search([])
        molds    = env['casting.mold'].search([])

        if not (alloys and machines and molds):
            raise UserError(
                'casting_foundry Stammdaten fehlen. '
                'Bitte zuerst casting_foundry-Modul-Demo-Daten laden.'
            )

        base_date = date.today().replace(day=1)
        orders_per_month = max(1, order_count // months)

        for month_offset in range(months, 0, -1):
            # relativedelta: exakte Monatsberechnung (timedelta(days=30) != 1 Monat)
            month_start = base_date - relativedelta(months=month_offset)

            volume_factor = 1.0 + (months - month_offset) * 0.05
            actual_orders = int(
                orders_per_month * volume_factor * random.uniform(0.9, 1.1)
            )

            is_winter = month_start.month in (11, 12, 1, 2)
            base_scrap = 0.06 if is_winter else 0.03

            for i in range(actual_orders):
                order_date = month_start + timedelta(days=random.randint(0, 28))
                planned_qty = random.choice([50, 100, 200, 500, 1000])
                scrap_pct   = max(0.0, random.gauss(base_scrap, 0.01))
                scrap_qty   = int(planned_qty * scrap_pct)
                produced    = planned_qty - scrap_qty

                order = env['casting.order'].create({
                    'name':         f"DEMO-{order_date.strftime('%Y%m')}-{i+1:04d}",
                    'alloy_id':     random.choice(alloys).id,
                    'machine_id':   random.choice(machines).id,
                    'mold_id':      random.choice(molds).id,
                    'state':        'done',
                    'order_date':   order_date,
                    'planned_qty':  planned_qty,
                    'produced_qty': produced,
                    'scrap_qty':    scrap_qty,
                    'is_demo_data': True,
                })

                env['casting.quality.check'].create({
                    'name':         f"DEMO-QC-{order.name}",
                    'order_id':     order.id,
                    'state':        'pass' if scrap_pct < 0.05 else 'fail',
                    'checked_by':   env.ref('base.user_admin').id,
                    'check_date':   order_date + timedelta(days=1),
                    'is_demo_data': True,
                })

    @api.model
    def _generate_machining_data(self, months, order_count):
        """Werkzeugmaschinen-Demo — Implementierung Sprint 4."""
        _logger.info("IIL Seed Engine: machining data generator not yet implemented (Sprint 4).")

    @api.model
    def _generate_casting_and_machining_data(self, months, order_count):
        """Beide Branchen — delegiert an die jeweiligen Generatoren."""
        half = order_count // 2
        self._generate_casting_data(months=months, order_count=half)
        self._generate_machining_data(months=months, order_count=half)

    @api.model
    def _generate_generic_data(self, months, order_count):
        """Generische Demo-Daten — Implementierung Sprint 3."""
        _logger.info("IIL Seed Engine: generic data generator not yet implemented (Sprint 3).")

    @api.model
    def _activate_nl2sql_schema(self, industry):
        """NL2SQL Schema-Metadaten für die gewählte Branche aktivieren."""
        SchemaTable = self.env.get('nl2sql.schema.table')
        if not SchemaTable:
            return  # mfg_nl2sql nicht installiert — kein Fehler

        domains = {
            'casting':   ['casting'],
            'machining': ['machining'],
            'both':      ['casting', 'machining'],
            'generic':   ['generic'],
        }
        for domain in domains.get(industry, ['generic']):
            SchemaTable.search([('domain', '=', domain)]).write({'active': True})
