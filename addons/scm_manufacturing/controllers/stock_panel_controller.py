# -*- coding: utf-8 -*-
import logging
from datetime import date, timedelta

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class StockPanelController(http.Controller):

    @http.route("/scm_manufacturing/stock_kpis", type="json", auth="user")
    def get_stock_kpis(self):
        """KPI-Daten für das Lagerverwaltungs-Panel."""
        env = request.env
        today = date.today()
        month_start = today.replace(day=1)
        month_start_str = month_start.isoformat()

        # ── Teile gesamt / Typen ───────────────────────────────────────────
        parts_total   = env['scm.part'].search_count([('active', '=', True)])
        parts_low     = env['scm.part'].search_count([('stock_qty', '<=', 0), ('active', '=', True)])
        parts_raw     = env['scm.part'].search_count([('part_type', '=', 'raw'),        ('active', '=', True)])
        parts_semi    = env['scm.part'].search_count([('part_type', '=', 'semi'),       ('active', '=', True)])
        parts_finished = env['scm.part'].search_count([('part_type', '=', 'finished'),  ('active', '=', True)])

        # ── Lagerbewegungen lfd. Monat ─────────────────────────────────────
        moves_in    = env['scm.stock.move'].search_count([('move_type', '=', 'in'),    ('date', '>=', month_start_str)])
        moves_out   = env['scm.stock.move'].search_count([('move_type', '=', 'out'),   ('date', '>=', month_start_str)])
        moves_scrap = env['scm.stock.move'].search_count([('move_type', '=', 'scrap'), ('date', '>=', month_start_str)])

        # ── Lager nach Typ ─────────────────────────────────────────────────
        warehouses = env['scm.warehouse'].search_read(
            [('active', '=', True)],
            fields=['name', 'code', 'warehouse_type', 'capacity_pallets'],
            order='code',
        )

        # ── Top-Teile nach kritischem Bestand ─────────────────────────────
        critical_parts = env['scm.part'].search_read(
            [('stock_qty', '<=', 0), ('active', '=', True)],
            fields=['part_number', 'name', 'stock_qty', 'unit', 'part_type'],
            order='stock_qty asc',
            limit=8,
        )

        # ── Gesamtwert Lager (standard_cost * stock_qty) ───────────────────
        all_parts = env['scm.part'].search([('active', '=', True), ('stock_qty', '>', 0)])
        stock_value = sum(p.standard_cost * p.stock_qty for p in all_parts)

        return {
            'parts_total':    parts_total,
            'parts_low':      parts_low,
            'parts_raw':      parts_raw,
            'parts_semi':     parts_semi,
            'parts_finished': parts_finished,
            'moves_in':       moves_in,
            'moves_out':      moves_out,
            'moves_scrap':    moves_scrap,
            'warehouses':     warehouses,
            'critical_parts': critical_parts,
            'stock_value':    round(stock_value, 2),
            'stock_health_pct': round((parts_total - parts_low) / parts_total * 100, 1) if parts_total else 100.0,
        }
