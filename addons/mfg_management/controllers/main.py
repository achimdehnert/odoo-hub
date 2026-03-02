# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request, Response


class MfgDashboardController(http.Controller):

    @http.route("/mfg_management/kpis", type="http", auth="user", methods=["GET"], csrf=False)
    def get_kpis(self):
        env = request.env

        # ── Casting Orders ─────────────────────────────────────────────────
        casting_states = {}
        for state in ["draft", "confirmed", "in_production", "quality_check", "done", "cancelled"]:
            casting_states[state] = env["casting.order"].search_count([("state", "=", state)])

        # ── SCM Production Orders ──────────────────────────────────────────
        scm_states = {}
        for state in ["draft", "confirmed", "in_progress", "done", "cancelled"]:
            scm_states[state] = env["scm.production.order"].search_count([("state", "=", state)])

        # ── Machine Status ─────────────────────────────────────────────────
        machine_states = {}
        for state in ["operational", "maintenance", "breakdown", "decommissioned"]:
            machine_states[state] = env["casting.machine"].search_count(
                [("state", "=", state), ("active", "=", True)]
            )

        # ── Purchase Orders ────────────────────────────────────────────────
        purchase_states = {}
        for state in ["draft", "sent", "confirmed", "received", "done", "cancelled"]:
            purchase_states[state] = env["scm.purchase.order"].search_count([("state", "=", state)])

        # ── Deliveries ─────────────────────────────────────────────────────
        delivery_states = {}
        for state in ["draft", "ready", "shipped", "delivered", "cancelled"]:
            delivery_states[state] = env["scm.delivery"].search_count([("state", "=", state)])

        # ── Quality Checks ─────────────────────────────────────────────────
        qc_pass = env["casting.quality.check"].search_count([("result", "=", "pass")])
        qc_fail = env["casting.quality.check"].search_count([("result", "=", "fail")])
        qc_cond = env["casting.quality.check"].search_count([("result", "=", "conditional")])
        qc_total = qc_pass + qc_fail + qc_cond
        qc_rate = round(qc_pass / qc_total * 100, 1) if qc_total else 0.0

        # ── Stock (Parts) ──────────────────────────────────────────────────
        parts_low_stock = env["scm.part"].search_count([("stock_qty", "<=", 0), ("active", "=", True)])
        parts_total = env["scm.part"].search_count([("active", "=", True)])

        return Response(json.dumps({
            "casting_orders": casting_states,
            "scm_production": scm_states,
            "machines": machine_states,
            "purchases": purchase_states,
            "deliveries": delivery_states,
            "quality": {
                "pass": qc_pass,
                "fail": qc_fail,
                "conditional": qc_cond,
                "total": qc_total,
                "pass_rate": qc_rate,
            },
            "parts": {
                "total": parts_total,
                "low_stock": parts_low_stock,
            },
        }), content_type="application/json")

    @http.route("/mfg_management/production_board", type="http", auth="user", methods=["GET"], csrf=False)
    def get_production_board(self):
        env = request.env

        casting_orders = env["casting.order"].search_read(
            [("state", "not in", ["done", "cancelled"])],
            fields=["name", "state", "date_planned", "total_pieces", "total_scrap_pct", "customer_reference"],
            order="date_planned asc, name asc",
            limit=100,
        )

        scm_orders = env["scm.production.order"].search_read(
            [("state", "not in", ["done", "cancelled"])],
            fields=["name", "state", "date_planned", "planned_qty", "produced_qty", "yield_pct", "part_id"],
            order="date_planned asc, name asc",
            limit=100,
        )

        for o in scm_orders:
            if o.get("part_id"):
                o["part_name"] = o["part_id"][1]
                o["part_id"] = o["part_id"][0]

        return Response(json.dumps({
            "casting_orders": casting_orders,
            "scm_orders": scm_orders,
        }), content_type="application/json")

    @http.route("/mfg_management/machine_status", type="http", auth="user", methods=["GET"], csrf=False)
    def get_machine_status(self):
        env = request.env

        machines = env["casting.machine"].search_read(
            [("active", "=", True)],
            fields=["name", "code", "machine_type", "state", "hall", "manufacturer"],
            order="state asc, name asc",
        )

        return Response(json.dumps({"machines": machines}), content_type="application/json")

    @http.route("/mfg_management/scm_overview", type="http", auth="user", methods=["GET"], csrf=False)
    def get_scm_overview(self):
        env = request.env

        open_purchases = env["scm.purchase.order"].search_read(
            [("state", "in", ["draft", "sent", "confirmed"])],
            fields=["name", "state", "partner_id", "date_order", "date_expected", "total_amount"],
            order="date_expected asc",
            limit=50,
        )
        for p in open_purchases:
            if p.get("partner_id"):
                p["partner_name"] = p["partner_id"][1]
                p["partner_id"] = p["partner_id"][0]

        open_deliveries = env["scm.delivery"].search_read(
            [("state", "in", ["draft", "ready", "shipped"])],
            fields=["name", "state", "partner_id", "date_shipped", "date_delivered", "carrier"],
            order="date_shipped asc",
            limit=50,
        )
        for d in open_deliveries:
            if d.get("partner_id"):
                d["partner_name"] = d["partner_id"][1]
                d["partner_id"] = d["partner_id"][0]

        warehouses = env["scm.warehouse"].search_read(
            [("active", "=", True)],
            fields=["name", "code", "warehouse_type", "capacity_pallets"],
            order="code asc",
        )

        return Response(json.dumps({
            "open_purchases": open_purchases,
            "open_deliveries": open_deliveries,
            "warehouses": warehouses,
        }), content_type="application/json")
