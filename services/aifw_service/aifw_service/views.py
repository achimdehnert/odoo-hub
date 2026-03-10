"""
aifw-service HTTP Views.

POST /nl2sql/query  — NL2SQL pipeline via NL2SQLEngine
GET  /health        — liveness probe
"""
import json
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

logger = logging.getLogger(__name__)


@require_GET
def health(request):
    return JsonResponse({"status": "ok"})


@csrf_exempt
def nl2sql_examples(request):
    """
    GET  /nl2sql/examples/  — list all examples
    POST /nl2sql/examples/  — create new example
    """
    if request.method == "GET":
        try:
            from aifw.nl2sql.models import NL2SQLExample
            qs = NL2SQLExample.objects.select_related("source").filter(is_active=True)
            results = [
                {
                    "id": ex.id,
                    "source_code": ex.source.code,
                    "question": ex.question,
                    "sql": ex.sql,
                    "domain": ex.domain,
                    "difficulty": ex.difficulty,
                    "is_active": ex.is_active,
                    "created_at": ex.created_at.isoformat() if ex.created_at else None,
                }
                for ex in qs
            ]
            return JsonResponse({"results": results, "count": len(results)})
        except Exception as exc:
            logger.exception("nl2sql_examples GET Fehler")
            return JsonResponse({"success": False, "error": str(exc)}, status=500)

    if request.method == "POST":
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=400)
        try:
            from aifw.nl2sql.models import NL2SQLExample, SchemaSource
            source_code = body.get("source_code", "odoo_mfg")
            source = SchemaSource.objects.filter(code=source_code, is_active=True).first()
            if not source:
                return JsonResponse(
                    {"success": False, "error": f"SchemaSource '{source_code}' nicht gefunden"},
                    status=400,
                )
            ex = NL2SQLExample.objects.create(
                source=source,
                question=body["question"],
                sql=body["sql"],
                domain=body.get("domain", ""),
                difficulty=int(body.get("difficulty", 1)),
                is_active=body.get("is_active", True),
            )
            return JsonResponse({"id": ex.id, "success": True}, status=201)
        except Exception as exc:
            logger.exception("nl2sql_examples POST Fehler")
            return JsonResponse({"success": False, "error": str(exc)}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
def nl2sql_feedback_list(request):
    """
    GET /nl2sql/feedback/  — list all feedback entries
    """
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        from aifw.nl2sql.models import NL2SQLFeedback
        qs = NL2SQLFeedback.objects.select_related("source").order_by("-created_at")[:200]
        results = [
            {
                "id": fb.id,
                "source_code": fb.source.code,
                "question": fb.question,
                "bad_sql": fb.bad_sql,
                "error_message": fb.error_message,
                "error_type": fb.error_type,
                "corrected_sql": fb.corrected_sql,
                "promoted": fb.promoted,
                "created_at": fb.created_at.isoformat() if fb.created_at else None,
            }
            for fb in qs
        ]
        return JsonResponse({"results": results, "count": len(results)})
    except Exception as exc:
        logger.exception("nl2sql_feedback_list Fehler")
        return JsonResponse({"success": False, "error": str(exc)}, status=500)


@csrf_exempt
@require_POST
def nl2sql_feedback_promote(request, feedback_id: int):
    """
    POST /nl2sql/feedback/<id>/promote/

    Body: {"corrected_sql": "SELECT ..."}
    Promotes corrected_sql to NL2SQLExample.
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)

    corrected_sql = (body.get("corrected_sql") or "").strip()
    if not corrected_sql:
        return JsonResponse(
            {"success": False, "error": "corrected_sql fehlt oder leer"}, status=400
        )

    try:
        from aifw.nl2sql.models import NL2SQLExample, NL2SQLFeedback
        fb = NL2SQLFeedback.objects.select_related("source").filter(id=feedback_id).first()
        if not fb:
            return JsonResponse(
                {"success": False, "error": f"Feedback {feedback_id} nicht gefunden"}, status=404
            )
        if fb.promoted:
            return JsonResponse(
                {"success": False, "error": "Bereits promoted"}, status=400
            )
        fb.corrected_sql = corrected_sql
        fb.promoted = True
        fb.save(update_fields=["corrected_sql", "promoted"])

        ex = NL2SQLExample.objects.create(
            source=fb.source,
            question=fb.question,
            sql=corrected_sql,
            domain="",
            difficulty=2,
            is_active=True,
            promoted_from=fb,
        )
        logger.info("Feedback %d promoted to NL2SQLExample %d", fb.id, ex.id)
        return JsonResponse({"success": True, "example_id": ex.id})
    except Exception as exc:
        logger.exception("nl2sql_feedback_promote Fehler")
        return JsonResponse({"success": False, "error": str(exc)}, status=500)


@csrf_exempt
@require_POST
def nl2sql_query(request):
    """
    NL2SQL query endpoint.

    Request body (JSON):
        {
            "query": "Welche Maschinen sind in Störung?",
            "source_code": "odoo_mfg",          # optional, default: odoo_mfg
            "conversation_history": []           # optional
        }

    Response (JSON):
        {
            "success": true,
            "sql": "SELECT ...",
            "columns": [{"name": "...", "type_code": "..."}],
            "rows": [[...], ...],
            "row_count": 15,
            "execution_time_ms": 42.3,
            "chart_type": "bar",
            "chart": {"x_column": "...", "y_columns": [...], "reasoning": "..."},
            "warnings": [],
            "summary": "15 Zeilen — 42 ms"
        }

    Clarification response (when question is ambiguous):
        {
            "success": false,
            "needs_clarification": true,
            "clarification_question": "Worüber möchtest du eine Übersicht?",
            "clarification_options": [
                {"label": "Maschinen", "description": "...", "hint": "— bezogen auf Maschinen"}
            ]
        }

    Error response:
        {
            "success": false,
            "error": "Fehlerbeschreibung",
            "error_type": "NL2SQLGenerationError"
        }
    """
    # ── Parse request ────────────────────────────────────────────────────────
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return JsonResponse(
            {"success": False, "error": f"Ungültiger JSON-Body: {exc}", "error_type": "ParseError"},
            status=400,
        )

    query = (body.get("query") or "").strip()
    if not query:
        return JsonResponse(
            {"success": False, "error": "Parameter 'query' fehlt oder leer.", "error_type": "ValidationError"},
            status=400,
        )

    source_code = body.get("source_code") or "odoo_mfg"
    conversation_history = body.get("conversation_history") or []

    # ── Run NL2SQL engine ───────────────────────────────────────
    try:
        from aifw.nl2sql.engine import NL2SQLEngine

        engine = NL2SQLEngine(
            source_code=source_code,
            clarification_domains=[
                "Maschinen", "Gießaufträge", "Qualitätsprüfungen",
                "Einkauf/SCM", "Lager", "Produkte",
            ],
        )
        result = engine.ask(
            question=query,
            conversation_history=conversation_history,
        )
    except ValueError as exc:
        # SchemaSource not found
        logger.warning("NL2SQL SchemaSource fehler: %s", exc)
        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
                "error_type": "NL2SQLSchemaError",
            },
            status=400,
        )
    except Exception as exc:
        logger.exception("NL2SQL unerwarteter Fehler")
        return JsonResponse(
            {
                "success": False,
                "error": f"Interner Fehler: {exc}",
                "error_type": "InternalError",
            },
            status=500,
        )

    if result.needs_clarification:
        opts = []
        for o in (result.clarification_options or []):
            if isinstance(o, dict):
                opts.append(o)
            else:
                opts.append({
                    "label": getattr(o, "label", str(o)),
                    "description": getattr(o, "description", ""),
                    "hint": getattr(o, "hint", ""),
                })
        return JsonResponse({
            "success": False,
            "needs_clarification": True,
            "clarification_question": result.clarification_question or "",
            "clarification_options": opts,
        })

    if not result.success:
        return JsonResponse(
            {
                "success": False,
                "error": result.error,
                "error_type": result.error_type,
                "sql": result.sql or "",
            },
            status=422,
        )

    # ── Serialize result ─────────────────────────────────────────────────────
    fmt = result.formatted
    chart = fmt.chart

    return JsonResponse({
        "success": True,
        "sql": result.sql,
        "columns": fmt.columns,
        "rows": fmt.rows,
        "row_count": fmt.row_count,
        "execution_time_ms": round(fmt.execution_time_ms, 1),
        "truncated": fmt.truncated,
        "chart_type": chart.chart_type,
        "chart": {
            "x_column": chart.x_column,
            "y_columns": chart.y_columns,
            "title": chart.title,
            "reasoning": chart.reasoning,
        },
        "warnings": result.warnings,
        "summary": fmt.summary,
        "model_used": result.generation.model_used if result.generation else "",
        "tokens": {
            "input": result.generation.input_tokens if result.generation else 0,
            "output": result.generation.output_tokens if result.generation else 0,
        },
    })
