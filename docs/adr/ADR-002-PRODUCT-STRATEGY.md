# ADR-002: Produktstrategie & Implementierungsvorschlag
## Odoo ERP + NL2SQL als Managed-Service-Produkt für den Mittelstand

| Feld | Wert |
|------|------|
| **Datum** | 2026-03-03 |
| **Reviewer** | Cascade — IT-Architekt & Produktmanager Perspektive |
| **Eingaben** | `odoo_produktvorschlag.docx`, `odoo_flyer_mittelstand.html`, `ADR-001-REVIEW.md` |
| **Status** | **AKTUALISIERT** — ergänzt durch ADR-005-KONFIGURATOR.md (2026-03-03) |
| **Entscheidungsträger** | Achim Dehnert |

---

## 0. Executive Summary

Der Produktvorschlag ist **strategisch richtig positioniert** — Odoo im Mittelstand ist ein
echter Product-Market-Fit. Die Marketingaussagen (ROI < 5 Monate, SAP-Vergleich, Referenzen)
sind branchenüblich und vertretbar.

**Die kritische Lücke:** Das Dokument behandelt Odoo als Standard-ERP-Implementierung.
Das Differenzierungsmerkmal — der NL2SQL-KI-Layer aus `mfg_nl2sql` / `aifw.nl2sql` — 
wird **nicht erwähnt**. Das ist entweder ein Marketingfehler oder ein Zeichen, dass
die Produktstrategie noch nicht geklärt ist.

**Empfehlung:** Zwei klar getrennte Produkte definieren, dann konsequent durchziehen.

> **Update 2026-03-03 (ADR-005):** Der Produktkonfigurator (`iil_configurator`) ist als
> Kernprodukt bestätigt. Er transformiert das Geschäftsmodell von Dienstleistung zu
> skalierbarlem Software-Produkt. Zweite Vertikale (Werkzeugmaschinen, `mfg_machining`)
> ist entschieden. Siehe ADR-005-KONFIGURATOR.md für vollständige Architektur.

---

## 1. Bewertung des Produktvorschlags

### 1.1 Stärken (aus Produktmanager-Sicht)

**Marktpositionierung**
- Zielgruppe 10–200 Mitarbeiter, Produktionsbetriebe: richtig gewählt — SAP B1 ist hier
  überdimensioniert, Lexware/Sage zu limitiert. Odoo trifft den Sweet Spot.
- Preisvergleich €19,90 vs. €108–250/User: korrekt und überzeugend.
- ROI-Kalkulation ist konservativ und damit glaubwürdig (nicht aufgebläht).
- Die drei Referenzprojekte (Lebensmittel, Kunststoff, Metallbau) decken die wichtigsten
  Branchen ab — gut gewählt.

**Implementierungsansatz**
- 4-Phasen-Modell mit Hypercare ist Industriestandard und seriös.
- Festpreisversprechen differenziert vom Markt (die meisten Implementierer arbeiten T&M).
- 6–12 Wochen sind realistisch für den beschriebenen Scope.

**Fehlende Stärke: KI-Differenzierung**
Der NL2SQL-Layer (`mfg_nl2sql`) ist ein echter USP, der **kein Wettbewerber** in diesem
Preissegment hat. Dass er im Produktvorschlag fehlt, verschenkt das stärkste
Verkaufsargument.

---

### 1.2 Schwächen & Risiken (aus IT-Architekten-Sicht)

#### Risiko 1: Stack-Inkonsistenz — KRITISCH

Das Dokument verkauft "Odoo Enterprise", aber der technische Stack enthält:
- `mfg_nl2sql` — Odoo 18 OWL-Modul ✅
- `aifw.nl2sql` — **Django**-Package, inkompatibel mit Odoo WSGI/gevent ❌
- `casting_foundry` — Odoo 18 Addon ✅

Die geplante Integration `asyncio.run(engine.ask(...))` aus einem Odoo-Controller
**wird in Production crashen** (gevent-Event-Loop-Konflikt, siehe ADR-001-REVIEW C2).

**Impact:** Der KI-Layer ist der USP — wenn er nicht funktioniert, ist das Produkt
eine Standard-Odoo-Implementierung ohne Differenzierung.

#### Risiko 2: Security — NL2SQL läuft als Odoo-Superuser

Aktuell kein Read-Only-Datenbankbenutzer für NL2SQL-Queries. Ein LLM kann
beliebige SELECT-Statements generieren — ohne DB-seitige Einschränkung ist das
ein erhebliches Datenrisiko (full table scans, JOINs über alle Tabellen).

#### Risiko 3: Produktreife vs. Verkaufsversprechen

Das Dokument nennt ROI-Zahlen ("18% Umsatzwachstum", "Liefertreue 71%→94%") aus
Referenzprojekten. Das impliziert, das Produkt ist production-ready. Die aktuelle
Codebase hat 4 kritische und 6 hohe Befunde (ADR-001-REVIEW). Dieser Gap muss
geschlossen werden bevor der erste zahlende Kunde ongeboardet wird.

#### Risiko 4: Hosting-Modell unklar

Das Dokument nennt "Odoo.sh" (€150/Monat) als Hosting-Option — aber die Infrastruktur
in `docker-compose.prod.yml` läuft auf eigenem Hetzner-Server. Das ist ein Widerspruch:
Odoo.sh unterstützt keine Custom-Docker-Addons wie `aifw_service`. Eigenes Hosting ist
die einzig viable Option für den KI-Layer.

---

### 1.3 Markt-Assessment: Was fehlt im Wettbewerbsvergleich

Die Vergleichstabelle (Odoo vs. SAP B1 vs. D365 BC vs. NetSuite) ist korrekt aber
**defensiv** — sie positioniert Odoo als "billiger als SAP". Das ist nicht genug für
eine Differenzierungsstrategie.

**Fehlendes Kriterium: KI/NL2SQL**

| Kriterium | Odoo + mfg_nl2sql | SAP B1 | D365 BC | NetSuite |
|-----------|-------------------|--------|---------|----------|
| NL-Abfragen auf Produktionsdaten | **✅ Integriert** | Copilot (extra €) | Copilot (extra €) | ❌ |
| Kein SQL-Knowhow erforderlich | **✅** | ❌ | ❌ | ❌ |
| Eigene LLM-Konfiguration | **✅ Anthropic/OpenAI** | ❌ | MS-only | ❌ |
| Datensouveränität (eigenes Hosting) | **✅** | ❌ | ❌ | ❌ |

**Das** ist der echte USP. Kein Wettbewerber in diesem Preissegment bietet
Natural-Language-Queries auf Produktionsdaten out-of-the-box.

---

## 2. Produktstrategie-Entscheidung

### Option A: Standard Odoo-Implementierer (ohne KI-Layer)
Fokus auf Odoo-Rollout, Beratung, Support. Keine eigene IP.

**Bewertung:** Valides Geschäftsmodell, aber reiner Wettbewerb auf Preis/Qualität.
Commoditisiert. Hunderte Wettbewerber.

### Option B: Odoo + NL2SQL als Produkt (eigene IP)
Odoo als Plattform, `mfg_nl2sql` + `casting_foundry` als proprietary Add-on-Schicht.
Monatliche SaaS-Komponente (KI-Layer) on top der Odoo-Lizenz.

**Bewertung:** ✅ **Empfohlen.** Echter Moat. Schwer zu kopieren ohne gleiche Domänen-
und KI-Expertise. Recurring Revenue möglich.

### Option C: KI-Layer als eigenständiges SaaS (ohne Odoo-Lock-in)
`aifw.nl2sql` als universelles NL2SQL-Tool für beliebige Datenbanken.

**Bewertung:** Zu breite Plattform, zu früh. Fokus fehlt.

**Entscheidung: Option B** — Odoo + NL2SQL als vertikales Produkt für Produktionsbetriebe.

> **Update 2026-03-03:** Option B wird durch den Produktkonfigurator zur **Option B+**:
> Nicht nur KI-Layer als USP, sondern auch der Konfigurator selbst ist proprietäres IP.
> Kein Wettbewerber im deutschen Mittelstand kombiniert: Branchenvertikale + KI-Layer
> + automatischer Konfiguration + Demo-Daten-Generierung.

---

## 3. Optimaler Implementierungsvorschlag

### 3.1 Ziel-Architektur (Target State)

```
┌─────────────────────────────────────────────────────────────┐
│                    Odoo 18 (Hetzner VM)                     │
│                                                             │
│  ┌─────────────────┐  ┌──────────────────┐                 │
│  │ casting_foundry │  │  mfg_nl2sql      │                 │
│  │ (Gießerei-ERP)  │  │  (NL Dashboard)  │                 │
│  │                 │  │                  │                 │
│  │ • Auftragsverw. │  │ • OWL Dashboard  │                 │
│  │ • Qualitätsmgmt │  │ • Query History  │                 │
│  │ • Maschinenmgmt │  │ • Audit Log      │                 │
│  └────────┬────────┘  └────────┬─────────┘                 │
│           │                   │                             │
│           └──────────┬────────┘                             │
│                      ▼                                      │
│              PostgreSQL 16 (nl2sql_ro)                      │
│                      │                                      │
│                      ▼ HTTP/REST                            │
│  ┌───────────────────────────────────┐                      │
│  │        aifw_service               │                      │
│  │   (eigenständiger Django-Service) │                      │
│  │                                   │                      │
│  │  • NL→SQL Engine (Anthropic/OAI) │                      │
│  │  • Schema Registry               │                      │
│  │  • Read-Only Query Execution     │                      │
│  │  • Streaming Response            │                      │
│  └───────────────────────────────────┘                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Kern-Entscheidung:** `aifw_service` und `mfg_nl2sql` kommunizieren per **HTTP** —
kein direkter Python-Import, kein `asyncio.run()` in Odoo. Das löst C1, C2, C4
aus ADR-001-REVIEW in einem Schritt.

---

### 3.2 Implementierungsplan (5 Sprints à 2 Wochen)

> **Update 2026-03-03:** Sprint-Plan unten bleibt gültig, wird aber durch ADR-005 Abschnitt 9
> (Konfigurator-fokussierter Sprint-Plan) präzisiert und ergänzt.

#### Sprint 1 — Architektur-Fundament (Wochen 1–2)

**Ziel:** Kritische Bugs aus ADR-001-REVIEW beheben, saubere Schnittstelle definieren.

**Tasks:**

1. **`mfg_nl2sql`: Controller refactoren** — Service Layer extrahieren
   ```
   mfg_nl2sql/services/
     llm_service.py      # HTTP-Call zu aifw_service (kein asyncio!)
     sql_service.py      # Savepoint statt cr.rollback()
     chart_service.py    # chart type detection + config building
   ```

2. **`mfg_nl2sql`: Datenbankebene härten**
   - `result_data`, `result_columns`, `chart_config` → `fields.Json` (statt `fields.Text`)
   - `_sql_constraints` für `state`-Übergänge hinzufügen
   - Stille Fallbacks (`or '[]'`) durch explizites Error-Handling ersetzen

3. **`aifw_service`: REST-Endpoint definieren**
   ```
   POST /api/nl2sql/query
   Body: { "question": "...", "schema_source": "casting_foundry", "max_rows": 500 }
   Response: { "sql": "...", "columns": [...], "rows": [...], "chart_type": "..." }
   ```

4. **DB-Sicherheit: `nl2sql_ro`-Role ausbauen**
   ```sql
   -- docker/db/init.sql erweitern:
   GRANT SELECT ON TABLE
       casting_order, casting_order_line, casting_machine,
       casting_alloy, casting_mold, casting_quality_check,
       casting_defect_type, casting_material
   TO nl2sql_ro;
   ALTER ROLE nl2sql_ro SET statement_timeout = '30s';
   ALTER ROLE nl2sql_ro SET default_transaction_read_only = on;
   ```

**Akzeptanzkriterien:**
- `mfg_nl2sql` Controller < 80 Zeilen (reine Orchestrierung)
- Kein `cr.rollback()` mehr im Codebase
- `nl2sql_ro` kann `casting_*` lesen, kann nichts schreiben

---

#### Sprint 2 — aifw_service Production-Readiness (Wochen 3–4)

**Ziel:** `aifw_service` als stabilen, eigenständigen HTTP-Microservice deployen.

**Tasks:**

1. **Schema Registry für `casting_foundry`**
   ```python
   # aifw_service: casting_foundry SchemaSource in DB anlegen
   SchemaSource.objects.create(
       code='casting_foundry',
       name='Gießerei Management',
       db_alias='odoo_ro',           # Read-only Connection
       table_prefix='casting_',
       max_rows=1000,
       timeout_seconds=30,
   )
   ```

2. **Streaming-Support im aifw_service**
   - Server-Sent Events (SSE) für lange NL→SQL Generierungen
   - OWL-Component in `mfg_nl2sql` für Streaming-Anzeige

3. **Migration `0004_schemasource.py` fertigstellen**
   (Datei existiert bereits in `aifw/migrations/`, Status prüfen)

4. **`docker-compose.prod.yml`: aifw_service absichern**
   ```yaml
   aifw_service:
     networks:
       - internal        # nur intern erreichbar, kein direkter Internet-Zugang
     environment:
       - ALLOWED_HOSTS=odoo_web  # nur Odoo-Container darf anfragen
   ```

5. **Health-Check-Endpoint**
   ```
   GET /api/health → { "status": "ok", "schema_sources": ["casting_foundry"], "llm": "anthropic" }
   ```

**Akzeptanzkriterien:**
- `aifw_service` antwortet auf NL2SQL-Queries < 8s (p95)
- Odoo kann `aifw_service` per HTTP erreichen, Außenwelt nicht
- Migration läuft durch ohne Fehler

---

#### Sprint 3 — NL2SQL Dashboard UX (Wochen 5–6)

**Ziel:** `mfg_nl2sql` Dashboard zu einem echten Verkaufsargument machen.

**Tasks:**

1. **Dashboard-Tiles für `casting_foundry` Use Cases**
   ```
   Tile 1: "Ausschuss-Trend letzter 6 Monate" (Line Chart)
   Tile 2: "Top-5 Defekttypen" (Bar Chart)
   Tile 3: "Maschinenauslastung aktuell" (Gauge/Heatmap)
   Tile 4: "Offene Aufträge nach Priorität" (KPI Cards)
   Tile 5: "Liefertermintreue letzter 3 Monate" (Line Chart)
   ```

2. **Natural Language Examples im UI**
   - Autocomplete-Vorschläge basierend auf `casting_foundry`-Schema
   - Beispiel-Queries im Onboarding-Dialog

3. **Export-Funktion**
   - Query-Ergebnis → Excel-Download
   - Query-Ergebnis → PDF-Bericht (Odoo Report Engine)

4. **Audit Log vervollständigen**
   - Wer hat was wann gefragt
   - Welches SQL wurde generiert und ausgeführt
   - Ergebnis-Zeilenanzahl + Ausführungszeit

**Akzeptanzkriterien:**
- 5 Demo-Tiles funktionieren mit realen `casting_foundry`-Daten
- Jede Frage produziert korrektes SQL (Testmatrix: 20 Use-Case-Queries)
- Export funktioniert für Tabellen und Charts

---

#### Sprint 4 — Mandantenfähigkeit & Produktisierung (Wochen 7–8)

**Ziel:** Das Produkt für mehrere Kunden (Mandanten) vorbereiten.

**Tasks:**

1. **Multi-Tenant Schema Sources**
   ```python
   # Jeder Kunde hat eigene SchemaSource mit eigenem db_alias
   # aifw_service routet basierend auf API-Key → SchemaSource
   SchemaSource.objects.create(
       code='kunde_a_casting',
       db_alias='kunde_a_db',
       api_key=secrets.token_urlsafe(32),  # pro Mandant
       ...
   )
   ```

2. **Lizenzmodell implementieren**
   ```
   Tier 1 (Starter):    50 NL2SQL-Queries/Monat, max 500 Rows, 1 Dashboard
   Tier 2 (Professional): 500 Queries/Monat, max 2000 Rows, 5 Dashboards
   Tier 3 (Enterprise): Unlimited, Custom Schema, Priority LLM
   ```
   - Query-Counter in `nl2sql.query.history` (bereits vorhanden)
   - Scheduled Action: monatlicher Reset + Billing-Event

3. **Onboarding-Wizard**
   ```
   Schritt 1: LLM-Provider wählen (Anthropic / OpenAI / Azure OpenAI)
   Schritt 2: API-Key eingeben + Test-Query ausführen
   Schritt 3: Schema-Tabellen aktivieren/deaktivieren
   Schritt 4: Erste Demo-Tile anlegen
   ```

4. **Dokumentation**
   - User-Guide (PDF, automatisch aus Odoo generiert)
   - Admin-Guide (Hosting, API-Key-Rotation)
   - Release Notes Template

**Akzeptanzkriterien:**
- 2 separate Mandanten laufen auf einer Instanz ohne Datenleck
- Onboarding dauert < 30 Minuten für neuen Kunden
- Query-Limit wird korrekt enforced

---

#### Sprint 5 — Production Hardening & GTM (Wochen 9–10)

**Ziel:** Production-Ready, Monitoring, Go-to-Market-Material.

**Tasks:**

1. **Monitoring & Alerting**
   ```yaml
   # docker-compose.prod.yml ergänzen:
   prometheus:
     image: prom/prometheus:latest
   grafana:
     image: grafana/grafana:latest
   ```
   - Alert: `aifw_service` down → PagerDuty/Slack
   - Alert: LLM-API-Error-Rate > 5%
   - Alert: Query-Ausführungszeit > 25s (near-timeout)

2. **Backup-Strategie**
   ```bash
   # Täglicher pg_dump via Cron:
   docker exec odoo_db pg_dump -U odoo -Fc odoo > /backups/odoo_$(date +%Y%m%d).dump
   # Retention: 7 Tage lokal, 30 Tage S3
   ```

3. **Security Audit**
   - Penetrationstest der NL2SQL-Endpoints (SQL-Injection via LLM-Output)
   - API-Key-Rotation-Prozess dokumentieren
   - DSGVO-Konformität: Keine Kundendaten an LLM senden (nur Schema-Metadaten)

4. **GTM-Material aktualisieren**
   - `odoo_produktvorschlag.docx` überarbeiten: NL2SQL als USP prominent einbauen
   - `odoo_flyer_mittelstand.html`: KI-Sektion hinzufügen
   - Demo-Video: NL2SQL live auf `casting_foundry`-Daten (mit Seed-Daten aus `seed_nl2sql_demo.sql`)

5. **Pricing finalisieren**
   ```
   Odoo Enterprise Lizenz:    €29,90/User/Monat  (wie im Dokument)
   NL2SQL Add-on Starter:     + €149/Monat       (neu)
   NL2SQL Add-on Professional:+ €349/Monat       (neu)
   NL2SQL Add-on Enterprise:  auf Anfrage        (neu)
   ```

**Akzeptanzkriterien:**
- Uptime > 99.5% über 2 Wochen Hypercare
- Alle kritischen und hohen Befunde aus ADR-001-REVIEW geschlossen
- Demo mit echten `casting_foundry`-Daten funktioniert für 20 Test-Queries

---

## 4. Technische Schulden — Priorisierte Abarbeitungsliste

Aus ADR-001-REVIEW, sortiert nach Business Impact:

| Prio | Befund | Sprint | Aufwand |
|------|--------|--------|---------|
| 🔴 | `cr.rollback()` → Savepoint (C1) | 1 | 2h |
| 🔴 | `asyncio.run()` → HTTP-Call (C2/C4) | 1 | 4h |
| 🔴 | `statement_timeout` via `nl2sql_ro` Role (C3) | 1 | 1h |
| 🟡 | `fields.Text` → `fields.Json` (H1) | 1 | 3h |
| 🟡 | Stille Fallbacks entfernen (H2) | 1 | 2h |
| 🟡 | Service Layer extrahieren (H3) | 1 | 6h |
| 🟡 | Eine `__manifest__.py` (H4) | 1 | 1h |
| 🟡 | `nl2sql_ro` GRANT für casting_* (H6) | 1 | 1h |
| 🟠 | `_sql_constraints` state transitions (M1) | 2 | 2h |
| 🟠 | `_rec_name = 'display_name'` fix (M2) | 2 | 1h |
| 🟠 | Django Migration `0004_schemasource` (M3) | 2 | 2h |

**Sprint 1 Gesamtaufwand: ~20h** — alle Blocker für Production beseitigt.

---

## 5. Produktmarketing — Was geändert werden muss

### 5.1 `odoo_produktvorschlag.docx` — Überarbeitungen

**Hinzufügen: Modul 6 — KI-gestützte Produktionsanalyse**
```
Modul 6: KI-Analyse & Natural Language Reporting (NEU)
▸ Stellen Sie Fragen in natürlicher Sprache — erhalten Sie sofort Datenanalysen
▸ "Welche Maschine hatte letzten Monat den höchsten Ausschuss?" → Chart in 3 Sekunden
▸ Kein SQL-Knowhow erforderlich — funktioniert für Geschäftsführung und Shopfloor
▸ Kompatibel mit Anthropic Claude und OpenAI GPT-4
▸ Datensouveränität: Ihre Daten verlassen nie Ihren Server
▸ Audit-Log: Jede Anfrage wird protokolliert (DSGVO-konform)
```

**Wettbewerbsvergleich erweitern:**
KI/NL2SQL als zusätzliches Kriterium — einziger Anbieter mit nativer Integration.

**ROI-Berechnung ergänzen:**
```
Zeitersparnis Reporting (4h/Woche Analyst → 30min mit NL2SQL):
3,5h × €55/h × 48 Wochen = €9.240/Jahr zusätzlich
```

### 5.2 Neue Seite: "Wie KI Ihre Produktion analysiert"

Demo-Szenario mit `casting_foundry` Seed-Daten:
- Screenshot: Frage eingeben "Welche Legierung hatte Q3 2025 den höchsten Ausschuss?"
- Screenshot: SQL wird generiert und ausgeführt (transparent)
- Screenshot: Chart erscheint automatisch

Das ist überzeugender als jede Feature-Liste.

---

## 6. Entscheidungspunkte (Action Items)

| # | Entscheidung | Owner | Deadline |
|---|--------------|-------|----------|
| D1 | Option B (Odoo + NL2SQL Produkt) bestätigen | Achim | sofort |
| D2 | LLM-Provider-Strategie: Anthropic (claude-3-5-sonnet) als Default? | Achim | Sprint 1 |
| D3 | Hosting-Modell: eigener Hetzner-Server (nicht Odoo.sh) bestätigen | Achim | Sprint 1 |
| D4 | Pricing-Modell NL2SQL Add-on: €149/€349/Enterprise? | Achim | Sprint 4 |
| D5 | Erster Pilot-Kunde definieren (Gießerei-Branche empfohlen wegen `casting_foundry`) | Achim | Sprint 3 |
| D6 | DSGVO-Check: Welche Kundendaten gehen an Anthropic/OpenAI? | Achim + Datenschutz | Sprint 2 |
| **D7** | **Konfigurator als eigenständiges Addon `iil_configurator`** | **✅ ENTSCHIEDEN (ADR-005)** | — |
| **D8** | **Zweite Vertikale: Werkzeugmaschinen (`mfg_machining`)** | **✅ ENTSCHIEDEN (ADR-005)** | — |
| **D9** | **Demo-Daten-Generierung als Pflichtbestandteil des Wizards** | **✅ ENTSCHIEDEN (ADR-005)** | — |

---

## 7. Fazit

Der Produktvorschlag ist **solide als Odoo-Implementierungsangebot**, aber er verschenkt
den stärksten USP: den NL2SQL-KI-Layer.

Die Architektur hat lösbare Probleme — alle kritischen Bugs können in Sprint 1 (~20h)
geschlossen werden. Danach ist der Stack production-ready.

**Die Reihenfolge stimmt:** Seed-Daten (erledigt), Bugs fixen (Sprint 1), dann verkaufen.

Der optimale nächste Schritt ist **nicht** ein weiteres Marketing-Dokument — es ist
die Entscheidung D1 und dann Sprint 1 starten.

---

*Dieses Dokument ersetzt nicht ADR-001-REVIEW, sondern baut darauf auf.*
*Stand: 2026-03-03. Ergänzt durch ADR-005-KONFIGURATOR.md (2026-03-03).*
*Für vollständige Konfigurator-Architektur, D7/D8/D9 und aktualisierten Sprint-Plan: siehe ADR-005.*
