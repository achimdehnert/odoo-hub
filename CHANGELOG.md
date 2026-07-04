# Changelog

All notable changes to odoo-hub are documented here.
Format: [Semantic Versioning](https://semver.org/) — `MAJOR.MINOR.PATCH`
Odoo module versions follow the `18.0.X.Y.Z` scheme.

---

## [Unreleased]

### Security
- **`mfg_nl2sql` (18.0.1.0.1 / 19.0.1.0.1): LLM-generated SQL in the fallback
  pipeline now runs inside a read-only PostgreSQL transaction** (NL2X-Audit
  WP1, achimdehnert/platform#913). `_execute_sql` no longer executes on the
  shared `request.env.cr` (full RW Odoo DB user); it opens a fresh registry
  cursor, issues `SET TRANSACTION READ ONLY` as the first statement plus
  `SET LOCAL statement_timeout`, and always rolls back (never commits). Any
  write that slips past the `sanitize_sql` regex blocklist is rejected by the
  database itself. The preferred aifw_service path is unchanged.
- **`allow_write` opt-out removed** from `sanitize_sql`, the controller config
  plumbing and the `res.config.settings` UI (`mfg_nl2sql.allow_write`). Write
  queries can no longer be enabled by configuration. Covered by unit tests in
  `tests/test_nl2sql_readonly.py` (v18 + v19, mock cursor — statement order,
  rollback) and addon-level `TransactionCase` tests.

### Added
- `iil_dashboard_core` — generic OWL 2 plugin-registry dashboard engine
  - `PanelErrorBoundary`: isolates crashing panels, prevents OWL-app navigation freeze
  - `IilDynamicDashboard`: subclassable feature-driven grid container
  - `getPanelComponent()` / `getPanelMeta()`: iil_panels registry resolver
  - Responsive CSS grid (1 / 2 / 3 columns at 1200 / 1800px)
- CI/CD: automatic `odoo -u` step after every deployment (no more manual module updates)
- CI/CD: explicit restart + health check after module update
- CI/CD: `workflow_dispatch`-Input `target` (choice `staging`|`prod`, Default
  `staging`) in `_deploy-odoo-hub.yml` (Retro R4, platform#913). Push auf main
  deployt weiterhin prod; manuelle Runs deployen per Default den
  Staging-v18-Stack (gleicher Host wie Prod, `docker-compose.staging.yml
  --profile v18`, Compose-Env-Datei `.env.staging` muss serverseitig gepflegt
  sein). Host, Pfad, Compose-File, Web-Service, DB und Health-Check-Domain
  werden zentral aus dem Target abgeleitet; der Prod-Traefik wird bei
  Staging-Deploys nicht angefasst.

### Changed
- `mfg_management`: `DynamicDashboard` now subclasses `IilDynamicDashboard` from core
- `mfg_management`: `panel_registry.js` delegates to `iil_dashboard_core` (re-export)
- `mfg_management`: `mfg_management.DynamicDashboard` XML template inherits from core

### Fixed
- **Critical**: OWL app navigation freeze caused by `MfgDashboard` (full action component)
  being used as panel component inside the grid — removed from `PANEL_REGISTRY_STATIC`
- **Critical**: `NL2SqlQueryBar` cross-module import in `casting_foundry` + `scm_manufacturing`
  without declaring `mfg_management` as dependency → JS bundle load error → blank dashboard
- `mrp` feature deactivated in DB (no panel registered → was causing null-component error)
- **Critical (CI, #12)**: Deploy-Workflow `_deploy-odoo-hub.yml` war als
  Workflow-File invalide — `if: ${{ secrets.SOPS_AGE_KEY != '' }}` auf
  Job-Ebene ist nicht erlaubt (secrets-Kontext dort nicht verfügbar) und
  führte zu 0s-Fails mit 0 Jobs auf jedem Push. Guard jetzt als
  Fail-Fast-Step im Job (Retro R6b, Nachtrag).
- **Critical (CI, #12, Prod-Incident 2026-07-04 17:24–17:46 UTC)**: Die
  Generierung der Compose-Env-Datei schrieb via quoted+eingerücktem Heredoc
  die `$(cat /run/secrets/…)`-Kommandos LITERAL in die Datei (Terminator
  matchte nie) → `odoo_web` crashloopte an `wait-for-psql`. Heredoc durch
  Echo-Block mit serverseitiger Evaluierung + Sanity-Checks (keine literalen
  Kommandos, Pflicht-Keys nicht leer) ersetzt (Retro R6b, Nachtrag).

---

## [1.2.0] — 2026-03-04

### Added
- `mfg_machining` module: CNC machining orders, machine management, MachiningPanel
- `MachiningPanel`: yield rate, order progress, NL2SQL query bar integration
- `DynamicDashboard`: feature-registry-driven panel grid (iil_configurator)
- `SeedEngine` (iil_configurator): realistic demo data for all modules

### Changed
- `QualityPanel`: `qc_total` now shows overall counts (all-time), monthly trend bars
- `CastingPanel`, `QualityPanel`, `MachinesPanel`, `ScmPanel`: removed `NL2SqlQueryBar`
  import (modules without `mfg_management` dependency)

### Fixed
- `casting_data.xml` UNIQUE constraint error during module update
- `ir.model.data` record reconciliation for casting demo data
- `scm.stock.move` datetime handling in SeedEngine

---

## [1.1.0] — 2026-03-02

### Added
- `mfg_management` module: unified KPI dashboard, Production Board, Machine Status, SCM Overview
- `NL2SqlQueryBar` component (mfg_management / mfg_nl2sql)
- `iil_configurator` module: setup wizard, feature registry, `iil.product.feature` model
- `ProductionBoard`, `MachineStatus`, `ScmOverview` as standalone client actions

### Fixed
- DNS: odoo.iil.pet A-Record corrected (88.198.191.108 → 46.225.127.211)
- Docker downgrade 29.2.1 → 27.5.1 (Docker 28+ breaks Traefik /v1.24/version handshake)
- `web.base.url` corrected (http://localhost:8069 → https://odoo.iil.pet)

---

## [1.0.0] — 2026-02-15

### Added
- `casting_foundry` module: foundry management (orders, machines, quality checks, defect types)
- `scm_manufacturing` module: supply chain (purchase orders, production orders, warehouse, stock)
- `mfg_nl2sql` module: NL2SQL proxy controller + aifw_service integration
- Docker Compose production stack: Traefik v3.3 + Odoo 18.0 + PostgreSQL 16
- SOPS/age secrets management
- GitHub Actions CI: lint (ruff) + addon manifest tests + Docker build
- GitHub Actions CD: deploy-on-push to production

---

[Unreleased]: https://github.com/achimdehnert/odoo-hub/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/achimdehnert/odoo-hub/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/achimdehnert/odoo-hub/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/achimdehnert/odoo-hub/releases/tag/v1.0.0
