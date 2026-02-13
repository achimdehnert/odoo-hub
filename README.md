# odoo-hub

Odoo 18 custom addons hub — Management & Reporting apps.

Part of the **Dual-Framework Governance** strategy (ADR-030):
Django for existing 7+ apps, Odoo for management/reporting/backoffice.

## Architecture

```
odoo-hub/
├── addons/                    # Custom Odoo modules
│   └── schutztat_reporting/   # First module (risk-hub sync)
├── docker/
│   └── app/
│       └── Dockerfile         # Odoo 18 + custom addons
├── docker-compose.prod.yml    # Production stack
├── requirements.txt           # Python deps for custom modules
└── .github/workflows/         # CI/CD
```

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
- [schutztat-reporting](https://github.com/achimdehnert/schutztat-reporting)
- [risk-hub](https://github.com/achimdehnert/risk-hub)
