"""Laedt die Few-Shot-Beispiele aus nl2sql_examples.json in NL2SQLExample.

Warum beides — Datei UND Datenbank (platform#2546, Entscheidung 2026-08-31):

Die Engine liest Beispiele ausschliesslich aus der Datenbank
(`NL2SQLEngine._load_examples` -> `NL2SQLExample.objects`). Eine JSON-Datei allein
wuerde von ihr nie gelesen. Die Datenbank ist ausserdem der Ort, an dem der
Lernkreislauf stattfindet: aus einem erfolgreichen Retry wird automatisch ein neues
Beispiel (`engine.py`, "auto-promote to example") — das kann eine Datei nicht.

Umgekehrt ist eine reine Datenbank-Ablage nicht reviewbar und nicht versioniert.
Die 16 Beispiele sind erarbeitetes Fachwissen; sie sollen in einem Diff sichtbar
sein, wenn jemand sie aendert.

Deshalb: die Datei ist die **Quelle**, die Datenbank die **Laufzeit-Ablage**, und
dieser Befehl ist der Weg dazwischen. Er ist idempotent — mehrfaches Ausfuehren
legt nichts doppelt an. Beispiele, die der Lernkreislauf ergaenzt hat, bleiben
unangetastet: der Befehl loescht nicht, er gleicht ab.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

# Vorgabe: die Beispieldatei neben dem Dienst. Ueberschreibbar per --datei, weil
# der Dienst als gemeinsames Image laeuft (ghcr.io/achimdehnert/odoo-hub/aifw-service)
# und jede Installation ihre eigenen Faelle mitbringt — ttz-hub fragt nach Drohnen,
# odoo-hub nach Giesserei. Der Laeufer gehoert zum Dienst, die Daten zur
# Installation (achimdehnert/platform#2546).
BEISPIELE_VORGABE = Path(__file__).resolve().parents[2] / "nl2sql_examples.json"


class Command(BaseCommand):
    help = "Laedt nl2sql_examples.json in NL2SQLExample (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            required=True,
            help="source_code der SchemaSource, der die Beispiele zugeordnet werden",
        )
        parser.add_argument(
            "--datei",
            type=Path,
            default=BEISPIELE_VORGABE,
            help="Beispieldatei (Vorgabe: nl2sql_examples.json neben dem Dienst)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="nur zeigen, was angelegt wuerde",
        )

    def handle(self, *args, **opts):
        from aifw.nl2sql.models import NL2SQLExample, SchemaSource

        datei = opts["datei"]
        if not datei.is_file():
            raise CommandError(f"Beispieldatei fehlt: {datei}")

        daten = json.loads(datei.read_text(encoding="utf-8"))
        beispiele = daten.get("examples") or []
        if not beispiele:
            raise CommandError("Kein 'examples'-Block in der Beispieldatei")

        try:
            source = SchemaSource.objects.get(code=opts["source"])
        except SchemaSource.DoesNotExist as exc:
            raise CommandError(
                f"SchemaSource '{opts['source']}' existiert nicht — "
                "erst das Schema initialisieren, dann die Beispiele laden."
            ) from exc

        neu = uebersprungen = 0
        for b in beispiele:
            frage, sql = b.get("question"), b.get("sql")
            if not frage or not sql:
                self.stderr.write(f"unvollstaendiges Beispiel uebersprungen: {b!r}")
                continue
            # Abgleich ueber die Frage: sie ist der fachliche Schluessel. Zwei
            # Beispiele mit derselben Frage und anderem SQL waeren ein Widerspruch
            # in der Quelle, kein Grund fuer einen zweiten Datensatz.
            if NL2SQLExample.objects.filter(source=source, question=frage).exists():
                uebersprungen += 1
                continue
            if not opts["dry_run"]:
                NL2SQLExample.objects.create(
                    source=source, question=frage, sql=sql, is_active=True
                )
            neu += 1

        vorsatz = "wuerde anlegen" if opts["dry_run"] else "angelegt"
        self.stdout.write(
            f"{vorsatz}: {neu} · bereits vorhanden: {uebersprungen} · "
            f"Quelle: {datei} · SchemaSource: {opts['source']}"
        )
