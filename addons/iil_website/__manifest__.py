# -*- coding: utf-8 -*-
{
    "name": "IIL Website - Landing Page",
    "version": "18.0.1.0.0",
    "category": "Website",
    "summary": "IIL Landing Page mit Produktuebersicht, Login, Registrierung und Modul-Buchung",
    "author": "IIL",
    "website": "https://iil.gmbh",
    "license": "LGPL-3",
    "depends": [
        "base",
        "web",
        "website",
        "auth_signup",
    ],
    "data": [
        "views/landing_page_template.xml",
        "views/website_menu.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "iil_website/static/src/css/landing.css",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "sequence": 1,
}
