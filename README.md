# odoo-hub

Odoo 18 custom addons hub — Management & Reporting apps.

Part of the **Dual-Framework Governance** strategy (ADR-030):
Django for existing 7+ apps, Odoo for management/reporting/backoffice.

## Architecture

```text
odoo-hub/
├── addons/
│   ├── schutztat_reporting/   # Risk assessment sync (ADR-030)
│   ├── casting_foundry/       # Foundry management (33 files)
│   └── scm_manufacturing/     # Supply chain & production (25 files)
├── docs/
│   ├── images/                # Mermaid ER diagrams
│   └── testdaten/
│       ├── casting_foundry/   # Module source + populate scripts
│       └── csv/               # Static CSV test data (8 files)
├── docker/
│   └── app/Dockerfile         # Odoo 18 + custom addons
├── docker-compose.prod.yml    # Production stack
├── requirements.txt           # Python deps for custom modules
└── .github/workflows/         # CI/CD
```

## Modules

### schutztat_reporting (v18.0.1.0.0)

Syncs risk assessment data from Django **risk-hub** via REST API:

| Odoo Model | Django Source | Sync |
|------------|-------------|------|
| `schutztat.assessment` | `/api/v1/risk/assessments` | 15 min |
| `schutztat.hazard` | `/api/v1/risk/hazards` | 15 min |
| `schutztat.action.item` | `/api/v1/actions` | 15 min |
| `schutztat.sync.log` | — | local |

### casting_foundry (v18.0.1.0.0)

Foundry management with quality control:

- **8 models:** Material, Alloy, Mold, Machine, Order, OrderLine, QualityCheck, DefectType
- **Populate scripts:** Bulk data generation (small/medium/large)
- **Workflow:** Draft → Confirmed → In Production → Quality Check → Done

### scm_manufacturing (v18.0.1.0.0)

Supply chain management (based on `docs/images/scm-overview.mer`):

- **11 models:** Part, PartCategory, BOM, BOMLine, SupplierInfo, PurchaseOrder, PurchaseLine, ProductionOrder, WorkStep, Warehouse, StockMove, Delivery, IncomingInspection
- **Workflows:** Purchase (Draft→Sent→Confirmed→Received→Done), Production (Draft→Confirmed→InProgress→Done), Delivery (Draft→Ready→Shipped→Delivered)

## Deployment

- **Server:** 88.198.191.108 (Hetzner)
- **Domain:** [odoo.iil.pet](https://odoo.iil.pet)
- **Landing:** Static HTML at `/var/www/odoo.iil.pet/`
- **SSL:** Let's Encrypt (auto-renew)
- **Stack:** Odoo 18.0 + PostgreSQL 16 + Nginx reverse proxy
- **Containers:** `odoo_web` (port 127.0.0.1:8069), `odoo_db`

## Quick Start

```bash
# Build & run (first time: init DB with -i base)
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml run --rm web \
  odoo --config=/etc/odoo/odoo.conf --workers=0 -d odoo -i base --stop-after-init
docker compose -f docker-compose.prod.yml up -d

# Install custom modules
docker compose -f docker-compose.prod.yml run --rm web \
  odoo --config=/etc/odoo/odoo.conf --workers=0 -d odoo \
  -i casting_foundry,scm_manufacturing,schutztat_reporting --stop-after-init
```

## Related

- [ADR-030](https://github.com/achimdehnert/platform/blob/main/docs/adr/ADR-030-odoo-management-app.md)
- [risk-hub](https://github.com/achimdehnert/risk-hub)
- [iil.pet Portal](https://iil.pet) — Odoo Hub listed as app
