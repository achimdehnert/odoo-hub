# -*- coding: utf-8 -*-
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class MachinesPanelController(http.Controller):

    @http.route("/casting_foundry/machines_kpis", type="json", auth="user")
    def get_machines_kpis(self):
        """Kombinierte Maschinenübersicht: casting.machine + machining.machine."""
        env = request.env

        # ── Casting-Maschinen ──────────────────────────────────────────────
        casting_states = {}
        for state in ['operational', 'maintenance', 'breakdown', 'decommissioned']:
            casting_states[state] = env['casting.machine'].search_count(
                [('state', '=', state), ('active', '=', True)]
            )

        casting_machines = env['casting.machine'].search_read(
            [('active', '=', True)],
            fields=['name', 'code', 'machine_type', 'state', 'hall', 'manufacturer', 'year_built'],
            order='state asc, name asc',
        )
        for m in casting_machines:
            m['domain'] = 'casting'

        # ── CNC-Maschinen (optional — mfg_machining) ─────────────────────
        machining_states = {}
        machining_machines = []
        MachiningMachine = env.get('machining.machine')
        if MachiningMachine is not None:
            for state in ['operational', 'maintenance', 'breakdown', 'decommissioned']:
                machining_states[state] = MachiningMachine.search_count(
                    [('state', '=', state), ('active', '=', True)]
                )
            machining_machines = MachiningMachine.search_read(
                [('active', '=', True)],
                fields=['name', 'code', 'machine_type', 'state', 'hall', 'manufacturer', 'year_built'],
                order='state asc, name asc',
            )
            for m in machining_machines:
                m['domain'] = 'machining'

        # ── Kombinierte Summen ─────────────────────────────────────────────
        def _sum(d1, d2, key):
            return (d1.get(key, 0) or 0) + (d2.get(key, 0) or 0)

        combined_states = {
            s: _sum(casting_states, machining_states, s)
            for s in ['operational', 'maintenance', 'breakdown', 'decommissioned']
        }
        total = sum(combined_states.values())
        availability_pct = round(combined_states['operational'] / total * 100, 1) if total else 0.0

        return {
            'casting_states':    casting_states,
            'machining_states':  machining_states,
            'combined_states':   combined_states,
            'total':             total,
            'availability_pct':  availability_pct,
            'casting_machines':  casting_machines,
            'machining_machines': machining_machines,
        }
