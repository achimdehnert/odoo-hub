# IIL Manufacturing Cockpit — Präsentations-Outline
### Slides-Struktur für Product Manager · IT-Architekt · Management

> Version 1.0 · Stand: März 2026
> Drei Varianten: (A) Product Review · (B) IT-Architektur-Review · (C) Management-Briefing

---

## Variante A — Product Review (Product Manager)
**Ziel:** Produktverständnis, Feature-Vollständigkeit, Roadmap-Diskussion
**Dauer:** 30–45 Min · 12 Slides

---

### Slide 1 — Titel
**IIL Manufacturing Cockpit**
*Operational Intelligence. Nativ im ERP.*
> Subline: Odoo 18 Add-on · 6 Panels · KI-Assistent · Konfigurierbar ohne Code

---

### Slide 2 — Das Problem (1/2)
**"Wie viele Systeme braucht es, um zu wissen was in der Fabrik passiert?"**

- Aufträge: Odoo Produktion
- Maschinen: Excel / Whiteboard
- Qualität: Separate QS-Software oder Odoo-Berichte
- Lager: Odoo Lager-Modul, aber kein Überblick
- Lieferkette: ERP + Mail + Telefon

*Visualisierung: 5 Blasen, keine Verbindung → Frustration*

---

### Slide 3 — Das Problem (2/2)
**Was Schichtleiter wirklich wollen:**

> *"Ich will auf einen Blick sehen: Was läuft? Was brennt? Was muss ich heute entscheiden?"*

- Kein Tab-Wechsel zwischen Modulen
- Kein manuelles Zusammenstellen von Berichten
- Keine veralteten Zahlen aus Exporten

---

### Slide 4 — Die Lösung
**Ein Bildschirm. Alle Entscheidungsgrundlagen.**

*Screenshot/Mockup: DynamicDashboard mit 6 Panels*

- Echtzeit-Daten direkt aus Odoo
- Farbkodierte Trends (Vormonat-Vergleich)
- Konfigurierbar: nur aktive Produktionsbereiche sichtbar

---

### Slide 5 — Die 6 Panels (Überblick)
*Tabelle / Icon-Grid:*

| Panel | Kerninformation |
|---|---|
| 🔥 Gießerei | Auftragsfortschritt, Ausschussrate, Maschinenauslastung |
| ⚙️ CNC-Fertigung | Fertigungsaufträge, Yield-Rate, KI-Assistent |
| 🏭 Maschinenpark | Status aller Maschinen, Verfügbarkeit % |
| ✅ Qualitätssicherung | Prüfrate, Fehlerarten, 6-Monats-Trend |
| 📦 Lager | Bestandsgesundheit, Warenbestandswert, Bewegungstrend |
| 🚚 Supply Chain | Offene Bestellungen, überfällige Lieferungen, Top-Lieferanten |

---

### Slide 6 — KI-Assistent (NL2SQL)
**"Frag einfach."**

*Screenshot: NL2SqlQueryBar im Machining-Panel*

Beispiele:
- *"Alle CNC-Aufträge mit Yield unter 80% diese Woche"*
- *"Welche Lieferanten haben im letzten Quartal überfällige Bestellungen?"*
- *"Zeige Ausschussrate nach Legierung im Jahresvergleich"*

> Kein SQL nötig. Antwort in Sekunden. Folge-Fragen möglich.

---

### Slide 7 — Konfiguration (IIL-Konfigurator)
**Setup in 10 Minuten. Kein Code.**

*Screenshot: Setup-Wizard*

1. Branche / Produktionstyp auswählen
2. Aktive Module wählen (Gießerei? CNC? SCM?)
3. Dashboard zeigt nur relevante Panels

> Neue Vertikale? Neues Panel-Modul installieren → automatisch sichtbar.

---

### Slide 8 — Nutzerperspektive nach Rolle
*Persona-Karten (3 Stück):*

**Schichtleiter Klaus** — sieht in 30 Sek. ob die Schicht im Plan ist
**SCM-Managerin Sarah** — erkennt überfällige Lieferungen bevor der Produktionsstopp kommt
**Qualitätsbeauftragter Thomas** — sieht Prüftrend-Verschlechterung zwei Wochen früher

---

### Slide 9 — Was es nicht ist
**Bewusste Abgrenzung:**

- ❌ Kein BI-Tool / Reporting-Ersatz (kein Export, kein Ad-hoc-Bericht)
- ❌ Kein Ersatz für operative Odoo-Formulare
- ❌ Kein Finanz-Dashboard (kein P&L, kein Controlling)
- ✅ Die Lücke zwischen ERP-Detail und Management-Überblick

---

### Slide 10 — Deployment & Integration
**Heute läuft es auf:**
- Odoo 18 · Docker · Traefik · PostgreSQL 16
- URL: https://odoo.iil.pet
- Login: Standard Odoo-Authentifizierung

**Integrationspunkte:**
- Alle Daten kommen aus Odoo (kein Daten-Sync)
- KI-Assistent optional (eigener Microservice)

---

### Slide 11 — Roadmap (Vorschlag)
| Phase | Inhalt |
|---|---|
| **Jetzt (Live)** | 6 Panels, KI-Assistent, Konfigurator, SeedEngine |
| **Q2 2026** | Mobile-optimierte Ansicht, Push-Alerts bei Schwellwerten |
| **Q3 2026** | Historisches Reporting (Monats-/Quartalsvergleich), PDF-Export |
| **Q4 2026** | Weitere Vertikalen (z. B. Instandhaltung, HR-Schichtplanung) |

---

### Slide 12 — Open Questions / Review-Punkte
*Für die Diskussion:*

- [ ] Welche Panels sind für euren Betrieb prioritär?
- [ ] Welche KPIs fehlen in den bestehenden Panels?
- [ ] KI-Assistent: eigener Server oder SaaS-Integration (OpenAI)?
- [ ] Mobile-Anforderungen: Tablet am Shopfloor?
- [ ] Wer ist Owner für Panel-Inhalte (IT oder Fachbereich)?

---
---

## Variante B — IT-Architektur-Review
**Ziel:** Technische Validierung, Security, Skalierbarkeit, Wartbarkeit
**Dauer:** 45–60 Min · 10 Slides

---

### Slide 1 — Titel
**IIL Manufacturing Cockpit — Technische Architektur**
*Odoo 18 Native Extension · OWL 2 Frontend · Loose-Coupled Module*

---

### Slide 2 — Stack-Übersicht
*Architekturdiagramm (aus product_description.md Teil B)*

- Traefik v3.3 (TLS, Reverse Proxy)
- Odoo 18 (Python 3.12, OWL 2 Frontend)
- PostgreSQL 16
- aifw_service (NL2SQL Microservice, optional)
- Docker Compose Deployment

---

### Slide 3 — Modul-Dependency-Graph
*Visualisierung:*
```
casting_foundry ──┐
scm_manufacturing ─┼──► mfg_management ◄── mfg_machining
iil_configurator ──┘         │
                         mfg_nl2sql
```

- Keine Zirkel-Dependencies
- Klare Schichtung: Domain → Frontend → Config
- Jedes Modul unabhängig installierbar/deinstallierbar

---

### Slide 4 — Frontend-Architektur (OWL 2)
- `ir.actions.client` → OWL-Komponente (Odoo-Standard-Pattern)
- `iil_panels` Registry: lose Kopplung, kein Monolith
- Asset Bundle: Odoo-kompiliert, Cache-Busting via Hash
- Kein externes JS-Framework, kein Node.js im Betrieb

*Code-Snippet: Panel-Selbstregistrierung*

---

### Slide 5 — API-Design (JSON-RPC)
- 8 Backend-Routen, alle `type="json"`, `auth="user"`
- Keine öffentlichen Endpoints
- NL2SQL-Route: reiner HTTP-Proxy (kein direkter DB-Zugriff vom Browser)
- Read-Only DB-Role für NL2SQL (`nl2sql_ro`)

*Tabelle: alle Routen mit Rückgabe-Schema*

---

### Slide 6 — Security-Modell
- Odoo-RBAC: Standard `ir.model.access` + `ir.rule`
- TLS: Let's Encrypt, auto-renewal via Traefik
- NL2SQL: Separate Read-Only PostgreSQL-Role
- Keine externen API-Keys im Code (via `ir.config_parameter`)
- Docker: Kein privileged mode, kein host network

---

### Slide 7 — Deployment & CI
- Docker Compose (`docker-compose.prod.yml`)
- Module-Update: `odoo -u <module> --stop-after-init`
- Kein Zero-Downtime-Deployment (Odoo-Limitation)
- Git-Flow: main Branch → direkt auf Prod (rsync + docker restart)
- Offener Punkt: CI/CD-Pipeline noch nicht automatisiert

---

### Slide 8 — Skalierbarkeit & Performance
- Alle Dashboard-Daten: Odoo ORM-Queries (kein Raw SQL im Frontend)
- Kein Caching Layer (Odoo-Standard-ORM-Cache)
- Bei >1000 gleichzeitigen Nutzern: Odoo Worker-Scaling nötig
- NL2SQL-Microservice: horizontal skalierbar (zustandslos)

*Empfehlung ab 50+ gleichzeitigen Nutzern: PgBouncer (ADR-001)*

---

### Slide 9 — Bekannte Constraints & Design-Entscheidungen
*Tabelle aus product_description.md Teil B*

- Kein Zirkel: casting_foundry ohne mfg_management Dependency
- Plugin-Registry statt hardcoded Panel-Map
- HTTP-Proxy für NL2SQL (keine direkten HTTP-Requests aus OWL)
- noupdate="0" für Demo-Daten (SeedEngine-Kompatibilität)

---

### Slide 10 — Open Questions / Review-Punkte
- [ ] PgBouncer: wann nötig? (Threshold definieren)
- [ ] CI/CD: GitHub Actions für automatisiertes `odoo -u`?
- [ ] Staging-Umgebung: separate Docker-Instanz oder Odoo-Multi-DB?
- [ ] NL2SQL: aifw_service HA/Failover-Strategie?
- [ ] Monitoring: Odoo-Logs reichen oder Prometheus/Grafana?
- [ ] Backup-Strategie: PostgreSQL WAL-Archivierung dokumentiert?

---
---

## Variante C — Management-Briefing (Werksleitung / CFO)
**Ziel:** Go/No-Go-Entscheidung, TCO-Argument, Business Value
**Dauer:** 15–20 Min · 7 Slides

---

### Slide 1 — Titel
**IIL Manufacturing Cockpit**
*Operative Transparenz. Ohne zweites System.*

---

### Slide 2 — Ausgangslage
**Das kostet euch heute:**
- Schichtübergabe: 15–30 Min manueller Statusbericht
- SCM-Reaktionszeit: Überfällige Lieferung wird zu spät erkannt
- Qualitätsprobleme: Trend sichtbar erst bei Reklamation
- IT-Aufwand: Mehrere Tools, mehrere Logins, mehrere Datenquellen

---

### Slide 3 — Die Lösung in 3 Sätzen
Das IIL Manufacturing Cockpit ist eine **native Erweiterung des bereits vorhandenen Odoo-ERP**.

Es zeigt alle Fertigungs-, Maschinen- und Lieferkettendaten **in Echtzeit** auf einem Bildschirm.

**Kein neues System. Keine neuen Lizenzkosten. Kein Datenbruch.**

---

### Slide 4 — Was es zeigt
*Icon-Grid mit 6 Panels, je 1 Satz Beschreibung*
*(Visualisierung: Screenshot oder Mockup des Dashboards)*

---

### Slide 5 — TCO: Was es kostet
| Posten | Kosten |
|---|---|
| Lizenz | In Odoo enthalten |
| Zusätzlicher Server | Keiner |
| Implementierung | Einmalig ~1 Tag IT |
| Schulung | Minimal (Odoo-Oberfläche bekannt) |
| Laufender Betrieb | Kein Mehraufwand |

**Alternative Power BI / Tableau:** Lizenz + Konnektoren + Wartung + Training = vielfaches Aufwand

---

### Slide 6 — Business Value
| Bereich | Verbesserung |
|---|---|
| Schichtübergabe | Von 20 Min. auf 2 Min. |
| Reaktionszeit SCM | Überfällige Lieferung 2–5 Tage früher erkannt |
| Qualitäts-Trend | Verschlechterung 2–4 Wochen früher sichtbar |
| Maschinenverfügbarkeit | Ausfälle proaktiv planbar statt reaktiv |

---

### Slide 7 — Empfehlung
**Sofort produktiv. Keine Risiken. Kein neues System.**

- ✅ Live unter https://odoo.iil.pet
- ✅ 6 Panels, KI-Assistent aktiv
- ✅ Konfigurierbar ohne IT-Aufwand

**Nächste Schritte:**
1. Pilotbetrieb mit Schichtleitern (2 Wochen)
2. Feedback-Runde: welche Panels/KPIs fehlen?
3. Rollout auf weitere Standorte / Schichten

---

*Alle Details: `product_description.md` (Business + Technisch) und `product_description_lean_erp.md` (TCO-Analyse)*
