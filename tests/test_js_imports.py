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


def _get_addon_dirs() -> list[Path]:
    return [
        d for d in ADDONS_DIR.iterdir()
        if d.is_dir() and (d / "__manifest__.py").exists()
    ]


def _get_addon_js_files() -> list[tuple[Path, str]]:
    """Return (js_file_path, addon_name) tuples for all JS files in custom addons."""
    result = []
    for addon_dir in _get_addon_dirs():
        addon_name = addon_dir.name
        for js_file in addon_dir.rglob("*.js"):
            if "node_modules" in js_file.parts or "__pycache__" in js_file.parts:
                continue
            result.append((js_file, addon_name))
    return result


def _get_addon_xml_files() -> list[Path]:
    files = []
    for addon_dir in _get_addon_dirs():
        for xml_file in addon_dir.rglob("*.xml"):
            if "node_modules" in xml_file.parts:
                continue
            files.append(xml_file)
    return files


JS_FILE_TUPLES = _get_addon_js_files()
JS_IDS = [t[0].relative_to(ADDONS_DIR).as_posix() for t in JS_FILE_TUPLES]

XML_FILES = _get_addon_xml_files()
XML_IDS = [f.relative_to(ADDONS_DIR).as_posix() for f in XML_FILES]


@pytest.mark.parametrize("js_tuple", JS_FILE_TUPLES, ids=JS_IDS)
class TestJsImports:
    def test_no_forbidden_cross_module_imports(self, js_tuple: tuple) -> None:
        """Ensure no cross-module JS imports that break the Odoo 18 bundler.

        Odoo 18 transforms relative imports within a module to @modulename/
        internally. Imports from OTHER modules via @othername/ or full static
        paths cannot be resolved at runtime and silently freeze the OWL app.

        Intra-module @own_modulename/ is valid (it's how Odoo bundles it).
        Only inter-module @other_modulename/ is forbidden.
        """
        js_file, addon_name = js_tuple
        source = js_file.read_text(encoding="utf-8")

        violations = []

        # Pattern 1: from "@other_module/..." — cross-module alias import
        cross_alias = re.compile(r'from\s+["\']@(?!web/|odoo/)([^/"\'\.][^"\']*)["\']\'?')
        for match in cross_alias.finditer(source):
            imported_path = match.group(1)
            # Allow if the alias starts with own module name (intra-module)
            if imported_path.startswith(addon_name + "/"):
                continue
            line_num = source[:match.start()].count("\n") + 1
            violations.append(f"  Line {line_num}: {match.group(0)!r}")

        # Pattern 2: from "other_module/static/src/..." — full path cross-module
        full_path = re.compile(
            r'from\s+["\'](?!@|\.\./|\./|' + re.escape(addon_name) + r'/)'
            r'([a-zA-Z_][a-zA-Z0-9_]*/static/[^"\']*)["\']\'?'
        )
        for match in full_path.finditer(source):
            line_num = source[:match.start()].count("\n") + 1
            violations.append(f"  Line {line_num}: {match.group(0)!r}")

        assert not violations, (
            f"\n{js_file.relative_to(ADDONS_DIR)}: "
            f"Forbidden cross-module import(s) detected.\n"
            f"Odoo 18 can only resolve @web/, @odoo/, and relative (./) imports.\n"
            f"Imports from OTHER modules (@other_module/...) freeze the OWL app.\n"
            f"Violations:\n" + "\n".join(violations) + "\n\n"
            f"Fix: duplicate the needed code into this module, or use the OWL "
            f"registry pattern. See docs/adr/ADR-006-ODOO18-JS-IMPORTS.md"
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
