from odoo import models
from odoo.tools import populate


class CastingMaterialPopulate(models.Model):
    _inherit = "casting.material"

    _populate_sizes = {"small": 8, "medium": 15, "large": 30}

    def _populate_factories(self):
        return [
            ("name", populate.iterate([
                "Aluminium", "Grauguss", "Sphäroguss", "Stahlguss",
                "Zink", "Magnesium", "Kupfer", "Bronze",
                "Messing", "Chromstahl", "Manganstahl", "Nickelbasis",
                "Titan", "Zinn", "Blei-Frei Legierung",
            ])),
            ("code", populate.iterate([
                "AL", "GG", "GGG", "GS",
                "ZN", "MG", "CU", "BZ",
                "MS", "CRS", "MNS", "NI",
                "TI", "SN", "PBF",
            ])),
            ("material_type", populate.iterate([
                "non_ferrous", "ferrous", "ferrous", "ferrous",
                "non_ferrous", "non_ferrous", "non_ferrous", "non_ferrous",
                "non_ferrous", "ferrous", "ferrous", "special",
                "special", "non_ferrous", "special",
            ])),
            ("density", populate.iterate([
                2.7, 7.2, 7.1, 7.85,
                7.13, 1.74, 8.96, 8.8,
                8.5, 7.75, 7.8, 8.9,
                4.51, 7.29, 7.3,
            ])),
            ("melting_point", populate.iterate([
                660.3, 1200.0, 1150.0, 1520.0,
                419.5, 650.0, 1084.0, 950.0,
                900.0, 1450.0, 1400.0, 1455.0,
                1668.0, 231.9, 327.5,
            ])),
            ("cost_per_kg", populate.iterate([
                2.80, 0.85, 1.20, 1.45,
                3.50, 4.20, 9.50, 12.80,
                7.20, 2.10, 1.90, 28.50,
                35.00, 25.00, 3.10,
            ])),
        ]
