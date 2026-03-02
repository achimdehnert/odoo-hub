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
