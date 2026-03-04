# ADR-007: IIL-Package-Architektur — Implementierungsort für Funktionen

**Status:** Aktiv  
**Datum:** 2026-03-04  
**Autoren:** IIL Engineering

---

## Kontext

Das odoo-hub-System besteht aus mehreren spezialisierten Odoo-Addons (iil-Packages), die jeweils einen fachlichen Bereich abdecken. Im Laufe der Entwicklung entstand die Gefahr, dass Logik und Funktionen direkt in übergeordnete Module (z.B. `mfg_management`) implementiert werden, anstatt in den zuständigen Fach-Addons zu verbleiben.

---

## Entscheidung

**Funktionen werden durch iil-Packages realisiert.**

Jede neue Funktion gehört in das Addon, das für den fachlichen Bereich zuständig ist. Übergeordnete Module wie `mfg_management` sind **Integrations- und Präsentationsschichten**, keine Implementierungsorte für Fachlogik.

---

## Zuständigkeiten der iil-Packages

| Addon | Fachbereich | Zuständig für |
|---|---|---|
| `casting_foundry` | Gießerei | Gießaufträge, Maschinen, Qualität, Formen, Legierungen |
| `mfg_machining` | CNC-Fertigung | Fertigungsaufträge, Maschinen, Maschinenauslastung |
| `scm_manufacturing` | Supply Chain | Einkauf, Lager, Teile, Lieferungen, BOM |
| `mfg_nl2sql` | KI-Analyse | NL2SQL-Service, Schema-Metadaten, Query-History |
| `iil_configurator` | Produktkonfigurator | Produktfeatures, Wizard, Seed-Engine |
| `iil_dashboard_core` | Dashboard-Framework | Panel-Registry, Basis-Komponenten |
| `mfg_management` | **Cockpit-Integration** | Nur: Dashboard-Routing, Panel-Grid, Cross-Modul-KPIs |

---

## Regeln

### ✅ Korrekt

```
casting_foundry/
  static/src/js/casting_panel.js    ← Gießerei-Panel im Gießerei-Addon
  controllers/casting_controller.py ← Gießerei-KPIs im Gießerei-Addon
  models/casting_order.py           ← Geschäftslogik im Fach-Addon
```

```
mfg_management/
  static/src/js/dynamic_dashboard.js  ← Nur: Panel-Grid-Rendering
  controllers/main.py                 ← Nur: Cross-Modul-KPI-Aggregation
```

### ❌ Verboten

```
# Gießerei-Logik in mfg_management implementieren
mfg_management/
  static/src/js/casting_logic.js    ← FALSCH: gehört in casting_foundry
  models/casting_helper.py          ← FALSCH: gehört in casting_foundry
```

---

## Genehmigte Ausnahmen

Insellösungen in fremden Modulen sind **nur im genehmigten Ausnahmefall** erlaubt und müssen explizit dokumentiert werden.

### Aktuelle Ausnahmen

| Datei | Normaler Ort | Ausnahme-Grund | Genehmigt |
|---|---|---|---|
| `mfg_management/static/src/js/nl2sql_panel.js` | `mfg_nl2sql` | Odoo 18 Cross-Module-JS-Imports nicht möglich ohne explizite Asset-Abhängigkeiten; `mfg_management` bereits im Bundle | 2026-03-04 |

### Ausnahme-Kriterien

Eine Insellösung ist genehmigungsfähig wenn:
1. **Technische Notwendigkeit**: Framework-Einschränkung verhindert korrekte Platzierung
2. **Temporär**: Ein Migrations-Pfad zum korrekten Ort ist definiert
3. **Dokumentiert**: Eintrag in dieser Tabelle mit Datum und Grund

---

## Migrationspfad für aktuelle Ausnahmen

### `nl2sql_panel.js` → `mfg_nl2sql`

Sobald `mfg_nl2sql` in `mfg_management/__manifest__.py` als Dependency eingetragen und dessen Assets im Backend-Bundle verfügbar sind:

```python
# mfg_management/__manifest__.py
"depends": [
    ...
    "mfg_nl2sql",   # dann möglich
],
```

Dann:
1. `nl2sql_panel.js` + `nl2sql_panel.xml` nach `mfg_nl2sql/static/src/` verschieben
2. Aus `mfg_management/__manifest__.py` Assets-Liste entfernen
3. `mfg_nl2sql/__manifest__.py` Assets-Liste ergänzen

---

## Konsequenzen

### Positiv
- Klare Ownership: jedes Addon verantwortet seinen Bereich vollständig
- Einfachere Wartung: Änderungen an Gießerei-Logik nur in `casting_foundry`
- Bessere Testbarkeit: Fach-Addons können isoliert getestet werden
- Modulare Installation: Addons können unabhängig aktiviert/deaktiviert werden

### Negativ / zu beachten
- Odoo 18 Bundle-Einschränkungen erfordern manchmal Asset-Abhängigkeiten explizit zu definieren
- Bei neuen Panels: `__manifest__.py` des Ziel-Addons muss JS + XML in `web.assets_backend` listen

---

## Verwandte ADRs

- **ADR-006**: OWL 2 JS-Import-Einschränkungen (technischer Grund für `nl2sql`-Ausnahme)
- **ADR-005**: IIL-Konfigurator-Architektur (Feature-Registry als Steuerungsschicht)
