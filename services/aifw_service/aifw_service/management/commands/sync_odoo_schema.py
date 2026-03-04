"""
Management Command: sync_odoo_schema

Liest Feld-Metadaten (Labels, Typen, Beschreibungen) direkt aus der Odoo-PostgreSQL-DB
über den konfigurierten DATABASES['odoo']-Alias und generiert daraus ein Schema-XML
mit label-Attributen.

Das label-Attribut wird vom NL2SQLEngine System-Prompt genutzt um automatisch
korrekte deutsche Spaltenaliase zu erzwingen — ohne manuell gepflegte Beispiele.

Datenquellen (direkt via DB, kein HTTP-Session-Problem):
  1. nl2sql_schema_table   — kuratierte Tabellenliste mit model_name
  2. ir_model_fields       — Odoo-Feldlabels (field_description JSONB), Typen, Hilfetext

Workflow:
  1. nl2sql_schema_table aus Odoo-DB lesen
  2. ir_model_fields per JOIN → Labels, Typen
  3. XML generieren mit <column name="state" label="Status" type="selection">
  4. SchemaSource 'odoo_mfg' in aifw-DB aktualisieren

Usage:
    python manage.py sync_odoo_schema
    python manage.py sync_odoo_schema --db-alias odoo --dry-run
    python manage.py sync_odoo_schema --source odoo_mfg --output schema.xml
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from io import StringIO

from django.core.management.base import BaseCommand


# ---------------------------------------------------------------------------
# XML generation
# ---------------------------------------------------------------------------

TYPE_MAP = {
    "integer": "integer", "float": "numeric", "monetary": "numeric",
    "char": "varchar", "text": "text", "boolean": "boolean",
    "date": "date", "datetime": "timestamp",
    "selection": "varchar", "many2one": "integer",
}

SCALAR_TYPES = {
    "integer", "float", "monetary", "char", "text",
    "boolean", "date", "datetime", "selection", "many2one",
}


def _build_schema_xml(tables: list, source_name: str = "odoo_mfg") -> str:
    root = ET.Element("schema", name=source_name, description="Odoo 18 Manufacturing + SCM — auto-sync")

    for table_meta in tables:
        tbl = ET.SubElement(root, "table",
            name=table_meta["table"],
            domain=table_meta.get("domain", ""),
        )
        if table_meta.get("description"):
            desc_el = ET.SubElement(tbl, "description")
            desc_el.text = table_meta["description"]

        # Curated columns with Odoo labels
        for col in table_meta.get("columns", []):
            col_type = TYPE_MAP.get(col.get("type", ""), col.get("type", "varchar"))
            attrs = {
                "name":  col["name"],
                "type":  col_type,
                "label": col.get("label") or col["name"],
            }
            col_el = ET.SubElement(tbl, "column", **attrs)

            # description = curated text or Odoo help
            desc = col.get("description") or col.get("help", "")
            if desc:
                d = ET.SubElement(col_el, "description")
                d.text = desc

            # selection values hint
            if col.get("selection"):
                sv = ET.SubElement(col_el, "values")
                sv.text = col["selection"]

            # FK hint
            if col.get("fk_table"):
                fk = ET.SubElement(col_el, "fk")
                fk.text = col["fk_table"]

        # Extra discovered fields (auto=True, not yet in curated list)
        for col in table_meta.get("extra_fields", []):
            if col.get("type") not in SCALAR_TYPES:
                continue
            col_type = TYPE_MAP.get(col.get("type", ""), "varchar")
            col_el = ET.SubElement(tbl, "column",
                name=col["name"],
                type=col_type,
                label=col.get("label") or col["name"],
                auto="true",
            )

    # Pretty-print
    _indent(root)
    tree = ET.ElementTree(root)
    buf = StringIO()
    buf.write('<?xml version="1.0" encoding="utf-8"?>\n')
    buf.write(ET.tostring(root, encoding="unicode"))
    return buf.getvalue()


def _indent(elem, level=0):
    pad = "\n" + "  " * level
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = pad + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = pad
        for child in elem:
            _indent(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = pad
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = pad


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = "Sync Schema-XML aus Odoo ir.model.fields (direkte DB-Abfrage via DATABASES['odoo'])"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--db-alias", default="odoo", dest="db_alias",
                            help="Django DATABASES-Alias der Odoo-DB (Standard: odoo)")
        parser.add_argument("--source", default="odoo_mfg",
                            help="SchemaSource-Code in aifw-DB")
        parser.add_argument("--output", default="",
                            help="XML in Datei schreiben statt DB-Update")
        parser.add_argument("--dry-run", action="store_true",
                            help="XML ausgeben ohne DB zu ändern")

    def handle(self, *args, **options) -> None:
        from django.db import connections

        db_alias = options["db_alias"]
        source_code = options["source"]
        dry_run = options["dry_run"]

        # 1. Load nl2sql_schema_table from Odoo DB
        self.stdout.write(f"→ Lese nl2sql_schema_table aus DB alias '{db_alias}' …")
        try:
            conn = connections[db_alias]
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT t.name, t.model_name, t.domain, t.description
                    FROM nl2sql_schema_table t
                    WHERE t.is_active = true
                    ORDER BY t.domain, t.name
                """)
                schema_tables = [
                    {"name": r[0], "model_name": r[1] or "", "domain": r[2] or "", "description": r[3] or ""}
                    for r in cur.fetchall()
                ]
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"  DB-Zugriff fehlgeschlagen: {e}"))
            return

        if not schema_tables:
            self.stderr.write(self.style.WARNING(
                "  nl2sql_schema_table ist leer — Schema-Tabellen anlegen:\n"
                "  Odoo > NL2SQL Dashboard > Schema-Verwaltung"
            ))
            return
        self.stdout.write(f"  ✓ {len(schema_tables)} Tabellen")

        # 2. For each table: load columns + ir.model.fields labels
        SKIP_TYPES = {"one2many", "many2many", "binary", "html"}
        SKIP_FIELDS = {"create_uid", "write_uid", "__last_update"}

        tables = []
        with connections[db_alias].cursor() as cur:
            for st in schema_tables:
                model_name = st["model_name"]
                columns = []

                if model_name:
                    cur.execute("""
                        SELECT
                            f.name,
                            f.field_description->>'en_US'  AS label,
                            f.ttype,
                            COALESCE(f.help->>'en_US', '') AS help
                        FROM ir_model_fields f
                        JOIN ir_model m ON m.id = f.model_id
                        WHERE m.model = %s
                          AND f.store = true
                          AND f.ttype != ALL(%s)
                          AND f.name != ALL(%s)
                        ORDER BY f.name
                    """, [
                        model_name,
                        list(SKIP_TYPES),
                        list(SKIP_FIELDS),
                    ])
                    for fname, label, ftype, fhelp in cur.fetchall():
                        columns.append({
                            "name":        fname,
                            "label":       label or fname,
                            "type":        ftype,
                            "description": fhelp,
                            "fk_table":    "",
                            "selection":   "",
                        })

                labeled = sum(1 for c in columns if c["label"] != c["name"])
                self.stdout.write(
                    f"  [{st['name']}] {len(columns)} Spalten, {labeled} mit Odoo-Label"
                )
                tables.append({
                    "table":        st["name"],
                    "model":        model_name,
                    "domain":       st["domain"],
                    "description":  st["description"],
                    "columns":      columns,
                    "extra_fields": [],
                })

        # 3. Build XML
        self.stdout.write("→ Generiere Schema-XML mit label-Attributen …")
        schema_xml = _build_schema_xml(tables, source_name=source_code)
        xml_len = len(schema_xml)
        self.stdout.write(f"  ✓ {xml_len} Zeichen XML")

        # 4a. Write to file
        if options["output"]:
            with open(options["output"], "w", encoding="utf-8") as f:
                f.write(schema_xml)
            self.stdout.write(self.style.SUCCESS(f"  XML → {options['output']}"))
            return

        # 4b. Dry-run
        if dry_run:
            self.stdout.write("\n" + schema_xml[:3000] + ("\n…[truncated]" if xml_len > 3000 else ""))
            return

        # 4c. Update SchemaSource
        from aifw.nl2sql.models import SchemaSource
        source, created = SchemaSource.objects.update_or_create(
            code=source_code,
            defaults={
                "name": "Odoo MFG (auto-sync aus ir.model.fields)",
                "db_alias": db_alias,
                "schema_xml": schema_xml,
                "is_active": True,
            },
        )
        verb = "Erstellt" if created else "Aktualisiert"
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{verb}: SchemaSource '{source_code}' — {xml_len} Zeichen XML\n"
                f"Odoo-Labels aktiv — LLM generiert automatisch deutsche Spaltenaliase."
            )
        )
