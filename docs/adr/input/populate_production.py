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
