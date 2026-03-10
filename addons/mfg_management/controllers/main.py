# -*- coding: utf-8 -*-
import json
import logging
from datetime import date

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class MfgDashboardController(http.Controller):

    @http.route("/mfg_management/kpis", type="json", auth="user")
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

        return {
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
        }

    @http.route("/mfg_management/production_board", type="json", auth="user")
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

        return {
            "casting_orders": casting_orders,
            "scm_orders": scm_orders,
        }

    @http.route("/mfg_management/machine_status", type="json", auth="user")
    def get_machine_status(self):
        env = request.env

        machines = env["casting.machine"].search_read(
            [("active", "=", True)],
            fields=["name", "code", "machine_type", "state", "hall", "manufacturer"],
            order="state asc, name asc",
        )

        return {"machines": machines}

    @http.route("/mfg_management/scm_overview", type="json", auth="user")
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

        return {
            "open_purchases": open_purchases,
            "open_deliveries": open_deliveries,
            "warehouses": warehouses,
        }

    # ── Drilldown ──────────────────────────────────────────────────────────
    @http.route("/mfg_management/drilldown", type="json", auth="user")
    def get_drilldown(self, key):
        env = request.env
        today = date.today()

        if key == "casting_active":
            rows = env["casting.order"].search_read(
                [("state", "not in", ["done", "cancelled"])],
                fields=["name", "state", "date_planned", "total_pieces",
                        "total_scrap_pct", "customer_reference"],
                order="state asc, date_planned asc",
                limit=100,
            )
            return {"rows": rows}

        elif key == "scm_in_progress":
            rows = env["scm.production.order"].search_read(
                [("state", "not in", ["done", "cancelled"])],
                fields=["name", "state", "date_planned", "planned_qty",
                        "produced_qty", "yield_pct", "part_id"],
                order="state asc, date_planned asc",
                limit=100,
            )
            for r in rows:
                if r.get("part_id"):
                    r["part_name"] = r["part_id"][1]
                    r["part_id"] = r["part_id"][0]
            return {"rows": rows}

        elif key == "machines_op":
            rows = env["casting.machine"].search_read(
                [("state", "=", "operational"), ("active", "=", True)],
                fields=["name", "code", "machine_type", "hall", "state"],
                order="code asc",
            )
            return {"rows": rows}

        elif key == "machines_fail":
            rows = env["casting.machine"].search_read(
                [("state", "=", "breakdown"), ("active", "=", True)],
                fields=["name", "code", "machine_type", "hall", "state"],
                order="code asc",
            )
            return {"rows": rows}

        elif key == "quality":
            qc_pass = env["casting.quality.check"].search_count(
                [("result", "=", "pass")])
            qc_fail = env["casting.quality.check"].search_count(
                [("result", "=", "fail")])
            qc_cond = env["casting.quality.check"].search_count(
                [("result", "=", "conditional")])
            qc_total = qc_pass + qc_fail + qc_cond
            rows = env["casting.quality.check"].search_read(
                [],
                fields=["name", "result", "check_date", "inspector_id"],
                order="check_date desc",
                limit=50,
            )
            for r in rows:
                r["date_check"] = r.pop("check_date", None)
                if r.get("inspector_id"):
                    r["inspector_name"] = r["inspector_id"][1]
                    r["inspector_id"] = r["inspector_id"][0]
            return {
                "summary": {
                    "pass": qc_pass, "fail": qc_fail,
                    "conditional": qc_cond, "total": qc_total,
                    "pass_rate": round(qc_pass / qc_total * 100, 1) if qc_total else 0.0,
                },
                "rows": rows,
            }

        elif key == "purchases_open":
            rows = env["scm.purchase.order"].search_read(
                [("state", "in", ["draft", "sent", "confirmed"])],
                fields=["name", "state", "partner_id", "date_order",
                        "date_expected", "total_amount"],
                order="date_expected asc",
                limit=50,
            )
            for r in rows:
                if r.get("partner_id"):
                    r["partner_name"] = r["partner_id"][1]
                    r["partner_id"] = r["partner_id"][0]
                if r.get("date_expected"):
                    try:
                        exp = r["date_expected"]
                        if hasattr(exp, "date"):
                            exp = exp.date()
                        elif isinstance(exp, str):
                            from datetime import datetime
                            exp = datetime.strptime(exp[:10], "%Y-%m-%d").date()
                        r["overdue"] = exp < today
                    except Exception:
                        r["overdue"] = False
                else:
                    r["overdue"] = False
            return {"rows": rows}

        return {"error": f"Unbekannter Drilldown-Key: {key}"}

    # ── NL2SQL Proxy → aifw_service ───────────────────────────────────────
    @http.route("/mfg_management/nl2sql", type="json", auth="user")
    def nl2sql_query(self, query, source_code="odoo_mfg", conversation_history=None):
        """HTTP proxy to aifw_service NL2SQL microservice."""
        import urllib.error
        import urllib.request

        if not query or not query.strip():
            return {"error": "Leere Anfrage"}

        aifw_url = request.env["ir.config_parameter"].sudo().get_param(
            "mfg_management.aifw_service_url", "http://aifw_service:8001"
        )
        endpoint = f"{aifw_url.rstrip('/')}/nl2sql/query"

        payload = json.dumps({
            "query": query,
            "source_code": source_code,
            "conversation_history": conversation_history or [],
        }).encode("utf-8")

        req = urllib.request.Request(
            endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                body = resp.read()
                result = json.loads(body)
                # aifw_service liefert needs_clarification mit success=false —
                # das ist kein Fehler, sondern ein Dialog-Schritt.
                if result.get("needs_clarification"):
                    result["success"] = True
                    return result
                # History-Eintrag schreiben (success + error)
                self._log_nl2sql_history(query, result)
                return result

        except urllib.error.HTTPError as exc:
            try:
                err_body = json.loads(exc.read())
                error_msg = err_body.get("error", f"HTTP {exc.code}")
            except Exception:
                error_msg = f"aifw-service HTTP {exc.code}"
            self._log_nl2sql_history(query, {"success": False, "error": error_msg})
            return {"success": False, "error": error_msg}

        except urllib.error.URLError as exc:
            error_msg = "KI-Service nicht erreichbar. aifw_service Container pruefen."
            _logger.warning("aifw_service nicht erreichbar: %s", exc.reason)
            self._log_nl2sql_history(query, {"success": False, "error": error_msg})
            return {
                "success": False,
                "error": error_msg,
                "error_type": "ServiceUnavailable",
            }

        except Exception as exc:
            _logger.exception("NL2SQL proxy error")
            error_msg = f"Fehler: {str(exc)}"
            self._log_nl2sql_history(query, {"success": False, "error": error_msg})
            return {"success": False, "error": error_msg}

    def _log_nl2sql_history(self, query, result):
        """Schreibt Query-Ergebnis in nl2sql.query.history für Feedback-Loop."""
        try:
            History = request.env["nl2sql.query.history"].sudo()
            is_success = result.get("success", False) and not result.get("error")
            vals = {
                "name": query,
                "domain_filter": "all",
                "state": "success" if is_success else "error",
                "generated_sql": result.get("sql", ""),
                "sanitized_sql": result.get("sql", ""),
                "result_row_count": result.get("row_count", 0),
                "execution_time_ms": int(result.get("execution_time_ms", 0)),
                "llm_tokens_used": (result.get("tokens") or {}).get("input", 0),
            }
            if not is_success:
                vals["error_message"] = result.get("error", "Unbekannter Fehler")
            if result.get("columns"):
                vals["result_columns"] = json.dumps(result["columns"])
            if result.get("rows"):
                vals["result_data"] = json.dumps(result["rows"][:200])
            History.create(vals)
        except Exception:
            _logger.debug("nl2sql history logging failed (non-critical)", exc_info=True)

    @http.route("/mfg_management/nl2sql/feedback", type="json", auth="user")
    def nl2sql_feedback(self, history_id, rating, comment=None):
        """Feedback zu einem NL2SQL-Ergebnis: rating='good'|'bad'."""
        try:
            History = request.env["nl2sql.query.history"].sudo()
            record = History.browse(history_id)
            if not record.exists():
                return {"error": "Eintrag nicht gefunden"}
            # is_pinned = True bei positivem Feedback (Few-Shot Kandidat)
            vals = {"is_pinned": rating == "good"}
            if comment:
                vals["error_message"] = comment
            record.write(vals)
            # Bei positivem Feedback: automatisch als Few-Shot Example vorschlagen
            if rating == "good" and record.sanitized_sql:
                try:
                    request.env["nl2sql.example"].sudo().create({
                        "name": record.name,
                        "sql": record.sanitized_sql,
                        "domain": "all",
                        "is_active": False,  # Manuell aktivieren nach Review
                        "source": "feedback",
                    })
                except Exception:
                    pass  # Example-Model optional
            return {"success": True, "rating": rating}
        except Exception as exc:
            _logger.exception("NL2SQL feedback error")
            return {"error": str(exc)}
