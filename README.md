# odoo-hub

**IIL Manufacturing Cockpit** — Odoo 18 custom addons for production, supply chain, quality and machine management.

> Live: [https://odoo.iil.pet](https://odoo.iil.pet) · Odoo 18.0 · PostgreSQL 16 · Docker

---

## Modules

| Module | Version | Description |
|---|---|---|
| `iil_dashboard_core` | 18.0.1.0.0 | Generic OWL 2 plugin-registry dashboard engine (PanelErrorBoundary, IilDynamicDashboard) |
| `iil_configurator` | 18.0.1.0.0 | Setup wizard, feature registry (`iil.product.feature`), SeedEngine demo data |
| `casting_foundry` | 18.0.1.0.0 | Foundry management: orders, machines, quality checks, defect types |
| `scm_manufacturing` | 18.0.1.0.0 | Supply chain: purchase orders, production, warehouse, stock moves |
| `mfg_machining` | 18.0.1.0.0 | CNC machining orders, yield tracking |
| `mfg_management` | 18.0.1.2.0 | Unified dashboard frontend: Production Board, Machine Status, SCM Overview, KPIs |
| `mfg_nl2sql` | 18.0.1.0.0 | NL2SQL proxy + query bar (natural language → SQL via aifw_service) |
| `schutztat_reporting` | 18.0.1.0.0 | Risk assessment sync from Django risk-hub (ADR-030) |

### Module Dependency Order

```
base → web → mail → product
  → iil_dashboard_core
  → casting_foundry
  → scm_manufacturing
  → mfg_machining         (depends: iil_dashboard_core, mfg_management)
  → iil_configurator      (depends: casting_foundry)
  → mfg_management        (depends: iil_dashboard_core, casting_foundry, scm_manufacturing)
  → mfg_nl2sql            (depends: mfg_management)
```

---

## Architecture

```text
Browser (OWL 2)
  └── iil_dashboard_core:  IilDynamicDashboard + PanelErrorBoundary + iil_panels registry
        ├── CastingPanel        (casting_foundry)
        ├── MachiningPanel      (mfg_machining)
        ├── MachinesPanel       (casting_foundry)
        ├── QualityPanel        (casting_foundry)
        ├── StockPanel          (scm_manufacturing)
        └── ScmPanel            (scm_manufacturing)

JSON-RPC Controllers → PostgreSQL 16
NL2SQL Proxy → aifw_service:8001 (Docker-internal)
```

### Panel Registration Pattern

```js
// Any module registers its own panels — no changes to mfg_management needed:
registry.category("iil_panels").add("my_code", {
    component: MyPanel,
    label: "My Panel",
    sequence: 10,
});
```

---

## Deployment

- **Server:** 46.225.127.211 (Hetzner CPX32)
- **Domain:** [odoo.iil.pet](https://odoo.iil.pet)
- **Stack:** Traefik v3.3 (TLS) + Odoo 18.0 + PostgreSQL 16 + aifw_service
- **Docker:** 27.5.1 (pinned — do NOT upgrade to 28.x, breaks Traefik handshake)
- **Secrets:** SOPS + age (`secrets.enc.env`)

### First-Time Setup

```bash
# 1. Start stack
docker compose -f docker-compose.prod.yml up -d

# 2. Install all modules (first time)
docker compose -f docker-compose.prod.yml run --rm web \
  odoo -d odoo -i iil_dashboard_core,casting_foundry,scm_manufacturing,mfg_machining,iil_configurator,mfg_management,mfg_nl2sql \
  --stop-after-init

# 3. Restart
docker restart odoo_web
```

### Module Update (after code changes)

```bash
docker compose -f docker-compose.prod.yml run --rm web \
  odoo -d odoo -u iil_dashboard_core,mfg_management \
  --stop-after-init
docker restart odoo_web
```

> **CI/CD:** Every push to `main` triggers automatic deploy + `odoo -u` + health check via GitHub Actions.

---

## Development

```bash
# Run static tests (no Odoo runtime required)
pip install -r requirements-test.txt
pytest --tb=short -v

# Lint
pip install ruff
ruff check addons/
```

Tests validate: manifest structure, version format, license, file structure, data file references.

---

## Related

- [CHANGELOG.md](./CHANGELOG.md)
- [docs/product_description.md](./docs/product_description.md) — Product & technical description
- [ADR-030](https://github.com/achimdehnert/platform/blob/main/docs/adr/ADR-030-odoo-management-app.md)
- [risk-hub](https://github.com/achimdehnert/risk-hub)
