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

    # ── Run NL2SQL engine ────────────────────────────────────────────────────
    try:
        from aifw.nl2sql import NL2SQLEngine

        engine = NL2SQLEngine(source_code=source_code)
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
