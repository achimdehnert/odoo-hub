-- docker/db/init.sql
-- PostgreSQL 16 Initialisierungs-Script für odoo-hub
-- Wird vom Docker-Entrypoint einmalig ausgeführt wenn das Volume leer ist.
--
-- IDEMPOTENT: Alle Statements nutzen IF NOT EXISTS / DO $$ Blöcke.
--             Kann auch manuell erneut ausgeführt werden:
--             docker exec odoo_db psql -U $POSTGRES_USER -d $POSTGRES_DB \
--               -f /docker-entrypoint-initdb.d/01_init.sql
--
-- Zweck:
--   1. Read-Only-Rolle für NL2SQL-Execution (nl2sql_ro)
--   2. Login-User nl2sql_user mit sicheren Defaults auf Rollen-Ebene
--   3. GRANT SELECT auf NL2SQL-Whitelist-Tabellen
--
-- Hinweis: GRANTs in Abschnitt 3 müssen nach jeder neuen Odoo-Modul-Installation
--          erneut ausgeführt werden (neue Tabellen erhalten keine automatischen GRANTs).

-- ── 1. Read-Only-Basisrolle ───────────────────────────────────────────────────
-- Kein Login, nur Rechte-Container. Sicherheits-Defaults auf Rollen-Ebene:
--   - statement_timeout:              Queries >30s werden abgebrochen
--   - lock_timeout:                   Lock-Wait >5s wird abgebrochen
--   - default_transaction_read_only:  Schreiboperationen technisch unmöglich
--
-- Diese Konfiguration wirkt unabhängig vom pgbouncer pool_mode und ist damit
-- robuster als SET LOCAL statement_timeout im Anwendungscode.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nl2sql_ro') THEN
        CREATE ROLE nl2sql_ro NOLOGIN;
        RAISE NOTICE '[init.sql] Rolle nl2sql_ro angelegt.';
    ELSE
        RAISE NOTICE '[init.sql] Rolle nl2sql_ro existiert bereits — übersprungen.';
    END IF;
END $$;

ALTER ROLE nl2sql_ro SET statement_timeout             = '30s';
ALTER ROLE nl2sql_ro SET lock_timeout                  = '5s';
ALTER ROLE nl2sql_ro SET idle_in_transaction_session_timeout = '60s';
ALTER ROLE nl2sql_ro SET default_transaction_read_only = on;

-- ── 2. Login-User für NL2SQL-Execution ────────────────────────────────────────
-- Passwort wird separat via ALTER USER gesetzt (nicht im Script hardcoded).
-- Vorgehen nach Deployment:
--   docker exec odoo_db psql -U $POSTGRES_USER \
--     -c "ALTER USER nl2sql_user PASSWORD '$NL2SQL_DB_PASSWORD';"

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nl2sql_user') THEN
        CREATE USER nl2sql_user PASSWORD 'changeme_set_via_env' IN ROLE nl2sql_ro;
        RAISE NOTICE '[init.sql] User nl2sql_user angelegt. Passwort bitte sofort ändern!';
    ELSE
        RAISE NOTICE '[init.sql] User nl2sql_user existiert bereits — übersprungen.';
    END IF;
END $$;

-- ── 3. Schema-Berechtigungen ──────────────────────────────────────────────────
-- USAGE auf Schema public: nl2sql_ro darf Objekte im Schema sehen.
-- SELECT-GRANTs: Explizite Whitelist — nur diese Tabellen sind abfragbar.
--
-- Standard-Odoo-Tabellen (immer vorhanden nach Modulinstallation):
GRANT USAGE ON SCHEMA public TO nl2sql_ro;

-- Hinweis: Die folgenden GRANTs schlagen fehl wenn die Tabellen noch nicht
-- existieren (Odoo noch nicht installiert). In diesem Fall nach der Odoo-
-- Installation erneut ausführen. Fehler werden mit NOTICE protokolliert.

DO $$
DECLARE
    tbl TEXT;
    tbls TEXT[] := ARRAY[
        -- Supply Chain / Einkauf
        'purchase_order',
        'purchase_order_line',
        -- Lager
        'stock_quant',
        'stock_location',
        'stock_move',
        'stock_picking',
        -- Partner / Produkte
        'res_partner',
        'product_product',
        'product_template',
        'product_category',
        -- Produktion (mrp)
        'mrp_production',
        'mrp_bom',
        'mrp_bom_line',
        'mrp_workcenter',
        'mrp_workorder',
        -- Qualität
        'quality_check',
        'quality_point',
        'quality_alert'
    ];
BEGIN
    FOREACH tbl IN ARRAY tbls LOOP
        IF EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'current_schema()'
               OR table_name = tbl
        ) THEN
            EXECUTE format('GRANT SELECT ON TABLE %I TO nl2sql_ro', tbl);
            RAISE NOTICE '[init.sql] GRANT SELECT ON % TO nl2sql_ro — OK', tbl;
        ELSE
            RAISE NOTICE '[init.sql] Tabelle % existiert noch nicht — GRANT übersprungen (nach Odoo-Installation erneut ausführen)', tbl;
        END IF;
    END LOOP;
END $$;

-- ── 4. Zukünftige Tabellen: Default-Privileges ────────────────────────────────
-- Damit neue Tabellen (z.B. mfg_nl2sql-Modelle) automatisch lesbar sind,
-- wenn sie vom odoo-User angelegt werden.
-- Betrifft NUR Tabellen die NACH diesem Statement angelegt werden.
ALTER DEFAULT PRIVILEGES FOR ROLE odoo IN SCHEMA public
    GRANT SELECT ON TABLES TO nl2sql_ro;

-- ── 5. SCM-Custom-Tabellen (optional, nur wenn scm_manufacturing installiert) ──
-- Auskommentiert — nach scm_manufacturing-Installation einkommentieren und
-- dieses Script erneut ausführen:
--
-- DO $$
-- DECLARE
--     tbl TEXT;
--     scm_tbls TEXT[] := ARRAY[
--         'scm_part', 'scm_part_category',
--         'scm_bom', 'scm_bom_line',
--         'scm_supplier_info',
--         'scm_purchase_order', 'scm_purchase_order_line',
--         'scm_production_order', 'scm_work_step',
--         'scm_warehouse', 'scm_delivery',
--         'scm_stock_move', 'scm_incoming_inspection'
--     ];
-- BEGIN
--     FOREACH tbl IN ARRAY scm_tbls LOOP
--         EXECUTE format('GRANT SELECT ON TABLE %I TO nl2sql_ro', tbl);
--         RAISE NOTICE '[init.sql] GRANT SELECT ON % TO nl2sql_ro — OK', tbl;
--     END LOOP;
-- END $$;
