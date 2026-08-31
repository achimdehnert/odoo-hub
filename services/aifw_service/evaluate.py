#!/usr/bin/env python3
"""NL->SQL-Accuracy-Benchmark gegen NL2SQLEngine.

Der Vorgaenger lebte in ttz-hub und rief `views._get_odoo_schema()` und
`views._build_messages()` — Interna des dortigen NL2SQL-Eigenbaus. Mit dessen
Ablösung durch die Bibliothek war er nicht mehr lauffaehig und wurde entfernt
(achimdehnert/platform#2546). Diese Fassung ruft `NL2SQLEngine.ask()` und ist
damit an die Schnittstelle gebunden statt an eine Implementierung.

Der Datensatz ist ein Argument, kein fester Pfad: die Faelle sind fachlich
(Drohnenfertigung, Giesserei, …) und gehoeren zur Installation, der Laeufer zum
Dienst.

ACHTUNG: ruft ein LIVE-LLM und kostet Geld. Kein Test, sondern eine Messung —
deshalb kein pytest, sondern ein Skript mit ausdruecklichem Aufruf.

    python evaluate.py --dataset tests/eval_dataset.json --source odoo_mfg
    python evaluate.py --dataset ... --nur-kategorie simple --limit 5
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


def _django_hochfahren() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aifw_service.settings")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import django

    django.setup()


def _bewerte(fall: dict, sql: str | None) -> tuple[bool, list[str]]:
    """Erfuellt das erzeugte SQL den Fall? Gibt (bestanden, Gruende) zurueck.

    Bewusst nachsichtig bei der Form und streng beim Inhalt: es gibt viele
    richtige Schreibweisen derselben Abfrage, aber wenn die erwartete Tabelle
    fehlt, hat das Modell die Frage nicht verstanden. Ein Zeichenketten-Vergleich
    mit einer Referenz-SQL wuerde dagegen jede zulaessige Variante als Fehler
    zaehlen und die Quote wertlos machen.
    """
    if not sql:
        return False, ["kein SQL erzeugt"]
    gross = sql.upper()
    gruende = []
    for tabelle in fall.get("tables") or []:
        if tabelle.upper() not in gross:
            gruende.append(f"Tabelle fehlt: {tabelle}")
    for spalte in fall.get("must_contain") or []:
        if spalte.upper() not in gross:
            gruende.append(f"erwartet, aber nicht enthalten: {spalte}")
    return not gruende, gruende


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", required=True, type=Path)
    ap.add_argument("--source", default="odoo_mfg", help="source_code der SchemaSource")
    ap.add_argument("--nur-kategorie", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--json", type=Path, help="Ergebnis zusaetzlich als JSON ablegen")
    args = ap.parse_args()

    if not args.dataset.is_file():
        print(f"Datensatz nicht gefunden: {args.dataset}", file=sys.stderr)
        return 2

    daten = json.loads(args.dataset.read_text(encoding="utf-8"))
    faelle = daten.get("cases") or []
    if args.nur_kategorie:
        faelle = [f for f in faelle if f.get("category") == args.nur_kategorie]
    if args.limit:
        faelle = faelle[: args.limit]
    if not faelle:
        print("Keine Faelle im Datensatz (nach Filterung)", file=sys.stderr)
        return 2

    _django_hochfahren()
    from aifw.nl2sql.engine import NL2SQLEngine

    engine = NL2SQLEngine(source_code=args.source)

    ergebnisse = []
    bestanden = 0
    beginn = time.monotonic()

    for i, fall in enumerate(faelle, 1):
        frage = fall["question"]
        try:
            r = engine.ask(question=frage)
            sql = getattr(r, "sql", None)
            nachfrage = bool(getattr(r, "needs_clarification", False))
        except Exception as exc:  # noqa: BLE001 — ein Ausfall ist ein Messwert
            sql, nachfrage = None, False
            gruende = [f"Ausnahme: {exc.__class__.__name__}: {exc}"]
            ok = False
        else:
            if nachfrage and fall.get("expect") == "sql":
                ok, gruende = False, ["Rueckfrage statt SQL"]
            else:
                ok, gruende = _bewerte(fall, sql)

        bestanden += ok
        ergebnisse.append(
            {
                "id": fall.get("id"),
                "kategorie": fall.get("category"),
                "schwierigkeit": fall.get("difficulty"),
                "bestanden": ok,
                "gruende": gruende,
                "sql": sql,
            }
        )
        zeichen = "ok  " if ok else "FEHL"
        print(f"[{i}/{len(faelle)}] {zeichen} {fall.get('id')}")
        for g in gruende:
            print(f"          {g}")

    dauer = time.monotonic() - beginn
    quote = 100 * bestanden / len(faelle)
    print(f"\n{bestanden}/{len(faelle)} bestanden ({quote:.0f} %) in {dauer:.0f}s")

    # Aufschluesselung: eine Gesamtquote verdeckt, ob die schweren Faelle
    # scheitern oder die einfachen — und nur das erste ist normal.
    for feld in ("kategorie", "schwierigkeit"):
        gruppen: dict[str, list[bool]] = {}
        for e in ergebnisse:
            gruppen.setdefault(str(e[feld]), []).append(e["bestanden"])
        teile = [f"{k}: {sum(v)}/{len(v)}" for k, v in sorted(gruppen.items())]
        print(f"  nach {feld} — " + " · ".join(teile))

    if args.json:
        args.json.write_text(
            json.dumps(
                {"bestanden": bestanden, "gesamt": len(faelle), "faelle": ergebnisse},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"  Rohdaten: {args.json}")

    # Exit 1 bei Fehlschlaegen, damit der Aufruf in einer Kette bemerkt wird.
    return 0 if bestanden == len(faelle) else 1


if __name__ == "__main__":
    sys.exit(main())
