# Produktmodul-Liste — odoo-hub Produktstrategie

| Feld | Wert |
|------|------|
| **Datum** | 2026-03-03 |
| **Basis** | ADR-001 bis ADR-005, bestätigte Entscheidungen D1/D3/D6/D7/D8/D9 |
| **Produkt** | Odoo 18 + Produktkonfigurator + NL2SQL KI-Layer für Produktionsbetriebe |
| **Stack** | Odoo 18, PostgreSQL 16, Docker, Hetzner CPX32 |

---

## Legende

| Symbol | Bedeutung |
|--------|-----------|
| ✅ | Vorhanden, production-ready |
| 🔧 | Vorhanden, bugfix/refactoring erforderlich (ADR-004) |
| 🚧 | In Entwicklung / Sprint-Backlog |
| ❌ | Fehlt, muss neu erstellt werden |

---

## Schicht 1 — Odoo-Addons (im Repo `addons/`)

### MOD-01 · `casting_foundry` ✅
**Typ:** Odoo 18 Application Addon  
**Status:** Installiert auf Production (https://odoo.iil.pet)  
**Zweck:** Vertikallösung Gießerei-Management

**Enthält:**
- `casting_material` — Rohstoffe (Aluminium, Stahl, etc.)
- `casting_alloy` — Legierungen mit Materialeigenschaften
- `casting_machine` — Maschinenpark (Druckguss, Schmelzofen, etc.)
- `casting_mold` — Werkzeuge/Formen
- `casting_order` + `casting_order_line` — Produktionsaufträge
- `casting_quality_check` — Qualitätsprüfungen
- `casting_defect_type` — Defekttypen-Katalog
- Sicherheitsrollen: Manager, User

**Offene Aufgaben:** keine (Bugfixes in `init.sql` ADR-004/H3 betreffen nur GRANTs)

---

### MOD-02 · `mfg_nl2sql` 🔧
**Typ:** Odoo 18 Application Addon  
**Status:** Installiert auf Production, **4 kritische Bugs (ADR-004)**  
**Zweck:** NL2SQL Dashboard — natürlichsprachliche Queries auf Produktionsdaten

**Enthält:**
- `nl2sql.query.history` — Abfrageverlauf mit State-Machine
- `nl2sql.saved.query` — Wiederverwendbare Abfragen als Dashboard-Tiles
- `nl2sql.schema.table` / `nl2sql.schema.column` — Schema-Whitelist (Security-Boundary)
- `nl2sql.dashboard.config` — Pro-User-Dashboard-Konfiguration
- OWL-Frontend: Dashboard, Query-Input, Chart, Table, KPI-Cards
- REST-Endpoints: `/mfg_nl2sql/query`, `/dashboard_data`, `/history`, `/schema`

**Kritische Bugs (Sprint 1, ADR-004):**
- C1: `cr.rollback()` → Savepoint
- C2: SQL f-String → `psycopg2.sql`
- C3: `fields.Text` → `fields.Json` + `_sql_constraints`
- C4: `SET LOCAL statement_timeout` ohne garantiertes `BEGIN`
- H4: Stille `or '[]'`-Fallbacks entfernen

---

### MOD-03 · `mfg_management` ✅
**Typ:** Odoo 18 Application Addon  
**Status:** Installiert auf Production  
**Zweck:** Cross-Modul Cockpit (Kanban Board, Maschinenübersicht, SCM-Übersicht)  
**Depends:** `casting_foundry` + `scm_manufacturing`

**Enthält:**
- Production Kanban Board (casting + scm)
- Machine Status Board (Live-Zustand)
- SCM Overview (Einkauf, Lieferung, Lager-KPIs)
- Unified KPI Tiles

**Offene Aufgaben:** keine bekannten Bugs

---

### MOD-04a · `iil_configurator` 🚧
**Typ:** Odoo 18 Application Addon — **Kernprodukt (ADR-005/D7)**
**Status:** Neu zu erstellen (Sprint 2+3)
**Zweck:** Produktkonfigurator — Feature-Registry, Demo-Daten-Generator, Onboarding-Wizard

**Enthält:**
- `iil.product.feature` — Feature-Registry: code, is_active, sequence, config (JSON)
- `iil.seed.engine` — Demo-Daten-Generator: branchenspezifisch, parametrisiert, idempotent
- `iil.configurator.wizard` — 5-Schritt-Fragebogen (TransientModel)
  - Schritt 1: Branche (Gießerei / Werkzeugmaschinen / Beide / Generisch)
  - Schritt 2: Prozesse (MRP, Lager, Einkauf, Qualität, Instandhaltung, Vertrieb, Buchhaltung)
  - Schritt 3: KI-Features (NL2SQL, LLM-Provider)
  - Schritt 4: Dashboard-Layout
  - Schritt 5: Demo-Daten-Generierung (Monate, Anzahl Aufträge)
- OWL-Wizard-Wrapper (mehrstufig, mit Fortschrittsanzeige)

**Offene Aufgaben (Sprint 2+3):**
- Addon-Grundgerüst erstellen
- `iil.product.feature` Model + Feature-Defaults-XML
- Wizard vollständig (alle 5 Schritte)
- Seed-Engine für Gießerei (Sprint 3)
- Seed-Engine für Werkzeugmaschinen (Sprint 4)

---

### MOD-04b · `iil_mrp` 🚧
**Typ:** Odoo 18 Addon — Erweiterung von Odoo-Standard `mrp`
**Status:** Neu zu erstellen (Sprint 2) — benötigt `mrp` auf Prod installiert
**Zweck:** Branchenspezifische MRP-Erweiterung (Gießerei + Werkzeugmaschinen on top von Odoo-mrp)
**Depends:** `mrp`, `casting_foundry`

**Enthält:**
- `mrp.production` `_inherit`: Gießerei-Felder (alloy_id, mold_id, yield_pct)
- `mrp.workcenter` `_inherit`: Maschinentyp, Kapazität
- Odoo-Standard `mrp` liefert: BOM-Auflösung, MRP-Scheduler, Kapazitätsplanung, Shopfloor

**Offene Aufgaben:** `mrp` + `stock` auf Prod installieren, Addon erstellen

---

### MOD-04c · `iil_stock` 🚧
**Typ:** Odoo 18 Addon — Erweiterung von Odoo-Standard `stock` + `purchase`
**Status:** Neu zu erstellen (Sprint 2) — benötigt `stock` auf Prod installiert
**Zweck:** Branchenspezifische Lager-/Einkaufserweiterung
**Depends:** `stock`, `purchase`, `casting_foundry`

**Enthält:**
- `stock.move` `_inherit`: casting_material_id, alloy_grade
- `stock.quant` `_inherit`: Gießerei-Materialfelder
- Odoo-Standard `stock` liefert: Mehrlager, Chargen/Serien, FIFO/FEFO, Barcode

**Offene Aufgaben:** Addon erstellen, Schema-Metadaten für `mfg_nl2sql` ergänzen

---

### MOD-04d · `mfg_machining` 🚧
**Typ:** Odoo 18 Application Addon — **Zweite Branchenvertikale (ADR-005/D8)**
**Status:** Neu zu erstellen (Sprint 3+4)
**Zweck:** Werkzeugmaschinen/CNC-Vertikale — analog `casting_foundry`-Pattern (~70% Reuse)
**Depends:** `iil_mrp`, `product`

**Enthält (Ziel Sprint 4):**
- `machining_material` — Werkstoffe (Stahl, Aluminium, Titan)
- `machining_tool` — Werkzeuge: Fräser, Wendeplatten, Bohrer
- `machining_fixture` — Spannmittel
- `machining_nc_program` — NC-Programme: Maschine, Material, Revision
- `machining_machine` — CNC-Maschinen: Typ (Drehen/Fräsen), Achsen
- `machining_order` + `machining_order_operation` — Fertigungsaufträge mit Arbeitsplänen
- `machining_quality_check` — Maßprotokoll: Soll/Ist/Toleranz
- `machining_defect_type` — Fehlertypen: Maßabweichung, Rauheit, Riss
- `machining_setup_sheet` — Rüstblatt

**Offene Aufgaben (Sprint 3 Grundgerüst, Sprint 4 vollständig):**
- Models nach `casting_foundry`-Pattern erstellen
- Demo-Daten-Generator in `iil_seed_engine`
- NL2SQL-Schema-Metadaten

---

### MOD-04 · `scm_manufacturing` ⚠️ MIGRATION GEPLANT
**Typ:** Odoo 18 Application Addon  
**Status:** Im Repo, eigenständige Models (kein `mrp`/`stock` Odoo-Standard, `depends: [base, mail]`)  
**Zweck:** Supply Chain Management (Teile, Stücklisten, Einkauf, Lieferung)

**Enthält:**
- `scm_part`, `scm_bom`, `scm_bom_line`
- `scm_purchase_order`, `scm_production_order`
- `scm_warehouse`, `scm_delivery`

**Migrationsstrategie (Sprint 3):**
Schrittweise Ablösung durch `iil_mrp` + `iil_stock` (`_inherit` auf Odoo-Standard).
Eigenständige Models werden durch Odoo-Standard-Models ersetzt.
Gießerei-spezifische Felder wandern als `_inherit`-Erweiterungen in `iil_mrp`/`iil_stock`.

**Offene Aufgaben:** Migrationsskript, Schema-Metadaten vor Migration anlegen

---

### MOD-05 · `schutztat_reporting` 🚧
**Typ:** Odoo 18 Addon  
**Status:** Im Repo, nicht in Produkt-Kernpfad  
**Zweck:** Unklar — separates Reporting-Modul  
**Entscheidung erforderlich:** In Produktstrategie aufnehmen oder als eigenständiges Projekt behandeln?

---

## Schicht 2 — Django-Microservices (eigenständige Container)

### MOD-06 · `aifw_service` 🔧
**Typ:** Django-Microservice (Docker-Container `aifw_service`)  
**Status:** Container vorhanden auf Production, Code unter `/home/dehnert/github/aifw/`  
**Zweck:** LLM-Backbone — NL→SQL-Engine, Schema-Registry, Query-Execution via `nl2sql_user`

**Enthält (Ziel-Zustand per ADR-003/A1):**
- `POST /api/nl2sql/query` — NL→SQL + Execute + Chart-Detect
- `GET /api/health` — Health-Check
- `SchemaSource` Model (Django ORM, PostgreSQL)
- `SQLGenerator` — sync LLM-Call via `aifw.sync_completion()`
- `SQLValidator` — Blocklist + Read-Only-Enforcement
- `SQLExecutor` — Execution via `nl2sql_user` (READ ONLY, 30s timeout)
- `ResultFormatter` — Spaltentyp-Mapping, Serialisierung

**Kritische offene Aufgaben:**
- `aifw.nl2sql`-Subpackage in `iil-aifw` v0.6.0 implementieren (ADR-001-DECISIONS/F2)
- Migration `0004_schemasource.py` fertigstellen (Datei existiert, Status prüfen)
- REST-Endpoint implementieren (derzeit nur intern als Django-Package)
- Nur intern erreichbar (`networks: internal`, kein Traefik-Routing)

---

### MOD-07 · `iil-aifw` (Python Package) 🔧
**Typ:** PyPI-Package (`iil-aifw`), aktuell v0.5.0  
**Status:** `.whl` gebaut, `src/aifw/` im Repo **leer** (ADR-001-DECISIONS kritischer Bug)  
**Zweck:** LLM-Infrastruktur — Provider-Routing, Fallback, Budget-Tracking, Audit-Log

**Enthält (v0.5.0, aus Wheel):**
- `completion()` / `sync_completion()` / `sync_completion_with_fallback()`
- `LLMProvider`, `LLMModel`, `AIActionType`, `AIUsageLog` (Django Models)
- `AIActionType(code="nl2sql")` — DB-gesteuertes Model-Routing
- Budget-Tracking via `AIActionType.budget_per_day`

**Ziel v0.6.0 (Sprint 2):**
- `aifw.nl2sql` Subpackage: `generator.py`, `validator.py`, `executor.py`, `formatter.py`, `registry.py`
- `SchemaSource` Model mit Migration

**Kritische offene Aufgaben:**
- `src/aifw/` aus Wheel extrahieren und committen (ADR-001-DECISIONS/Sofortmaßnahme)

---

## Schicht 3 — Infrastruktur

### MOD-08 · `docker-compose.prod.yml` 🔧
**Typ:** Docker Compose Stack  
**Status:** Live auf Production (46.225.127.211, CPX32)  
**Zweck:** Gesamter Produktions-Stack

**Aktuelle Services:**
- `odoo_traefik` — Traefik v3.3, TLS via Let's Encrypt
- `odoo_web` — Odoo 18.0
- `odoo_db` — PostgreSQL 16-alpine (persistent Volume)

**Fehlende Services (Sprint 1/2):**
- `aifw_service` — Django-Microservice (intern only, ADR-003/D3)
- Optional: `ollama` — Lokales LLM für DSGVO-maximale Kunden (ADR-003/D6)

---

### MOD-09 · `docker/db/init.sql` 🔧
**Typ:** PostgreSQL-Init-Script  
**Status:** Deployed, **2 kritische Bugs (ADR-004/H2+H3)**  
**Zweck:** `nl2sql_ro`-Rolle, `nl2sql_user`, SELECT-GRANTs

**Bugs (sofort beheben, ADR-004/Patch 1):**
- `WHERE table_schema = 'current_schema()'` ist String-Literal → immer TRUE
- Falsche Tabellennamen: `casting_defect` (→ `casting_defect_type`), `casting_mold_usage` (existiert nicht)
- Fehlend: `casting_material`, `casting_defect_type_casting_quality_check_rel`

---

## Schicht 4 — Daten & Schema

### MOD-10 · Schema-Metadaten `casting_foundry` 🚧
**Typ:** Odoo Data XML (`mfg_nl2sql/data/schema_metadata.xml`)  
**Status:** Standard-Odoo-Tabellen vorhanden, **casting_foundry-Tabellen fehlen**  
**Zweck:** LLM-Prompt-Kontext — Tabellen/Spalten-Beschreibungen für NL2SQL

**Zu erstellen (Sprint 3):**
```
nl2sql.schema.table: casting_order, casting_order_line, casting_machine,
                     casting_alloy, casting_mold, casting_quality_check,
                     casting_defect_type, casting_material
nl2sql.schema.column: alle relevanten Spalten mit deutschen Beschreibungen
                      + Beispiel-Queries je Tabelle
```

---

### MOD-11 · Seed-Daten `seed_nl2sql_demo.sql` ✅
**Typ:** SQL-Script (`scripts/seed_nl2sql_demo.sql`)  
**Status:** Deployed auf Production, 336 Aufträge über 18 Monate  
**Zweck:** Realistische Testdaten für NL2SQL-Demo und Pilotkundenpräsentation

---

## Schicht 5 — Marketing & Dokumentation

### MOD-12 · Produktvorschlag-Dokumente 🔧
**Typ:** Verkaufsunterlagen  
**Status:** Vorhanden (`docs/adr/input/odoo_produktvorschlag.docx`, `odoo_flyer_mittelstand.html`)  
**Zweck:** Kundenakquise  
**Offene Aufgaben (Sprint 5, ADR-002/5.1):**
- NL2SQL als Modul 6 hinzufügen
- KI-Differenzierung in Wettbewerbsvergleich aufnehmen
- ROI-Kalkulation um NL2SQL-Zeitersparnis ergänzen (€9.240/Jahr)
- Demo-Screenshots mit echten `casting_foundry`-Daten

---

## Abhängigkeitsdiagramm

```
Odoo 18 CE
  mrp   stock   purchase   maintenance   sale   account
   │      │        │            │          │        │
   └──────┴────────┴────────────┴──────────┴────────┘
                       │
             ┌────────┴────────┐
             │                   │
          iil_mrp            iil_stock
        (MOD-04b)            (MOD-04c)
             │                   │
             └────────┬────────┘
                      │
      ┌─────────────┴─────────────┐
      │              │              │
casting_foundry  mfg_machining  iil_configurator
  (MOD-01)       (MOD-04d)      (MOD-04a)
  │              │              │
  │              │   Feature-Registry + Seed-Engine
  └─────────────┬─────────────┘
               │
  ┌──────────┴─────────┐
  │                      │
mfg_management          mfg_nl2sql
(MOD-03, OWL-Cockpit,   (MOD-02, KI-Layer)
dynamische Panels)       │
  │                      │ HTTP
  └──────────┬─────────┘
             │
       aifw_service (MOD-06)
      [intern, Django]
             │ nl2sql_ro (READ ONLY)
       PostgreSQL 16 (MOD-08/09)
```

---

## Sprint-Zuordnung

| Sprint | Module | Typ | Definition of Done |
|--------|--------|-----|--------------------|
| **Sprint 1** | MOD-02 (Bugs C1–C4), MOD-09 (Bugs H2+H3) | Bugfix | Kein `cr.rollback()`, kein `asyncio.run()`, `nl2sql_ro` funktioniert |
| **Sprint 2** | MOD-04a (`iil_configurator` Grundgerüst), MOD-04b (`iil_mrp`), MOD-04c (`iil_stock`), MOD-06 (REST-Endpoint), MOD-07 (v0.6.0) | Neu/Refactoring | Wizard läuft durch, OWL-Panel-Registry aktiv |
| **Sprint 3** | MOD-04a (Wizard vollständig + Seed-Engine Gießerei), MOD-04d (`mfg_machining` Grundgerüst), MOD-10 (Schema-Metadaten) | Feature + **Konfigurator-Kern** | Vollständige Gießerei-Demo < 1h ab Leer-Instanz |
| **Sprint 4** | MOD-04d (`mfg_machining` vollständig), MOD-04a (Seed-Engine Werkzeugmaschinen), MOD-06 (Multi-Tenant) | Feature | Werkzeugmaschinen-Demo < 1h ab Leer-Instanz |
| **Sprint 5** | MOD-12 (Marketing), MOD-08 (Monitoring, Backup), Self-Service-Provisionierung | GTM + Hardening | SaaS-Onboarding-Flow funktioniert |

---

## Offene Entscheidungen mit Modulbezug

| Entscheidung | Betrifft | Bis Sprint |
|---|---|---|
| D2: LLM-Default (claude-haiku vs. sonnet) | MOD-06, MOD-07 | Sprint 1 |
| D4: NL2SQL Pricing-Tier-Logik | MOD-02 (Query-Counter) | Sprint 4 |
| D5: Erster Pilot-Kunde (Gießerei?) | MOD-01, MOD-10, MOD-11 | Sprint 3 |
| MOD-05 (`schutztat_reporting`): in Produkt oder separat? | MOD-05 | offen |
| MOD-04: `scm_manufacturing` Migration-Zeitplan (Sprint 3 oder 4?) | MOD-04, MOD-04b, MOD-04c | Sprint 2 |
