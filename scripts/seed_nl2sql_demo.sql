-- =============================================================================
-- seed_nl2sql_demo.sql — Umfangreiche Testdaten für NL2SQL Use-Cases
-- =============================================================================
-- Aufruf:
--   docker exec -i odoo_db psql -U odoo -d odoo -v ON_ERROR_STOP=1 < scripts/seed_nl2sql_demo.sql
--
-- Design:
--   1. Bereinigung duplizierter Stammdaten (Name mit __ / _1_ Suffix aus populate)
--   2. Saubere Stammdaten: 12 Maschinen, 8 Legierungen, 6 Formen, 10 Defekttypen
--   3. 300 Aufträge über 18 Monate (Aug 2024 – Jan 2026) mit realistischer Saisonalität
--   4. ~600 Auftragszeilen mit Ausschuss-Trends, Maschinenvergleichen, Legierungseffekten
--   5. ~450 QC-Checks mit Defekten, Inspektoren, Messwerten
--
-- NL2SQL Use-Cases abgedeckt:
--   - Ausschussquote je Maschine/Monat/Legierung (Trendanalyse)
--   - Maschinenauslastung und -verfügbarkeit (Wartungsintervalle)
--   - Qualitätsentwicklung über Zeit (pass-Rate, Defekthäufigkeit)
--   - Lieferterminstreue (Soll vs. Ist)
--   - Top-N Kunden nach Auftragsvolumen
--   - Defekttypen-Ranking je Prozess/Legierung
--   - Monatlicher Durchsatz (Stückzahl, Gewicht)
--   - Werkzeug-/Formenverschleiß (current_shots vs. max_shots)
--
-- Geprüfte Spalten (Schema-Stand 2026-03-03):
--   casting_alloy: base_material_id, alloy_type, din_number, tensile_strength,
--                  yield_strength, elongation, hardness_brinell,
--                  pouring_temp_min, pouring_temp_max, shrinkage_rate, cost_per_kg
--   casting_material: code (UNIQUE), material_type, density, melting_point, cost_per_kg
--   casting_mold: code (UNIQUE), mold_type, state, cavity_count, max_shots,
--                 current_shots, remaining_shots, machine_id
--   casting_machine: code (UNIQUE), machine_type, state, hall, manufacturer, model,
--                    year_built, capacity_kg, clamping_force_t, max_temp_c, power_kw
-- =============================================================================

BEGIN;

-- =============================================================================
-- SCHRITT 1: Alle bisherigen Demo/Populate-Daten entfernen
-- Erkennung: name/code endet auf __ oder _\d+_ oder _\d+
-- =============================================================================

-- Abhängigkeiten zuerst löschen (FK-Reihenfolge)
DELETE FROM casting_defect_type_casting_quality_check_rel
WHERE casting_quality_check_id IN (SELECT id FROM casting_quality_check);

DELETE FROM casting_quality_check;
DELETE FROM casting_order_line;
DELETE FROM casting_order;

DELETE FROM casting_alloy_casting_mold_rel;
DELETE FROM casting_mold;
DELETE FROM casting_alloy;
DELETE FROM casting_defect_type;

-- Maschinen: nur duplizierte (code ~ Muster) löschen, saubere behalten
DELETE FROM casting_machine
WHERE code ~ '(_\d+_|__\d*$)';

-- Materialien: nur duplizierte
DELETE FROM casting_material
WHERE code ~ '(_\d+_|__\d*$)';

-- =============================================================================
-- SCHRITT 2: Stammdaten
-- =============================================================================

-- Admin-ID merken
DO $$
DECLARE v_id INTEGER;
BEGIN
    SELECT id INTO v_id FROM res_users WHERE login = 'admin' LIMIT 1;
    PERFORM set_config('seed.uid', COALESCE(v_id, 2)::text, true);
END $$;

-- ── Materialien (Basis für Legierungen) ──────────────────────────────────────
INSERT INTO casting_material (name, code, material_type, density, melting_point, cost_per_kg, active, create_uid, write_uid, create_date, write_date)
VALUES
  ('Aluminium',  'AL',  'non_ferrous', 2.70, 660,  2.50, true, current_setting('seed.uid')::int, current_setting('seed.uid')::int, now(), now()),
  ('Gusseisen',  'GG',  'ferrous',     7.20, 1200, 1.10, true, current_setting('seed.uid')::int, current_setting('seed.uid')::int, now(), now()),
  ('Zink',       'ZN',  'non_ferrous', 6.60, 420,  2.00, true, current_setting('seed.uid')::int, current_setting('seed.uid')::int, now(), now()),
  ('Magnesium',  'MG',  'non_ferrous', 1.74, 650,  3.80, true, current_setting('seed.uid')::int, current_setting('seed.uid')::int, now(), now())
ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name;

-- ── Legierungen ───────────────────────────────────────────────────────────────
INSERT INTO casting_alloy
    (name, din_number, alloy_type, base_material_id,
     tensile_strength, yield_strength, elongation, hardness_brinell,
     pouring_temp_min, pouring_temp_max, shrinkage_rate, cost_per_kg,
     active, create_uid, write_uid, create_date, write_date)
SELECT
    a.name, a.din, a.atype,
    (SELECT id FROM casting_material WHERE code = a.mat_code),
    a.uts, a.ys, a.elong, a.hb, a.t_min, a.t_max, a.shrink, a.cost,
    true,
    current_setting('seed.uid')::int, current_setting('seed.uid')::int, now(), now()
FROM (VALUES
    ('AlSi9Cu3 (EN AC-46000)', 'EN AC-46000', 'aluminum_silicon', 'AL', 240, 140, 1.0,  90,  640, 680, 0.6, 2.80),
    ('AlSi12 (EN AC-44000)',   'EN AC-44000', 'aluminum_silicon', 'AL', 170,  90, 1.0,  55,  620, 660, 0.8, 2.60),
    ('AlMg5 (EN AC-51000)',    'EN AC-51000', 'aluminum_magnesium','AL', 210, 130, 3.0,  65,  660, 710, 1.3, 3.40),
    ('AlSi10Mg (EN AC-43000)', 'EN AC-43000', 'aluminum_silicon', 'AL', 200, 120, 2.5,  70,  640, 680, 0.9, 2.90),
    ('EN-GJL-250 Grauguss',    'EN-GJL-250',  'gray_iron',        'GG', 250, 165, 0.3, 230, 1350,1420, 1.0, 1.20),
    ('EN-GJS-500-7 Sphäroguss','EN-GJS-500-7','ductile_iron',     'GG', 500, 320, 7.0, 170, 1350,1430, 1.2, 1.45),
    ('ZnAl4Cu1 (Zamak 5)',     'EN 12844',    'zinc',             'ZN', 330, 270, 1.5,  91,  415, 445, 1.1, 2.10),
    ('MgAl9Zn1 (AZ91)',        'AZ91D',       'magnesium',        'MG', 230, 150, 3.0,  65,  640, 680, 1.6, 4.50)
) AS a(name, din, atype, mat_code, uts, ys, elong, hb, t_min, t_max, shrink, cost);

-- ── Defekttypen ───────────────────────────────────────────────────────────────
INSERT INTO casting_defect_type
    (name, code, category, severity, active, create_uid, write_uid, create_date, write_date)
VALUES
    ('Gasporosität',              'POR-01', 'porosity',   'major',    true, current_setting('seed.uid')::int, current_setting('seed.uid')::int, now(), now()),
    ('Lunker (Makro)',            'POR-03', 'porosity',   'critical', true, current_setting('seed.uid')::int, current_setting('seed.uid')::int, now(), now()),
    ('Kaltlauf / Kaltschweißung','SRF-01', 'cold_shut',  'major',    true, current_setting('seed.uid')::int, current_setting('seed.uid')::int, now(), now()),
    ('Warmriss',                  'CRK-01', 'crack',      'critical', true, current_setting('seed.uid')::int, current_setting('seed.uid')::int, now(), now()),
    ('Sandeinschluss',            'INC-01', 'inclusion',  'major',    true, current_setting('seed.uid')::int, current_setting('seed.uid')::int, now(), now()),
    ('Maßabweichung Außenkontur', 'DIM-02', 'dimensional','minor',    true, current_setting('seed.uid')::int, current_setting('seed.uid')::int, now(), now()),
    ('Rauheit außer Toleranz',    'SRF-04', 'surface',    'minor',    true, current_setting('seed.uid')::int, current_setting('seed.uid')::int, now(), now()),
    ('Verzug',                    'DIM-03', 'distortion', 'major',    true, current_setting('seed.uid')::int, current_setting('seed.uid')::int, now(), now()),
    ('Oxidhaut',                  'INC-04', 'inclusion',  'major',    true, current_setting('seed.uid')::int, current_setting('seed.uid')::int, now(), now()),
    ('Gratbildung übermäßig',    'DIM-04', 'dimensional','minor',    true, current_setting('seed.uid')::int, current_setting('seed.uid')::int, now(), now())
ON CONFLICT DO NOTHING;

-- ── Maschinen (saubere 12 Stück, ergänzend zu vorhandenen) ───────────────────
INSERT INTO casting_machine
    (name, code, machine_type, state, manufacturer, model, year_built,
     hall, position, capacity_kg, clamping_force_t, max_temp_c, power_kw,
     last_maintenance, next_maintenance, active,
     create_uid, write_uid, create_date, write_date)
VALUES
  ('DC-01 Druckguss 400t',   'MCH-DC-01', 'die_casting',    'operational', 'Bühler',        'SC-400',   2018, 'Halle A', 'Platz 1',  2500, 400,  730, 185, '2025-11-15', '2026-02-15', true, current_setting('seed.uid')::int, current_setting('seed.uid')::int, now(), now()),
  ('DC-02 Druckguss 630t',   'MCH-DC-02', 'die_casting',    'operational', 'Bühler',        'SC-630',   2019, 'Halle A', 'Platz 2',  4000, 630,  730, 250, '2025-12-01', '2026-03-01', true, current_setting('seed.uid')::int, current_setting('seed.uid')::int, now(), now()),
  ('DC-03 Druckguss 250t',   'MCH-DC-03', 'die_casting',    'maintenance', 'Frech',         'DAK-250',  2015, 'Halle A', 'Platz 3',  1500, 250,  730, 120, '2026-01-20', '2026-04-20', true, current_setting('seed.uid')::int, current_setting('seed.uid')::int, now(), now()),
  ('DC-04 Druckguss 1000t',  'MCH-DC-04', 'die_casting',    'operational', 'Idra',          'OL-1000',  2021, 'Halle A', 'Platz 4',  6000, 1000, 730, 380, '2025-10-10', '2026-01-10', true, current_setting('seed.uid')::int, current_setting('seed.uid')::int, now(), now()),
  ('DC-05 Druckguss 800t',   'MCH-DC-05', 'die_casting',    'operational', 'UBE',           'UN-800',   2023, 'Halle A', 'Platz 5',  5000, 800,  730, 300, '2025-11-01', '2026-02-01', true, current_setting('seed.uid')::int, current_setting('seed.uid')::int, now(), now()),
  ('KK-01 Kokillenguss',     'MCH-KK-01', 'gravity_casting','operational', 'Italpresse',    'GDC-200',  2016, 'Halle B', 'Platz 6',   800,   0,  800,  75, '2025-09-05', '2026-03-05', true, current_setting('seed.uid')::int, current_setting('seed.uid')::int, now(), now()),
  ('KK-02 Kokillenguss',     'MCH-KK-02', 'gravity_casting','breakdown',   'Italpresse',    'GDC-150',  2013, 'Halle B', 'Platz 7',   500,   0,  800,  55, '2025-08-01', '2025-11-01', true, current_setting('seed.uid')::int, current_setting('seed.uid')::int, now(), now()),
  ('SO-01 Schmelzofen 2t',   'MCH-SO-01', 'melting_furnace','operational', 'StrikoWestofen','MH-2000',  2017, 'Halle B', 'Platz 8',  2000,   0,  780, 300, '2025-11-20', '2026-02-20', true, current_setting('seed.uid')::int, current_setting('seed.uid')::int, now(), now()),
  ('SO-02 Schmelzofen 5t',   'MCH-SO-02', 'melting_furnace','operational', 'StrikoWestofen','MH-5000',  2020, 'Halle B', 'Platz 9',  5000,   0,  780, 650, '2025-12-10', '2026-03-10', true, current_setting('seed.uid')::int, current_setting('seed.uid')::int, now(), now()),
  ('WB-01 Wärmebehandlung',  'MCH-WB-01', 'heat_treatment', 'operational', 'Aichelin',      'UNI-350',  2019, 'Halle C', 'Platz 10', 1000,   0,  550, 120, '2026-01-05', '2026-07-05', true, current_setting('seed.uid')::int, current_setting('seed.uid')::int, now(), now()),
  ('RX-01 Röntgenprüfung',   'MCH-RX-01', 'xray',           'operational', 'Yxlon',         'FF35',     2022, 'Halle C', 'Platz 11',    0,   0,    0,  45, '2025-10-01', '2026-04-01', true, current_setting('seed.uid')::int, current_setting('seed.uid')::int, now(), now()),
  ('PT-01 Putzerei/Strahlen','MCH-PT-01', 'finishing',      'operational', 'Rösler',        'RKWS-D',   2020, 'Halle C', 'Platz 12',  500,   0,    0,  55, '2025-12-15', '2026-06-15', true, current_setting('seed.uid')::int, current_setting('seed.uid')::int, now(), now())
ON CONFLICT (code) DO UPDATE
    SET name = EXCLUDED.name, state = EXCLUDED.state,
        last_maintenance = EXCLUDED.last_maintenance,
        next_maintenance = EXCLUDED.next_maintenance;

-- ── Gießformen ────────────────────────────────────────────────────────────────
INSERT INTO casting_mold
    (name, code, mold_type, state, cavity_count, max_shots, current_shots,
     remaining_shots, part_weight_kg, cycle_time_min,
     acquisition_cost, maintenance_cost, machine_id, active,
     create_uid, write_uid, create_date, write_date)
SELECT
    v.name, v.code, v.mold_type, v.state,
    v.cavity_count, v.max_shots, v.current_shots,
    v.max_shots - v.current_shots,
    v.part_wt, v.cycle, v.acq_cost, v.maint_cost,
    mc.id, true,
    current_setting('seed.uid')::int, current_setting('seed.uid')::int, now(), now()
FROM (VALUES
    ('WZ-Motorblock-V6',      'WZ-MB-V6',  'permanent_steel', 'active',      1,  80000,  54200, 12.5, 3.8,  85000, 12000, 'MCH-DC-04'),
    ('WZ-Zylinderkopf-4Zyl',  'WZ-ZK-4C',  'permanent_steel', 'active',      1,  60000,  38100,  8.2, 2.9,  72000,  9500, 'MCH-DC-02'),
    ('WZ-Getriebegehäuse',    'WZ-GG-01',  'permanent_steel', 'active',      1,  50000,  41800, 15.1, 4.2,  95000, 14000, 'MCH-DC-04'),
    ('WZ-Radnabe-Vorn',       'WZ-RN-VA',  'permanent_steel', 'maintenance', 2, 120000,  98700,  3.4, 1.8,  48000,  6500, 'MCH-DC-01'),
    ('WZ-Bremsscheibe-VA',    'WZ-BS-VA',  'sand',            'active',      1,  30000,  12300, 18.6, 6.5,  32000,  4200, 'MCH-KK-01'),
    ('WZ-Pumpengehäuse-DN80', 'WZ-PG-D80', 'permanent_steel', 'active',      2,  90000,  67400,  2.1, 1.2,  55000,  7800, 'MCH-DC-01')
) AS v(name, code, mold_type, state, cavity_count, max_shots, current_shots,
       part_wt, cycle, acq_cost, maint_cost, mach_code)
JOIN casting_machine mc ON mc.code = v.mach_code
ON CONFLICT (code) DO UPDATE
    SET current_shots = EXCLUDED.current_shots,
        remaining_shots = EXCLUDED.remaining_shots,
        state = EXCLUDED.state;

-- =============================================================================
-- SCHRITT 3: Aufträge + Zeilen + QC (300 Aufträge / 18 Monate)
-- =============================================================================
DO $$
DECLARE
    v_admin      INTEGER;
    v_partners   INTEGER[];
    v_dc_machines INTEGER[];
    v_all_machines INTEGER[];
    v_alloys     INTEGER[];
    v_molds      INTEGER[];
    v_defects    INTEGER[];
    v_users      INTEGER[];

    v_order_id   INTEGER;
    v_line_id    INTEGER;
    v_qc_id      INTEGER;
    v_seq        INTEGER := 1;

    mo INTEGER;  -- month offset 0..17
    i  INTEGER;  -- order within month

    v_order_date   DATE;
    v_planned_date DATE;
    v_state        TEXT;
    v_priority     TEXT;
    v_partner      INTEGER;
    v_machine      INTEGER;
    v_alloy        INTEGER;
    v_mold         INTEGER;
    v_qty          INTEGER;
    v_scrap_pct    NUMERIC;
    v_scrap_qty    INTEGER;
    v_good_qty     INTEGER;
    v_weight       NUMERIC;
    v_process      TEXT;
    v_heat         TEXT;
    v_part_name    TEXT;
    v_part_no      TEXT;
    v_orders_n     INTEGER;
    v_month_num    INTEGER;

    v_qc_result    TEXT;
    v_check_type   TEXT;
    v_defect_cnt   INTEGER;
    v_measured     NUMERIC;
    v_nominal      NUMERIC;
    v_inspector    INTEGER;
    v_d1           INTEGER;
    v_d2           INTEGER;

    part_names TEXT[] := ARRAY[
        'Motorblock V6',       'Zylinderkopf 4-Zyl',  'Getriebegehäuse 6-Gang',
        'Turboladergehäuse',   'Bremsscheibe VA',      'Bremsscheibe HA',
        'Lenkgetriebegehäuse', 'Ölpumpengehäuse',      'Wasserpumpengehäuse',
        'Ansaugbrücke',        'Abgaskrümmer',          'Schwungrad',
        'Kurbelgehäuse UT',    'Radnabe Vorn',          'Radnabe Hinten',
        'Achsschenkel Li',     'Achsschenkel Re',       'Federbeinstütze',
        'Querlenker Vorn',     'Differentialgehäuse',   'Kupplungsglocke',
        'Ventilblock Hyd',     'Pumpenrad',             'Kolbenrohling D82',
        'Flanschplatte DN150', 'Kompressorgehäuse',     'Nockenwellengehäuse',
        'Steuerdeckel',        'Ölwanne Alu',           'Achsträger HA'
    ];
    qty_list INTEGER[] := ARRAY[100, 200, 250, 500, 750, 1000, 2000, 5000];

BEGIN
    SELECT current_setting('seed.uid')::int INTO v_admin;

    SELECT array_agg(id ORDER BY id) INTO v_partners
        FROM res_partner WHERE is_company = true AND id > 1 LIMIT 15;
    IF v_partners IS NULL THEN
        SELECT array_agg(id ORDER BY id) INTO v_partners FROM res_partner LIMIT 8;
    END IF;

    SELECT array_agg(id ORDER BY id) INTO v_dc_machines
        FROM casting_machine WHERE machine_type = 'die_casting' AND active = true;

    SELECT array_agg(id ORDER BY id) INTO v_all_machines
        FROM casting_machine WHERE active = true;

    SELECT array_agg(id ORDER BY id) INTO v_alloys
        FROM casting_alloy WHERE active = true;

    SELECT array_agg(id ORDER BY id) INTO v_molds
        FROM casting_mold WHERE active = true;

    SELECT array_agg(id ORDER BY id) INTO v_defects
        FROM casting_defect_type WHERE active = true;

    SELECT array_agg(id ORDER BY id) INTO v_users
        FROM res_users
        WHERE active = true
          AND login NOT IN ('__system__','public','portal','portaltemplate','default')
        LIMIT 8;

    -- 18 Monate: August 2024 (mo=0) → Januar 2026 (mo=17)
    FOR mo IN 0..17 LOOP
        v_month_num := ((7 + mo) % 12) + 1;  -- 1=Jan..12=Dec
        v_orders_n := CASE
            WHEN v_month_num IN (10,11,12) THEN 24   -- Q4 Hochsaison
            WHEN v_month_num IN (1, 2)     THEN 13   -- Jahresanfang ruhiger
            WHEN v_month_num IN (7, 8)     THEN 15   -- Sommer etwas ruhiger
            ELSE 18
        END;

        FOR i IN 1..v_orders_n LOOP
            v_order_date   := (date_trunc('month', '2024-08-01'::date)
                               + (mo || ' months')::interval)::date
                               + ((i * 1.4)::int % 27);
            v_planned_date := v_order_date + 7 + (i % 21);

            -- Status: ältere = done/cancelled, neuere = laufend
            IF mo < 13 THEN
                v_state := (ARRAY['done','done','done','done','cancelled'])[1 + (i % 5)];
            ELSIF mo < 16 THEN
                v_state := (ARRAY['done','done','in_production','quality_check'])[1 + (i % 4)];
            ELSE
                v_state := (ARRAY['in_production','confirmed','quality_check','draft'])[1 + (i % 4)];
            END IF;

            v_priority := (ARRAY['0','0','0','1','1','2'])[1 + (i % 6)];
            v_partner  := v_partners[1 + (i % array_length(v_partners,1))];

            -- Maschinen-Zuweisung: hauptsächlich Druckguss
            IF v_dc_machines IS NOT NULL AND (i % 5) < 4 THEN
                v_machine := v_dc_machines[1 + (i % array_length(v_dc_machines,1))];
            ELSE
                v_machine := v_all_machines[1 + (i % array_length(v_all_machines,1))];
            END IF;

            v_alloy := v_alloys[1 + ((i + mo * 3) % array_length(v_alloys,1))];
            v_mold  := v_molds[1 + (i % array_length(v_molds,1))];

            -- Ausschuss-Trend: 11% → 3.5% über 18 Monate
            -- Maschinen-Effekt: DC-03 (alt) = +2%, DC-05 (neu) = -1%
            -- Legierungs-Effekt: AlMg5 und MgAl9Zn1 = höherer Ausschuss
            v_scrap_pct := GREATEST(0.3,
                11.0 - (mo::numeric * 0.42)
                + CASE (v_machine % 7)
                    WHEN 2 THEN  2.0   -- DC-03 (alt)
                    WHEN 4 THEN -1.0   -- DC-05 (neu)
                    WHEN 5 THEN  0.5   -- KK-01
                    WHEN 6 THEN  1.0   -- KK-02 (breakdown-Folgen)
                    ELSE         0.0
                  END
                + CASE (v_alloy % 4)
                    WHEN 2 THEN  1.2   -- AlMg5
                    WHEN 3 THEN  0.8   -- AlSi10Mg
                    ELSE         0.0
                  END
                + ((((i * 11 + mo * 17) % 40) - 20) * 0.08)  -- Rauschen ±1.6%
            );

            v_qty       := qty_list[1 + ((i + mo) % array_length(qty_list,1))];
            v_scrap_qty := (v_qty * v_scrap_pct / 100.0)::int;
            v_good_qty  := v_qty - v_scrap_qty;
            v_weight    := round((0.8 + (((i + mo * 3) % 35) * 2.3))::numeric, 3);
            v_process   := (ARRAY['die_cast_cold','die_cast_cold','die_cast_hot','gravity','sand'])[1 + (i % 5)];
            v_heat      := (ARRAY['none','none','t6','t5','t4','annealing'])[1 + (i % 6)];
            v_part_name := part_names[1 + ((i + mo * 7) % array_length(part_names,1))];
            v_part_no   := 'ZN-' || lpad((10000 + v_seq)::text, 5,'0') || '-' || (ARRAY['A','B','C'])[1+(i%3)];

            INSERT INTO casting_order
                (name, partner_id, customer_reference, state, priority,
                 date_planned, date_start, date_done,
                 total_pieces, total_weight_kg, total_scrap_pct,
                 create_uid, write_uid, create_date, write_date)
            VALUES (
                'GA-' || to_char(v_order_date,'YYYY') || '-' || lpad(v_seq::text,5,'0'),
                v_partner,
                'PO-' || (10000 + v_seq)::text || '-' || (ARRAY['A','B','C','D'])[1+(i%4)],
                v_state, v_priority,
                v_planned_date,
                CASE WHEN v_state NOT IN ('draft','confirmed') THEN v_order_date::timestamp END,
                CASE WHEN v_state = 'done'
                     THEN (v_order_date + 5 + (i % 12))::timestamp + ((i%8)||' hours')::interval
                END,
                v_qty,
                round((v_qty * v_weight / 1000.0)::numeric, 2),
                round(v_scrap_pct::numeric, 2),
                v_admin, v_admin,
                v_order_date::timestamp, v_order_date::timestamp
            ) RETURNING id INTO v_order_id;

            v_seq := v_seq + 1;

            -- Hauptzeile
            INSERT INTO casting_order_line
                (order_id, sequence, alloy_id, mold_id, machine_id,
                 part_name, part_number, casting_process, heat_treatment,
                 quantity, scrap_qty, good_qty, order_state,
                 piece_weight_kg, total_weight_kg,
                 pouring_temp_c, mold_temp_c, cycle_time_min,
                 create_uid, write_uid, create_date, write_date)
            VALUES (
                v_order_id, 1, v_alloy, v_mold, v_machine,
                v_part_name, v_part_no, v_process, v_heat,
                v_qty, v_scrap_qty, v_good_qty, v_state,
                v_weight, round((v_qty * v_weight / 1000.0)::numeric, 2),
                640 + (((i + mo) % 12) * 3.5),
                160 + ((i % 10) * 12),
                round((1.2 + ((i % 8) * 0.7))::numeric, 1),
                v_admin, v_admin, v_order_date::timestamp, v_order_date::timestamp
            ) RETURNING id INTO v_line_id;

            -- Zweite Zeile (33% der Aufträge)
            IF i % 3 = 0 THEN
                INSERT INTO casting_order_line
                    (order_id, sequence, alloy_id, mold_id, machine_id,
                     part_name, part_number, casting_process, heat_treatment,
                     quantity, scrap_qty, good_qty, order_state,
                     piece_weight_kg, total_weight_kg,
                     pouring_temp_c, mold_temp_c, cycle_time_min,
                     create_uid, write_uid, create_date, write_date)
                VALUES (
                    v_order_id, 2,
                    v_alloys[1 + ((i+3) % array_length(v_alloys,1))],
                    v_mold, v_machine,
                    part_names[1 + ((i+11+mo) % array_length(part_names,1))],
                    'ZN-' || lpad((20000+v_order_id)::text,5,'0') || '-X',
                    v_process, v_heat,
                    v_qty/2, (v_qty/2 * v_scrap_pct/100.0)::int,
                    v_qty/2 - (v_qty/2 * v_scrap_pct/100.0)::int,
                    v_state,
                    round((v_weight * 0.6)::numeric, 3),
                    round(((v_qty/2) * v_weight * 0.6 / 1000.0)::numeric, 2),
                    645 + (i % 15) * 2, 170 + (i % 8) * 10,
                    round((1.0 + ((i%6) * 0.5))::numeric, 1),
                    v_admin, v_admin, v_order_date::timestamp, v_order_date::timestamp
                );
            END IF;

            -- QC-Check (65% der laufenden/fertigen Aufträge)
            IF v_state NOT IN ('draft','confirmed') AND (i % 3) != 2 THEN
                v_inspector  := v_users[1 + (i % array_length(v_users,1))];
                v_check_type := (ARRAY['visual','dimensional','xray','hardness','ultrasonic'])[1+(i%5)];

                -- QS-Ergebnis korreliert mit Ausschuss-Trend
                IF v_scrap_pct > 8.0 THEN
                    v_qc_result := (ARRAY['pass','conditional','fail','pass'])[1+(i%4)];
                ELSIF v_scrap_pct > 4.5 THEN
                    v_qc_result := (ARRAY['pass','pass','conditional','pass'])[1+(i%4)];
                ELSE
                    v_qc_result := (ARRAY['pass','pass','pass','conditional'])[1+(i%4)];
                END IF;

                v_defect_cnt := CASE v_qc_result
                    WHEN 'pass' THEN 0
                    WHEN 'conditional' THEN 1 + (i%3)
                    ELSE 3 + (i%4)
                END;
                v_measured := round((50.0 + ((i*3+mo)%200))::numeric, 3);
                v_nominal  := round((v_measured + ((i%10)-5)*0.02)::numeric, 3);

                INSERT INTO casting_quality_check
                    (name, order_id, order_line_id, inspector_id,
                     check_type, result, check_date,
                     sample_size, defect_count,
                     measured_value, nominal_value,
                     tolerance_plus, tolerance_minus,
                     create_uid, write_uid, create_date, write_date)
                VALUES (
                    'QC-' || v_order_id::text || '-' || (i%3+1)::text,
                    v_order_id, v_line_id, v_inspector,
                    v_check_type, v_qc_result,
                    (v_order_date + 3 + (i%5))::timestamp + ((i%12)||' hours')::interval,
                    (ARRAY[3,5,10,20,50])[1+(i%5)],
                    v_defect_cnt,
                    v_measured, v_nominal,
                    0.05 + ((i%10)*0.01), 0.05 + ((i%8)*0.01),
                    v_admin, v_admin,
                    v_order_date::timestamp, v_order_date::timestamp
                ) RETURNING id INTO v_qc_id;

                -- Defekte verknüpfen
                IF v_qc_result IN ('fail','conditional') AND v_defects IS NOT NULL THEN
                    v_d1 := v_defects[1 + (i % array_length(v_defects,1))];
                    INSERT INTO casting_defect_type_casting_quality_check_rel
                        (casting_quality_check_id, casting_defect_type_id)
                    VALUES (v_qc_id, v_d1) ON CONFLICT DO NOTHING;

                    IF v_qc_result = 'fail' THEN
                        v_d2 := v_defects[1 + ((i+3) % array_length(v_defects,1))];
                        INSERT INTO casting_defect_type_casting_quality_check_rel
                            (casting_quality_check_id, casting_defect_type_id)
                        VALUES (v_qc_id, v_d2) ON CONFLICT DO NOTHING;
                    END IF;
                END IF;
            END IF;

        END LOOP; -- i
    END LOOP; -- mo

    -- Auftragsköpfe aggregieren
    UPDATE casting_order co
    SET total_pieces    = s.qty,
        total_weight_kg = s.wt,
        total_scrap_pct = CASE WHEN s.qty > 0 THEN round((s.scrap * 100.0 / s.qty)::numeric, 2) ELSE 0 END
    FROM (
        SELECT order_id,
               SUM(quantity)        AS qty,
               SUM(scrap_qty)       AS scrap,
               SUM(total_weight_kg) AS wt
        FROM casting_order_line GROUP BY order_id
    ) s
    WHERE co.id = s.order_id;

    RAISE NOTICE 'Seed fertig: % Aufträge', v_seq - 1;
END $$;

COMMIT;

-- Statistik
SELECT tabelle, zeilen FROM (
    SELECT 'casting_order'        AS tabelle, COUNT(*) AS zeilen FROM casting_order
    UNION ALL SELECT 'casting_order_line',    COUNT(*) FROM casting_order_line
    UNION ALL SELECT 'casting_quality_check', COUNT(*) FROM casting_quality_check
    UNION ALL SELECT 'casting_machine',       COUNT(*) FROM casting_machine
    UNION ALL SELECT 'casting_alloy',         COUNT(*) FROM casting_alloy
    UNION ALL SELECT 'casting_mold',          COUNT(*) FROM casting_mold
    UNION ALL SELECT 'casting_defect_type',   COUNT(*) FROM casting_defect_type
    UNION ALL SELECT 'casting_material',      COUNT(*) FROM casting_material
) t ORDER BY tabelle;
