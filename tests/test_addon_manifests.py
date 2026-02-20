"""Static tests for Odoo addon manifests and structure — no Odoo runtime needed.

These tests run in CI without an Odoo installation. They validate:
- __manifest__.py structure and required keys
- Odoo version format compliance
- Referenced data/security files exist on disk
- Python import structure is intact
"""

import ast
import os
from pathlib import Path

import pytest

ADDONS_DIR = Path(__file__).parent.parent / "addons"

REQUIRED_MANIFEST_KEYS = {
    "name",
    "version",
    "license",
    "depends",
    "installable",
}

VALID_LICENSES = {"LGPL-3", "AGPL-3", "OPL-1", "MIT", "Apache-2.0"}


def _get_addon_dirs() -> list[Path]:
    """Return all addon directories that contain a __manifest__.py."""
    return [
        d for d in ADDONS_DIR.iterdir()
        if d.is_dir() and (d / "__manifest__.py").exists()
    ]


def _load_manifest(addon_dir: Path) -> dict:
    """Parse __manifest__.py as a Python literal (safe, no exec)."""
    manifest_path = addon_dir / "__manifest__.py"
    source = manifest_path.read_text(encoding="utf-8")
    # Strip leading comments/encoding declarations before the dict
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or stripped == "":
            continue
        break
    # Find the dict literal
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Dict):
            return ast.literal_eval(node.value)
    raise ValueError(f"No dict literal found in {manifest_path}")


ADDON_DIRS = _get_addon_dirs()
ADDON_IDS = [d.name for d in ADDON_DIRS]


@pytest.mark.parametrize("addon_dir", ADDON_DIRS, ids=ADDON_IDS)
class TestManifestStructure:
    def test_should_have_required_keys(self, addon_dir: Path) -> None:
        manifest = _load_manifest(addon_dir)
        missing = REQUIRED_MANIFEST_KEYS - set(manifest.keys())
        assert not missing, f"{addon_dir.name}: missing keys {missing}"

    def test_should_have_valid_odoo_version_format(self, addon_dir: Path) -> None:
        manifest = _load_manifest(addon_dir)
        version = manifest.get("version", "")
        parts = version.split(".")
        assert len(parts) == 5, (
            f"{addon_dir.name}: version '{version}' must be X.Y.A.B.C (e.g. 18.0.1.0.0)"
        )
        assert parts[0] == "18", f"{addon_dir.name}: must target Odoo 18, got '{parts[0]}'"

    def test_should_have_valid_license(self, addon_dir: Path) -> None:
        manifest = _load_manifest(addon_dir)
        license_ = manifest.get("license", "")
        assert license_ in VALID_LICENSES, (
            f"{addon_dir.name}: license '{license_}' not in {VALID_LICENSES}"
        )

    def test_should_have_installable_true(self, addon_dir: Path) -> None:
        manifest = _load_manifest(addon_dir)
        assert manifest.get("installable") is True, (
            f"{addon_dir.name}: installable must be True"
        )

    def test_should_have_non_empty_name(self, addon_dir: Path) -> None:
        manifest = _load_manifest(addon_dir)
        assert manifest.get("name", "").strip(), f"{addon_dir.name}: name must not be empty"

    def test_should_have_depends_list(self, addon_dir: Path) -> None:
        manifest = _load_manifest(addon_dir)
        depends = manifest.get("depends", None)
        assert isinstance(depends, list), f"{addon_dir.name}: depends must be a list"
        assert len(depends) >= 1, f"{addon_dir.name}: depends must include at least 'base'"


@pytest.mark.parametrize("addon_dir", ADDON_DIRS, ids=ADDON_IDS)
class TestAddonFileStructure:
    def test_should_have_init_py(self, addon_dir: Path) -> None:
        assert (addon_dir / "__init__.py").exists(), (
            f"{addon_dir.name}: missing __init__.py"
        )

    def test_should_have_security_dir(self, addon_dir: Path) -> None:
        assert (addon_dir / "security").is_dir(), (
            f"{addon_dir.name}: missing security/ directory"
        )

    def test_should_have_access_csv(self, addon_dir: Path) -> None:
        csv_path = addon_dir / "security" / "ir.model.access.csv"
        assert csv_path.exists(), (
            f"{addon_dir.name}: missing security/ir.model.access.csv"
        )

    def test_should_have_views_dir(self, addon_dir: Path) -> None:
        assert (addon_dir / "views").is_dir(), (
            f"{addon_dir.name}: missing views/ directory"
        )

    def test_manifest_data_files_exist(self, addon_dir: Path) -> None:
        manifest = _load_manifest(addon_dir)
        missing = []
        for rel_path in manifest.get("data", []):
            full_path = addon_dir / rel_path
            if not full_path.exists():
                missing.append(rel_path)
        assert not missing, (
            f"{addon_dir.name}: data files missing: {missing}"
        )
