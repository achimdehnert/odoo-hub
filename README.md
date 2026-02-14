# odoo-hub

Odoo 18 custom addons hub — Management & Reporting apps.

Part of the **Dual-Framework Governance** strategy (ADR-030):
Django for existing 7+ apps, Odoo for management/reporting/backoffice.

## Architecture

```text
odoo-hub/
├── addons/
│   └── schutztat_reporting/   # Risk assessment sync (ADR-030)
│       ├── models/            # Assessment, Hazard, ActionItem, SyncLog
│       ├── views/             # List/Form XML views + menus
│       ├── security/          # ACL (user=read, manager=full)
│       └── data/              # Cron jobs (15 min sync)
├── docs/
│   └── images/                # Mermaid ER diagrams
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

### Planned: scm_manufacturing

Supply Chain Management module — see `docs/images/scm-overview.mer` for ER diagram.

## Deployment

- **Server:** 46.225.127.211 (Hetzner CPX32, 8 GB)
- **Domain:** schutztat.iil.pet
- **Registry:** ghcr.io/achimdehnert/odoo-hub:latest
- **Stack:** Odoo 18.0 + PostgreSQL 16 + Nginx

## Quick Start

```bash
# Build & run locally
docker compose -f docker-compose.prod.yml up -d

# Deploy to production
bash deployment/scripts/deploy-remote.sh
```

## Related

- [ADR-030](https://github.com/achimdehnert/platform/blob/main/docs/adr/ADR-030-odoo-management-app.md)
- [risk-hub](https://github.com/achimdehnert/risk-hub)
