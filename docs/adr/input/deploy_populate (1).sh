#!/bin/bash
# ==============================================================
# SCM Manufacturing: Populate-Framework Deployment
# Ausführen im Root des odoo-hub Repos auf dem Hetzner-Server
# ==============================================================
set -e

ADDON_DIR="addons/scm_manufacturing"

echo "=== 1. Populate-Verzeichnis erstellen ==="
mkdir -p "$ADDON_DIR/populate"

echo "=== 2. __init__.py patchen ==="
if ! grep -q "populate" "$ADDON_DIR/__init__.py" 2>/dev/null; then
    cat > "$ADDON_DIR/__init__.py" << 'EOF'
from . import models
from . import populate
EOF
    echo "  -> __init__.py aktualisiert"
else
    echo "  -> populate-Import bereits vorhanden"
fi

echo "=== 3. Populate-Dateien schreiben ==="

cat > "$ADDON_DIR/populate/__init__.py" << 'PYEOF'
from . import populate_warehouse
from . import populate_part
from . import populate_supplier
from . import populate_bom
from . import populate_purchase
from . import populate_production
from . import populate_logistics
PYEOF
echo "  -> __init__.py"

cat > "$ADDON_DIR/populate/populate_warehouse.py" << 'PYEOF'
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
PYEOF
echo "  -> populate_warehouse.py"

cat > "$ADDON_DIR/populate/populate_part.py" << 'PYEOF'
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
PYEOF
echo "  -> populate_part.py"

cat > "$ADDON_DIR/populate/populate_supplier.py" << 'PYEOF'
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
PYEOF
echo "  -> populate_supplier.py"

cat > "$ADDON_DIR/populate/populate_bom.py" << 'PYEOF'
from odoo import models
from odoo.tools import populate


class ScmBomPopulate(models.Model):
    _inherit = "scm.bom"

    _populate_sizes = {"small": 10, "medium": 40, "large": 120}
    _populate_dependencies = ["scm.part"]

    def _populate_factories(self):
        part_ids = (
            self.env.registry.populated_models.get("scm.part", [])
        )
        # BOM nur für Eigenfertigung (make) und Halbfertig/Fertig
        make_parts = self.env["scm.part"].browse(part_ids).filtered(
            lambda p: p.make_or_buy == "make"
        )
        make_ids = make_parts.ids or part_ids[:10]

        def get_part(values, counter, random):
            return random.choice(make_ids) if make_ids else False

        return [
            ("part_id", populate.compute(get_part)),
            ("revision", populate.randomize(
                ["A", "B", "C", "D"], [0.50, 0.30, 0.15, 0.05],
            )),
            ("bom_type", populate.randomize(
                ["standard", "phantom", "variant"],
                [0.75, 0.15, 0.10],
            )),
            ("state", populate.randomize(
                ["draft", "active", "obsolete"],
                [0.15, 0.70, 0.15],
            )),
        ]


class ScmBomLinePopulate(models.Model):
    _inherit = "scm.bom.line"

    _populate_sizes = {"small": 40, "medium": 200, "large": 700}
    _populate_dependencies = ["scm.bom", "scm.part"]

    def _populate_factories(self):
        bom_ids = (
            self.env.registry.populated_models.get("scm.bom", [])
        )
        part_ids = (
            self.env.registry.populated_models.get("scm.part", [])
        )

        def get_bom(values, counter, random):
            return random.choice(bom_ids) if bom_ids else False

        def get_component(values, counter, random):
            return random.choice(part_ids) if part_ids else False

        def get_qty(values, counter, random):
            return random.choice([
                1, 1, 1, 2, 2, 3, 4, 6, 8, 12, 16, 24,
            ])

        return [
            ("bom_id", populate.compute(get_bom)),
            ("component_id", populate.compute(get_component)),
            ("quantity", populate.compute(get_qty)),
            ("sequence", populate.compute(
                lambda counter, **kw: (counter % 8 + 1) * 10,
            )),
        ]
PYEOF
echo "  -> populate_bom.py"

cat > "$ADDON_DIR/populate/populate_purchase.py" << 'PYEOF'
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
PYEOF
echo "  -> populate_purchase.py"

cat > "$ADDON_DIR/populate/populate_production.py" << 'PYEOF'
import datetime

from odoo import models
from odoo.tools import populate


class ScmProductionOrderPopulate(models.Model):
    _inherit = "scm.production.order"

    _populate_sizes = {"small": 15, "medium": 150, "large": 1000}
    _populate_dependencies = ["scm.part", "scm.bom"]

    def _populate_factories(self):
        part_ids = (
            self.env.registry.populated_models.get("scm.part", [])
        )
        bom_ids = (
            self.env.registry.populated_models.get("scm.bom", [])
        )

        def get_part(values, counter, random):
            return random.choice(part_ids) if part_ids else False

        def get_bom(values, counter, random):
            if not bom_ids:
                return False
            return random.choice(bom_ids) if random.random() < 0.8 else False

        def get_date_planned(values, counter, random):
            today = datetime.date.today()
            delta = random.randint(-270, 60)
            return today + datetime.timedelta(days=delta)

        def get_date_start(values, counter, random):
            state = values.get("state")
            d_plan = values.get("date_planned")
            if state in ("in_progress", "done") and d_plan:
                offset = random.randint(-3, 5)
                dt = datetime.datetime.combine(
                    d_plan + datetime.timedelta(days=offset),
                    datetime.time(
                        random.randint(6, 14),
                        random.choice([0, 15, 30, 45]),
                    ),
                )
                return dt
            return False

        def get_date_done(values, counter, random):
            state = values.get("state")
            d_start = values.get("date_start")
            if state == "done" and d_start:
                hours = random.randint(4, 240)
                return d_start + datetime.timedelta(hours=hours)
            return False

        def get_planned_qty(values, counter, random):
            return random.choice([
                5, 10, 20, 25, 50, 100, 200, 500,
            ])

        def get_produced_qty(values, counter, random):
            state = values.get("state")
            planned = values.get("planned_qty", 0)
            if state == "done":
                return round(
                    planned * random.uniform(0.88, 1.02), 2
                )
            if state == "in_progress":
                return round(
                    planned * random.uniform(0.10, 0.85), 2
                )
            return 0

        def get_scrap(values, counter, random):
            produced = values.get("produced_qty", 0)
            if produced > 0:
                rate = random.uniform(0.0, 0.08)
                return round(produced * rate, 2)
            return 0

        def get_total_cost(values, counter, random):
            planned = values.get("planned_qty", 0)
            return round(
                planned * random.uniform(5.0, 350.0), 2
            )

        return [
            ("part_id", populate.compute(get_part)),
            ("bom_id", populate.compute(get_bom)),
            ("state", populate.randomize(
                ["draft", "confirmed", "in_progress", "done", "cancelled"],
                [0.08, 0.12, 0.18, 0.52, 0.10],
            )),
            ("date_planned", populate.compute(get_date_planned)),
            ("date_start", populate.compute(get_date_start)),
            ("date_done", populate.compute(get_date_done)),
            ("planned_qty", populate.compute(get_planned_qty)),
            ("produced_qty", populate.compute(get_produced_qty)),
            ("scrap_qty", populate.compute(get_scrap)),
            ("total_cost", populate.compute(get_total_cost)),
        ]


class ScmWorkStepPopulate(models.Model):
    _inherit = "scm.work.step"

    _populate_sizes = {"small": 40, "medium": 500, "large": 4000}
    _populate_dependencies = ["scm.production.order"]

    def _populate_factories(self):
        production_ids = (
            self.env.registry.populated_models.get(
                "scm.production.order", []
            )
        )

        step_names = [
            # Spanende Bearbeitung
            "Drehen Außenkontur", "Drehen Innenkontur",
            "Fräsen Planfläche", "Fräsen Kontur", "Fräsen Tasche",
            "Bohren", "Reiben", "Gewinde schneiden",
            "Schleifen Rundschliff", "Schleifen Flachschliff",
            "Honen", "Läppen",
            # Umformung / Schweißen
            "Biegen", "Stanzen", "Tiefziehen",
            "MAG-Schweißen", "WIG-Schweißen",
            # Wärmebehandlung
            "Einsatzhärten", "Vergüten", "Anlassen",
            "Nitrieren", "Induktivhärten",
            # Oberfläche
            "Entgraten", "Sandstrahlen", "Brünieren",
            "Verzinken galvanisch", "Eloxieren",
            "Lackieren Grundierung", "Lackieren Decklack",
            # Montage / Prüfung
            "Montage Baugruppe", "Pressfügen Lager",
            "Wuchten", "Dichtprüfung",
            "Maßprüfung 3D-Messmaschine", "Funktionsprüfung",
            "Verpacken",
        ]

        work_centers = [
            "CNC-Drehmaschine DMG CTX beta 800",
            "CNC-Fräse DMG DMU 50",
            "CNC-Fräse Hermle C400",
            "Flachschleifmaschine Blohm Planomat",
            "Rundschleifmaschine Studer S33",
            "Bohrwerk TOS WHN 13.8",
            "Abkantpresse Trumpf TruBend 5130",
            "Säge KASTO SBA 360",
            "Schweißroboter KUKA KR 16",
            "Härteofen Ipsen VTTC",
            "Waschanlage BvL Niagara",
            "Montagearbeitsplatz M1",
            "Montagearbeitsplatz M2",
            "3D-Messmaschine Zeiss Contura",
            "Prüfstand P1",
        ]

        def get_production(values, counter, random):
            return (
                random.choice(production_ids)
                if production_ids else False
            )

        def get_planned_dur(values, counter, random):
            return round(random.uniform(5.0, 180.0), 1)

        def get_actual_dur(values, counter, random):
            state = values.get("state")
            planned = values.get("planned_duration_min", 0)
            if state == "done" and planned > 0:
                # ±30% Abweichung
                factor = random.uniform(0.70, 1.35)
                return round(planned * factor, 1)
            if state == "in_progress" and planned > 0:
                return round(planned * random.uniform(0.2, 0.8), 1)
            return 0

        return [
            ("production_id", populate.compute(get_production)),
            ("name", populate.randomize(step_names)),
            ("work_center", populate.randomize(work_centers)),
            ("planned_duration_min", populate.compute(get_planned_dur)),
            ("state", populate.randomize(
                ["pending", "in_progress", "done"],
                [0.25, 0.15, 0.60],
            )),
            ("actual_duration_min", populate.compute(get_actual_dur)),
            ("sequence", populate.compute(
                lambda counter, **kw: (counter % 6 + 1) * 10,
            )),
        ]
PYEOF
echo "  -> populate_production.py"

cat > "$ADDON_DIR/populate/populate_logistics.py" << 'PYEOF'
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
PYEOF
echo "  -> populate_logistics.py"

echo ""
echo "=== 4. Git commit & push ==="
git add "$ADDON_DIR/populate/" "$ADDON_DIR/__init__.py"
git commit -m "feat(scm_manufacturing): add populate framework

- 7 populate files for all 13 SCM models
- Realistic Maschinenbau data (SKF/FAG bearings, DIN fasteners,
  gears, shafts, Bosch Rexroth hydraulics, Siemens motors)
- ~2800 records at medium size
- EN 10204 quality certificates, German carriers
- Proper dependency chain for populate order"

git push origin main

echo ""
echo "=== 5. Populate ausführen ==="
echo ""
echo "  python3 odoo-bin populate --models \\"
echo "    scm.warehouse,scm.part.category,scm.part,scm.supplier.info,\\"
echo "    scm.bom,scm.bom.line,scm.purchase.order,scm.purchase.line,\\"
echo "    scm.production.order,scm.work.step,scm.stock.move,\\"
echo "    scm.delivery,scm.incoming.inspection \\"
echo "    --size medium -d <DATENBANK>"
echo ""
echo "=== Fertig! ==="
