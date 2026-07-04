"""Drift-Guard: addons/mfg_nl2sql (v18) vs. addons_v19/mfg_nl2sql (v19).

Kontext (Retro R8 / F-E5, achimdehnert/platform#913)
====================================================
Die Retro-Annahme "beide Baeume sind bis auf 6 Controller-Zeilen identisch"
wurde per ``diff -ru`` geprueft und ist FALSCH. Die reale Divergenz umfasst
8 Dateien:

1. ``controllers/nl2sql_controller.py`` — 6x ``type='json'`` (v18) vs.
   ``type='jsonrpc'`` (v19). Odoo 19 hat den Route-Typ umbenannt.
2. ``__manifest__.py`` — Versionsprefix ``18.0.`` vs. ``19.0.`` plus
   zusaetzlicher data-Eintrag ``security/module_category.xml`` in v19.
3. ``security/module_category.xml`` — existiert NUR in v19.
4. ``security/security.xml`` — v19 hat den ``ir.module.category``-Record
   ausgelagert und ``comment``/``category_id`` von den ``res.groups``
   entfernt (Odoo-19-Inkompatibilitaet).
5.-8. Vier View-XMLs — Odoo 19 akzeptiert ``<group expand="0" string=...>``
   in Search-Views nicht mehr; v19 nutzt ``<group>``.

Warum Guard statt Konsolidierung auf EINE Quelle
------------------------------------------------
- Die Docker-Mounts verhindern Cross-Tree-Imports zur Laufzeit:
  ``docker-compose.prod.yml`` mountet NUR ``./addons`` (-> /mnt/extra-addons),
  ``docker-compose.staging.yml`` (Profil v19) mountet NUR ``./addons_v19``
  (-> /mnt/extra-addons-v19). Ein v19-Wrapper, der aus dem v18-Modul
  importiert, faende sein Ziel im Container nicht.
- XML-Datendateien (Views/Security) lassen sich nicht ueber Addon-Grenzen
  "importieren"; ihr Inhalt unterscheidet sich versionsbedingt wirklich.
- Ein Generator/Symlink-Ansatz wuerde Prod-Compose-Aenderungen erfordern —
  odoo-hub deployt bei jedem main-Push automatisch nach Prod.

Stattdessen erzwingt dieser Guard, dass JEDE Divergenz zwischen den Baeumen
eine der oben dokumentierten, Odoo-19-bedingten Transformationen ist:

- Dateibestand beider Baeume muss identisch sein (Ausnahme-Allowlist).
- Controller/Manifest/Views: nach deterministischer Normalisierung der
  bekannten Odoo-19-Transformationen muessen die Dateien byte-identisch sein.
- ``security/security.xml`` + ``security/module_category.xml``: bekannte,
  nicht mechanisch normalisierbare Divergenz — per SHA-256 gepinnt. Wer eine
  der Dateien bewusst aendert, muss BEIDE Baeume anfassen und die Pins hier
  aktualisieren (das ist der Zweck: Divergenz nur noch bewusst).
- Alle uebrigen Dateien muessen byte-identisch sein.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
V18_ROOT = REPO_ROOT / "addons" / "mfg_nl2sql"
V19_ROOT = REPO_ROOT / "addons_v19" / "mfg_nl2sql"

CONTROLLER = "controllers/nl2sql_controller.py"
MANIFEST = "__manifest__.py"

#: Dateien, die es nur in einem der beiden Baeume geben darf.
V19_ONLY_FILES = {"security/module_category.xml"}
V18_ONLY_FILES: set[str] = set()

#: Bekannte, nicht normalisierbare Divergenz — SHA-256-gepinnt (v18, v19).
#: None = Datei existiert in diesem Baum nicht.
PINNED_SHA256 = {
    "security/security.xml": (
        "944e68a5f78943a142487bd50eb816f680f2ab446e166bc486f85316eb824bd5",
        "4a85fc88397a1445ff9e7b1854252205ba91702872f6d68ab6119150bccd4a3e",
    ),
    "security/module_category.xml": (
        None,
        "163ec907a0b5e0bb156268193023a90c6cf87c5761e810e0e0f534f1db1e0328",
    ),
}

#: Odoo 19: <group expand="0" string="..."> in Search-Views -> <group>
_RE_GROUP_EXPAND = re.compile(r'<group expand="0" string="[^"]*">')


def _iter_rel_files(root: Path) -> set[str]:
    return {
        str(p.relative_to(root)).replace("\\", "/")
        for p in root.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
    }


def _normalize(rel: str, text: str) -> str:
    """Apply the documented v18<->v19 transformations (idempotent on both sides)."""
    if rel == CONTROLLER:
        # Odoo 19 renamed the JSON route type.
        return text.replace("type='jsonrpc'", "type='json'")
    if rel == MANIFEST:
        text = text.replace("'version': '19.0.", "'version': '18.0.")
        # v19-only data file entry (any indentation).
        return re.sub(r"^\s*'security/module_category\.xml',\n", "", text, flags=re.M)
    if rel.startswith("views/") and rel.endswith(".xml"):
        return _RE_GROUP_EXPAND.sub("<group>", text)
    return text


COMMON_FILES = sorted(
    (_iter_rel_files(V18_ROOT) & _iter_rel_files(V19_ROOT)) - set(PINNED_SHA256)
)


def test_should_have_matching_file_sets_between_v18_and_v19():
    v18_files = _iter_rel_files(V18_ROOT)
    v19_files = _iter_rel_files(V19_ROOT)
    unexpected_v19_only = (v19_files - v18_files) - V19_ONLY_FILES
    unexpected_v18_only = (v18_files - v19_files) - V18_ONLY_FILES
    assert not unexpected_v19_only, (
        "Neue Datei(en) nur in addons_v19/mfg_nl2sql: "
        f"{sorted(unexpected_v19_only)} — bitte in BEIDEN Baeumen anlegen "
        "oder hier dokumentiert allowlisten."
    )
    assert not unexpected_v18_only, (
        "Neue Datei(en) nur in addons/mfg_nl2sql: "
        f"{sorted(unexpected_v18_only)} — bitte in BEIDEN Baeumen anlegen "
        "oder hier dokumentiert allowlisten."
    )


@pytest.mark.parametrize("rel", COMMON_FILES)
def test_should_be_identical_after_documented_odoo19_transforms(rel):
    v18_bytes = (V18_ROOT / rel).read_bytes()
    v19_bytes = (V19_ROOT / rel).read_bytes()
    try:
        v18_text = v18_bytes.decode("utf-8")
        v19_text = v19_bytes.decode("utf-8")
    except UnicodeDecodeError:
        # Binaerdateien (z.B. static/description/icon.png): byte-identisch.
        assert v18_bytes == v19_bytes, (
            f"DRIFT in Binaerdatei {rel}: addons/ und addons_v19/ "
            "unterscheiden sich — Aenderung in BEIDE Baeume uebernehmen."
        )
        return
    assert _normalize(rel, v18_text) == _normalize(rel, v19_text), (
        f"DRIFT in {rel}: addons/ und addons_v19/ unterscheiden sich ueber die "
        "dokumentierten Odoo-19-Transformationen (Route-Typ, Manifest-Version, "
        "module_category-Eintrag, <group expand>) hinaus. Aenderungen an "
        "mfg_nl2sql muessen in BEIDE Baeume (Retro R8, platform#913)."
    )


@pytest.mark.parametrize("rel", sorted(PINNED_SHA256))
def test_should_match_pinned_hash_for_known_divergent_file(rel):
    expected_v18, expected_v19 = PINNED_SHA256[rel]
    for root, expected, label in (
        (V18_ROOT, expected_v18, "v18"),
        (V19_ROOT, expected_v19, "v19"),
    ):
        path = root / rel
        if expected is None:
            assert not path.exists(), (
                f"{rel} existiert jetzt auch im {label}-Baum — Pin in "
                "PINNED_SHA256 aktualisieren und Divergenz-Doku anpassen."
            )
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == expected, (
            f"{rel} ({label}) wurde geaendert (SHA-256 {actual[:12]}… statt "
            f"{expected[:12]}…). Diese Datei ist als bekannte v18/v19-Divergenz "
            "gepinnt: bitte pruefen, ob die Aenderung in BEIDE Baeume muss, "
            "und dann die Pins in PINNED_SHA256 aktualisieren."
        )


def test_should_diverge_only_in_route_type_lines_in_controller():
    """Explizite Retro-R8-Forderung: Controller-Diff > Route-Typ-Zeilen = rot."""
    v18_lines = (V18_ROOT / CONTROLLER).read_text(encoding="utf-8").splitlines()
    v19_lines = (V19_ROOT / CONTROLLER).read_text(encoding="utf-8").splitlines()
    assert len(v18_lines) == len(v19_lines), (
        "Controller-Dateien haben unterschiedliche Zeilenzahl — Divergenz "
        "jenseits des Route-Typs. Aenderung in BEIDE Baeume uebernehmen."
    )
    bad = [
        (i + 1, a, b)
        for i, (a, b) in enumerate(zip(v18_lines, v19_lines))
        if a != b and a.replace("type='json'", "type='jsonrpc'") != b
    ]
    assert not bad, f"Controller-Divergenz jenseits type='json(rpc)': {bad}"


def test_should_have_route_type_divergence_in_expected_direction():
    v18_text = (V18_ROOT / CONTROLLER).read_text(encoding="utf-8")
    v19_text = (V19_ROOT / CONTROLLER).read_text(encoding="utf-8")
    assert "type='jsonrpc'" not in v18_text, (
        "v18-Controller enthaelt type='jsonrpc' — Odoo 18 kennt diesen "
        "Route-Typ nicht."
    )
    assert "type='json'" not in v19_text.replace("type='jsonrpc'", ""), (
        "v19-Controller enthaelt type='json' — Odoo 19 erwartet type='jsonrpc'."
    )
    assert v18_text.count("type='json'") == v19_text.count("type='jsonrpc'"), (
        "Anzahl der JSON-Routen in v18 und v19 stimmt nicht ueberein."
    )
