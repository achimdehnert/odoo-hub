from odoo import models
from odoo.tools import populate


class CastingAlloyPopulate(models.Model):
    _inherit = "casting.alloy"

    _populate_sizes = {"small": 20, "medium": 60, "large": 150}
    _populate_dependencies = ["casting.material"]

    def _populate_factories(self):
        material_ids = self.env.registry.populated_models.get("casting.material", [])

        def get_material_id(values, counter, random):
            if material_ids:
                return random.choice(material_ids)
            return False

        return [
            ("name", populate.iterate([
                # Aluminum alloys
                "AlSi7Mg0.3", "AlSi9Cu3", "AlSi12", "AlSi10Mg",
                "AlCu4Ti", "AlSi7Mg0.6", "AlMg5Si2Mn", "AlSi9Mg",
                # Cast iron
                "EN-GJL-200", "EN-GJL-250", "EN-GJL-300", "EN-GJL-350",
                "EN-GJS-400-18", "EN-GJS-500-7", "EN-GJS-600-3", "EN-GJS-700-2",
                "EN-GJS-800-2", "EN-GJS-900-2",
                # Cast steel
                "GS-38", "GS-45", "GS-52", "GS-60",
                "G17CrMoV5-10", "G20Mn5", "GX120Mn12",
                # Zinc
                "ZnAl4Cu1", "ZnAl4Cu3", "ZnAl4",
                # Bronze
                "CuSn10", "CuSn12", "CuAl10Fe5Ni5", "CuAl10Ni5Fe4",
                # Magnesium
                "AZ91D", "AM60B", "AS41B",
                # Copper
                "CuZn39Pb3", "CuZn37Mn3Al2PbSi", "CuSn5Zn5Pb5",
                # Extended alloys
                "AlSi8Cu3", "AlSi6Cu4", "EN-GJL-150", "EN-GJL-400",
                "EN-GJS-450-10", "EN-GJV-300", "EN-GJV-400", "EN-GJV-500",
                "GS-25CrMo4", "GS-30CrNiMo8", "ZnAl8Cu1",
                "CuSn7Zn4Pb7", "AZ91HP", "AM50A", "AE44",
                "AlSi17Cu4", "AlSi12Cu1Fe", "AlMg9", "EN-GJS-400-15",
                "CuAl9Mn2", "CuAl11Ni6Fe5", "ZnAl6Cu1",
                "GS-20Mn5V", "AlSi7Cu3Mg", "EN-GJL-HB195",
            ])),
            ("din_number", populate.iterate([
                "3.2371", "3.2163", "3.2581", "3.2381",
                "3.1841", "3.2371.61", "3.3261", "3.2373",
                "0.6020", "0.6025", "0.6030", "0.6035",
                "0.7040", "0.7050", "0.7060", "0.7070",
                "0.7080", "0.7090",
                "1.0420", "1.0446", "1.0552", "1.0558",
                "1.7706", "1.1120", "1.3401",
                "2.0210", "2.0230", "2.0200",
                "2.1050", "2.1052", "2.0966", "2.0975",
                "3.5912", "3.5612", "3.5120",
                "2.0402", "2.0592", "2.1096",
                None, None, "0.6015", "0.6040",
                "0.7045", "0.7300", "0.7305", "0.7310",
                "1.7218.04", "1.6580.04", "2.0240",
                "2.1090", "3.5912.05", "3.5610", "3.5324",
                "3.2583", "3.2582", "3.3539", "0.7040.01",
                "2.0960", "2.0980", "2.0250",
                "1.1120.04", "3.2494", "0.6019",
            ])),
            ("base_material_id", populate.compute(get_material_id)),
            ("alloy_type", populate.randomize(
                [
                    "aluminum", "aluminum", "aluminum", "aluminum",
                    "cast_iron", "cast_iron", "cast_iron",
                    "cast_steel", "cast_steel",
                    "zinc", "bronze", "magnesium", "copper",
                ],
                [0.25, 0.05, 0.05, 0.05,
                 0.15, 0.10, 0.05,
                 0.08, 0.02,
                 0.05, 0.05, 0.05, 0.05],
            )),
            ("tensile_strength", populate.compute(
                lambda random, **kw: round(random.uniform(150, 900), 1),
            )),
            ("yield_strength", populate.compute(
                lambda random, **kw: round(random.uniform(80, 600), 1),
            )),
            ("elongation", populate.compute(
                lambda random, **kw: round(random.uniform(0.5, 25.0), 1),
            )),
            ("hardness_brinell", populate.compute(
                lambda random, **kw: round(random.uniform(50, 350), 0),
            )),
            ("pouring_temp_min", populate.compute(
                lambda random, **kw: round(random.uniform(380, 1550), 0),
            )),
            ("pouring_temp_max", populate.compute(
                lambda random, **kw: round(random.uniform(420, 1620), 0),
            )),
            ("shrinkage_rate", populate.compute(
                lambda random, **kw: round(random.uniform(0.3, 2.5), 2),
            )),
            ("fluidity_rating", populate.randomize(
                ["low", "medium", "high"], [0.2, 0.5, 0.3],
            )),
            ("cost_per_kg", populate.compute(
                lambda random, **kw: round(random.uniform(0.80, 45.00), 2),
            )),
        ]
