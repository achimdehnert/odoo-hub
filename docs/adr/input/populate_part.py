from odoo import models
from odoo.tools import populate


class ScmPartCategoryPopulate(models.Model):
    _inherit = "scm.part.category"

    _populate_sizes = {"small": 12, "medium": 18, "large": 25}

    def _populate_factories(self):
        return [
            ("name", populate.iterate([
                # Rohmaterial-Kategorien
                "Rundstahl", "Flachstahl", "Stahlblech", "Aluminiumprofile",
                # Normteile
                "Wälzlager", "Gleitlager", "Dichtringe",
                "Schrauben DIN", "Muttern DIN", "Sicherungsringe",
                # Halbfertigteile
                "Zahnräder", "Wellen", "Gehäuse",
                "Flansche", "Kupplungen",
                # Fertigteile
                "Getriebebaugruppen", "Antriebseinheiten",
                # Hydraulik
                "Hydraulikzylinder", "Hydraulikventile", "Hydraulikpumpen",
                # Elektronik/Sensorik
                "Sensoren", "Elektromotoren",
                # Verbrauch
                "Schmierstoffe", "Kühlschmiermittel", "Filtermaterial",
            ])),
            ("code", populate.iterate([
                "RDS", "FLS", "BLE", "ALU",
                "WLG", "GLG", "DIC",
                "SCR", "MUT", "SIR",
                "ZHR", "WEL", "GEH",
                "FLA", "KUP",
                "GTR", "ANT",
                "HYZ", "HYV", "HYP",
                "SEN", "EMO",
                "SMI", "KSM", "FIL",
            ])),
        ]


class ScmPartPopulate(models.Model):
    _inherit = "scm.part"

    _populate_sizes = {"small": 40, "medium": 150, "large": 500}
    _populate_dependencies = ["scm.part.category"]

    def _populate_factories(self):
        category_ids = (
            self.env.registry.populated_models.get("scm.part.category", [])
        )

        # ── Realistische Maschinenbau-Teile ──────────────────────
        part_data = [
            # Wälzlager (SKF / FAG)
            ("WLG-6205-2RS", "Rillenkugellager 6205-2RS SKF", "100Cr6", 0.112),
            ("WLG-6208-2Z", "Rillenkugellager 6208-2Z SKF", "100Cr6", 0.295),
            ("WLG-6310-C3", "Rillenkugellager 6310/C3 FAG", "100Cr6", 0.820),
            ("WLG-NU210", "Zylinderrollenlager NU210-E FAG", "100Cr6", 0.430),
            ("WLG-7206B", "Schrägkugellager 7206-B-TVP FAG", "100Cr6", 0.250),
            ("WLG-32208", "Kegelrollenlager 32208 SKF", "100Cr6", 0.540),
            ("WLG-51107", "Axial-Rillenkugellager 51107", "100Cr6", 0.098),
            ("WLG-22312E", "Pendelrollenlager 22312-E SKF", "100Cr6", 2.850),
            # Wellen
            ("WEL-A50-500", "Antriebswelle Ø50×500 C45", "C45", 7.700),
            ("WEL-A60-800", "Antriebswelle Ø60×800 42CrMo4", "42CrMo4", 17.800),
            ("WEL-G35-300", "Getriebewelle Ø35×300 16MnCr5", "16MnCr5", 2.270),
            ("WEL-H80-1200", "Hohlwelle Ø80×1200 34CrNiMo6", "34CrNiMo6", 22.500),
            ("WEL-K25-200", "Keilwelle Ø25×200 C45+QT", "C45", 0.770),
            # Zahnräder
            ("ZHR-S72-M3", "Stirnrad z=72 Modul 3 16MnCr5", "16MnCr5", 3.200),
            ("ZHR-S48-M4", "Stirnrad z=48 Modul 4 16MnCr5", "16MnCr5", 5.800),
            ("ZHR-K36-M3", "Kegelrad z=36 Modul 3 16MnCr5", "16MnCr5", 1.850),
            ("ZHR-SNK24-M2", "Schneckenrad z=24 Modul 2 CuSn12", "CuSn12", 1.200),
            ("ZHR-ZST20-M2", "Zahnstange M2 L=500mm C45", "C45", 2.450),
            # Gehäuse
            ("GEH-GTR-200", "Getriebegehäuse Größe 200 GJL-250", "GJL-250", 45.000),
            ("GEH-MOT-160", "Motorgehäuse Baugr. 160 AlSi9Cu3", "AlSi9Cu3", 12.500),
            ("GEH-PMP-DN80", "Pumpengehäuse DN80 GGG-40", "EN-GJS-400-18", 18.700),
            ("GEH-VNT-NG10", "Ventilgehäuse NG10 C45", "C45", 2.800),
            # DIN-Normteile (Schrauben)
            ("SCR-931-M8x50", "Sechskantschraube DIN 931 M8×50 8.8", "8.8 verz.", 0.028),
            ("SCR-912-M10x40", "Zylinderschraube DIN 912 M10×40 12.9", "12.9 blank", 0.036),
            ("SCR-933-M12x60", "Sechskantschraube DIN 933 M12×60 10.9", "10.9 verz.", 0.072),
            ("SCR-7991-M6x20", "Senkkopfschraube DIN 7991 M6×20 10.9", "10.9 blank", 0.008),
            ("SCR-6914-M16x80", "HV-Schraube DIN 6914 M16×80 10.9", "10.9 fvz.", 0.195),
            # DIN-Normteile (Muttern, Sicherungsringe)
            ("MUT-934-M8", "Sechskantmutter DIN 934 M8 Kl.8", "Kl.8 verz.", 0.006),
            ("MUT-985-M10", "Sicherungsmutter DIN 985 M10", "Kl.8 verz.", 0.012),
            ("SIR-471-50", "Sicherungsring DIN 471 Ø50", "Federstahl", 0.005),
            ("SIR-472-40", "Sicherungsring DIN 472 Ø40", "Federstahl", 0.004),
            # Dichtringe
            ("DIC-OR-50x3", "O-Ring 50×3 NBR 70 Shore", "NBR", 0.003),
            ("DIC-RWDR-50x72", "Radialwellendichtring 50×72×8 BASL", "FKM", 0.025),
            ("DIC-FLAT-DN50", "Flachdichtung DN50 PN16 Klingersil", "Klingersil C-4400", 0.018),
            # Rohmaterial
            ("RDS-C45-60", "Rundstahl C45 Ø60 h11 1m", "C45", 21.900),
            ("RDS-42CR-80", "Rundstahl 42CrMo4+QT Ø80 1m", "42CrMo4", 39.300),
            ("FLS-S355-20x100", "Flachstahl S355J2 20×100 1m", "S355J2", 15.700),
            ("BLE-DC04-2x1000", "Blech DC04 2×1000×2000", "DC04", 31.400),
            ("ALU-6060-50x5", "Alu-Rechteckrohr 6060 50×30×5 6m", "EN-AW-6060 T66", 4.250),
            # Kupplungen / Flansche
            ("KUP-ROTEX-42", "ROTEX 42 GGG Kupplung Shore 98A", "EN-GJS-400-18", 2.150),
            ("KUP-OLDH-80", "Oldham-Kupplung Ø80 Alu", "AlMgSi1", 0.850),
            ("FLA-PN16-DN100", "Vorschweißflansch PN16 DN100 P250GH", "P250GH", 3.200),
            # Hydraulik
            ("HYZ-63x36-500", "Hydraulikzylinder 63/36×500 Hub", "E355+SR", 8.500),
            ("HYV-4WE6-NG6", "Wegeventil 4/3 NG6 24VDC Bosch Rexroth", "div.", 0.950),
            ("HYP-AXIAL-28", "Axialkolbenpumpe 28cm³/U Bosch Rexroth", "div.", 12.800),
            # Sensorik / E-Motoren
            ("SEN-IND-M12", "Induktiver Sensor M12 PNP NO IFM", "V2A", 0.045),
            ("SEN-TEMP-PT100", "Temperatursensor Pt100 L=100mm", "V4A", 0.035),
            ("EMO-SERVO-4NM", "Servomotor 4Nm 3000rpm Siemens 1FK7", "div.", 6.200),
            ("EMO-ASYNC-5KW", "Drehstrommotor 5.5kW 1500rpm SEW", "GJL", 38.500),
            # Schmierstoffe / Verbrauch
            ("SMI-KLÜB-004", "Klüber Isoflex NBU 15 400g Kartusche", "Spezialfett", 0.400),
            ("KSM-CSTF-20L", "Kühlschmierstoff Castrol 20L Kanister", "Emulsion", 22.000),
        ]

        part_numbers = [p[0] for p in part_data]
        part_names = [p[1] for p in part_data]
        materials = [p[2] for p in part_data]
        weights = [p[3] for p in part_data]

        def get_category(values, counter, random):
            if not category_ids:
                return False
            return random.choice(category_ids)

        def get_part_type(values, counter, random):
            pn = values.get("part_number", "")
            if pn.startswith(("RDS", "FLS", "BLE", "ALU")):
                return "raw"
            if pn.startswith(("SMI", "KSM", "FIL")):
                return "consumable"
            if pn.startswith("WEL") or pn.startswith("ZHR"):
                return "semi"
            return "finished"

        def get_make_or_buy(values, counter, random):
            pn = values.get("part_number", "")
            # Normteile, Lager, Rohmaterial, Sensoren = Fremdbezug
            if pn.startswith((
                "WLG", "SCR", "MUT", "SIR", "DIC", "RDS", "FLS",
                "BLE", "ALU", "SEN", "EMO", "SMI", "KSM", "HYV",
                "HYP",
            )):
                return "buy"
            return "make"

        def get_cost(values, counter, random):
            pn = values.get("part_number", "")
            w = values.get("weight_kg", 1.0)
            if pn.startswith("WLG"):
                return round(random.uniform(8.0, 120.0), 2)
            if pn.startswith("SCR") or pn.startswith("MUT"):
                return round(random.uniform(0.02, 0.80), 2)
            if pn.startswith("SIR") or pn.startswith("DIC"):
                return round(random.uniform(0.15, 4.50), 2)
            if pn.startswith(("RDS", "FLS", "BLE", "ALU")):
                return round(w * random.uniform(1.2, 3.5), 2)
            if pn.startswith("GEH"):
                return round(w * random.uniform(5.0, 12.0), 2)
            if pn.startswith(("ZHR", "WEL")):
                return round(w * random.uniform(8.0, 25.0), 2)
            if pn.startswith("HY"):
                return round(random.uniform(85.0, 1500.0), 2)
            if pn.startswith("EMO"):
                return round(random.uniform(250.0, 2800.0), 2)
            if pn.startswith("SEN"):
                return round(random.uniform(25.0, 180.0), 2)
            if pn.startswith(("SMI", "KSM")):
                return round(random.uniform(15.0, 120.0), 2)
            return round(w * random.uniform(4.0, 15.0), 2)

        def get_stock(values, counter, random):
            pn = values.get("part_number", "")
            if pn.startswith(("SCR", "MUT", "SIR", "DIC")):
                return round(random.uniform(200, 10000), 0)
            if pn.startswith(("RDS", "FLS", "BLE", "ALU")):
                return round(random.uniform(5, 80), 0)
            if pn.startswith("WLG"):
                return round(random.uniform(10, 200), 0)
            if pn.startswith(("SMI", "KSM")):
                return round(random.uniform(2, 30), 0)
            return round(random.uniform(0, 50), 0)

        return [
            ("part_number", populate.iterate(part_numbers)),
            ("name", populate.iterate(part_names)),
            ("category_id", populate.compute(get_category)),
            ("material", populate.iterate(materials)),
            ("weight_kg", populate.iterate(weights)),
            ("part_type", populate.compute(get_part_type)),
            ("make_or_buy", populate.compute(get_make_or_buy)),
            ("standard_cost", populate.compute(get_cost)),
            ("stock_qty", populate.compute(get_stock)),
            ("unit", populate.compute(
                lambda values, **kw: "kg"
                if values.get("part_number", "").startswith(
                    ("RDS", "FLS", "BLE", "ALU", "SMI", "KSM")
                ) else "Stk"
            )),
        ]
