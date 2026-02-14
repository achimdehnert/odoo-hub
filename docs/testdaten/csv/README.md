# CSV-Testdaten — Casting & Foundry

Statische Testdaten zum Import in Odoo oder für externe Analyse.

## Dateien

| Datei | Modell | Zeilen | Beschreibung |
|-------|--------|--------|--------------|
| `materials.csv` | `casting.material` | 15 | Grundwerkstoffe (AL, GG, GGG, GS, ZN, ...) |
| `alloys.csv` | `casting.alloy` | 33 | Legierungen mit mech. Eigenschaften |
| `machines.csv` | `casting.machine` | 25 | Maschinen & Anlagen (5 Hallen) |
| `molds.csv` | `casting.mold` | 30 | Gussformen mit Lebensdauer-Tracking |
| `defect_types.csv` | `casting.defect.type` | 30 | Fehlerarten-Katalog (6 Kategorien) |
| `orders.csv` | `casting.order` | 30 | Gießaufträge (alle Workflow-Status) |
| `order_lines.csv` | `casting.order.line` | 36 | Auftragspositionen mit Prozessparametern |
| `quality_checks.csv` | `casting.quality.check` | 32 | Qualitätsprüfungen (9 Prüfarten) |

## Import in Odoo

```
Einstellungen → Technisch → Datenbank-Struktur → Import CSV
```

Reihenfolge beachten (Abhängigkeiten):

1. `materials.csv`
2. `alloys.csv` (referenziert materials)
3. `machines.csv`
4. `molds.csv` (referenziert machines)
5. `defect_types.csv`
6. `orders.csv`
7. `order_lines.csv` (referenziert orders, alloys, molds, machines)
8. `quality_checks.csv` (referenziert orders, defect_types)

## Alternativ: Bulk-Daten via Populate

Für größere Datenmengen (500+ Aufträge) die Odoo-Populate-API nutzen:

```bash
docker exec -it odoo_web odoo-bin populate \
    --models casting.material,casting.alloy,casting.machine,casting.mold,casting.defect.type,casting.order,casting.order.line,casting.quality.check \
    --size medium \
    -d <db_name>
```
