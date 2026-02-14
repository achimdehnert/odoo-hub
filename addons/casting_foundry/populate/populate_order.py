import datetime

from odoo import models
from odoo.tools import populate


class CastingDefectTypePopulate(models.Model):
    _inherit = "casting.defect.type"

    _populate_sizes = {"small": 15, "medium": 30, "large": 50}

    def _populate_factories(self):
        return [
            ("name", populate.iterate([
                # Porosity
                "Gasporosität", "Mikroporosität", "Lunker (Makro)", "Mikrolunker",
                "Einfallstelle", "Schrumpfungsporosität",
                # Surface
                "Kaltlauf", "Fließlinien", "Orangenhaut", "Rauheit außer Toleranz",
                "Brandstelle", "Metallspritzer", "Formstoff-Einbrand",
                # Dimensional
                "Maßabweichung Bohrung", "Maßabweichung Außenkontur", "Verzug",
                "Gratbildung übermäßig", "Versatz Trennebene",
                # Cracks
                "Warmriss", "Kaltriss", "Spannungsriss", "Ermüdungsriss",
                # Inclusions
                "Sandeinschluss", "Schlackeneinschluss", "Oxideinschluss", "Oxidhaut",
                # Misrun/Cold shut
                "Formfüllung unvollständig", "Kaltschweißstelle", "Schülpe",
                "Blattrippe",
            ])),
            ("code", populate.iterate([
                "POR-01", "POR-02", "POR-03", "POR-04", "POR-05", "POR-06",
                "SRF-01", "SRF-02", "SRF-03", "SRF-04", "SRF-05", "SRF-06", "SRF-07",
                "DIM-01", "DIM-02", "DIM-03", "DIM-04", "DIM-05",
                "CRK-01", "CRK-02", "CRK-03", "CRK-04",
                "INC-01", "INC-02", "INC-03", "INC-04",
                "MIS-01", "MIS-02", "MIS-03", "MIS-04",
            ])),
            ("category", populate.iterate([
                "porosity", "porosity", "porosity", "porosity", "shrinkage", "porosity",
                "cold_shut", "surface", "surface", "surface", "surface", "surface", "surface",
                "dimensional", "dimensional", "distortion", "dimensional", "dimensional",
                "crack", "crack", "crack", "crack",
                "inclusion", "inclusion", "inclusion", "inclusion",
                "misrun", "cold_shut", "surface", "surface",
            ])),
            ("severity", populate.randomize(
                ["minor", "major", "critical"], [0.40, 0.40, 0.20],
            )),
        ]


class CastingOrderPopulate(models.Model):
    _inherit = "casting.order"

    _populate_sizes = {"small": 30, "medium": 500, "large": 3000}
    _populate_dependencies = ["casting.alloy", "casting.mold", "casting.machine"]

    def _populate_factories(self):
        partner_ids = self.env["res.partner"].search([("is_company", "=", True)], limit=50).ids
        if not partner_ids:
            partner_ids = self.env["res.partner"].search([], limit=20).ids

        def get_partner(values, counter, random):
            return random.choice(partner_ids) if partner_ids else False

        def get_date_planned(values, counter, random):
            today = datetime.date.today()
            delta = random.randint(-180, 90)
            return today + datetime.timedelta(days=delta)

        return [
            ("partner_id", populate.compute(get_partner)),
            ("customer_reference", populate.compute(
                lambda random, counter, **kw: f"PO-{random.randint(10000, 99999)}-{random.choice(['A', 'B', 'C', 'D'])}",
            )),
            ("state", populate.randomize(
                ["draft", "confirmed", "in_production", "quality_check", "done", "cancelled"],
                [0.10, 0.15, 0.20, 0.10, 0.35, 0.10],
            )),
            ("priority", populate.randomize(["0", "1", "2"], [0.70, 0.20, 0.10])),
            ("date_planned", populate.compute(get_date_planned)),
        ]


class CastingOrderLinePopulate(models.Model):
    _inherit = "casting.order.line"

    _populate_sizes = {"small": 60, "medium": 1200, "large": 8000}
    _populate_dependencies = [
        "casting.order", "casting.alloy", "casting.mold", "casting.machine",
    ]

    def _populate_factories(self):
        order_ids = self.env.registry.populated_models.get("casting.order", [])
        alloy_ids = self.env.registry.populated_models.get("casting.alloy", [])
        mold_ids = self.env.registry.populated_models.get("casting.mold", [])
        machine_ids = self.env.registry.populated_models.get("casting.machine", [])

        part_names = [
            "Motorblock V6", "Zylinderkopf 4-Zyl", "Getriebegehäuse 6-Gang",
            "Turboladergehäuse", "Bremsscheibe VA", "Bremsscheibe HA",
            "Lenkgetriebegehäuse", "Ölpumpengehäuse", "Wasserpumpengehäuse",
            "Ansaugbrücke", "Abgaskrümmer Zyl.1-3", "Schwungrad",
            "Kurbelgehäuse-Unterteil", "Radnabe vorn", "Radnabe hinten",
            "Achsschenkel links", "Achsschenkel rechts", "Federbeinstütze",
            "Querlenker vorn", "Differentialgehäuse",
            "Kupplungsglocke", "Ventilblock Hydraulik", "Pumpenrad",
            "Leitrad Wandler", "Kolbenrohling D=82mm", "Kolbenrohling D=92mm",
            "Zylinderrohr DN100", "Flanschplatte DN150", "Kompressorgehäuse",
            "Nockenwellengehäuse", "Steuergehäusedeckel", "Ölwanne Alu",
        ]
        part_numbers = [f"ZN-{i:05d}-{s}" for i, s in enumerate(["A", "B", "C", "D", "E"] * 20, start=10000)]

        def get_order_id(values, counter, random):
            return random.choice(order_ids) if order_ids else False

        def get_alloy_id(values, counter, random):
            return random.choice(alloy_ids) if alloy_ids else False

        def get_mold_id(values, counter, random):
            if mold_ids and random.random() < 0.8:
                return random.choice(mold_ids)
            return False

        def get_machine_id(values, counter, random):
            if machine_ids and random.random() < 0.7:
                return random.choice(machine_ids)
            return False

        def get_scrap(values, counter, random):
            qty = values.get("quantity", 100)
            scrap_rate = random.uniform(0.0, 0.12)  # 0-12% scrap rate
            return int(qty * scrap_rate)

        return [
            ("order_id", populate.compute(get_order_id)),
            ("part_name", populate.randomize(part_names)),
            ("part_number", populate.randomize(part_numbers)),
            ("alloy_id", populate.compute(get_alloy_id)),
            ("mold_id", populate.compute(get_mold_id)),
            ("machine_id", populate.compute(get_machine_id)),
            ("casting_process", populate.randomize(
                [
                    "die_cast_cold", "die_cast_hot", "gravity", "sand",
                    "investment", "centrifugal", "continuous",
                ],
                [0.30, 0.15, 0.20, 0.15, 0.10, 0.05, 0.05],
            )),
            ("quantity", populate.compute(
                lambda random, **kw: random.choice([
                    10, 25, 50, 100, 200, 500, 1000, 2000, 5000,
                ]),
            )),
            ("scrap_qty", populate.compute(get_scrap)),
            ("piece_weight_kg", populate.compute(
                lambda random, **kw: round(random.uniform(0.05, 85.0), 3),
            )),
            ("pouring_temp_c", populate.compute(
                lambda random, **kw: round(random.uniform(400, 1580), 0),
            )),
            ("mold_temp_c", populate.compute(
                lambda random, **kw: round(random.uniform(150, 450), 0),
            )),
            ("cycle_time_min", populate.compute(
                lambda random, **kw: round(random.uniform(0.5, 12.0), 1),
            )),
            ("heat_treatment", populate.randomize(
                ["none", "t4", "t5", "t6", "t7", "annealing", "normalizing", "quench_temper"],
                [0.30, 0.05, 0.10, 0.25, 0.05, 0.10, 0.05, 0.10],
            )),
        ]


class CastingQualityCheckPopulate(models.Model):
    _inherit = "casting.quality.check"

    _populate_sizes = {"small": 40, "medium": 800, "large": 5000}
    _populate_dependencies = ["casting.order", "casting.defect.type"]

    def _populate_factories(self):
        order_ids = self.env.registry.populated_models.get("casting.order", [])
        defect_ids = self.env.registry.populated_models.get("casting.defect.type", [])
        user_ids = self.env["res.users"].search([], limit=10).ids or [self.env.uid]

        def get_order_id(values, counter, random):
            return random.choice(order_ids) if order_ids else False

        def get_inspector(values, counter, random):
            return random.choice(user_ids)

        def get_check_date(values, counter, random):
            today = datetime.date.today()
            delta = random.randint(-120, 0)
            dt = today + datetime.timedelta(days=delta)
            hour = random.randint(6, 22)
            minute = random.choice([0, 15, 30, 45])
            return datetime.datetime.combine(dt, datetime.time(hour, minute))

        def get_defect_ids(values, counter, random):
            result = values.get("result")
            if result in ("conditional", "fail") and defect_ids:
                count = random.randint(1, min(4, len(defect_ids)))
                return [(6, 0, random.sample(defect_ids, count))]
            return [(6, 0, [])]

        return [
            ("order_id", populate.compute(get_order_id)),
            ("inspector_id", populate.compute(get_inspector)),
            ("check_date", populate.compute(get_check_date)),
            ("check_type", populate.randomize(
                [
                    "visual", "dimensional", "xray", "ultrasonic",
                    "hardness", "tensile", "spectrometry", "leak", "cmm",
                ],
                [0.25, 0.20, 0.10, 0.08, 0.10, 0.05, 0.07, 0.05, 0.10],
            )),
            ("result", populate.randomize(
                ["pass", "conditional", "fail"],
                [0.70, 0.18, 0.12],
            )),
            ("defect_type_ids", populate.compute(get_defect_ids)),
            ("sample_size", populate.compute(
                lambda random, **kw: random.choice([1, 3, 5, 10, 20, 50]),
            )),
            ("defect_count", populate.compute(
                lambda random, values, **kw: random.randint(0, 5)
                if values.get("result") != "pass" else 0,
            )),
            ("measured_value", populate.compute(
                lambda random, **kw: round(random.uniform(10.0, 500.0), 3),
            )),
            ("nominal_value", populate.compute(
                lambda random, **kw: round(random.uniform(10.0, 500.0), 3),
            )),
            ("tolerance_plus", populate.compute(
                lambda random, **kw: round(random.uniform(0.01, 0.5), 3),
            )),
            ("tolerance_minus", populate.compute(
                lambda random, **kw: round(random.uniform(0.01, 0.5), 3),
            )),
        ]
