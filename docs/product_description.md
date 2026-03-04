# IIL Manufacturing Cockpit — Produktbeschreibung

> Version 1.1 · Stand: März 2026 · Review-Dokument für Product Manager & IT-Architekt

---

## Executive Summary

Das **IIL Manufacturing Cockpit** bringt alle operativen Fertigungsdaten in einer einzigen, kontextbewussten Oberfläche zusammen — direkt im bestehenden Odoo 18 ERP, ohne paralleles System, ohne Datensynchronisation, ohne zusätzlichen Server.

**Für den Nutzer:** Ein Bildschirm mit allen Entscheidungsgrundlagen — Aufträge, Maschinen, Qualität, Lager, Lieferkette — in Echtzeit, mit Trendvergleich zum Vormonat und optionalem KI-Assistenten für natürlichsprachliche Abfragen.

**Für das Unternehmen:** Kein neues Tool-Silo. Das Cockpit ist eine native Odoo-Erweiterung — Security, Authentifizierung, Datenhaltung und Updates laufen vollständig über die bestehende ERP-Infrastruktur. Total Cost of Ownership: nahezu null zusätzlicher Betriebsaufwand.

**Für die IT:** Loose-Coupled Modularchitektur. Jede Produktionsvertikale (Gießerei, CNC, SCM) aktiviert ihre Panels eigenständig via Plugin-Registry. Neue Module erweitern das Dashboard ohne Änderung am Kern.

---

## Teil A — Produktbeschreibung (Business / User)

### Was ist das IIL Manufacturing Cockpit?

Das **IIL Manufacturing Cockpit** ist ein integriertes Operations-Dashboard für produzierende Unternehmen, das alle relevanten Fertigungs-, Maschinen- und Lieferkettendaten in einer einzigen Oberfläche bündelt. Es ist als Erweiterung (Add-on) für **Odoo 18** realisiert und fügt sich nahtlos in die bestehende ERP-Umgebung ein.

Kernanspruch: **Ein Bildschirm — alle Entscheidungsgrundlagen.** Schichtleiter, Produktionsleiter und Supply-Chain-Manager sehen auf einen Blick, was läuft, was stockt und wo Handlungsbedarf besteht — ohne zwischen verschiedenen Menüs, Berichten oder Systemen wechseln zu müssen.

---

### Für wen ist es?

| Rolle | Nutzen |
|---|---|
| **Schichtleiter / Produktionsleiter** | Live-Überblick über laufende Gieß- und Fertigungsaufträge, Maschinenzustand, Ausschussraten |
| **Supply-Chain-Manager** | Offene Bestellungen, überfällige Lieferungen, Lagerbestand auf einen Blick |
| **Qualitätsbeauftragte** | Prüfquoten, Fehlerarten, Trend-Verlauf über mehrere Monate |
| **Werksleitung / Management** | Konsolidierte KPIs über alle Bereiche, historische Trendlinien |
| **IT / Operations** | Konfigurierbare Modul-Aktivierung per Wizard, kein Custom-Code nötig |

---

### Die 6 Dashboard-Panels

#### 1. Gießerei-Panel (Casting)
Zeigt alle aktiven Gießaufträge nach Status (Entwurf → Bestätigt → In Fertigung → QS-Prüfung → Fertig), aktuelle Ausschussraten im Vergleich zum Vormonat sowie den Maschinenauslastungsgrad. Farbkodierte Trendpfeile zeigen auf einen Blick ob die Qualität besser oder schlechter wird.

#### 2. Werkzeugmaschinen-Panel (Machining)
CNC-Fertigungsaufträge mit Fortschrittsbalken (produzierte vs. geplante Menge), Yield-Rate je Auftrag und integrierter KI-Abfrageleiste für natürlichsprachliche Analysen ("Zeige alle CNC-Aufträge mit Yield unter 80%").

#### 3. Maschinenpark-Panel (Machines)
Echtzeit-Status aller Maschinen (In Betrieb / Wartung / Störung / Stillgelegt), filterbar nach Maschinentyp und Halle. Verfügbarkeitsprozent als Top-KPI mit Ampel-Farbgebung.

#### 4. Qualitätssicherungs-Panel (Quality)
Prüfbestehensrate gesamt und monatlich, Anzahl bestandener / nicht bestandener Prüfungen, Top-Fehlerarten nach Häufigkeit und Schweregrad, monatliche Trendbalken der letzten 6 Monate.

#### 5. Lager-Panel (Stock)
Lagerbestandsgesundheit (% der Positionen mit ausreichendem Bestand), Warenbestandswert je Lagertyp (Rohstoff, WIP, Fertigware), Bewegungs-Trendlinie der letzten 6 Monate.

#### 6. Supply-Chain-Panel (SCM)
Offene Bestellungen mit Fälligkeitsstatus, aktive Fertigungsaufträge im SCM, überfällige Lieferungen (Ampel-Alert), Top-5-Lieferanten nach Bestellvolumen.

---

### Zusatzfunktion: KI-Assistent (NL2SQL)

Im Machining-Panel ist ein **natürlichsprachlicher Abfrage-Assistent** integriert. Nutzer können Fragen in normalem Deutsch stellen — das System übersetzt sie in Datenbankabfragen und gibt strukturierte Antworten zurück. Gesprächsverlauf wird für Follow-up-Fragen gespeichert.

Beispielfragen:
- *"Wie viele CNC-Aufträge sind diese Woche fällig?"*
- *"Zeige Ausschussrate nach Legierung im letzten Quartal"*
- *"Welche Maschinen hatten in den letzten 30 Tagen eine Störung?"*

---

### Konfiguration ohne IT-Aufwand: IIL-Konfigurator

Über einen geführten **Setup-Wizard** wählt der Administrator einmalig aus, welche Produktionsbereiche im Unternehmen aktiv sind (Gießerei, CNC, SCM, etc.). Das Dashboard zeigt dann nur die relevanten Panels — ohne dass Code angepasst werden muss.

---

### Was ist es nicht?

- Kein Ersatz für die operativen Odoo-Module (Aufträge werden weiterhin in den Standard-Odoo-Formularen erfasst)
- Kein eigenständiges System — es setzt eine laufende Odoo 18 Instanz voraus
- Kein BI-Tool / Reporting-System (kein Drilldown-Export, keine Ad-hoc-Berichte)

---

---

## Teil B — Technische Beschreibung (IT-Architekt)

### Systemarchitektur

```
┌─────────────────────────────────────────────────────────────────┐
│                        Odoo 18 (Python 3.12)                    │
│                                                                 │
│  ┌──────────────────┐  ┌─────────────────┐  ┌───────────────┐  │
│  │  casting_foundry │  │ scm_manufacturing│  │ mfg_machining │  │
│  │  (Domain-Model)  │  │  (Domain-Model) │  │ (Domain-Model)│  │
│  └────────┬─────────┘  └────────┬────────┘  └───────┬───────┘  │
│           │                     │                   │          │
│           └──────────┬──────────┘                   │          │
│                      │                              │          │
│           ┌──────────▼──────────────────────────────▼───────┐  │
│           │              mfg_management                      │  │
│           │  JSON-RPC Controllers · OWL Frontend Components  │  │
│           │  ir.actions.client · Asset Bundle                │  │
│           └───────────────────────┬───────────────────────┘   │
│                                   │                            │
│           ┌───────────────────────▼───────────────────────┐   │
│           │              iil_configurator                  │   │
│           │  Setup-Wizard · Feature-Registry · SeedEngine  │   │
│           └───────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
         │ HTTP/JSON-RPC                   │ HTTP/JSON
         ▼                                ▼
   Browser (OWL 2)               aifw_service:8001
   Asset Bundle                  (NL2SQL Microservice)
```

---

### Modul-Übersicht

| Modul | Typ | Funktion |
|---|---|---|
| `casting_foundry` | Domain | Modelle für Gießaufträge, Maschinen, Qualitätsprüfungen, Defekttypen |
| `scm_manufacturing` | Domain | Modelle für SCM-Fertigungsaufträge, Einkauf, Lieferungen, Lager, Teile |
| `mfg_machining` | Domain | Modelle für CNC-Werkzeugmaschinen und Bearbeitungsaufträge |
| `mfg_management` | Frontend | OWL-Dashboard, JSON-RPC-Controller, Menüs, Client-Actions |
| `iil_configurator` | Config | Wizard, Feature-Registry, Demo-Datengenerator (SeedEngine) |
| `mfg_nl2sql` | AI | NL2SQL-Proxy-Controller und Query-Bar-Komponente |

---

### Frontend-Architektur (OWL 2 / Odoo 18)

**Component-Hierarchie:**

```
ir.actions.client (tag: mfg_management.Dashboard)
  └── DynamicDashboard           ← Feature-Registry-gesteuert
        ├── CastingPanel         (casting_foundry, iil_panels registry)
        ├── MachiningPanel       (mfg_machining, iil_panels registry)
        ├── MachinesPanel        (casting_foundry, iil_panels registry)
        ├── QualityPanel         (casting_foundry, iil_panels registry)
        ├── StockPanel           (scm_manufacturing, iil_panels registry)
        └── ScmPanel             (scm_manufacturing, iil_panels registry)

ir.actions.client (tag: mfg_management.ProductionBoard)
  └── ProductionBoard            ← eigenständige Action

ir.actions.client (tag: mfg_management.MachineStatus)
  └── MachineStatus              ← eigenständige Action

ir.actions.client (tag: mfg_management.ScmOverview)
  └── ScmOverview                ← eigenständige Action
```

**Panel-Registry-Pattern:**

Jedes Domain-Modul registriert seine Panels selbst in der `iil_panels` OWL-Registry:
```js
registry.category("iil_panels").add("casting", {
    component: CastingPanel,
    label: "Gießerei",
    sequence: 10,
});
```

`DynamicDashboard` liest die aktiven Features via ORM-Call (`iil.product.feature.get_active_features`) und rendert nur die konfigurierten Panels. Fallback auf statischen `MfgDashboard` wenn `iil_configurator` nicht installiert.

---

### Backend — JSON-RPC Controller-Routen

| Route | Modul | Rückgabe |
|---|---|---|
| `POST /casting_foundry/kpis` | casting_foundry | Auftrags-States, Maschinen-States, QC-Rate, Ausschuss |
| `POST /casting_foundry/quality_kpis` | casting_foundry | QC-Gesamt/Monat, Trend (6M), Top-Defekte |
| `POST /casting_foundry/machines_kpis` | casting_foundry | Maschinen-Liste, Verfügbarkeit, Maschinenauslastung |
| `POST /scm_manufacturing/kpis` | scm_manufacturing | Fertigungsaufträge, Einkauf, Lieferungen, Lager-KPIs |
| `POST /scm_manufacturing/stock_kpis` | scm_manufacturing | Lagergesundheit, Bestandswert, Bewegungs-Trend |
| `POST /mfg_management/production_board` | mfg_management | Gieß- + SCM-Aufträge (live, nicht done/cancelled) |
| `POST /mfg_management/machine_status` | mfg_management | Alle aktiven Maschinen mit Status |
| `POST /mfg_management/scm_overview` | mfg_management | Offene Bestellungen, Lieferungen, Lager |
| `POST /mfg_management/nl2sql` | mfg_management | Proxy → aifw_service NL2SQL Microservice |

Alle Routen: `type="json"`, `auth="user"` — keine anonymen Zugriffe.

---

### Datenmodell-Übersicht (Kernentitäten)

```
casting.order          1──n  casting.order.line
casting.machine        1──n  casting.order (machine_id)
casting.quality.check  n──1  casting.order
casting.defect.type    n──n  casting.quality.check

scm.production.order   n──1  scm.part
scm.purchase.order     n──1  res.partner (Lieferant)
scm.delivery           n──1  res.partner
scm.warehouse          1──n  scm.stock.move
scm.part               1──n  scm.stock.move

mfg.machining.order    n──1  mfg.machine
mfg.machine            (eigenständig)
```

---

### NL2SQL-Integration

**Datenfluss:**
```
Browser (NL2SqlQueryBar)
  → POST /mfg_management/nl2sql  {query, source_code, conversation_history}
  → aifw_service:8001/nl2sql/query  (Docker-internes Netz)
  → PostgreSQL (nl2sql_ro READ-ONLY Role)
  → Antwort zurück an Browser
```

- Der Odoo-Controller ist ein reiner **HTTP-Proxy** (urllib, kein Requests-Dependency)
- `aifw_service` URL konfigurierbar via `ir.config_parameter` (`mfg_management.aifw_service_url`)
- DB-Zugriff durch `nl2sql_ro` Role (Read-Only, definiert in `docker/db/init.sql`)
- Timeout: 45s, Fehler werden graceful als UI-Message zurückgegeben

---

### Deployment

**Stack:** Docker Compose (Traefik v3.3 → Odoo 18.0 → PostgreSQL 16)

```yaml
# docker-compose.prod.yml (vereinfacht)
services:
  traefik:   # Reverse Proxy + TLS (Let's Encrypt)
  web:       # odoo:18.0  → Port 8069 intern
  db:        # postgres:16
  aifw_service:  # NL2SQL Microservice (Port 8001)
```

**Modul-Installationsreihenfolge:**
```
base → mail → product
  → casting_foundry
  → scm_manufacturing
  → mfg_machining
  → iil_configurator
  → mfg_management
  → mfg_nl2sql
```

**Asset-Bundle:** `web.assets_backend` — alle JS/XML-Dateien werden von Odoo zu einem minifizierten Bundle kompiliert. Bundle-Hash ändert sich bei jedem Modul-Update automatisch.

---

### Bekannte Constraints / Design-Entscheidungen

| Entscheidung | Begründung |
|---|---|
| `casting_foundry` hat **keine** Dependency auf `mfg_management` | Verhindert zirkuläre Dependencies. `NL2SqlQueryBar` nur in `mfg_machining` (hat explizite Dep.) |
| Panels registrieren sich selbst via `iil_panels` Registry | Lose Kopplung — neue Module können Panels hinzufügen ohne `mfg_management` zu ändern |
| JSON-RPC (type="json") statt REST | Odoo-Standard, automatische Session-Authentifizierung |
| `nl2sql_ro` Read-Only DB-Role | Security — NL2SQL kann keine Daten schreiben oder löschen |
| `iil_configurator` SeedEngine | Realistische Demo-Daten für alle Module ohne manuelle Eingabe |

---

### Sicherheit

- Alle API-Routen: `auth="user"` — nur authentifizierte Odoo-Sessions
- NL2SQL-DB-Zugriff: Read-Only Role (`nl2sql_ro`)
- Kein direkter Datenbankzugriff vom Browser
- TLS: Let's Encrypt via Traefik, auto-renewal
- Odoo-Standard-RBAC: Menüs und Aktionen über `ir.model.access` gesteuert

---

*Dokument erstellt für Review durch Product Manager und IT-Architekt.*
*Feedback bitte direkt in diesem Dokument oder als GitHub-Issue unter achimdehnert/odoo-hub.*
