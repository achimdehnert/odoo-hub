# -*- coding: utf-8 -*-
import logging
import random
from datetime import date, datetime as _datetime, timedelta

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
        'scm':       '_generate_scm_data',
        'all':       '_generate_all_data',
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
        if industry in ('casting', 'both', 'all'):
            self.env['casting.order'].sudo().search(
                [('is_demo_data', '=', True)]
            ).unlink()
            self.env['casting.quality.check'].sudo().search(
                [('is_demo_data', '=', True)]
            ).unlink()
        if industry in ('machining', 'both', 'all'):
            self.env['machining.order'].sudo().search(
                [('is_demo_data', '=', True)]
            ).unlink()
        if industry in ('scm', 'all'):
            self.env['scm.purchase.order'].sudo().search(
                [('is_demo_data', '=', True)]
            ).unlink()
            self.env['scm.delivery'].sudo().search(
                [('is_demo_data', '=', True)]
            ).unlink()
            self.env['scm.production.order'].sudo().search(
                [('is_demo_data', '=', True)]
            ).unlink()
            self.env['scm.stock.move'].sudo().search(
                [('is_demo_data', '=', True)]
            ).unlink()

    _CASTING_PROCESSES = [
        'gravity', 'die_cast_hot', 'die_cast_cold', 'sand', 'investment',
    ]
    _PART_NAMES = [
        'Gehäusedeckel', 'Lagergehäuse', 'Pumpengehäuse', 'Ventilblock',
        'Getriebegehäuse', 'Kurbelgehäuse', 'Zylinderkopf', 'Bremskolben',
        'Flansch', 'Träger', 'Halterung', 'Abdeckung',
    ]

    @api.model
    def _generate_casting_data(self, months, order_count):
        """Gießerei-Demo-Daten: Aufträge (Header + Lines), Qualitätsprüfungen.

        Realistische Trends:
        - Auftragsvolumen: leicht wachsend (+5%/Monat)
        - Ausschussrate: saisonale Schwankung (Winter höher)
        """
        env = self.env

        alloys   = env['casting.alloy'].search([])
        machines = env['casting.machine'].search([])
        molds    = env['casting.mold'].search([])

        if not alloys:
            raise UserError(
                'casting.alloy Stammdaten fehlen. '
                'Bitte zuerst casting_foundry Demo-Daten laden.'
            )

        check_types_all = ['visual', 'dimensional', 'xray', 'hardness', 'cmm']
        base_date = date.today().replace(day=1)
        orders_per_month = max(1, order_count // months)
        partners = env['res.partner'].search([('is_company', '=', True)], limit=10)
        if not partners:
            partners = env['res.partner'].search([], limit=5)

        for month_offset in range(months, -1, -1):
            month_start = base_date - relativedelta(months=month_offset)

            volume_factor = 1.0 + (months - month_offset) * 0.05
            actual_orders = int(
                orders_per_month * volume_factor * random.uniform(0.9, 1.1)
            )

            is_winter = month_start.month in (11, 12, 1, 2)
            base_scrap = 0.06 if is_winter else 0.03

            if month_offset > 2:
                state = 'done'
            elif month_offset == 2:
                state = random.choices(['done', 'quality_check'], weights=[0.7, 0.3])[0]
            else:
                state = random.choices(
                    ['confirmed', 'in_production', 'quality_check', 'draft'],
                    weights=[0.3, 0.4, 0.2, 0.1]
                )[0]

            for i in range(actual_orders):
                order_date = month_start + timedelta(days=random.randint(0, 28))
                qty        = random.choice([50, 100, 200, 500])
                scrap_pct  = max(0.0, random.gauss(base_scrap, 0.01))
                scrap_qty  = int(qty * scrap_pct)

                order_vals = {
                    'state':        state,
                    'date_planned': order_date,
                    'is_demo_data': True,
                }
                if partners:
                    order_vals['partner_id'] = random.choice(partners).id

                order = env['casting.order'].create(order_vals)

                # ── Order-Line (Pflichtfelder: part_name, alloy_id, casting_process, quantity) ──
                line_vals = {
                    'order_id':       order.id,
                    'part_name':      random.choice(self._PART_NAMES),
                    'alloy_id':       random.choice(alloys).id,
                    'casting_process': random.choice(self._CASTING_PROCESSES),
                    'quantity':       qty,
                    'scrap_qty':      scrap_qty if state == 'done' else 0,
                    'piece_weight_kg': round(random.uniform(0.2, 15.0), 3),
                    'cycle_time_min': round(random.uniform(1.5, 12.0), 1),
                }
                if machines:
                    line_vals['machine_id'] = random.choice(machines).id
                if molds:
                    line_vals['mold_id'] = random.choice(molds).id
                env['casting.order.line'].create(line_vals)

                # ── Qualitätsprüfung ───────────────────────────────────────
                if scrap_pct < 0.03:
                    result = 'pass'
                elif scrap_pct < 0.06:
                    result = random.choices(['pass', 'conditional'], weights=[0.6, 0.4])[0]
                else:
                    result = random.choices(['conditional', 'fail'], weights=[0.4, 0.6])[0]
                check_dt = _datetime.combine(
                    order_date + timedelta(days=1), _datetime.min.time()
                ).replace(hour=10)
                env['casting.quality.check'].create({
                    'order_id':     order.id,
                    'check_type':   random.choice(check_types_all),
                    'result':       result,
                    'inspector_id': env.ref('base.user_admin').id,
                    'check_date':   check_dt,
                    'sample_size':  random.randint(5, 50),
                    'defect_count': 0 if result == 'pass' else random.randint(1, 5),
                    'is_demo_data': True,
                })

    # ── Machining Stammdaten ─────────────────────────────────────────────────

    _MACHINING_MACHINES = [
        {'name': 'DMG MORI DMU 50',        'code': 'BAZ-001', 'machine_type': 'machining_center', 'manufacturer': 'DMG MORI', 'model': 'DMU 50',     'year_built': 2019, 'axes': 5, 'max_spindle_rpm': 18000, 'travel_x_mm': 500, 'travel_y_mm': 450, 'travel_z_mm': 400, 'hall': 'Halle A', 'position': 'A-01'},
        {'name': 'Mazak Integrex i-400',    'code': 'BAZ-002', 'machine_type': 'machining_center', 'manufacturer': 'Mazak',    'model': 'Integrex i-400', 'year_built': 2020, 'axes': 5, 'max_spindle_rpm': 12000, 'travel_x_mm': 1054, 'travel_y_mm': 0,   'travel_z_mm': 550, 'hall': 'Halle A', 'position': 'A-02'},
        {'name': 'Hermle C 400',            'code': 'BAZ-003', 'machine_type': 'machining_center', 'manufacturer': 'Hermle',   'model': 'C 400',         'year_built': 2021, 'axes': 5, 'max_spindle_rpm': 18000, 'travel_x_mm': 850, 'travel_y_mm': 700, 'travel_z_mm': 500, 'hall': 'Halle A', 'position': 'A-03'},
        {'name': 'Deckel Maho DMF 260',     'code': 'FRA-001', 'machine_type': 'milling',          'manufacturer': 'DMG MORI', 'model': 'DMF 260',      'year_built': 2018, 'axes': 3, 'max_spindle_rpm': 10000, 'travel_x_mm': 2600, 'travel_y_mm': 900, 'travel_z_mm': 800, 'hall': 'Halle B', 'position': 'B-01'},
        {'name': 'Emco Hyperturn 65',       'code': 'DRE-001', 'machine_type': 'lathe',            'manufacturer': 'Emco',     'model': 'Hyperturn 65',  'year_built': 2019, 'axes': 2, 'max_spindle_rpm': 4500,  'travel_x_mm': 320, 'travel_y_mm': 0,   'travel_z_mm': 1000,'hall': 'Halle B', 'position': 'B-02'},
        {'name': 'INDEX C200',              'code': 'DRE-002', 'machine_type': 'lathe',            'manufacturer': 'INDEX',    'model': 'C200',          'year_built': 2022, 'axes': 2, 'max_spindle_rpm': 6300,  'travel_x_mm': 260, 'travel_y_mm': 0,   'travel_z_mm': 700, 'hall': 'Halle B', 'position': 'B-03'},
        {'name': 'Studer S33',              'code': 'SCH-001', 'machine_type': 'grinding',         'manufacturer': 'Studer',   'model': 'S33',           'year_built': 2017, 'axes': 3, 'max_spindle_rpm': 60000, 'travel_x_mm': 175, 'travel_y_mm': 0,   'travel_z_mm': 700, 'hall': 'Halle C', 'position': 'C-01'},
        {'name': 'Zeiss Contura G2',        'code': 'KMG-001', 'machine_type': 'measuring',        'manufacturer': 'Zeiss',    'model': 'Contura G2',    'year_built': 2020, 'axes': 3, 'max_spindle_rpm': 0,     'travel_x_mm': 900, 'travel_y_mm': 1500,'travel_z_mm': 600, 'hall': 'Halle C', 'position': 'C-02'},
    ]

    _MACHINING_MATERIALS = [
        ('Stahl 1.4301 (V2A)',    12.5),
        ('Stahl 1.7225 (42CrMo4)', 8.0),
        ('Aluminium EN AW-6082',   4.0),
        ('Titan Grade 5 (Ti6Al4V)', 35.0),
        ('Messing CuZn39Pb3',      6.5),
        ('Grauguss GG-25',         5.0),
        ('Kunststoff PA66-GF30',   2.5),
        ('Stahl C45',              5.5),
    ]

    _DRAWING_PREFIXES = ['WZ', 'TL', 'GH', 'FL', 'ZY', 'KO', 'LA', 'SP']

    @api.model
    def _generate_machining_data(self, months, order_count):
        """CNC-Fertigungsaufträge Demo-Daten — Sprint 4.

        Generiert:
        - 8 realistische CNC-Maschinen (Stammdaten, idempotent via code)
        - Fertigungsaufträge mit realistischen Trends:
          - Auslastung: wachsend über Zeitraum (+3%/Monat)
          - Ausschuss: Maschinentyp-abhängig (BAZ am besten, Drehen mittel)
          - Zykluszeit: Material-abhängig (Titan/Stahl langsamer)
        """
        env = self.env

        # Maschinen anlegen (idempotent via code)
        machines = []
        for spec in self._MACHINING_MACHINES:
            machine = env['machining.machine'].search(
                [('code', '=', spec['code'])], limit=1
            )
            if not machine:
                machine = env['machining.machine'].create(spec)
            machines.append(machine)

        if not machines:
            raise UserError('Keine CNC-Maschinen verfügbar — Seed-Engine-Fehler.')

        # Aufträge generieren
        base_date = date.today().replace(day=1)
        orders_per_month = max(1, order_count // months)

        for month_offset in range(months, 0, -1):
            month_start = base_date - relativedelta(months=month_offset)

            # Auslastungstrend: leicht wachsend
            volume_factor = 1.0 + (months - month_offset) * 0.03
            actual_orders = int(
                orders_per_month * volume_factor * random.uniform(0.85, 1.15)
            )

            for i in range(actual_orders):
                order_date = month_start + timedelta(days=random.randint(0, 27))
                machine = random.choice(machines)
                material, cycle_base = random.choice(self._MACHINING_MATERIALS)
                drawing_no = (
                    f"{random.choice(self._DRAWING_PREFIXES)}"
                    f"-{random.randint(1000, 9999)}"
                )

                # Zykluszeit: Basiszeit ± 20% Streuung
                cycle_time = round(cycle_base * random.uniform(0.8, 1.2), 1)

                # Mengen
                planned_qty = random.choice([1, 5, 10, 25, 50, 100, 200])
                scrap_pct = random.gauss(0.02, 0.01)
                scrap_pct = max(0.0, min(scrap_pct, 0.15))
                scrap_qty = int(planned_qty * scrap_pct)
                produced_qty = planned_qty - scrap_qty

                # Status-Verteilung: ältere Aufträge eher 'done'
                if month_offset > 2:
                    state = random.choices(
                        ['done', 'cancelled'],
                        weights=[0.92, 0.08]
                    )[0]
                elif month_offset == 2:
                    state = random.choices(
                        ['done', 'in_production', 'quality_check'],
                        weights=[0.6, 0.3, 0.1]
                    )[0]
                else:
                    state = random.choices(
                        ['confirmed', 'in_production', 'quality_check', 'draft'],
                        weights=[0.3, 0.4, 0.2, 0.1]
                    )[0]

                env['machining.order'].create({
                    'date_planned':  order_date,
                    'machine_id':    machine.id,
                    'material':      material,
                    'drawing_no':    drawing_no,
                    'cycle_time_min': cycle_time,
                    'planned_qty':   planned_qty,
                    'produced_qty':  produced_qty if state == 'done' else 0,
                    'scrap_qty':     scrap_qty if state == 'done' else 0,
                    'state':         state,
                    'is_demo_data':  True,
                })

        _logger.info(
            "IIL Seed Engine: %d Maschinierung-Aufträge für %d Monate generiert.",
            order_count, months,
        )

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

    # ── SCM / Stock Demo-Daten ────────────────────────────────────────────────

    _SCM_PARTS = [
        {'part_number': 'RM-001', 'name': 'Stahlrohr 50x3', 'part_type': 'raw', 'make_or_buy': 'buy', 'material': 'Stahl', 'standard_cost': 12.50, 'unit': 'Stk', 'stock_qty': 500.0},
        {'part_number': 'RM-002', 'name': 'Aluminiumplatte 200x10', 'part_type': 'raw', 'make_or_buy': 'buy', 'material': 'Aluminium', 'standard_cost': 28.00, 'unit': 'Stk', 'stock_qty': 250.0},
        {'part_number': 'RM-003', 'name': 'Edelstahlblech 1.4301 2mm', 'part_type': 'raw', 'make_or_buy': 'buy', 'material': 'Edelstahl', 'standard_cost': 45.00, 'unit': 'm²', 'stock_qty': 80.0},
        {'part_number': 'RM-004', 'name': 'Messingronde Ø60', 'part_type': 'raw', 'make_or_buy': 'buy', 'material': 'Messing', 'standard_cost': 8.50, 'unit': 'Stk', 'stock_qty': 1200.0},
        {'part_number': 'RM-005', 'name': 'Titanstange Ø25 Ti6Al4V', 'part_type': 'raw', 'make_or_buy': 'buy', 'material': 'Titan', 'standard_cost': 185.00, 'unit': 'Stk', 'stock_qty': 40.0},
        {'part_number': 'SF-001', 'name': 'Gehäuseteil gefräst', 'part_type': 'semi', 'make_or_buy': 'make', 'material': 'Aluminium', 'standard_cost': 95.00, 'unit': 'Stk', 'stock_qty': 60.0},
        {'part_number': 'SF-002', 'name': 'Welle gedreht Ø30x150', 'part_type': 'semi', 'make_or_buy': 'make', 'material': 'Stahl C45', 'standard_cost': 42.00, 'unit': 'Stk', 'stock_qty': 120.0},
        {'part_number': 'SF-003', 'name': 'Flansch geschliffen', 'part_type': 'semi', 'make_or_buy': 'make', 'material': 'Stahl 42CrMo4', 'standard_cost': 78.00, 'unit': 'Stk', 'stock_qty': 35.0},
        {'part_number': 'FT-001', 'name': 'Pumpengehäuse komplett', 'part_type': 'finished', 'make_or_buy': 'make', 'material': 'Aluminium', 'standard_cost': 320.00, 'unit': 'Stk', 'stock_qty': 15.0},
        {'part_number': 'FT-002', 'name': 'Präzisionswelle Baugruppe', 'part_type': 'finished', 'make_or_buy': 'make', 'material': 'Stahl', 'standard_cost': 185.00, 'unit': 'Stk', 'stock_qty': 28.0},
        {'part_number': 'VB-001', 'name': 'Kühlschmierstoff Emulsion 5L', 'part_type': 'consumable', 'make_or_buy': 'buy', 'material': '', 'standard_cost': 24.00, 'unit': 'Kan', 'stock_qty': 45.0},
        {'part_number': 'VB-002', 'name': 'VHM-Fräser Ø10 4-schneidig', 'part_type': 'consumable', 'make_or_buy': 'buy', 'material': 'VHM', 'standard_cost': 68.00, 'unit': 'Stk', 'stock_qty': 18.0},
    ]

    _SCM_WAREHOUSES = [
        {'name': 'Rohstofflager Nord', 'code': 'WH-RAW-N', 'warehouse_type': 'raw',      'capacity_pallets': 500},
        {'name': 'Zwischenlager WIP',  'code': 'WH-WIP-1', 'warehouse_type': 'wip',       'capacity_pallets': 200},
        {'name': 'Fertigwarenlager',   'code': 'WH-FW-01', 'warehouse_type': 'finished',  'capacity_pallets': 300},
        {'name': 'Sperrlager QS',      'code': 'WH-QUA-1', 'warehouse_type': 'quarantine','capacity_pallets': 50},
    ]

    _SCM_SUPPLIERS = ['Böhler Stahl GmbH', 'Aleris Aluminium AG', 'ThyssenKrupp Materials', 'Sandvik Coromant GmbH', 'Walter Tools GmbH']

    @api.model
    def _generate_scm_data(self, months, order_count):
        """SCM-Demo-Daten: Teile, Lager, Bestellungen, Fertigungsaufträge, Lieferungen, Lagerbewegungen."""
        env = self.env

        # ── Lager anlegen (idempotent via code) ───────────────────────────
        warehouses = []
        for spec in self._SCM_WAREHOUSES:
            wh = env['scm.warehouse'].search([('code', '=', spec['code'])], limit=1)
            if not wh:
                wh = env['scm.warehouse'].create(spec)
            warehouses.append(wh)

        raw_wh      = warehouses[0]
        wip_wh      = warehouses[1]
        finished_wh = warehouses[2]

        # ── Teile anlegen (idempotent via part_number) ────────────────────
        parts = []
        for spec in self._SCM_PARTS:
            p = env['scm.part'].search([('part_number', '=', spec['part_number'])], limit=1)
            if not p:
                p = env['scm.part'].create(spec)
            else:
                p.write({'stock_qty': spec['stock_qty']})
            parts.append(p)

        raw_parts      = [p for p in parts if p.part_type == 'raw']
        semi_parts     = [p for p in parts if p.part_type == 'semi']
        finished_parts = [p for p in parts if p.part_type == 'finished']
        consumables    = [p for p in parts if p.part_type == 'consumable']
        all_buy_parts  = [p for p in parts if p.make_or_buy == 'buy']

        # Lieferanten-Partner (admin-Company-Kontakte suchen oder Dummy nutzen)
        suppliers = env['res.partner'].search([('is_company', '=', True)], limit=5)
        if not suppliers:
            suppliers = env['res.partner'].search([], limit=3)

        base_date = date.today().replace(day=1)
        po_per_month  = max(1, order_count // months // 3)
        prod_per_month = max(1, order_count // months // 2)

        for month_offset in range(months, -1, -1):
            month_start = base_date - relativedelta(months=month_offset)
            is_past     = month_offset > 1

            # ── Bestellungen ──────────────────────────────────────────────
            for i in range(po_per_month):
                order_date    = month_start + timedelta(days=random.randint(0, 25))
                expected_date = order_date + timedelta(days=random.randint(14, 45))
                part          = random.choice(all_buy_parts)
                supplier      = random.choice(suppliers)
                qty           = random.choice([50, 100, 200, 500, 1000])

                if is_past:
                    state = random.choices(['done', 'received'], weights=[0.7, 0.3])[0]
                elif month_offset == 1:
                    state = random.choices(['confirmed', 'sent', 'draft'], weights=[0.5, 0.3, 0.2])[0]
                else:
                    state = 'confirmed'

                po = env['scm.purchase.order'].create({
                    'partner_id':    supplier.id,
                    'state':         state,
                    'date_order':    order_date,
                    'date_expected': expected_date,
                    'is_demo_data':  True,
                })
                env['scm.purchase.line'].create({
                    'order_id':   po.id,
                    'part_id':    part.id,
                    'quantity':   qty,
                    'unit_price': part.standard_cost * random.uniform(0.9, 1.1),
                })

                # Lagerbewegung Zugang wenn erhalten
                if state in ('done', 'received') and raw_parts:
                    move_dt = _datetime.combine(expected_date, _datetime.min.time()).replace(hour=10)
                    env['scm.stock.move'].create({
                        'part_id':      part.id,
                        'warehouse_id': raw_wh.id,
                        'move_type':    'in',
                        'quantity':     qty,
                        'date':         move_dt,
                        'reference':    po.name,
                        'is_demo_data': True,
                    })

            # ── Fertigungsaufträge ────────────────────────────────────────
            for i in range(prod_per_month):
                prod_date = month_start + timedelta(days=random.randint(0, 27))
                part      = random.choice(semi_parts + finished_parts) if (semi_parts + finished_parts) else random.choice(parts)
                qty       = random.choice([10, 25, 50, 100])
                scrap     = int(qty * random.uniform(0.01, 0.04))

                if is_past:
                    state = random.choices(['done', 'cancelled'], weights=[0.9, 0.1])[0]
                else:
                    state = random.choices(['confirmed', 'in_progress', 'draft'], weights=[0.4, 0.4, 0.2])[0]

                env['scm.production.order'].create({
                    'part_id':      part.id,
                    'state':        state,
                    'date_planned': prod_date,
                    'planned_qty':  qty,
                    'produced_qty': qty - scrap if state == 'done' else 0,
                    'scrap_qty':    scrap if state == 'done' else 0,
                    'is_demo_data': True,
                })

                # Lager-Abgang (Rohstoff) + Zugang (Fertigteil)
                if state == 'done' and raw_parts:
                    raw = random.choice(raw_parts)
                    out_dt = _datetime.combine(prod_date, _datetime.min.time()).replace(hour=8)
                    in_dt  = _datetime.combine(prod_date + timedelta(days=2), _datetime.min.time()).replace(hour=16)
                    env['scm.stock.move'].create({
                        'part_id':      raw.id,
                        'warehouse_id': raw_wh.id,
                        'move_type':    'out',
                        'quantity':     qty * random.uniform(0.5, 2.0),
                        'date':         out_dt,
                        'is_demo_data': True,
                    })
                    env['scm.stock.move'].create({
                        'part_id':      part.id,
                        'warehouse_id': wip_wh.id,
                        'move_type':    'in',
                        'quantity':     qty - scrap,
                        'date':         in_dt,
                        'is_demo_data': True,
                    })

        _logger.info("IIL Seed Engine: SCM Demo-Daten für %d Monate generiert.", months)

    @api.model
    def _generate_all_data(self, months, order_count):
        """Alle Branchen — casting + machining + scm."""
        third = order_count // 3
        self._generate_casting_data(months=months, order_count=third)
        self._generate_machining_data(months=months, order_count=third)
        self._generate_scm_data(months=months, order_count=third)

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
