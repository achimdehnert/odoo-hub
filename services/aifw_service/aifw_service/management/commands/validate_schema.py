"""
Management Command: validate_schema

Validates the NL2SQL Schema-XML against the actual Odoo PostgreSQL database.
Detects schema drift: columns/tables in XML that don't exist in DB and vice versa.

Usage:
    python manage.py validate_schema
    python manage.py validate_schema --source odoo_mfg --strict
    python manage.py validate_schema --check  # exit 1 on errors (CI mode)
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET

from django.core.management.base import BaseCommand
from django.db import connections


class Command(BaseCommand):
    help = "Validate NL2SQL Schema-XML against actual DB schema (drift detection)"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--source",
            default="odoo_mfg",
            help="SchemaSource code to validate (default: odoo_mfg)",
        )
        parser.add_argument(
            "--check",
            action="store_true",
            help="CI mode: exit 1 if any errors found",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Also warn about DB columns missing from schema XML",
        )

    def handle(self, *args, **options) -> None:
        from aifw.nl2sql.models import SchemaSource

        source_code = options["source"]
        source = SchemaSource.objects.filter(code=source_code, is_active=True).first()
        if not source:
            self.stderr.write(self.style.ERROR(
                f"SchemaSource '{source_code}' not found or inactive."
            ))
            sys.exit(1)

        # Parse schema XML
        root = ET.fromstring(source.schema_xml)
        schema_tables = self._parse_schema_xml(root)

        # Query actual DB schema
        db_alias = source.db_alias or "default"
        db_tables = self._query_db_schema(db_alias, schema_tables.keys())

        # Compare
        errors: list[str] = []
        warnings: list[str] = []

        for table_name, xml_columns in schema_tables.items():
            if table_name not in db_tables:
                errors.append(f"TABLE {table_name}: exists in schema XML but NOT in database")
                continue

            db_columns = db_tables[table_name]

            # Columns in XML but not in DB
            for col_name in xml_columns:
                if col_name not in db_columns:
                    errors.append(
                        f"COLUMN {table_name}.{col_name}: in schema XML but NOT in database"
                    )

            # Columns in DB but not in XML (informational)
            if options["strict"]:
                for col_name in db_columns:
                    if col_name not in xml_columns and col_name not in (
                        "write_uid", "write_date", "create_uid", "create_date",
                        "__last_update",
                    ):
                        warnings.append(
                            f"COLUMN {table_name}.{col_name}: in database but NOT in schema XML"
                        )

        # Tables in DB matching prefix but not in XML
        if options["strict"]:
            blocked = source.get_blocked_tables_set() if hasattr(source, "get_blocked_tables_set") else set()
            all_db_tables = self._query_all_tables(db_alias, prefixes=["casting_", "scm_"])
            for t in all_db_tables:
                if t not in schema_tables and t not in blocked:
                    warnings.append(f"TABLE {t}: exists in database but NOT in schema XML")

        # Output
        if errors:
            self.stderr.write(self.style.ERROR(f"\n{'='*60}"))
            self.stderr.write(self.style.ERROR(f"SCHEMA DRIFT DETECTED — {len(errors)} error(s)"))
            self.stderr.write(self.style.ERROR(f"{'='*60}"))
            for e in errors:
                self.stderr.write(self.style.ERROR(f"  ✗ {e}"))

        if warnings:
            self.stderr.write(self.style.WARNING(f"\n{len(warnings)} warning(s):"))
            for w in warnings:
                self.stderr.write(self.style.WARNING(f"  ⚠ {w}"))

        if not errors and not warnings:
            self.stdout.write(self.style.SUCCESS(
                f"✓ Schema '{source_code}' is consistent with database "
                f"({len(schema_tables)} tables, "
                f"{sum(len(c) for c in schema_tables.values())} columns)"
            ))
        elif not errors:
            self.stdout.write(self.style.SUCCESS(
                f"✓ No errors — {len(warnings)} warnings (use --strict for details)"
            ))

        if options["check"] and errors:
            sys.exit(1)

    def _parse_schema_xml(self, root: ET.Element) -> dict[str, set[str]]:
        """Parse schema XML and return {table_name: {col1, col2, ...}}."""
        tables: dict[str, set[str]] = {}
        for table_el in root.findall(".//table"):
            table_name = table_el.get("name", "")
            if not table_name:
                continue
            columns = set()
            for col_el in table_el.findall("column"):
                col_name = col_el.get("name", "")
                if col_name:
                    columns.add(col_name)
            tables[table_name] = columns
        return tables

    def _query_db_schema(
        self, db_alias: str, table_names: set[str] | dict
    ) -> dict[str, set[str]]:
        """Query actual column names from PostgreSQL information_schema."""
        if not table_names:
            return {}
        tables_list = list(table_names)
        placeholders = ", ".join(["%s"] * len(tables_list))
        sql = f"""
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name IN ({placeholders})
            ORDER BY table_name, ordinal_position
        """
        with connections[db_alias].cursor() as cursor:
            cursor.execute(sql, tables_list)
            rows = cursor.fetchall()

        result: dict[str, set[str]] = {}
        for table_name, column_name in rows:
            result.setdefault(table_name, set()).add(column_name)
        return result

    def _query_all_tables(self, db_alias: str, prefixes: list[str]) -> set[str]:
        """Query all table names matching given prefixes."""
        conditions = " OR ".join(["table_name LIKE %s"] * len(prefixes))
        params = [f"{p}%" for p in prefixes]
        sql = f"""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND ({conditions})
        """
        with connections[db_alias].cursor() as cursor:
            cursor.execute(sql, params)
            return {row[0] for row in cursor.fetchall()}
