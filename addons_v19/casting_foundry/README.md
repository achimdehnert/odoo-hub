# Casting & Foundry Management — Odoo 18 Community

Gießerei-Management-Modul für Odoo 18 mit integriertem Bulk-Testdatengenerator.

## Modulstruktur

```
casting_foundry/
├── __manifest__.py
├── __init__.py
├── models/                         # 8 Domänenmodelle
│   ├── casting_material.py         # Grundwerkstoffe (AL, GG, CU, ...)
│   ├── casting_alloy.py            # Legierungen (AlSi9Cu3, EN-GJS-400, ...)
│   ├── casting_mold.py             # Gussformen mit Lebensdauer-Tracking
│   ├── casting_machine.py          # Maschinen & Anlagen
│   ├── casting_order.py            # Gießaufträge mit Workflow
│   ├── casting_order_line.py       # Auftragspositionen
│   ├── casting_quality_check.py    # Qualitätsprüfungen (9 Prüfarten)
│   └── casting_defect_type.py      # Fehlerarten-Katalog
├── populate/                       # 🔥 Bulk-Datengeneratoren
│   ├── populate_material.py        # 15 Werkstoffe
│   ├── populate_alloy.py           # 60 Legierungen mit mech. Eigenschaften
│   ├── populate_mold.py            # 80 Gussformen
│   ├── populate_machine.py         # 40 Maschinen
│   └── populate_order.py           # 500 Aufträge, 1200 Positionen, 800 QS-Prüfungen
├── views/                          # List, Form, Pivot, Graph Views
├── security/                       # Gruppen + ACL
├── data/                           # Sequenzen + Stamm-Fehlerarten
└── demo/                           # Kleine Demo-Daten (DB mit Demo-Flag)
```

## Installation auf dem Hetzner-Server

### 1. Modul auf den Server kopieren

```bash
# Vom lokalen Rechner:
scp -r casting_foundry/ root@46.225.127.211:/opt/odoo/addons/

# Oder per Git (empfohlen):
ssh root@46.225.127.211
cd /opt/odoo/addons
git clone <your-repo> casting_foundry
```

### 2. Odoo-Addons-Pfad prüfen

In `odoo.conf` muss der Pfad enthalten sein:
```ini
addons_path = /mnt/extra-addons,/opt/odoo/addons
```

### 3. Modul installieren

```bash
# Via Docker:
docker exec -it odoo_web odoo -d <db_name> -i casting_foundry --stop-after-init

# Oder im Odoo UI:
# Apps → Filter "Apps" entfernen → "casting" suchen → Installieren
```

## 🔥 Bulk-Testdaten generieren (das Herzstück)

### Via CLI (empfohlen)

```bash
# Medium: ~500 Aufträge, ~1200 Positionen, ~800 QS-Prüfungen
docker exec -it odoo_web odoo-bin populate \
    --models casting.material,casting.alloy,casting.machine,casting.mold,casting.defect.type,casting.order,casting.order.line,casting.quality.check \
    --size medium \
    -d <db_name>
```

### Größen

| Size   | Werkstoffe | Legierungen | Formen | Maschinen | Aufträge | Positionen | QS-Prüfungen |
|--------|-----------|-------------|--------|-----------|----------|------------|---------------|
| small  | 8         | 20          | 15     | 10        | 30       | 60         | 40            |
| medium | 15        | 60          | 80     | 40        | 500      | 1.200      | 800           |
| large  | 30        | 150         | 300    | 100       | 3.000    | 8.000      | 5.000         |

### Einzelne Modelle nachgenerieren

```bash
# Nur Aufträge + Positionen:
docker exec -it odoo_web odoo-bin populate \
    --models casting.order,casting.order.line \
    --size large \
    -d <db_name>
```

## Domänenmodell

```
casting.material (Werkstoff)
  └── casting.alloy (Legierung)
        └── casting.order.line (Auftragsposition)
              ├── casting.mold (Gussform)
              └── casting.machine (Maschine)

casting.order (Gießauftrag)
  ├── casting.order.line (Positionen)
  └── casting.quality.check (Prüfungen)
        └── casting.defect.type (Fehlerarten)
```

## Gießauftrag-Workflow

```
Entwurf → Bestätigt → In Fertigung → Qualitätsprüfung → Abgeschlossen
                                                        ↘ Storniert
```

## Technische Details

- **Odoo 18 Community** kompatibel
- **Python 3.12+**
- Abhängigkeiten: `base`, `mail`, `product`
- Alle Felder mit deutschen Bezeichnungen
- Pivot + Graph Views für Auftragsdaten
- Sequences: `GA-2026-00001` (Aufträge), `QC-2026-00001` (Prüfungen)
