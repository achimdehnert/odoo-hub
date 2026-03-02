import datetime

from odoo import models
from odoo.tools import populate


class ScmPurchaseOrderPopulate(models.Model):
    _inherit = "scm.purchase.order"

    _populate_sizes = {"small": 20, "medium": 200, "large": 1500}
    _populate_dependencies = ["scm.warehouse"]

    def _populate_factories(self):
        partner_ids = self.env["res.partner"].search(
            [("is_company", "=", True)], limit=50
        ).ids
        if not partner_ids:
            partner_ids = self.env["res.partner"].search(
                [], limit=20
            ).ids

        warehouse_ids = (
            self.env.registry.populated_models.get("scm.warehouse", [])
        )

        def get_partner(values, counter, random):
            return random.choice(partner_ids) if partner_ids else False

        def get_warehouse(values, counter, random):
            return (
                random.choice(warehouse_ids) if warehouse_ids else False
            )

        def get_date_order(values, counter, random):
            today = datetime.date.today()
            delta = random.randint(-365, 0)
            return today + datetime.timedelta(days=delta)

        def get_date_expected(values, counter, random):
            d_order = values.get("date_order")
            if d_order:
                lead = random.randint(5, 60)
                return d_order + datetime.timedelta(days=lead)
            return False

        def get_date_received(values, counter, random):
            state = values.get("state")
            d_exp = values.get("date_expected")
            if state in ("received", "done") and d_exp:
                # Manchmal pünktlich, manchmal verspätet
                offset = random.randint(-5, 12)
                return d_exp + datetime.timedelta(days=offset)
            return False

        return [
            ("partner_id", populate.compute(get_partner)),
            ("warehouse_id", populate.compute(get_warehouse)),
            ("state", populate.randomize(
                [
                    "draft", "sent", "confirmed",
                    "received", "done", "cancelled",
                ],
                [0.08, 0.07, 0.15, 0.15, 0.45, 0.10],
            )),
            ("date_order", populate.compute(get_date_order)),
            ("date_expected", populate.compute(get_date_expected)),
            ("date_received", populate.compute(get_date_received)),
            ("incoterm", populate.randomize(
                ["exw", "fca", "cpt", "cip", "dap", "ddp"],
                [0.20, 0.25, 0.15, 0.05, 0.20, 0.15],
            )),
        ]


class ScmPurchaseLinePopulate(models.Model):
    _inherit = "scm.purchase.line"

    _populate_sizes = {"small": 50, "medium": 600, "large": 5000}
    _populate_dependencies = ["scm.purchase.order", "scm.part"]

    def _populate_factories(self):
        order_ids = (
            self.env.registry.populated_models.get(
                "scm.purchase.order", []
            )
        )
        part_ids = (
            self.env.registry.populated_models.get("scm.part", [])
        )

        def get_order(values, counter, random):
            return random.choice(order_ids) if order_ids else False

        def get_part(values, counter, random):
            return random.choice(part_ids) if part_ids else False

        def get_qty(values, counter, random):
            return random.choice([
                5, 10, 20, 25, 50, 100, 200, 500, 1000, 2500,
            ])

        def get_price(values, counter, random):
            return round(random.uniform(0.03, 1200.0), 4)

        def get_qty_received(values, counter, random):
            qty = values.get("quantity", 0)
            r = random.random()
            if r < 0.40:
                return qty  # vollständig
            if r < 0.65:
                return round(qty * random.uniform(0.7, 0.99), 2)
            if r < 0.85:
                return 0  # noch nicht geliefert
            return round(qty * random.uniform(0.3, 0.7), 2)

        return [
            ("order_id", populate.compute(get_order)),
            ("part_id", populate.compute(get_part)),
            ("quantity", populate.compute(get_qty)),
            ("unit_price", populate.compute(get_price)),
            ("qty_received", populate.compute(get_qty_received)),
            ("sequence", populate.compute(
                lambda counter, **kw: (counter % 5 + 1) * 10,
            )),
        ]
