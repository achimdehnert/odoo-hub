import datetime

from odoo import models
from odoo.tools import populate


class ScmStockMovePopulate(models.Model):
    _inherit = "scm.stock.move"

    _populate_sizes = {"small": 50, "medium": 500, "large": 5000}
    _populate_dependencies = [
        "scm.part", "scm.warehouse", "scm.production.order",
    ]

    def _populate_factories(self):
        part_ids = (
            self.env.registry.populated_models.get("scm.part", [])
        )
        warehouse_ids = (
            self.env.registry.populated_models.get("scm.warehouse", [])
        )
        production_ids = (
            self.env.registry.populated_models.get(
                "scm.production.order", []
            )
        )

        def get_part(values, counter, random):
            return random.choice(part_ids) if part_ids else False

        def get_warehouse(values, counter, random):
            return (
                random.choice(warehouse_ids)
                if warehouse_ids else False
            )

        def get_production(values, counter, random):
            move = values.get("move_type")
            if move in ("in", "out") and production_ids:
                if random.random() < 0.4:
                    return random.choice(production_ids)
            return False

        def get_date(values, counter, random):
            today = datetime.datetime.now()
            delta_days = random.randint(-365, 0)
            hour = random.randint(6, 22)
            minute = random.choice([0, 15, 30, 45])
            return today + datetime.timedelta(
                days=delta_days,
                hours=hour - today.hour,
                minutes=minute - today.minute,
            )

        def get_qty(values, counter, random):
            return round(random.uniform(1, 5000), 2)

        def get_lot(values, counter, random):
            if random.random() < 0.6:
                year = random.randint(2024, 2026)
                month = random.randint(1, 12)
                seq = random.randint(1, 999)
                return f"LOT-{year}{month:02d}-{seq:03d}"
            return False

        def get_reference(values, counter, random):
            move = values.get("move_type")
            if move == "in":
                return f"WE-{random.randint(10000, 99999)}"
            if move == "out":
                return f"WA-{random.randint(10000, 99999)}"
            if move == "transfer":
                return f"UB-{random.randint(10000, 99999)}"
            if move == "adjust":
                return f"INV-{random.randint(10000, 99999)}"
            if move == "scrap":
                return f"VSR-{random.randint(10000, 99999)}"
            return False

        return [
            ("part_id", populate.compute(get_part)),
            ("warehouse_id", populate.compute(get_warehouse)),
            ("move_type", populate.randomize(
                ["in", "out", "transfer", "adjust", "scrap"],
                [0.35, 0.30, 0.15, 0.10, 0.10],
            )),
            ("quantity", populate.compute(get_qty)),
            ("lot_number", populate.compute(get_lot)),
            ("date", populate.compute(get_date)),
            ("reference", populate.compute(get_reference)),
            ("production_id", populate.compute(get_production)),
        ]


class ScmDeliveryPopulate(models.Model):
    _inherit = "scm.delivery"

    _populate_sizes = {"small": 15, "medium": 120, "large": 800}
    _populate_dependencies = ["scm.part"]

    def _populate_factories(self):
        part_ids = (
            self.env.registry.populated_models.get("scm.part", [])
        )
        partner_ids = self.env["res.partner"].search(
            [("is_company", "=", True)], limit=50
        ).ids
        if not partner_ids:
            partner_ids = self.env["res.partner"].search(
                [], limit=20
            ).ids

        carriers = [
            "DHL Freight", "DB Schenker", "Dachser",
            "Hellmann Worldwide", "Kühne+Nagel", "UPS",
            "DPD", "GLS", "Spedition Zufall", "Eigentransport",
        ]

        def get_partner(values, counter, random):
            return random.choice(partner_ids) if partner_ids else False

        def get_part(values, counter, random):
            return random.choice(part_ids) if part_ids else False

        def get_qty(values, counter, random):
            return round(random.uniform(1, 2000), 2)

        def get_weight(values, counter, random):
            return round(random.uniform(5.0, 2500.0), 2)

        def get_tracking(values, counter, random):
            state = values.get("state")
            if state in ("shipped", "delivered"):
                prefix = random.choice(["JJD", "JVGL", "340", "1Z"])
                num = random.randint(10**11, 10**12 - 1)
                return f"{prefix}{num}"
            return False

        def get_date_shipped(values, counter, random):
            state = values.get("state")
            if state in ("shipped", "delivered"):
                today = datetime.date.today()
                return today - datetime.timedelta(
                    days=random.randint(1, 180)
                )
            return False

        def get_date_delivered(values, counter, random):
            state = values.get("state")
            d_ship = values.get("date_shipped")
            if state == "delivered" and d_ship:
                return d_ship + datetime.timedelta(
                    days=random.randint(1, 8)
                )
            return False

        return [
            ("partner_id", populate.compute(get_partner)),
            ("part_id", populate.compute(get_part)),
            ("quantity", populate.compute(get_qty)),
            ("carrier", populate.randomize(carriers)),
            ("total_weight_kg", populate.compute(get_weight)),
            ("state", populate.randomize(
                ["draft", "ready", "shipped", "delivered", "cancelled"],
                [0.08, 0.10, 0.15, 0.57, 0.10],
            )),
            ("tracking_number", populate.compute(get_tracking)),
            ("date_shipped", populate.compute(get_date_shipped)),
            ("date_delivered", populate.compute(get_date_delivered)),
        ]


class ScmIncomingInspectionPopulate(models.Model):
    _inherit = "scm.incoming.inspection"

    _populate_sizes = {"small": 20, "medium": 180, "large": 1200}
    _populate_dependencies = ["scm.purchase.order"]

    def _populate_factories(self):
        purchase_ids = (
            self.env.registry.populated_models.get(
                "scm.purchase.order", []
            )
        )
        user_ids = (
            self.env["res.users"].search([], limit=10).ids
            or [self.env.uid]
        )

        def get_purchase(values, counter, random):
            return (
                random.choice(purchase_ids)
                if purchase_ids else False
            )

        def get_inspector(values, counter, random):
            return random.choice(user_ids)

        def get_date(values, counter, random):
            today = datetime.datetime.now()
            delta = random.randint(-270, 0)
            hour = random.randint(6, 18)
            minute = random.choice([0, 15, 30, 45])
            dt = today + datetime.timedelta(days=delta)
            return dt.replace(hour=hour, minute=minute, second=0)

        def get_sample_size(values, counter, random):
            return random.choice([1, 3, 5, 10, 15, 20, 50, 100])

        def get_defect_count(values, counter, random):
            result = values.get("result")
            if result == "accepted":
                return 0
            if result == "conditional":
                return random.randint(1, 3)
            if result == "rejected":
                return random.randint(2, 15)
            return 0

        def get_acceptance_rate(values, counter, random):
            result = values.get("result")
            if result == "accepted":
                return round(random.uniform(95.0, 100.0), 1)
            if result == "conditional":
                return round(random.uniform(80.0, 94.9), 1)
            return round(random.uniform(40.0, 79.9), 1)

        def get_corrective(values, counter, random):
            result = values.get("result")
            if result == "rejected":
                actions = [
                    "Reklamation an Lieferant. Nachlieferung angefordert.",
                    "Ware gesperrt. 8D-Report angefordert.",
                    "Rücksendung eingeleitet. Gutschrift angefordert.",
                    "Sonderfreigabe durch QM abgelehnt. Ware verschrotten.",
                    "Lieferantengespräch terminiert. Auditierung geplant.",
                ]
                return random.choice(actions)
            if result == "conditional":
                actions = [
                    "Sonderfreigabe durch QM-Leiter erteilt.",
                    "Nacharbeit intern möglich. Kosten: Lieferant.",
                    "Abweichung dokumentiert. Nächste Lieferung überwachen.",
                ]
                return random.choice(actions)
            return False

        return [
            ("purchase_id", populate.compute(get_purchase)),
            ("inspector_id", populate.compute(get_inspector)),
            ("inspection_date", populate.compute(get_date)),
            ("inspection_type", populate.randomize(
                [
                    "visual", "dimensional", "functional",
                    "material", "documentation",
                ],
                [0.30, 0.30, 0.15, 0.10, 0.15],
            )),
            ("result", populate.randomize(
                ["accepted", "conditional", "rejected"],
                [0.68, 0.18, 0.14],
            )),
            ("sample_size", populate.compute(get_sample_size)),
            ("defect_count", populate.compute(get_defect_count)),
            ("acceptance_rate", populate.compute(get_acceptance_rate)),
            ("certificate_type", populate.randomize(
                ["none", "2_1", "2_2", "3_1", "3_2"],
                [0.20, 0.15, 0.10, 0.35, 0.20],
            )),
            ("corrective_action", populate.compute(get_corrective)),
        ]
