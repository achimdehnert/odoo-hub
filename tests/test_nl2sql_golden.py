"""
Golden-Query Test-Suite for NL2SQL Schema.

Validates that the Schema-XML fed to the LLM is internally consistent
and that key domain rules are encoded correctly. These tests run WITHOUT
an LLM call or database — they only parse the schema XML.

Why: The #1 cause of NL2SQL errors is schema drift (phantom columns,
missing tables, wrong FK descriptions). This suite catches those at CI time.

Usage:
    pytest tests/test_nl2sql_golden.py -v
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load schema XML from init_odoo_schema.py
# ---------------------------------------------------------------------------
_INIT_SCHEMA_PATH = Path(__file__).resolve().parent.parent / (
    "services/aifw_service/aifw_service/management/commands/init_odoo_schema.py"
)


def _load_schema_xml() -> str:
    """Extract ODOO_MFG_SCHEMA_XML from init_odoo_schema.py."""
    source = _INIT_SCHEMA_PATH.read_text()
    # Find the triple-quoted string
    marker_start = 'ODOO_MFG_SCHEMA_XML = """'
    marker_end = '"""'
    start = source.index(marker_start) + len(marker_start)
    end = source.index(marker_end, start)
    return source[start:end]


@pytest.fixture(scope="module")
def schema_root() -> ET.Element:
    xml_str = _load_schema_xml()
    return ET.fromstring(xml_str)


@pytest.fixture(scope="module")
def schema_tables(schema_root: ET.Element) -> dict[str, dict]:
    """Parse schema into {table_name: {columns: set, description: str, ...}}."""
    tables = {}
    for table_el in schema_root.findall(".//table"):
        name = table_el.get("name", "")
        columns = set()
        fk_columns = {}
        for col_el in table_el.findall("column"):
            col_name = col_el.get("name", "")
            columns.add(col_name)
            desc = col_el.findtext("description") or col_el.text or ""
            if "FK" in desc.upper() or "fk" in desc.lower():
                # Extract target table from "FK zu casting_machine"
                parts = desc.split("FK zu ")
                if len(parts) > 1:
                    target = parts[1].split()[0].strip("()")
                    fk_columns[col_name] = target
        tables[name] = {
            "columns": columns,
            "fk_columns": fk_columns,
            "description": table_el.findtext("description") or "",
            "element": table_el,
        }
    return tables


# ---------------------------------------------------------------------------
# Structural tests
# ---------------------------------------------------------------------------

class TestSchemaStructure:
    """Basic schema XML structure validation."""

    def test_schema_has_tables(self, schema_root):
        tables = schema_root.findall(".//table")
        assert len(tables) >= 5, f"Expected ≥5 tables, got {len(tables)}"

    def test_all_tables_have_id(self, schema_tables):
        for table_name, info in schema_tables.items():
            assert "id" in info["columns"], f"{table_name} missing 'id' column"

    def test_all_tables_have_description(self, schema_tables):
        for table_name, info in schema_tables.items():
            assert info["description"], f"{table_name} missing <description>"

    def test_all_tables_have_domain(self, schema_root):
        for table_el in schema_root.findall(".//table"):
            name = table_el.get("name")
            domain = table_el.get("domain")
            assert domain, f"{name} missing domain attribute"

    # Tables intentionally excluded from schema — secondary references
    # that don't affect common NL2SQL queries.
    EXCLUDED_FK_TARGETS = {"casting_mold", "res_users", "scm_part", "res_partner"}

    def test_fk_targets_exist(self, schema_tables):
        """Every FK reference should point to a table in the schema (or exclusion list)."""
        all_table_names = set(schema_tables.keys()) | self.EXCLUDED_FK_TARGETS
        for table_name, info in schema_tables.items():
            for col_name, target_table in info["fk_columns"].items():
                assert target_table in all_table_names, (
                    f"{table_name}.{col_name} references '{target_table}' "
                    f"but that table is not in the schema or exclusion list"
                )


# ---------------------------------------------------------------------------
# Domain-specific golden rules
# ---------------------------------------------------------------------------

class TestCastingDomainRules:
    """Rules specific to the casting/foundry domain schema."""

    def test_machine_id_not_on_casting_order(self, schema_tables):
        """machine_id must NOT be on casting_order — it's on casting_order_line."""
        co = schema_tables.get("casting_order")
        assert co is not None, "casting_order table missing"
        assert "machine_id" not in co["columns"], (
            "casting_order must NOT have machine_id — "
            "it belongs on casting_order_line"
        )

    def test_machine_id_on_casting_order_line(self, schema_tables):
        """machine_id MUST be on casting_order_line."""
        col = schema_tables.get("casting_order_line")
        assert col is not None, "casting_order_line table missing"
        assert "machine_id" in col["columns"], (
            "casting_order_line must have machine_id"
        )

    def test_casting_order_line_has_order_fk(self, schema_tables):
        """casting_order_line must have order_id FK to casting_order."""
        col = schema_tables.get("casting_order_line")
        assert col is not None
        assert "order_id" in col["columns"]
        assert col["fk_columns"].get("order_id") == "casting_order"

    def test_casting_order_has_join_hint(self, schema_tables):
        """casting_order should have a join_hint for machine lookups."""
        co = schema_tables.get("casting_order")
        assert co is not None
        join_hints = co["element"].findall("join_hint")
        assert len(join_hints) >= 1, (
            "casting_order needs a <join_hint> explaining "
            "how to reach machine via casting_order_line"
        )
        hint_text = join_hints[0].text or ""
        assert "casting_order_line" in hint_text, (
            "join_hint must mention casting_order_line"
        )

    def test_casting_order_description_warns_no_machine_id(self, schema_tables):
        """Description should warn LLM that machine_id is NOT here."""
        co = schema_tables.get("casting_order")
        assert co is not None
        desc = co["description"].lower()
        assert "machine_id" in desc or "maschine" in desc, (
            "casting_order description should warn about machine_id "
            "not being on this table"
        )

    def test_casting_machine_has_state(self, schema_tables):
        """casting_machine must expose state for 'which machines are broken' queries."""
        cm = schema_tables.get("casting_machine")
        assert cm is not None, "casting_machine table missing"
        assert "state" in cm["columns"]

    def test_quality_check_has_result(self, schema_tables):
        """casting_quality_check must have result column."""
        qc = schema_tables.get("casting_quality_check")
        assert qc is not None, "casting_quality_check table missing"
        assert "result" in qc["columns"]


class TestFKResolution:
    """FK columns must have JOIN hints so LLM resolves IDs to names."""

    def test_res_country_in_schema(self, schema_tables):
        """res_country must be in schema for country_id resolution."""
        assert "res_country" in schema_tables, (
            "res_country table missing — needed to resolve country_id to name"
        )

    def test_country_id_has_join_hint(self, schema_tables):
        """res_partner.country_id description should contain JOIN resolution hint."""
        rp = schema_tables.get("res_partner")
        assert rp is not None
        assert "country_id" in rp["columns"], "res_partner missing country_id"
        # Check the FK description mentions JOIN
        for col_el in rp["element"].findall("column"):
            if col_el.get("name") == "country_id":
                desc = (col_el.findtext("description") or "").lower()
                assert "join" in desc or "res_country" in desc, (
                    "country_id description must hint at JOIN resolution"
                )

    def test_res_country_has_name(self, schema_tables):
        """res_country must have name column for FK resolution."""
        rc = schema_tables.get("res_country")
        assert rc is not None
        assert "name" in rc["columns"]


class TestSCMDomainRules:
    """Rules specific to the SCM domain schema."""

    def test_production_order_has_yield(self, schema_tables):
        po = schema_tables.get("scm_production_order")
        assert po is not None
        assert "yield_pct" in po["columns"]

    def test_purchase_order_has_amount(self, schema_tables):
        po = schema_tables.get("scm_purchase_order")
        assert po is not None
        assert "total_amount" in po["columns"]


# ---------------------------------------------------------------------------
# Sample query consistency
# ---------------------------------------------------------------------------

class TestSampleQueries:
    """Validate that sample queries reference columns that exist."""

    def test_sample_queries_exist(self, schema_root):
        """Each table should have at least one sample_query."""
        for table_el in schema_root.findall(".//table"):
            name = table_el.get("name")
            samples = table_el.findall("sample_query")
            assert len(samples) >= 1, f"{name} has no <sample_query> elements"

    def test_sample_queries_not_empty(self, schema_root):
        for table_el in schema_root.findall(".//table"):
            for sq in table_el.findall("sample_query"):
                text = (sq.text or "").strip()
                assert len(text) > 10, (
                    f"{table_el.get('name')}: empty or too short sample_query"
                )
