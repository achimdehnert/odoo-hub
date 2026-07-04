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
- Tests: v18/v19-Paritäts-Guard für `mfg_nl2sql`
  (`tests/test_nl2sql_v18_v19_parity.py`, 43 Tests — Retro R8/F-E5,
  platform#913). Die geplante Konsolidierung auf EINE Quelle wurde geprüft
  und mit Beleg verworfen: die Divergenz umfasst nicht nur die 6
  Route-Typ-Zeilen (`type='json'` vs. `type='jsonrpc'`), sondern auch
  Manifest (Version + data-Liste), `security/security.xml`
  (ir.module.category-Restrukturierung), die v19-only
  `security/module_category.xml` und 4 View-XMLs (`<group expand>` in
  Odoo 19 entfernt); zudem mountet jeder Container nur seinen eigenen
  Addons-Baum (kein Cross-Tree-Import zur Laufzeit). Der Guard läuft im
  bestehenden CI-pytest-Job und wird rot bei jeder Divergenz, die über die
  dokumentierten Odoo-19-Transformationen hinausgeht (bekannte
  XML-Divergenzen SHA-256-gepinnt).

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
