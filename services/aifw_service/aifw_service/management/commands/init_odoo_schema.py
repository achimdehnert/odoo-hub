"""
Management Command: init_odoo_schema

Erstellt AIActionType(code='nl2sql') und SchemaSource(code='odoo_mfg')
mit dem Odoo-spezifischen Schema-XML für casting_* und scm_* Tabellen.

Idempotent — mehrfaches Ausführen ist sicher (update_or_create).

Usage:
    python manage.py init_odoo_schema
    python manage.py init_odoo_schema --provider anthropic --model claude-3-5-sonnet-20241022
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

ODOO_MFG_SCHEMA_XML = """<?xml version="1.0" encoding="utf-8"?>
<schema name="odoo_mfg" description="Odoo 18 Manufacturing + SCM schema">

  <table name="casting_order" domain="casting" row_count_hint="5000">
    <description>Gießaufträge (Haupttabelle Gießerei). Jeder Auftrag = eine Charge. KEIN machine_id-Feld — Maschinenverknüpfung erfolgt über casting_order_line.</description>
    <column name="id" type="integer" nullable="false"><description>Primary Key</description></column>
    <column name="name" type="varchar" nullable="false"><description>Auftragsnummer z.B. GA-2026-00001</description><example>GA-2026-00001</example></column>
    <column name="state" type="varchar"><description>Status: draft, confirmed, in_production, quality_check, done, cancelled</description><example>confirmed</example></column>
    <column name="date_planned" type="date"><description>Geplantes Fertigstellungsdatum</description></column>
    <column name="total_pieces" type="integer"><description>Geplante Gesamtstückzahl</description></column>
    <column name="total_scrap_pct" type="numeric"><description>Ausschussquote in Prozent</description></column>
    <column name="customer_reference" type="varchar"><description>Kundenbestellnummer</description></column>
    <column name="create_date" type="timestamp"><description>Erstellungszeitpunkt</description></column>
    <column name="is_demo_data" type="boolean"><description>True wenn Demo-Datensatz</description></column>
    <join_hint>Maschinen-Verknüpfung: JOIN casting_order_line col ON col.order_id = casting_order.id JOIN casting_machine cm ON cm.id = col.machine_id</join_hint>
    <sample_query>Welche Aufträge sind gerade in Produktion?</sample_query>
    <sample_query>Zeige Aufträge mit Ausschussquote über 5% dieser Woche</sample_query>
    <sample_query>Wie viele Aufträge je Status gibt es aktuell?</sample_query>
  </table>

  <table name="casting_order_line" domain="casting" row_count_hint="15000">
    <description>Auftragspositionen — Verbindung zwischen Auftrag und Maschine/Form/Legierung. WICHTIG: machine_id ist hier, NICHT in casting_order.</description>
    <column name="id" type="integer" nullable="false"><description>Primary Key</description></column>
    <column name="order_id" type="integer" nullable="false"><description>FK zu casting_order</description></column>
    <column name="machine_id" type="integer"><description>FK zu casting_machine — Maschine dieser Position</description></column>
    <column name="alloy_id" type="integer"><description>FK zu casting_alloy (Legierung)</description></column>
    <column name="mold_id" type="integer"><description>FK zu casting_mold (Form)</description></column>
    <column name="quantity" type="numeric"><description>Geplante Stückzahl</description></column>
    <column name="good_qty" type="numeric"><description>Gutteile</description></column>
    <column name="scrap_qty" type="numeric"><description>Ausschussstücke</description></column>
    <column name="part_name" type="varchar"><description>Teilename</description></column>
    <column name="casting_process" type="varchar"><description>Gießverfahren</description></column>
    <sample_query>Top 5 Maschinen nach Anzahl aktiver Aufträge: SELECT cm.name, COUNT(DISTINCT col.order_id) FROM casting_order_line col JOIN casting_machine cm ON cm.id = col.machine_id JOIN casting_order co ON co.id = col.order_id WHERE co.state = 'in_production' GROUP BY cm.name ORDER BY 2 DESC LIMIT 5</sample_query>
    <sample_query>Welche Maschine hat die meisten Wartungspositionen</sample_query>
  </table>

  <table name="casting_machine" domain="casting" row_count_hint="80">
    <description>Maschinen der Gießerei. Status zeigt Betriebszustand.</description>
    <column name="id" type="integer" nullable="false"/>
    <column name="name" type="varchar" nullable="false"><description>Maschinenname</description></column>
    <column name="code" type="varchar"><description>Maschinencode z.B. M-001</description><example>M-001</example></column>
    <column name="state" type="varchar"><description>operational, maintenance, breakdown, decommissioned</description><example>operational</example></column>
    <column name="machine_type" type="varchar"><description>Maschinentyp z.B. Druckguss, Schwerkraftguss</description></column>
    <column name="hall" type="varchar"><description>Halle/Standort</description></column>
    <column name="active" type="boolean"/>
    <sample_query>Welche Maschinen sind gerade in Störung?</sample_query>
    <sample_query>Wie viele Maschinen je Halle sind betriebsbereit?</sample_query>
  </table>

  <table name="casting_quality_check" domain="casting" row_count_hint="10000">
    <description>Qualitätsprüfungen für Gießaufträge.</description>
    <column name="id" type="integer" nullable="false"/>
    <column name="name" type="varchar"><description>Prüfungsreferenz</description></column>
    <column name="order_id" type="integer"><description>FK zu casting_order</description></column>
    <column name="result" type="varchar"><description>pass, fail, conditional</description><example>pass</example></column>
    <column name="check_date" type="date"><description>Datum der Prüfung</description></column>
    <column name="inspector_id" type="integer"><description>FK zu res_users (Prüfer)</description></column>
    <column name="defect_count" type="integer"><description>Anzahl gefundener Defekte</description></column>
    <sample_query>Was ist die Bestehensrate der letzten 30 Tage?</sample_query>
    <sample_query>Welcher Inspektor hat die meisten Prüfungen durchgeführt?</sample_query>
  </table>

  <table name="scm_production_order" domain="scm" row_count_hint="3000">
    <description>Fertigungsaufträge im Supply-Chain-Management.</description>
    <column name="id" type="integer" nullable="false"/>
    <column name="name" type="varchar" nullable="false"><description>Auftragsnummer z.B. PO-2026-00001</description></column>
    <column name="state" type="varchar"><description>draft, confirmed, in_progress, done, cancelled</description></column>
    <column name="date_planned" type="date"/>
    <column name="planned_qty" type="numeric"><description>Geplante Menge</description></column>
    <column name="produced_qty" type="numeric"><description>Bereits produzierte Menge</description></column>
    <column name="yield_pct" type="numeric"><description>Ausbeutequote in Prozent</description></column>
    <column name="part_id" type="integer"><description>FK zu scm_part</description></column>
    <sample_query>Welche SCM-Aufträge laufen aktuell und wie ist der Fortschritt?</sample_query>
    <sample_query>Aufträge mit Ausbeutequote unter 80%</sample_query>
  </table>

  <table name="scm_purchase_order" domain="scm" row_count_hint="2000">
    <description>Einkaufsbestellungen im SCM.</description>
    <column name="id" type="integer" nullable="false"/>
    <column name="name" type="varchar" nullable="false"/>
    <column name="state" type="varchar"><description>draft, sent, confirmed, received, cancelled</description></column>
    <column name="partner_id" type="integer"><description>FK zu res_partner (Lieferant)</description></column>
    <column name="date_order" type="date"><description>Bestelldatum</description></column>
    <column name="date_expected" type="date"><description>Erwartetes Lieferdatum</description></column>
    <column name="total_amount" type="numeric"><description>Gesamtbetrag in EUR</description></column>
    <sample_query>Welche Lieferanten haben offene Bestellungen über 10000 EUR?</sample_query>
    <sample_query>Überfällige Bestellungen der letzten 30 Tage</sample_query>
  </table>

  <table name="res_partner" domain="base" row_count_hint="500">
    <description>Partner (Kunden, Lieferanten).</description>
    <column name="id" type="integer" nullable="false"/>
    <column name="name" type="varchar" nullable="false"/>
    <column name="is_company" type="boolean"/>
    <column name="email" type="varchar"><description>E-Mail-Adresse</description></column>
    <column name="phone" type="varchar"><description>Telefonnummer</description></column>
  </table>

</schema>
"""


class Command(BaseCommand):
    help = "Initialisiert AIActionType(nl2sql) + SchemaSource(odoo_mfg) für Odoo MFG"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--provider",
            default="anthropic",
            help="LLM-Provider: anthropic | openai (Standard: anthropic)",
        )
        parser.add_argument(
            "--model",
            default="claude-3-5-sonnet-20241022",
            help="Modell-Name (Standard: claude-3-5-sonnet-20241022)",
        )
        parser.add_argument(
            "--fallback-model",
            dest="fallback_model",
            default="claude-3-haiku-20240307",
            help="Fallback-Modell (Standard: claude-3-haiku-20240307)",
        )

    def handle(self, *args, **options) -> None:
        from aifw.models import AIActionType, LLMModel, LLMProvider
        from aifw.nl2sql.models import SchemaSource

        # ── 1. Sicherstellen, dass Provider + Modelle existieren ────────────
        provider_name = options["provider"]
        provider, created = LLMProvider.objects.get_or_create(
            name=provider_name,
            defaults={
                "display_name": provider_name.capitalize(),
                "api_key_env_var": f"{provider_name.upper()}_API_KEY",
            },
        )
        self.stdout.write(f"{'Created' if created else 'Exists'}: Provider {provider.display_name}")

        def _get_or_create_model(model_name):
            defaults = {
                "display_name": model_name,
                "max_tokens": 8192,
                "supports_tools": True,
                "input_cost_per_million": 3.0,
                "output_cost_per_million": 15.0,
                "is_active": True,
            }
            obj, created = LLMModel.objects.get_or_create(
                provider=provider, name=model_name, defaults=defaults
            )
            self.stdout.write(f"  {'Created' if created else 'Exists'}: Model {obj.name}")
            return obj

        primary_model = _get_or_create_model(options["model"])
        fallback_model = _get_or_create_model(options["fallback_model"])

        # ── 2. AIActionType(code='nl2sql') ───────────────────────────────────
        action, created = AIActionType.objects.update_or_create(
            code="nl2sql",
            defaults={
                "name": "NL2SQL Query",
                "description": "Übersetzt natürlichsprachliche Fragen in SQL (Odoo MFG)",
                "default_model": primary_model,
                "fallback_model": fallback_model,
                "max_tokens": 2000,
                "temperature": 0.1,
                "is_active": True,
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"{'Created' if created else 'Updated'}: AIActionType 'nl2sql' "
                f"→ {primary_model.name} / fallback: {fallback_model.name}"
            )
        )

        # ── 3. SchemaSource(code='odoo_mfg') ────────────────────────────────
        source, created = SchemaSource.objects.update_or_create(
            code="odoo_mfg",
            defaults={
                "name": "Odoo Manufacturing & SCM",
                "db_alias": "odoo",
                "schema_xml": ODOO_MFG_SCHEMA_XML,
                "table_prefix": "",
                "blocked_tables": "res_users,res_groups,ir_config_parameter,auth_crypt_uid",
                "max_rows": 500,
                "timeout_seconds": 30,
                "allow_explain": False,
                "is_active": True,
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"{'Created' if created else 'Updated'}: SchemaSource 'odoo_mfg' "
                f"(db_alias=odoo, {len(ODOO_MFG_SCHEMA_XML)} Zeichen XML)\n"
                f"\nNächste Schritte:\n"
                f"  1. Sicherstellen dass ANTHROPIC_API_KEY oder OPENAI_API_KEY gesetzt ist\n"
                f"  2. nl2sql_user in PostgreSQL anlegen (docker/db/init.sql)\n"
                f"  3. Service testen: POST /nl2sql/query {{\"query\": \"Welche Maschinen sind in Störung?\"}}"
            )
        )
