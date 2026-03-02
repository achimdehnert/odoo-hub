# -*- coding: utf-8 -*-
"""Schema metadata for NL2SQL introspection.

Stores information about database tables and columns that are
available for natural language queries. This model serves as:
1. A whitelist of queryable tables (security boundary)
2. Context for the LLM to generate accurate SQL
3. Human-readable descriptions for schema documentation
"""
import json
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class SchemaTable(models.Model):
    _name = 'nl2sql.schema.table'
    _description = 'NL2SQL Schema Table'
    _order = 'domain, name'
    _rec_name = 'display_name'

    name = fields.Char(
        string='Table Name',
        required=True,
        index=True,
        help='PostgreSQL table name (e.g. mrp_production)',
    )
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
    )
    model_name = fields.Char(
        string='Odoo Model',
        help='Odoo model technical name (e.g. mrp.production)',
    )
    description = fields.Text(
        string='Description',
        help='Human-readable description for LLM context',
    )
    domain = fields.Selection(
        selection=[
            ('supply_chain', 'Supply Chain'),
            ('production', 'Produktion'),
            ('quality', 'Qualität'),
            ('master_data', 'Stammdaten'),
        ],
        string='Domäne',
        required=True,
        index=True,
    )
    is_active = fields.Boolean(
        string='Aktiv',
        default=True,
        help='Only active tables are available for NL2SQL queries',
    )
    column_ids = fields.One2many(
        'nl2sql.schema.column',
        'table_id',
        string='Spalten',
    )
    sample_queries = fields.Text(
        string='Beispiel-Abfragen',
        help='Example NL queries for this table (one per line)',
    )

    _sql_constraints = [
        ('unique_table_name', 'UNIQUE(name)', 'Table name must be unique.'),
    ]

    @api.depends('name', 'domain')
    def _compute_display_name(self):
        domain_labels = dict(self._fields['domain'].selection)
        for rec in self:
            domain_label = domain_labels.get(rec.domain, '')
            rec.display_name = f"[{domain_label}] {rec.name}" if rec.name else ''

    def get_schema_context(self, domain=None):
        """Build schema context string for LLM prompt.

        Returns a structured text describing all active tables
        and their columns, optionally filtered by domain.

        Args:
            domain: Optional domain filter ('supply_chain', 'production', 'quality')

        Returns:
            str: Formatted schema context for LLM injection
        """
        search_domain = [('is_active', '=', True)]
        if domain:
            search_domain.append(('domain', '=', domain))

        tables = self.search(search_domain)
        lines = []
        for table in tables:
            cols = table.column_ids.filtered(lambda c: c.is_active)
            col_descs = []
            for col in cols:
                col_str = f"  - {col.name} ({col.data_type})"
                if col.description:
                    col_str += f": {col.description}"
                if col.is_primary_key:
                    col_str += " [PK]"
                if col.foreign_key_table:
                    col_str += f" [FK → {col.foreign_key_table}]"
                col_descs.append(col_str)

            table_block = f"TABLE: {table.name}"
            if table.description:
                table_block += f"\n  Description: {table.description}"
            if col_descs:
                table_block += "\n  Columns:\n" + "\n".join(col_descs)

            lines.append(table_block)

        return "\n\n".join(lines)

    def get_schema_json(self, domain=None):
        """Return schema as JSON for frontend consumption."""
        search_domain = [('is_active', '=', True)]
        if domain:
            search_domain.append(('domain', '=', domain))

        tables = self.search(search_domain)
        result = []
        for table in tables:
            cols = []
            for col in table.column_ids.filtered(lambda c: c.is_active):
                cols.append({
                    'name': col.name,
                    'type': col.data_type,
                    'description': col.description or '',
                })
            result.append({
                'name': table.name,
                'domain': table.domain,
                'description': table.description or '',
                'columns': cols,
            })
        return result


class SchemaColumn(models.Model):
    _name = 'nl2sql.schema.column'
    _description = 'NL2SQL Schema Column'
    _order = 'sequence, name'

    table_id = fields.Many2one(
        'nl2sql.schema.table',
        string='Table',
        required=True,
        ondelete='cascade',
        index=True,
    )
    name = fields.Char(
        string='Column Name',
        required=True,
    )
    data_type = fields.Selection(
        selection=[
            ('integer', 'Integer'),
            ('float', 'Float'),
            ('varchar', 'Varchar'),
            ('text', 'Text'),
            ('boolean', 'Boolean'),
            ('date', 'Date'),
            ('datetime', 'Datetime'),
            ('selection', 'Selection'),
            ('many2one', 'Many2one'),
            ('json', 'JSON'),
        ],
        string='Data Type',
        required=True,
        default='varchar',
    )
    description = fields.Char(
        string='Description',
        help='Human-readable description for LLM context',
    )
    is_primary_key = fields.Boolean(
        string='Primary Key',
        default=False,
    )
    foreign_key_table = fields.Char(
        string='FK Table',
        help='Foreign key target table name',
    )
    is_active = fields.Boolean(
        string='Active',
        default=True,
    )
    selection_values = fields.Char(
        string='Allowed Values',
        help='Comma-separated list of allowed values for selection fields',
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )
