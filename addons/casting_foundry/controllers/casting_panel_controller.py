# -*- coding: utf-8 -*-
import logging
from datetime import date, timedelta

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class CastingPanelController(http.Controller):

    @http.route("/casting_foundry/kpis", type="json", auth="user")
    def get_casting_kpis(self):
        """KPI-Daten für das Gießerei-Dashboard-Panel."""
        env = request.env
        today = date.today()
        month_start = today.replace(day=1)
        last_month_start = (month_start - timedelta(days=1)).replace(day=1)

        # ── Auftrags-Status ────────────────────────────────────────────────
        order_states = {}
        for state in ['draft', 'confirmed', 'in_production', 'quality_check', 'done', 'cancelled']:
            order_states[state] = env['casting.order'].search_count(
                [('state', '=', state)]
            )

        # ── Maschinen-Status ───────────────────────────────────────────────
        machine_states = {}
        for state in ['operational', 'maintenance', 'breakdown', 'decommissioned']:
            machine_states[state] = env['casting.machine'].search_count(
                [('state', '=', state), ('active', '=', True)]
            )

        # ── Qualitätsprüfungen laufender Monat ────────────────────────────
        # check_date ist Datetime → Vergleich mit date als String (ISO)
        month_start_str = month_start.isoformat()
        last_month_str  = last_month_start.isoformat()

        qc_pass  = env['casting.quality.check'].search_count([('result', '=', 'pass'),  ('check_date', '>=', month_start_str)])
        env['casting.quality.check'].search_count([('result', '=', 'fail'),  ('check_date', '>=', month_start_str)])
        qc_total = env['casting.quality.check'].search_count([('check_date', '>=', month_start_str)])
        qc_rate  = round(qc_pass / qc_total * 100, 1) if qc_total else 0.0

        # ── Qualitätsprüfungen Vormonat ────────────────────────────────────
        qc_pass_lm  = env['casting.quality.check'].search_count([('result', '=', 'pass'), ('check_date', '>=', last_month_str), ('check_date', '<', month_start_str)])
        qc_total_lm = env['casting.quality.check'].search_count([('check_date', '>=', last_month_str), ('check_date', '<', month_start_str)])
        qc_rate_lm  = round(qc_pass_lm / qc_total_lm * 100, 1) if qc_total_lm else 0.0

        # ── Ausschuss laufender Monat ──────────────────────────────────────
        done_this_month = env['casting.order'].search(
            [('state', '=', 'done'), ('date_planned', '>=', month_start)]
        )
        scrap_avg = 0.0
        if done_this_month:
            scrap_vals = done_this_month.mapped('total_scrap_pct')
            scrap_avg = round(sum(scrap_vals) / len(scrap_vals), 1)

        done_last_month = env['casting.order'].search(
            [('state', '=', 'done'),
             ('date_planned', '>=', last_month_start),
             ('date_planned', '<', month_start)]
        )
        scrap_avg_lm = 0.0
        if done_last_month:
            vals_lm = done_last_month.mapped('total_scrap_pct')
            scrap_avg_lm = round(sum(vals_lm) / len(vals_lm), 1)

        # ── Top-5 Maschinen nach Auftragslast (via order.line) ─────────────
        machines = env['casting.machine'].search(
            [('active', '=', True)], order='name'
        )
        machine_load = []
        for m in machines[:10]:
            count = env['casting.order.line'].search_count(
                [('machine_id', '=', m.id),
                 ('order_state', 'in', ['confirmed', 'in_production', 'quality_check'])]
            )
            machine_load.append({
                'id':    m.id,
                'name':  m.name,
                'code':  m.code or '',
                'type':  m.machine_type or '',
                'state': m.state,
                'hall':  m.hall or '',
                'active_orders': count,
            })
        machine_load.sort(key=lambda x: x['active_orders'], reverse=True)

        return {
            'order_states':       order_states,
            'machine_states':     machine_states,
            'qc_rate':            qc_rate,
            'qc_rate_last_month': qc_rate_lm,
            'qc_total':           qc_total,
            'scrap_avg':          scrap_avg,
            'scrap_avg_lm':       scrap_avg_lm,
            'done_this_month':    len(done_this_month),
            'machine_load':       machine_load[:5],
        }
