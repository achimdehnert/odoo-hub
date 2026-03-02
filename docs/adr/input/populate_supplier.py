from odoo import models
from odoo.tools import populate


class ScmSupplierInfoPopulate(models.Model):
    _inherit = "scm.supplier.info"

    _populate_sizes = {"small": 30, "medium": 120, "large": 400}
    _populate_dependencies = ["scm.part"]

    def _populate_factories(self):
        part_ids = (
            self.env.registry.populated_models.get("scm.part", [])
        )
        # Realistische Lieferanten aus res.partner verwenden
        partner_ids = self.env["res.partner"].search(
            [("is_company", "=", True)], limit=50
        ).ids
        if not partner_ids:
            partner_ids = self.env["res.partner"].search(
                [], limit=20
            ).ids

        def get_part(values, counter, random):
            return random.choice(part_ids) if part_ids else False

        def get_partner(values, counter, random):
            return random.choice(partner_ids) if partner_ids else False

        def get_supplier_pn(values, counter, random):
            prefix = random.choice([
                "ART", "MAT", "BES", "LF", "PN", "REF",
            ])
            return f"{prefix}-{random.randint(100000, 999999)}"

        def get_price(values, counter, random):
            return round(random.uniform(0.05, 2500.0), 4)

        def get_lead_time(values, counter, random):
            # Normteile schnell, Gussteile langsam
            return random.choice([
                3, 5, 7, 10, 14, 21, 28, 35, 42, 56,
            ])

        def get_otd(values, counter, random):
            # Liefertreue: Normalverteilung um 92%
            pct = random.gauss(92.0, 6.0)
            return round(max(60.0, min(100.0, pct)), 1)

        return [
            ("part_id", populate.compute(get_part)),
            ("partner_id", populate.compute(get_partner)),
            ("priority", populate.randomize(
                ["1", "2", "3"], [0.40, 0.40, 0.20],
            )),
            ("rating", populate.randomize(
                ["a", "b", "c", "d"], [0.25, 0.45, 0.20, 0.10],
            )),
            ("supplier_part_number", populate.compute(get_supplier_pn)),
            ("price", populate.compute(get_price)),
            ("min_order_qty", populate.compute(
                lambda random, **kw: round(
                    random.choice([1, 5, 10, 25, 50, 100, 500, 1000]),
                ),
            )),
            ("lead_time_days", populate.compute(get_lead_time)),
            ("on_time_delivery_pct", populate.compute(get_otd)),
            ("currency", populate.constant("EUR")),
        ]
