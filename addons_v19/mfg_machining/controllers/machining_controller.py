# -*- coding: utf-8 -*-
import logging
from datetime import date, timedelta

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class MachiningController(http.Controller):

    @http.route("/mfg_machining/kpis", type="json", auth="user")
    def get_machining_kpis(self):
        """KPI-Daten für das CNC-Fertigungs-Dashboard."""
        env = request.env
        today = date.today()
        month_start = today.replace(day=1)
        last_month_start = (month_start - timedelta(days=1)).replace(day=1)

        # ── Auftrags-Status ────────────────────────────────────────────────
        # Demo-Daten als Fallback wenn keine echten Aufträge existieren
        has_real = env['machining.order'].search_count([('is_demo_data', '=', False)]) > 0
        domain_base = [('is_demo_data', '=', False)] if has_real else []

        order_states = {}
        for state in ['draft', 'confirmed', 'in_production', 'quality_check', 'done', 'cancelled']:
            order_states[state] = env['machining.order'].search_count(
                domain_base + [('state', '=', state)]
            )

        # ── Maschinen-Status ───────────────────────────────────────────────
        machine_states = {}
        for state in ['operational', 'maintenance', 'breakdown', 'decommissioned']:
            machine_states[state] = env['machining.machine'].search_count(
                [('state', '=', state), ('active', '=', True)]
            )

        # ── Ausschuss laufender Monat ──────────────────────────────────────
        done_this_month = env['machining.order'].search(
            domain_base + [
                ('state', '=', 'done'),
                ('date_planned', '>=', month_start),
            ]
        )
        planned_total = sum(done_this_month.mapped('planned_qty')) or 0
        scrap_total   = sum(done_this_month.mapped('scrap_qty')) or 0
        scrap_pct = round(scrap_total / planned_total * 100, 1) if planned_total else 0.0

        # ── Ausschuss Vormonat (Vergleich) ─────────────────────────────────
        done_last_month = env['machining.order'].search(
            domain_base + [
                ('state', '=', 'done'),
                ('date_planned', '>=', last_month_start),
                ('date_planned', '<', month_start),
            ]
        )
        planned_lm = sum(done_last_month.mapped('planned_qty')) or 0
        scrap_lm   = sum(done_last_month.mapped('scrap_qty')) or 0
        scrap_pct_lm = round(scrap_lm / planned_lm * 100, 1) if planned_lm else 0.0

        # ── Top-5 Maschinen nach Auftragslast ─────────────────────────────
        machines = env['machining.machine'].search([('active', '=', True)], order='name')
        machine_load = []
        for m in machines[:10]:
            count = env['machining.order'].search_count(
                domain_base + [
                    ('machine_id', '=', m.id),
                    ('state', 'in', ['confirmed', 'in_production', 'quality_check']),
                ]
            )
            machine_load.append({
                'id':   m.id,
                'name': m.name,
                'code': m.code,
                'type': m.machine_type,
                'state': m.state,
                'hall': m.hall or '',
                'active_orders': count,
            })
        machine_load.sort(key=lambda x: x['active_orders'], reverse=True)

        # ── Durchsatz laufender Monat ──────────────────────────────────────
        produced_this_month = sum(done_this_month.mapped('produced_qty')) or 0
        produced_last_month = sum(done_last_month.mapped('produced_qty')) or 0

        return {
            'order_states':       order_states,
            'machine_states':     machine_states,
            'scrap_pct':          scrap_pct,
            'scrap_pct_last_month': scrap_pct_lm,
            'produced_this_month': produced_this_month,
            'produced_last_month': produced_last_month,
            'machine_load':       machine_load[:5],
            'orders_done_month':  len(done_this_month),
        }

    @http.route("/mfg_machining/orders_board", type="json", auth="user")
    def get_orders_board(self):
        """Aktive Aufträge für Kanban-Board."""
        env = request.env
        has_real = env['machining.order'].search_count([('is_demo_data', '=', False)]) > 0
        domain_base = [('is_demo_data', '=', False)] if has_real else []

        orders = env['machining.order'].search_read(
            domain_base + [('state', 'not in', ['done', 'cancelled'])],
            fields=['name', 'state', 'date_planned', 'machine_id',
                    'material', 'drawing_no', 'planned_qty', 'cycle_time_min'],
            order='date_planned asc, name asc',
            limit=100,
        )
        for o in orders:
            if o.get('machine_id'):
                o['machine_name'] = o['machine_id'][1]
                o['machine_id'] = o['machine_id'][0]

        return {'orders': orders}
