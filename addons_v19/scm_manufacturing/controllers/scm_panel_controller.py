# -*- coding: utf-8 -*-
import logging
from datetime import date, timedelta

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class ScmPanelController(http.Controller):

    @http.route("/scm_manufacturing/kpis", type="json", auth="user")
    def get_scm_kpis(self):
        """KPI-Daten für das SCM-Dashboard-Panel."""
        env = request.env
        today = date.today()
        month_start = today.replace(day=1)
        last_month_start = (month_start - timedelta(days=1)).replace(day=1)

        # ── Fertigungsaufträge ─────────────────────────────────────────────
        prod_states = {}
        for state in ['draft', 'confirmed', 'in_progress', 'done', 'cancelled']:
            prod_states[state] = env['scm.production.order'].search_count(
                [('state', '=', state)]
            )

        # ── Einkaufsbestellungen ───────────────────────────────────────────
        purchase_states = {}
        for state in ['draft', 'sent', 'confirmed', 'received', 'done', 'cancelled']:
            purchase_states[state] = env['scm.purchase.order'].search_count(
                [('state', '=', state)]
            )

        open_purchases = (purchase_states.get('draft', 0) +
                         purchase_states.get('sent', 0) +
                         purchase_states.get('confirmed', 0))

        # ── Lieferungen ────────────────────────────────────────────────────
        delivery_states = {}
        for state in ['draft', 'ready', 'shipped', 'delivered', 'cancelled']:
            delivery_states[state] = env['scm.delivery'].search_count(
                [('state', '=', state)]
            )

        # ── Teile / Lager ──────────────────────────────────────────────────
        parts_total = env['scm.part'].search_count([('active', '=', True)])
        parts_low = env['scm.part'].search_count(
            [('stock_qty', '<=', 0), ('active', '=', True)]
        )

        # ── Überfällige Bestellungen ───────────────────────────────────────
        overdue = env['scm.purchase.order'].search_count([
            ('state', 'in', ['sent', 'confirmed']),
            ('date_expected', '<', today),
        ])

        # ── Durchsatz lfd. Monat ───────────────────────────────────────────
        done_this = env['scm.production.order'].search_count(
            [('state', '=', 'done'), ('date_planned', '>=', month_start)]
        )
        done_last = env['scm.production.order'].search_count(
            [('state', '=', 'done'),
             ('date_planned', '>=', last_month_start),
             ('date_planned', '<', month_start)]
        )

        # ── Top-5 offene Bestellungen ──────────────────────────────────────
        top_purchases = env['scm.purchase.order'].search_read(
            [('state', 'in', ['sent', 'confirmed'])],
            fields=['name', 'partner_id', 'total_amount', 'date_expected', 'state'],
            order='date_expected asc',
            limit=5,
        )
        for p in top_purchases:
            if p.get('partner_id'):
                p['partner_name'] = p['partner_id'][1]
                p['partner_id'] = p['partner_id'][0]

        return {
            'prod_states':       prod_states,
            'purchase_states':   purchase_states,
            'delivery_states':   delivery_states,
            'open_purchases':    open_purchases,
            'overdue_purchases': overdue,
            'parts_total':       parts_total,
            'parts_low_stock':   parts_low,
            'done_this_month':   done_this,
            'done_last_month':   done_last,
            'top_purchases':     top_purchases,
        }
