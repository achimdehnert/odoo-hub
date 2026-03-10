# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class IILWebsite(http.Controller):

    @http.route('/', auth='public', website=True, sitemap=True)
    def landing_page(self, **kwargs):
        modules = [
            {
                'key': 'casting_foundry',
                'name': 'Gießerei',
                'icon': '\U0001f3ed',
                'description': (
                    'Komplette Gießerei-Verwaltung: Aufträge, '
                    'Qualitätssicherung, Chargen-Tracking.'
                ),
                'color': '#1a56db',
                'route': '/web#action=185',
            },
            {
                'key': 'scm_manufacturing',
                'name': 'SCM / Fertigung',
                'icon': '\U0001f527',
                'description': (
                    'Supply Chain Management: Stücklisten, '
                    'Lieferanten, Lager und Bestellungen.'
                ),
                'color': '#0e9f6e',
                'route': '/web#action=199',
            },
            {
                'key': 'mfg_management',
                'name': 'MFG Cockpit',
                'icon': '\U0001f4ca',
                'description': (
                    'Einheitliches Produktions-Dashboard: '
                    'KPIs, Kanban-Board, Maschinen-Status.'
                ),
                'color': '#7e3af2',
                'route': '/web#action=204',
            },
            {
                'key': 'mfg_nl2sql',
                'name': 'NL2SQL Analytics',
                'icon': '\U0001f916',
                'description': (
                    'KI-gestützte Datenabfragen in natürlicher '
                    'Sprache - direkt auf Ihre Produktionsdaten.'
                ),
                'color': '#0891b2',
                'route': '/web#action=193',
            },
            {
                'key': 'iil_configurator',
                'name': 'Konfigurator',
                'icon': '\U0001f6e0\ufe0f',
                'description': (
                    'Produkt- und Variantenkonfigurator: '
                    'Regelbasierte Artikelkonfiguration.'
                ),
                'color': '#d61f69',
                'route': '/web#action=209',
            },
        ]
        values = {
            'modules': modules,
            'is_authenticated': not request.env.user._is_public(),
        }
        return request.render('iil_website.landing_page', values)

    @http.route('/impressum', auth='public', website=True, sitemap=True)
    def impressum(self, **kwargs):
        return request.render('iil_website.impressum_page', {})

    @http.route('/datenschutz', auth='public', website=True, sitemap=True)
    def datenschutz(self, **kwargs):
        return request.render('iil_website.datenschutz_page', {})

    @http.route('/module/<string:module_key>/book',
                auth='user', website=True)
    def book_module(self, module_key, **kwargs):
        return request.render('iil_website.module_booked', {
            'module_key': module_key,
        })
