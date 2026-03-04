"""Static tests for Odoo 18 JavaScript import correctness — no Odoo runtime needed.

BACKGROUND:
Odoo 18 uses a custom ES-module bundler that transforms relative imports
within a module to the @modulename/ namespace internally. This means:

  - Cross-module imports like `import X from "@my_addon/js/file"` are
    NOT resolvable at runtime (only @web/ and @odoo/ are valid aliases).
  - Cross-module imports like `import X from "my_addon/static/src/js/file"`
    are also NOT resolvable.
  - An unresolvable import causes require() to fail silently, which prevents
    the OWL application from mounting → entire navigation is frozen/unclickable.

RULE (enforced here):
All JavaScript files in custom addons MUST only use:
  1. Relative imports within the same module: `./file`, `../utils/file`
  2. @web/ alias: `import X from "@web/core/registry"`
  3. @odoo/ alias: `import X from "@odoo/owl"`
  4. Node built-ins (rare in Odoo context)

This test prevents re-introducing the cross-module import bug that caused
the OWL app navigation freeze (diagnosed 2026-03-04, fixed in commit 437f0eb).

KNOWN VALID ALIASES in Odoo 18:
  @web/        → Odoo web framework
  @odoo/owl    → OWL 2 component library
  @odoo/o-spreadsheet → spreadsheet component

All other @something/ imports are FORBIDDEN in custom addons.
"""

import re
from pathlib import Path

import pytest

ADDONS_DIR = Path(__file__).parent.parent / "addons"

VALID_IMPORT_PREFIXES = (
    "@web/",
    "@odoo/",
    "./",
    "../",
    "\"./",
    "'./",
    "\"../",
    "'../",
)

FORBIDDEN_IMPORT_PATTERNS = [
    re.compile(r'from\s+["\']@(?!web/|odoo/)([^"\']+)["\']'),
    re.compile(r'require\s*\(\s*["\']@(?!web/|odoo/)([^"\']+)["\']\s*\)'),
    re.compile(r'from\s+["\'](?!@|\.\.?/)([a-zA-Z_][a-zA-Z0-9_]*/static/[^"\']+)["\']'),
]

FORBIDDEN_XML_PATTERNS = [
    re.compile(r't-inherit-mode=["\']primary["\'][^>]*/\s*>'),
    re.compile(r't-inherit-mode=["\']primary["\'][^>]*/>'),
]


def _get_addon_js_files() -> list[Path]:
    files = []
    for addon_dir in ADDONS_DIR.iterdir():
        if not addon_dir.is_dir() or not (addon_dir / "__manifest__.py").exists():
            continue
        for js_file in addon_dir.rglob("*.js"):
            if "node_modules" in js_file.parts or "__pycache__" in js_file.parts:
                continue
            files.append(js_file)
    return files


def _get_addon_xml_files() -> list[Path]:
    files = []
    for addon_dir in ADDONS_DIR.iterdir():
        if not addon_dir.is_dir() or not (addon_dir / "__manifest__.py").exists():
            continue
        for xml_file in addon_dir.rglob("*.xml"):
            if "node_modules" in xml_file.parts:
                continue
            files.append(xml_file)
    return files


JS_FILES = _get_addon_js_files()
JS_IDS = [f.relative_to(ADDONS_DIR).as_posix() for f in JS_FILES]

XML_FILES = _get_addon_xml_files()
XML_IDS = [f.relative_to(ADDONS_DIR).as_posix() for f in XML_FILES]


@pytest.mark.parametrize("js_file", JS_FILES, ids=JS_IDS)
class TestJsImports:
    def test_no_forbidden_cross_module_imports(self, js_file: Path) -> None:
        """Ensure no cross-module JS imports that break the Odoo 18 bundler."""
        source = js_file.read_text(encoding="utf-8")

        violations = []
        for pattern in FORBIDDEN_IMPORT_PATTERNS:
            for match in pattern.finditer(source):
                line_num = source[: match.start()].count("\n") + 1
                violations.append(
                    f"  Line {line_num}: {match.group(0)!r}"
                )

        assert not violations, (
            f"\n{js_file.relative_to(ADDONS_DIR)}: "
            f"Forbidden cross-module import(s) detected.\n"
            f"Odoo 18 can only resolve @web/, @odoo/, and relative (./) imports.\n"
            f"Cross-module imports freeze the OWL app (navigation becomes unclickable).\n"
            f"Violations:\n" + "\n".join(violations) + "\n\n"
            f"Fix: duplicate the needed code into this module, or move shared code "
            f"into @web/ (Odoo core). See docs/adr/ADR-006-ODOO18-JS-IMPORTS.md"
        )


@pytest.mark.parametrize("xml_file", XML_FILES, ids=XML_IDS)
class TestXmlTemplates:
    def test_no_empty_primary_inherit(self, xml_file: Path) -> None:
        """Detect empty t-inherit-mode=primary templates that produce undefined OWL templates."""
        source = xml_file.read_text(encoding="utf-8")

        violations = []
        for pattern in FORBIDDEN_XML_PATTERNS:
            for match in pattern.finditer(source):
                line_num = source[: match.start()].count("\n") + 1
                violations.append(f"  Line {line_num}: {match.group(0)[:120]!r}")

        assert not violations, (
            f"\n{xml_file.relative_to(ADDONS_DIR)}: "
            f"Empty t-inherit-mode='primary' template(s) detected.\n"
            f"In Odoo 18 QWeb, a self-closing t-inherit-mode=primary tag produces\n"
            f"an undefined template, causing OWL to freeze on mount.\n"
            f"Violations:\n" + "\n".join(violations) + "\n\n"
            f"Fix: provide a full template body, or use t-inherit-mode='extension'."
        )
