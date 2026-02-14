from odoo import models
from odoo.tools import populate


class CastingMachinePopulate(models.Model):
    _inherit = "casting.machine"

    _populate_sizes = {"small": 10, "medium": 40, "large": 100}

    def _populate_factories(self):
        manufacturers = [
            "Bühler", "Frech", "Idra", "Italpresse", "Toshiba",
            "Ube", "Oskar Frech", "Colosio", "Heinrich Wagner Sinto",
            "Künkel Wagner", "DISA", "Loramendi", "ABP Induction",
            "Inductotherm", "StrikoWestofen", "Nabertherm", "Aichelin",
        ]
        halls = ["Halle A", "Halle B", "Halle C", "Halle D", "Halle E"]

        return [
            ("name", populate.compute(
                lambda random, counter, **kw: f"M-{counter + 1:03d} {random.choice([
                    'Druckguss', 'Schmelzofen', 'Kokillenguss', 'Formanlage',
                    'Warmhalteofen', 'Wärmebehandlung', 'Putzerei',
                    'Röntgen', 'Schleuderguss', 'Kernschießmaschine',
                ])}",
            )),
            ("code", populate.compute(
                lambda random, counter, **kw: f"MCH-{counter + 1:04d}",
            )),
            ("machine_type", populate.randomize(
                [
                    "die_casting", "melting_furnace", "gravity_casting",
                    "sand_molding", "holding_furnace", "heat_treatment",
                    "finishing", "xray", "centrifugal",
                ],
                [0.25, 0.15, 0.15, 0.10, 0.10, 0.08, 0.07, 0.05, 0.05],
            )),
            ("state", populate.randomize(
                ["operational", "maintenance", "breakdown", "decommissioned"],
                [0.70, 0.15, 0.10, 0.05],
            )),
            ("manufacturer", populate.randomize(manufacturers)),
            ("model", populate.compute(
                lambda random, **kw: f"{random.choice(['SC', 'DC', 'EVO', 'PRO', 'MAX', 'ECO'])}-{random.randint(100, 9999)}",
            )),
            ("year_built", populate.compute(
                lambda random, **kw: random.randint(1998, 2024),
            )),
            ("capacity_kg", populate.compute(
                lambda random, **kw: round(random.uniform(50, 5000), 0),
            )),
            ("clamping_force_t", populate.compute(
                lambda random, **kw: round(random.choice([0, 250, 400, 630, 800, 1000, 1600, 2500, 3500, 4400]), 0),
            )),
            ("max_temp_c", populate.compute(
                lambda random, **kw: round(random.uniform(350, 1700), 0),
            )),
            ("power_kw", populate.compute(
                lambda random, **kw: round(random.uniform(15, 500), 0),
            )),
            ("hall", populate.randomize(halls)),
            ("position", populate.compute(
                lambda random, **kw: f"Platz {random.randint(1, 30)}",
            )),
        ]
