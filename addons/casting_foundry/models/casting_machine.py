from odoo import models, fields


class CastingMachine(models.Model):
    _name = "casting.machine"
    _description = "Gießmaschine / Anlage"
    _inherit = ["mail.thread"]
    _order = "name"

    name = fields.Char(string="Maschinenbezeichnung", required=True, tracking=True)
    code = fields.Char(string="Maschinen-Nr.", required=True, index=True)
    machine_type = fields.Selection(
        [
            ("melting_furnace", "Schmelzofen"),
            ("holding_furnace", "Warmhalteofen"),
            ("die_casting", "Druckgussmaschine"),
            ("gravity_casting", "Schwerkraft-Kokillenguss"),
            ("sand_molding", "Formanlage (Sand)"),
            ("centrifugal", "Schleudergussmaschine"),
            ("heat_treatment", "Wärmebehandlungsofen"),
            ("finishing", "Nachbearbeitung / Putzerei"),
            ("xray", "Röntgenprüfanlage"),
        ],
        string="Maschinentyp",
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("operational", "Betriebsbereit"),
            ("maintenance", "In Wartung"),
            ("breakdown", "Störung"),
            ("decommissioned", "Stillgelegt"),
        ],
        string="Status",
        default="operational",
        required=True,
        tracking=True,
    )
    manufacturer = fields.Char(string="Hersteller")
    model = fields.Char(string="Modell / Typ")
    year_built = fields.Integer(string="Baujahr")
    # Capacity
    capacity_kg = fields.Float(string="Kapazität (kg)", digits=(10, 1))
    clamping_force_t = fields.Float(string="Schließkraft (t)", digits=(8, 1))
    max_temp_c = fields.Float(string="Max. Temperatur (°C)", digits=(6, 1))
    power_kw = fields.Float(string="Leistung (kW)", digits=(8, 1))
    # Location
    hall = fields.Char(string="Halle")
    position = fields.Char(string="Standplatz")
    # Maintenance
    last_maintenance = fields.Date(string="Letzte Wartung")
    next_maintenance = fields.Date(string="Nächste Wartung")
    # Relations
    mold_ids = fields.One2many("casting.mold", "machine_id", string="Zugeordnete Formen")
    notes = fields.Text(string="Bemerkungen")
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("code_uniq", "unique(code)", "Die Maschinen-Nr. muss eindeutig sein."),
    ]
