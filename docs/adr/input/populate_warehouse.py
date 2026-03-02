from odoo import models
from odoo.tools import populate


class ScmWarehousePopulate(models.Model):
    _inherit = "scm.warehouse"

    _populate_sizes = {"small": 5, "medium": 8, "large": 12}

    def _populate_factories(self):
        user_ids = self.env["res.users"].search([], limit=10).ids

        def get_manager(values, counter, random):
            return random.choice(user_ids) if user_ids else False

        return [
            ("name", populate.iterate([
                "Rohstofflager Halle A",
                "Rohstofflager Halle B",
                "Zwischenlager Fertigung",
                "Zwischenlager Montage",
                "Fertigwarenlager Nord",
                "Fertigwarenlager Süd",
                "Sperrlager / Quarantäne",
                "Versandlager Rampe 1-4",
                "Versandlager Rampe 5-8",
                "Werkzeuglager",
                "Außenlager Standort Ost",
                "Konsignationslager Kunde",
            ])),
            ("code", populate.iterate([
                "WH-RA", "WH-RB", "WH-WIP1", "WH-WIP2",
                "WH-FN", "WH-FS", "WH-QUA", "WH-SH1",
                "WH-SH2", "WH-WZG", "WH-EXT", "WH-KON",
            ])),
            ("warehouse_type", populate.iterate([
                "raw", "raw", "wip", "wip",
                "finished", "finished", "quarantine", "shipping",
                "shipping", "raw", "finished", "shipping",
            ])),
            ("capacity_pallets", populate.iterate([
                600, 400, 250, 180,
                1000, 800, 120, 200,
                200, 80, 500, 300,
            ])),
            ("manager_id", populate.compute(get_manager)),
        ]
