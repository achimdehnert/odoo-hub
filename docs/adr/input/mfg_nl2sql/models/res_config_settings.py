# -*- coding: utf-8 -*-
"""Configuration settings for NL2SQL module."""
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    nl2sql_llm_provider = fields.Selection(
        selection=[
            ('anthropic', 'Anthropic (Claude)'),
            ('openai', 'OpenAI (GPT)'),
        ],
        string='LLM Provider',
        default='anthropic',
        config_parameter='mfg_nl2sql.llm_provider',
    )
    nl2sql_api_key = fields.Char(
        string='API Key',
        config_parameter='mfg_nl2sql.api_key',
        help='API key for the selected LLM provider',
    )
    nl2sql_model_name = fields.Char(
        string='Model Name',
        default='claude-sonnet-4-5-20250929',
        config_parameter='mfg_nl2sql.model_name',
        help='Model identifier (e.g. claude-sonnet-4-5-20250929, gpt-4o)',
    )
    nl2sql_max_tokens = fields.Integer(
        string='Max Tokens',
        default=2048,
        config_parameter='mfg_nl2sql.max_tokens',
    )
    nl2sql_temperature = fields.Float(
        string='Temperature',
        default=0.0,
        config_parameter='mfg_nl2sql.temperature',
        help='Lower = more deterministic SQL generation',
    )
    nl2sql_query_timeout = fields.Integer(
        string='Query Timeout (s)',
        default=30,
        config_parameter='mfg_nl2sql.query_timeout',
    )
    nl2sql_max_rows = fields.Integer(
        string='Max Result Rows',
        default=1000,
        config_parameter='mfg_nl2sql.max_rows',
    )
    nl2sql_allow_write = fields.Boolean(
        string='Allow Write Queries',
        default=False,
        config_parameter='mfg_nl2sql.allow_write',
        help='DANGEROUS: Allow INSERT/UPDATE/DELETE. Default: read-only.',
    )
