from odoo import models
from odoo.tools import populate


class CastingMoldPopulate(models.Model):
    _inherit = "casting.mold"

    _populate_sizes = {"small": 15, "medium": 80, "large": 300}
    _populate_dependencies = ["casting.machine"]

    def _populate_factories(self):
        machine_ids = self.env.registry.populated_models.get("casting.machine", [])

        part_names = [
            "Motorblock", "Zylinderkopf", "Getriebegehäuse", "Ölwanne",
            "Lagerdeckel", "Pumpengehäuse", "Ventilkörper", "Turbinenrad",
            "Bremsscheibe", "Schwungscheibe", "Kurbelgehäuse", "Ansaugkrümmer",
            "Abgaskrümmer", "Lenkgehäuse", "Radnabe", "Achsschenkel",
            "Federbeinstütze", "Querlenker", "Wasserpumpengehäuse", "Kompressorgehäuse",
            "Pleuelstange", "Nockenwellenlager", "Thermostatgehäuse", "Drosselklappengehäuse",
            "Differentialgehäuse", "Kupplungsgehäuse", "Anlassergehäuse", "Generatorgehäuse",
            "Hydraulikblock", "Kolbenrohling", "Zylinderrohr", "Flanschplatte",
            "Ventilsitz", "Lagerbuchse", "Zahnradrohling", "Stützring",
        ]

        def get_machine_id(values, counter, random):
            if machine_ids and random.random() < 0.7:
                return random.choice(machine_ids)
            return False

        return [
            ("name", populate.compute(
                lambda random, counter, **kw: f"{random.choice(part_names)} Form {counter + 1:03d}",
            )),
            ("code", populate.compute(
                lambda random, counter, **kw: f"FRM-{counter + 1:05d}",
            )),
            ("mold_type", populate.randomize(
                ["permanent", "sand", "die_cast", "investment", "centrifugal", "shell"],
                [0.25, 0.25, 0.30, 0.10, 0.05, 0.05],
            )),
            ("state", populate.randomize(
                ["new", "active", "maintenance", "retired"],
                [0.10, 0.65, 0.15, 0.10],
            )),
            ("cavity_count", populate.randomize(
                [1, 2, 4, 6, 8], [0.30, 0.30, 0.20, 0.10, 0.10],
            )),
            ("part_weight_kg", populate.compute(
                lambda random, **kw: round(random.uniform(0.05, 120.0), 3),
            )),
            ("cycle_time_min", populate.compute(
                lambda random, **kw: round(random.uniform(0.3, 15.0), 1),
            )),
            ("max_shots", populate.compute(
                lambda random, **kw: random.choice([
                    5000, 10000, 20000, 50000, 80000, 100000, 150000, 200000,
                ]),
            )),
            ("current_shots", populate.compute(
                lambda random, **kw: random.randint(0, 150000),
            )),
            ("acquisition_cost", populate.compute(
                lambda random, **kw: round(random.uniform(5000, 250000), 2),
            )),
            ("maintenance_cost", populate.compute(
                lambda random, **kw: round(random.uniform(0, 35000), 2),
            )),
            ("machine_id", populate.compute(get_machine_id)),
        ]
