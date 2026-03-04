# IIL Manufacturing Cockpit — Lean ERP Extension
### Positionierung für Werksleitung & Management (CFO-Perspektive)

> Version 1.0 · Stand: März 2026

---

## Das Kernargument in einem Satz

Das IIL Manufacturing Cockpit erweitert das bereits bezahlte Odoo-ERP um ein vollständiges Operations-Dashboard — ohne zweites System, ohne Datenmigration, ohne zusätzliche Lizenzkosten.

---

## Das Problem mit klassischen Dashboard-Lösungen

Unternehmen, die operative Transparenz wollen, stehen typischerweise vor dieser Wahl:

| Option | Problem |
|---|---|
| **BI-Tool** (Power BI, Tableau) | Zweites System, Datensynchronisation nötig, Lizenzkosten pro User, IT-Aufwand für Konnektoren |
| **ERP-Standardberichte** | Statisch, kein Echtzeit-Überblick, einzelne Module nicht übergreifend |
| **Custom-Development** | Hohe Entwicklungskosten, schlechte Wartbarkeit, Odoo-Updates brechen Custom-Code |
| **Spreadsheet-Reporting** | Manuell, fehleranfällig, immer veraltet |

**Das Cockpit ist keine dieser Optionen.** Es ist eine native ERP-Erweiterung, die exakt dort ansetzt wo Odoo aufhört: am übergreifenden Echtzeit-Überblick über alle Produktionsbereiche.

---

## Total Cost of Ownership

### Was es **nicht** braucht:

- ❌ Keinen zusätzlichen Server
- ❌ Keine zweite Datenbank
- ❌ Keinen Daten-Sync-Job (ETL, Scheduler)
- ❌ Keine separaten User-Lizenzen
- ❌ Kein externes BI-Tool
- ❌ Kein Schulungsaufwand für neue Software (läuft in Odoo, sieht aus wie Odoo)

### Was es braucht:

- ✅ Laufende Odoo 18 Instanz (bereits vorhanden)
- ✅ Einmalige Modul-Installation (~30 Min. IT-Aufwand)
- ✅ Einmalige Konfiguration via Setup-Wizard (~10 Min. durch Admin)
- ✅ Optional: KI-Assistent (`aifw_service` Docker-Container, nur wenn NL2SQL gewünscht)

### Laufende Betriebskosten:

| Posten | Aufwand |
|---|---|
| Odoo-Module-Updates | Automatisch mit Odoo-Update-Zyklus (`odoo -u`) |
| Security-Patches | Über Odoo-Standard-Patches abgedeckt |
| User-Management | Über Odoo-RBAC — kein separates System |
| Monitoring | Odoo-Server-Logs decken alle Fehler ab |

**Fazit TCO:** Der dominierende Kostentreiber ist die bereits vorhandene Odoo-Infrastruktur. Das Cockpit selbst verursacht keinen messbaren Mehraufwand im Betrieb.

---

## Wertstiftung nach Bereich

### Produktionsleitung
- Schichtübergaben ohne manuelle Statusberichte: Alle Aufträge, alle Maschinen, aktueller Stand immer sichtbar
- Ausschuss- und Qualitätstrends über Monate vergleichbar — Eingriff bevor Reklamationen kommen
- Maschinenausfälle sichtbar bevor sie Folgeaufträge blockieren

### Supply Chain
- Überfällige Bestellungen sofort erkennbar (Ampel-Logik, kein manuelles Suchen)
- Lagerbestandsgesundheit auf einen Blick — rechtzeitig nachbestellen statt Produktionsstopp
- Lieferanten-Performance ohne Report-Erstellung sichtbar

### Qualitätssicherung
- Prüfbestehensrate im Monatsvergleich — Verschlechterung früh erkennen
- Top-Fehlerarten und Schweregrade ohne Datenbankabfrage abrufbar
- KI-Assistent ermöglicht Ad-hoc-Analysen ("Zeige alle Prüfungen unter 80% im letzten Quartal")

### IT / Operations
- Ein Deployment, ein Update-Zyklus, eine Nutzerverwaltung
- Keine Daten verlassen das ERP-System (kein externer BI-Connector)
- Neue Produktionsmodule (z. B. neue Fertigung) erweiterbar ohne Cockpit-Umbau

---

## Abgrenzung: Was das Cockpit nicht ist

Das Cockpit ist **kein Ersatz** für:
- Detaillierte Auftragsbearbeitung (läuft weiterhin in Odoo-Formularen)
- Finanzkennzahlen / Controlling (kein P&L, kein Cost-Center-Reporting)
- Langfristige Produktionsplanung / MRP
- Regulatorisches Reporting / Compliance-Dokumentation

Es ist die **Brücke** zwischen dem operativen ERP-Tagesbetrieb und dem Management-Überblick — ohne drittes System dazwischen.

---

## Entscheidungsmatrix: Cockpit vs. Alternativen

| Kriterium | IIL Cockpit | Power BI / Tableau | Custom Dev | ERP-Berichte |
|---|---|---|---|---|
| **Time-to-Live** | Stunden | Wochen–Monate | Monate | Sofort (aber statisch) |
| **Echtzeit-Daten** | ✅ | ⚠️ (Sync nötig) | ✅ | ❌ |
| **Lizenzkosten** | In Odoo enthalten | Pro-User-Lizenz | Einmalig hoch | In Odoo enthalten |
| **Wartungsaufwand** | Niedrig (Odoo-Update) | Mittel (Konnektoren) | Hoch (Custom-Code) | Niedrig |
| **Erweiterbarkeit** | Plugin-Registry | Neue Berichte | Neuentwicklung | Begrenzt |
| **User-Training** | Minimal (Odoo-Known) | Mittel | Minimal | Minimal |
| **KI-Integration** | Optional (NL2SQL) | Separat/teuer | Aufwändig | Nein |

---

## Empfehlung

Für Unternehmen, die bereits Odoo nutzen, ist das IIL Manufacturing Cockpit die **kosteneffizienteste Route** zu operativer Echtzeit-Transparenz über alle Produktionsbereiche. Es vermeidet Tool-Proliferation, nutzt bestehende Infrastruktur und Investitionen und ist in Stunden statt Monaten produktiv.

---

*Für technische Details: siehe `product_description.md` Teil B (IT-Architekt).*
*Für Nutzerperspektive: siehe `product_description.md` Teil A (Business / User).*
