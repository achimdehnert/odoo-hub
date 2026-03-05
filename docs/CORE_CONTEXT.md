# CORE_CONTEXT — odoo-hub
> Pflichtlektüre für jeden Coding Agent, Contributor und Reviewer.

## 1. Projekt-Identität
| Attribut | Wert |
|---|---|
| Repo | achimdehnert/odoo-hub |
| Produkt | Lean ERP / Odoo-Integration Hub — Django Service für ERP-Funktionen |
| Zweck | ERP-Kernfunktionen als tenant-fähiger Django Service |

## 2. Tech Stack
| Schicht | Technologie | Version |
|---|---|---|
| Backend | Django | 5.x |
| DB | PostgreSQL | — |
| Integration | Odoo API | — |
| Deployment | Docker + Hetzner | — |

## 3. Dokumentation
- docs/product_description.md — vollständige Produktbeschreibung
- docs/product_description_lean_erp.md — Lean ERP Variante
- docs/adr/ — Architecture Decision Records

## 4. Architektur-Regeln (NON-NEGOTIABLE)
```
views.py → services.py → models.py
- Views: nur HTTP. Services: Businesslogik. Models: datenzentriert.
- Zero Breaking Changes. Tests: test_should_*. BigAutoField immer.
- Templates: templates/<app>/ (nicht per-app)
- Secrets: nur via decouple.config()
```

## 5. Verbotene Muster
| Verboten | Korrekt |
|---|---|
| Businesslogik in views.py | services.py |
| UUID als PK | BigAutoField |
| Hard-coded Secrets | decouple.config() |
