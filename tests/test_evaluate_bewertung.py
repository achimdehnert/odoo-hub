"""Tests fuer die Bewertungslogik des NL->SQL-Benchmarks.

Der Benchmark selbst ruft ein Live-LLM und kostet Geld — er laeuft deshalb nicht
in CI. Seine Bewertungsfunktion ist aber reine Logik und entscheidet, welche
Trefferquote herauskommt. Eine falsch nachsichtige Bewertung meldet einen Erfolg,
den es nicht gibt; eine falsch strenge macht die Zahl wertlos, weil jede zulaessige
SQL-Variante als Fehler zaehlt. Beide Richtungen sind hier geprueft.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[1] / "services" / "aifw_service" / "evaluate.py"
_spec = importlib.util.spec_from_file_location("evaluate", _SRC)
evaluate = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = evaluate
_spec.loader.exec_module(evaluate)


def _fall(**over):
    f = {"id": "x", "tables": ["drone_machine"], "must_contain": ["state"]}
    f.update(over)
    return f


def test_should_pass_when_table_and_column_are_present():
    ok, gruende = evaluate._bewerte(
        _fall(), "SELECT name, state FROM drone_machine LIMIT 500"
    )
    assert (ok, gruende) == (True, [])


def test_should_accept_any_spelling_that_contains_the_expectations():
    # Es gibt viele richtige Formen derselben Abfrage. Der Benchmark misst, ob das
    # Modell die Frage verstanden hat — nicht, ob es formatiert wie die Vorlage.
    ok, _ = evaluate._bewerte(
        _fall(),
        "select\n  m.state,\n  m.name\nfrom DRONE_MACHINE m\norder by m.name",
    )
    assert ok


def test_should_fail_when_the_expected_table_is_missing():
    ok, gruende = evaluate._bewerte(_fall(), "SELECT state FROM other_table")
    assert not ok
    assert gruende == ["Tabelle fehlt: drone_machine"]


def test_should_fail_when_a_required_column_is_missing():
    ok, gruende = evaluate._bewerte(_fall(), "SELECT name FROM drone_machine")
    assert not ok
    assert gruende == ["erwartet, aber nicht enthalten: state"]


def test_should_collect_every_reason_not_just_the_first():
    # Wer nur den ersten Grund sieht, repariert einen Fall zweimal.
    ok, gruende = evaluate._bewerte(_fall(), "SELECT id FROM other_table")
    assert not ok
    assert len(gruende) == 2


def test_should_fail_when_no_sql_was_produced():
    for leer in (None, ""):
        ok, gruende = evaluate._bewerte(_fall(), leer)
        assert (ok, gruende) == (False, ["kein SQL erzeugt"])


@pytest.mark.parametrize(
    "fall,sql",
    [
        (_fall(tables=[], must_contain=[]), "SELECT 1"),
        (_fall(tables=[]), "SELECT state FROM irgendwas"),
        (_fall(must_contain=[]), "SELECT id FROM drone_machine"),
        ({"id": "ohne_felder"}, "SELECT 1"),
    ],
)
def test_should_not_invent_expectations_the_case_does_not_state(fall, sql):
    # Ein Fall, der keine Tabelle oder Spalte fordert, darf daran nicht scheitern.
    # Sonst waere jeder unvollstaendig beschriebene Fall automatisch ein Fehler,
    # und die Quote wuerde die Luecken im Datensatz messen statt das Modell.
    assert evaluate._bewerte(fall, sql) == (True, [])
