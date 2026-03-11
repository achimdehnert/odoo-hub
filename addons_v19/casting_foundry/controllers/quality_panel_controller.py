# -*- coding: utf-8 -*-
import logging
from datetime import date, timedelta

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class QualityPanelController(http.Controller):

    @http.route("/casting_foundry/quality_kpis", type="json", auth="user")
    def get_quality_kpis(self):
        """KPI-Daten für das Qualitäts-Dashboard-Panel."""
        env = request.env
        today = date.today()
        month_start = today.replace(day=1)
        month_start_str = month_start.isoformat()
        last_month_start = (month_start - timedelta(days=1)).replace(day=1)
        last_month_str   = last_month_start.isoformat()

        # ── QS gesamt ───────────────────────────────────────
        qc_pass_all  = env['casting.quality.check'].search_count([('result', '=', 'pass')])
        qc_fail_all  = env['casting.quality.check'].search_count([('result', '=', 'fail')])
        qc_cond_all  = env['casting.quality.check'].search_count([('result', '=', 'conditional')])
        qc_total_all = qc_pass_all + qc_fail_all + qc_cond_all
        qc_rate_all  = round(qc_pass_all / qc_total_all * 100, 1) if qc_total_all else 0.0

        # ── QS lfd. Monat ─────────────────────────────────────
        qc_pass  = env['casting.quality.check'].search_count([('result', '=', 'pass'),        ('check_date', '>=', month_start_str)])
        qc_fail  = env['casting.quality.check'].search_count([('result', '=', 'fail'),        ('check_date', '>=', month_start_str)])
        qc_cond  = env['casting.quality.check'].search_count([('result', '=', 'conditional'), ('check_date', '>=', month_start_str)])
        qc_total = qc_pass + qc_fail + qc_cond
        qc_rate  = round(qc_pass / qc_total * 100, 1) if qc_total else 0.0

        # ── QS Vormonat ────────────────────────────────────────────────────
        qc_pass_lm  = env['casting.quality.check'].search_count([('result', '=', 'pass'), ('check_date', '>=', last_month_str), ('check_date', '<', month_start_str)])
        qc_total_lm = env['casting.quality.check'].search_count([('check_date', '>=', last_month_str), ('check_date', '<', month_start_str)])
        qc_rate_lm  = round(qc_pass_lm / qc_total_lm * 100, 1) if qc_total_lm else 0.0

        # ── Prüfungen nach Typ (gesamt) ─────────────────────────────────
        check_types = ['visual', 'dimensional', 'xray', 'ultrasonic', 'hardness', 'tensile', 'spectrometry', 'leak', 'cmm']
        type_labels = {
            'visual': 'Sicht', 'dimensional': 'Maß', 'xray': 'Röntgen',
            'ultrasonic': 'Ultraschall', 'hardness': 'Härte', 'tensile': 'Zug',
            'spectrometry': 'Spektro', 'leak': 'Dicht', 'cmm': '3D-KMG',
        }
        by_type = []
        for ct in check_types:
            cnt = env['casting.quality.check'].search_count([('check_type', '=', ct)])
            if cnt:
                by_type.append({'type': ct, 'label': type_labels.get(ct, ct), 'count': cnt})
        by_type.sort(key=lambda x: x['count'], reverse=True)

        # ── Häufigste Fehlerarten (gesamt) ────────────────────────────────
        defect_types = env['casting.defect.type'].search([])
        top_defects = []
        for dt in defect_types:
            cnt = env['casting.quality.check'].search_count(
                [('defect_type_ids', 'in', [dt.id])]
            )
            if cnt:
                top_defects.append({'name': dt.name, 'code': dt.code or '', 'count': cnt, 'severity': dt.severity or 'minor'})
        top_defects.sort(key=lambda x: x['count'], reverse=True)

        # ── Offene Prüfungen (kein Ergebnis) ─────────────────────────────
        open_checks = env['casting.quality.check'].search_count([('result', '=', False)])

        # ── Prüfungen letzte 30 Tage (Trend-Timeline) ─────────────────────
        trend = []
        for day_offset in range(29, -1, -1):
            d = today - timedelta(days=day_offset)
            d_str = d.isoformat()
            d_next = (d + timedelta(days=1)).isoformat()
            p = env['casting.quality.check'].search_count([('result', '=', 'pass'), ('check_date', '>=', d_str), ('check_date', '<', d_next)])
            f = env['casting.quality.check'].search_count([('result', '=', 'fail'), ('check_date', '>=', d_str), ('check_date', '<', d_next)])
            if p or f:
                trend.append({'date': d_str, 'pass': p, 'fail': f})

        return {
            'qc_pass':        qc_pass,
            'qc_fail':        qc_fail,
            'qc_cond':        qc_cond,
            'qc_total':       qc_total,
            'qc_rate':        qc_rate,
            'qc_pass_all':    qc_pass_all,
            'qc_fail_all':    qc_fail_all,
            'qc_cond_all':    qc_cond_all,
            'qc_total_all':   qc_total_all,
            'qc_rate_all':    qc_rate_all,
            'qc_rate_lm':     qc_rate_lm,
            'qc_total_lm':    qc_total_lm,
            'open_checks':    open_checks,
            'by_type':        by_type[:6],
            'top_defects':    top_defects[:5],
            'trend':          trend,
        }
