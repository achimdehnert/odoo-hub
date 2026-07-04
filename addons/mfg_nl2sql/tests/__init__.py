# -*- coding: utf-8 -*-
"""Tests for NL2SQL module."""
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestSanitizeSQL(TransactionCase):
    """Test SQL sanitization logic."""

    def test_select_allowed(self):
        from odoo.addons.mfg_nl2sql.controllers.nl2sql_controller import sanitize_sql
        sql, err = sanitize_sql("SELECT * FROM purchase_order")
        self.assertIsNotNone(sql)
        self.assertIsNone(err)

    def test_with_cte_allowed(self):
        from odoo.addons.mfg_nl2sql.controllers.nl2sql_controller import sanitize_sql
        sql, err = sanitize_sql(
            "WITH cte AS (SELECT id FROM purchase_order) SELECT * FROM cte"
        )
        self.assertIsNotNone(sql)
        self.assertIsNone(err)

    def test_drop_blocked(self):
        from odoo.addons.mfg_nl2sql.controllers.nl2sql_controller import sanitize_sql
        sql, err = sanitize_sql("DROP TABLE purchase_order")
        self.assertIsNone(sql)
        self.assertIn("Verboten", err)

    def test_delete_blocked_readonly(self):
        from odoo.addons.mfg_nl2sql.controllers.nl2sql_controller import sanitize_sql
        sql, err = sanitize_sql("DELETE FROM purchase_order WHERE id = 1")
        self.assertIsNone(sql)
        self.assertIn("Schreiboperation", err)

    def test_insert_blocked_readonly(self):
        from odoo.addons.mfg_nl2sql.controllers.nl2sql_controller import sanitize_sql
        sql, err = sanitize_sql("INSERT INTO purchase_order (name) VALUES ('test')")
        self.assertIsNone(sql)

    def test_should_reject_write_sql_in_fallback(self):
        """DML/DDL is always rejected — incl. comment obfuscation (WP1)."""
        from odoo.addons.mfg_nl2sql.controllers.nl2sql_controller import sanitize_sql
        for bad in (
            "UPDATE purchase_order SET state='done' WHERE id=1",
            "INSERT INTO res_users (login) VALUES ('x')",
            "DROP TABLE purchase_order",
            "SELECT 1; -- harmlos\nDROP TABLE purchase_order",
            "SELECT * FROM (DELETE FROM res_users RETURNING *) AS t",
            "DELETE/*versteckt*/FROM res_users",
        ):
            sql, err = sanitize_sql(bad)
            self.assertIsNone(sql, f"nicht blockiert: {bad}")
            self.assertTrue(err)

    def test_should_not_accept_allow_write_parameter(self):
        """allow_write was removed (NL2X-Audit WP1) — no write opt-out."""
        from odoo.addons.mfg_nl2sql.controllers.nl2sql_controller import sanitize_sql
        with self.assertRaises(TypeError):
            sanitize_sql("SELECT 1", allow_write=True)

    def test_multiple_statements_blocked(self):
        from odoo.addons.mfg_nl2sql.controllers.nl2sql_controller import sanitize_sql
        sql, err = sanitize_sql(
            "SELECT 1; DROP TABLE purchase_order"
        )
        self.assertIsNone(sql)

    def test_empty_query_blocked(self):
        from odoo.addons.mfg_nl2sql.controllers.nl2sql_controller import sanitize_sql
        sql, err = sanitize_sql("")
        self.assertIsNone(sql)
        self.assertIn("Leer", err)


@tagged('post_install', '-at_install')
class TestChartDetection(TransactionCase):
    """Test chart type auto-detection."""

    def test_single_value_kpi(self):
        from odoo.addons.mfg_nl2sql.controllers.nl2sql_controller import (
            detect_chart_type,
        )
        cols = [{'name': 'count', 'type': 'integer'}]
        rows = [[42]]
        self.assertEqual(detect_chart_type(cols, rows), 'kpi')

    def test_label_numeric_pie(self):
        from odoo.addons.mfg_nl2sql.controllers.nl2sql_controller import (
            detect_chart_type,
        )
        cols = [
            {'name': 'status', 'type': 'varchar'},
            {'name': 'count', 'type': 'integer'},
        ]
        rows = [['open', 10], ['done', 20], ['cancel', 5]]
        self.assertEqual(detect_chart_type(cols, rows), 'pie')

    def test_date_numeric_line(self):
        from odoo.addons.mfg_nl2sql.controllers.nl2sql_controller import (
            detect_chart_type,
        )
        cols = [
            {'name': 'monat', 'type': 'date'},
            {'name': 'umsatz', 'type': 'float'},
        ]
        rows = [['2025-01', 1000], ['2025-02', 1200]]
        self.assertEqual(detect_chart_type(cols, rows), 'line')

    def test_many_rows_bar(self):
        from odoo.addons.mfg_nl2sql.controllers.nl2sql_controller import (
            detect_chart_type,
        )
        cols = [
            {'name': 'supplier', 'type': 'varchar'},
            {'name': 'total', 'type': 'float'},
        ]
        rows = [[f'Supplier {i}', i * 100] for i in range(15)]
        self.assertEqual(detect_chart_type(cols, rows), 'bar')

    def test_empty_returns_table(self):
        from odoo.addons.mfg_nl2sql.controllers.nl2sql_controller import (
            detect_chart_type,
        )
        self.assertEqual(detect_chart_type([], []), 'table')


@tagged('post_install', '-at_install')
class TestSchemaMetadata(TransactionCase):
    """Test schema metadata model."""

    def test_get_schema_context(self):
        """Schema context builds text with table and column info."""
        table = self.env['nl2sql.schema.table'].create({
            'name': 'test_table',
            'domain': 'production',
            'description': 'Test table',
            'column_ids': [(0, 0, {
                'name': 'id',
                'data_type': 'integer',
                'is_primary_key': True,
            }), (0, 0, {
                'name': 'value',
                'data_type': 'float',
                'description': 'A numeric value',
            })],
        })
        ctx = table.get_schema_context(domain='production')
        self.assertIn('test_table', ctx)
        self.assertIn('id', ctx)
        self.assertIn('[PK]', ctx)
        self.assertIn('A numeric value', ctx)

    def test_get_schema_json(self):
        """Schema JSON returns structured data."""
        self.env['nl2sql.schema.table'].create({
            'name': 'json_test',
            'domain': 'quality',
            'column_ids': [(0, 0, {
                'name': 'col1',
                'data_type': 'varchar',
            })],
        })
        result = self.env['nl2sql.schema.table'].get_schema_json(domain='quality')
        self.assertTrue(any(t['name'] == 'json_test' for t in result))
