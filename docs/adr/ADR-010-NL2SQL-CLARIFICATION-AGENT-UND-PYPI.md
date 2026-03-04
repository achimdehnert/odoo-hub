# ADR-010: NL2SQL Clarification-Agent und PyPI-Erweiterungsstrategie

**Status:** Entschieden — Rev. 2 (2026-03-04, Review-Korrekturen)
**Datum:** 2026-03-04  
**Autoren:** IIL Engineering  
**Verwandte ADRs:** ADR-007 (iil-Package-Architektur), ADR-008 (Fehlerlernen), ADR-009 (Evolutionspfad), ADR-011 (Plugin-Architektur)

### Änderungshistorie

| Rev | Datum | Änderung |
|---|---|---|
| 1 | 2026-03-04 | Erstversion |
| 2 | 2026-03-04 | Review-Korrekturen: falscher Import-Pfad, fehlende `NL2SQLResult`-Felder, `system_override`-Parameter existiert nicht, Token-Kalkulationen, Tag-Pattern-Inkonsistenz, Threshold-Logik konsolidiert, domänenspezifischer Prompt entkoppelt |

---

## 1. Clarification-Agent

### Kontext

Ambige NL2SQL-Anfragen wie „Wie läuft es?" oder „Was ist kritisch?" führen zu:
- Willkürlicher Tabellenauswahl durch das LLM
- Falschen oder irreführenden SQL-Ergebnissen
- Schlechter UX weil Ergebnis nicht der Erwartung entspricht

Bisher hat der Agent keine Möglichkeit Unsicherheit zu signalisieren — er generiert immer SQL,
auch wenn die Frage keine ausreichend konkreten Entitäten enthält.

### Entscheidung: Zweistufige Ausführung

```
Eingehende Frage
      ↓
[Stufe 1: Clarity-Check]  ← leichter LLM-Call (~50 Token)
      ↓
is_ambiguous?
  JA  → clarification_options zurückgeben → User wählt → Frage anreichern → Stufe 2
  NEIN → direkt weiter zu
      ↓
[Stufe 2: SQL-Generierung]  ← bestehender Engine-Flow
```

### Ambiguity-Kriterien

Eine Frage gilt als **ambig** wenn:
- Keine konkreten Entitäten (Maschinenname, Auftragsnummer, Datum, Lieferant)
- Pronomen ohne Anker: „diese", „die", „davon" — ohne Gesprächsverlauf
- Allgemeine Status-Fragen: „Wie läuft es?", „Was ist los?", „Übersicht?"
- Mehrere Domänen gleichwertig plausibel (Produktion + Qualität + SCM)

Eine Frage gilt als **eindeutig** wenn:
- Konkretes Feld oder Wert genannt: „Ausschuss über 5%", „Auftrag GA-2024-001"
- Explizite Tabellen-Referenz: „Maschinen", „Einkaufsbestellungen"
- Zahlenfilter, Datumsbereiche, Namen

### Voraussetzung: `NL2SQLResult` erweitern

Vor der Implementierung muss `aifw/nl2sql/results.py` um Clarification-Felder erweitert
werden. Das ist eine **non-breaking additive Änderung** (alle neuen Felder haben Defaults):

```python
# aifw/nl2sql/results.py — NL2SQLResult ergänzen
@dataclass
class NL2SQLResult:
    success: bool
    sql: str = ""
    error: str = ""
    error_type: str = ""
    warnings: list[str] = field(default_factory=list)
    generation: GenerationInfo | None = None
    formatted: FormattedResult = field(default_factory=FormattedResult)
    # NEU: Clarification-Felder (default=None/False → rückwärtskompatibel)
    needs_clarification: bool = False
    clarification_question: str = ""
    clarification_options: list[dict] = field(default_factory=list)
```

### Implementierung

**`aifw/nl2sql/clarification.py`** (neues Modul):

```python
"""
aifw.nl2sql.clarification — Intent-Disambiguation vor SQL-Generierung.

ClarificationDetector analysiert ob eine NL-Frage eindeutig genug ist
um direkt SQL zu generieren, oder ob zuerst eine Rückfrage nötig ist.

Der domains-Parameter macht den Detector schema-agnostisch:
  detector = ClarificationDetector(domains=["Maschinen", "Aufträge", ...])
So bleibt aifw.nl2sql Odoo-unabhängig (ADR-011).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from aifw.service import sync_completion   # korrekt: aifw.service, nicht aifw.core


@dataclass
class ClarificationOption:
    label: str        # "Maschinen"
    description: str  # "Betriebsstatus, Verfügbarkeit, Störungen"
    hint: str         # Wird an Frage angehängt: "— bezogen auf Maschinen"


@dataclass
class ClarificationResult:
    is_ambiguous: bool
    confidence: float            # 0.0 = eindeutig, 1.0 = maximal ambig
    reason: str
    question: str                # Rückfrage an User
    options: list[ClarificationOption] = field(default_factory=list)

    @classmethod
    def from_json(cls, raw: str) -> "ClarificationResult":
        data = json.loads(raw)
        opts = [ClarificationOption(**o) for o in data.get("options", [])]
        return cls(
            is_ambiguous=data["is_ambiguous"],
            confidence=float(data.get("confidence", 0.5)),
            reason=data.get("reason", ""),
            question=data.get("question", ""),
            options=opts,
        )


_CLARITY_SYSTEM_TEMPLATE = """
Du analysierst ob eine NL2SQL-Frage eindeutig genug ist um direkt SQL zu generieren.

Antworte NUR mit validem JSON:
{{
  "is_ambiguous": true/false,
  "confidence": 0.0-1.0,
  "reason": "Kurze Begründung",
  "question": "Rückfrage an den User (nur wenn ambig, sonst leer)",
  "options": [
    {{"label": "Kurzer Name", "description": "Was dieser Bereich umfasst", "hint": "— bezogen auf [Bereich]"}}
  ]
}}

Verfügbare Domänen: {domains}

EINDEUTIG: konkrete Entität, Zahl, Datum, Name, expliziter Filter
AMBIG: allgemeine Status-Fragen, fehlende Entität, Pronomen ohne Gesprächskontext
""".strip()


class ClarificationDetector:
    """Erkennt ambige NL2SQL-Anfragen und erzeugt Rückfrage-Optionen.

    Args:
        domains:   Liste der verfügbaren Domänen — schema-spezifisch, nicht hardcodiert.
        threshold: Confidence-Schwelle ab der nachgefragt wird (Standard: 0.65).
        action_code: AIActionType-Code für den Clarity-Check LLM-Call.
    """

    DEFAULT_THRESHOLD = 0.65
    HISTORY_THRESHOLD = 0.80  # Mit Gesprächsverlauf: höhere Schwelle nötig

    def __init__(
        self,
        domains: list[str],
        threshold: float = DEFAULT_THRESHOLD,
        action_code: str = "nl2sql_clarity_check",
    ) -> None:
        self.domains = domains
        self.threshold = threshold
        self.action_code = action_code
        self._system_prompt = _CLARITY_SYSTEM_TEMPLATE.format(
            domains=", ".join(domains)
        )

    def analyze(
        self,
        question: str,
        conversation_history: list[dict] | None = None,
    ) -> ClarificationResult:
        """Prüft ob die Frage zu ambig für direktes SQL ist.

        Args:
            question:             Natürlichsprachliche Nutzer-Frage.
            conversation_history: Liste von {tables, question} der Vorgänger-Turns.

        Returns:
            ClarificationResult mit is_ambiguous=True wenn Rückfrage empfohlen.
            Bei Parse-Fehler oder LLM-Ausfall: is_ambiguous=False (fail-open).
        """
        history = conversation_history or []
        effective_threshold = (
            self.HISTORY_THRESHOLD if history else self.threshold
        )

        context_note = ""
        if history:
            last_tables = history[-1].get("tables", "")
            if last_tables:
                context_note = f"\nGesprächskontext: letzte Abfrage betraf {last_tables}."

        # System-Prompt als erste Message — sync_completion hat kein system_override-Param
        result = sync_completion(
            action_code=self.action_code,
            messages=[
                {"role": "system", "content": self._system_prompt},
                {"role": "user",   "content": f"Frage: {question}{context_note}"},
            ],
            response_format={"type": "json_object"},
        )

        try:
            cr = ClarificationResult.from_json(result.content)
            # Threshold-Entscheidung an einer einzigen Stelle
            cr.is_ambiguous = cr.confidence >= effective_threshold
            return cr
        except Exception:
            # Fail-open: im Fehlerfall lieber falsches SQL als keine Antwort
            return ClarificationResult(
                is_ambiguous=False,
                confidence=0.0,
                reason="Parse-Fehler — Clarification-Check übersprungen",
                question="",
            )
```

**Integration in `NL2SQLEngine.__init__()` und `_run()`:**

```python
# aifw/nl2sql/engine.py
from aifw.nl2sql.clarification import ClarificationDetector
from aifw.nl2sql.results import NL2SQLResult

class NL2SQLEngine:
    def __init__(self, source_code: str, clarification_domains: list[str] | None = None):
        # ... bestehende Init ...
        # Einmalig instanziieren — nicht pro _run()-Aufruf
        self._clarifier = ClarificationDetector(
            domains=clarification_domains or [],
            action_code="nl2sql_clarity_check",
        ) if clarification_domains else None

    def _run(self, question: str, session_history: list[dict] | None = None) -> NL2SQLResult:
        # Clarification-Check nur wenn Detector konfiguriert
        if self._clarifier and self._clarifier.domains:
            clarity = self._clarifier.analyze(question, conversation_history=session_history)
            if clarity.is_ambiguous:
                return NL2SQLResult(
                    success=False,
                    needs_clarification=True,
                    clarification_question=clarity.question,
                    clarification_options=[vars(o) for o in clarity.options],
                )
        # ... bestehender SQL-Generierungs-Flow ...
```

**Konfiguration je Schema-Source (Odoo-spezifische Domänen bleiben außerhalb von `aifw`):**

```python
# aifw_service/management/commands/init_odoo_schema.py
engine = NL2SQLEngine(
    source_code="odoo_mfg",
    clarification_domains=[
        "Maschinen", "Gießaufträge", "Qualitätsprüfungen",
        "Einkauf/SCM", "Lager", "Produkte",
    ],
)
```

**Frontend — OWL-Panel (`nl2sql_panel.js`):**

```javascript
// Nach API-Antwort prüfen ob Clarification benötigt wird
if (res.needs_clarification) {
    this.state.clarification = {
        question: res.clarification_question,
        options:  res.clarification_options,   // [{label, description, hint}]
    };
    this.state.loading = false;
    return; // Warte auf User-Auswahl
}

// User wählt Option → Frage anreichern + erneut senden
async selectClarification(ev) {
    const hint = ev.currentTarget.dataset.hint;
    const enriched = this.state.query + " " + hint;
    this.state.clarification = null;
    await this.executeQuery(enriched);
}
```

**UX im Panel:**
```
┌─────────────────────────────────────────────────────────────┐
│ 🤔 Ich bin unsicher was gemeint ist.                        │
│ "Bitte präzisiere: Worüber möchtest du eine Übersicht?"    │
│                                                              │
│  [🏭 Maschinen]      [📋 Gießaufträge]                     │
│  Betriebsstatus,     Produktionsfortschritt,                │
│  Verfügbarkeit       Ausschuss, Termine                     │
│                                                              │
│  [🔍 Qualität]       [📦 Einkauf/SCM]                      │
│  Prüfergebnisse,     Bestellungen,                          │
│  Ausschussquote      Lieferzeiten                           │
└─────────────────────────────────────────────────────────────┘
```

### Kosten-Abschätzung (revidiert)

| Call | Richtung | ~Token | ~Kosten/1000 Fragen |
|---|---|---|---|
| Clarity-Check Input | System-Prompt (~130) + User (~30) + Kontext (~20) | ~180 | ~0,018 USD |
| Clarity-Check Output | JSON mit 4 Optionen | ~250 | ~0,063 USD |
| SQL-Generierung Input | Schema + Frage + Beispiele | ~800 | ~0,080 USD |
| SQL-Generierung Output | SQL + Erklärung | ~300 | ~0,075 USD |
| **Gesamt pro Frage** | | **~1530** | **~0,24 USD** |
| **Davon Clarity-Overhead** | +~430 Token | **+18%** | **+~0,08 USD** |

Bei ~15% ambigen Fragen verhindert der Clarity-Check falsche SQL-Ergebnisse.
**Qualitätsgewinn rechtfertigt den Overhead deutlich.**

> **Hinweis Rev. 1→2:** Ursprüngliche Schätzung (~80 Token, ~0,024 USD) unterschätzte
> den System-Prompt-Anteil (~130 Token) und den JSON-Output (~250 Token) erheblich.

---

## 2. PyPI-Erweiterungsstrategie für `iil-aifw`

### Kontext

`iil-aifw` ist aktuell (`v0.7.0`) ein privates Wheel das lokal gebaut und per `pip install` in den
`aifw_service`-Container eingespielt wird. Das funktioniert, hat aber Grenzen:

- Kein öffentlicher Index → manuelle Versionsverwaltung per Git
- Andere Projekte können `iil-aifw` nicht nutzen ohne Repo-Zugriff
- NL2SQL-Logik ist stark IIL-spezifisch — nicht generisch genug für öffentliches PyPI

### Optionen

#### Option A: Öffentliches PyPI (`pypi.org`)

**Pro:**
- Maximale Verbreitung, `pip install iil-aifw` von überall
- Community-Feedback, automatische Sicherheits-Scans (Snyk, PyPI Safety)
- Marketingeffekt: Open-Source-Signal

**Contra:**
- NL2SQL-Modul ist Odoo-spezifisch (Casting, IIL-Domäne) → schlechter für generische Nutzer
- Sicherheitsrisiko: Odoo-Schema-Struktur und Prompt-Engineering öffentlich
- Wartungsaufwand: Issues, PRs, Backwards-Compat-Garantien
- Paketname-Konflikt möglich (`iil-aifw` evtl. schon vergeben)

**Entscheidung: NEIN** — zu früh, zu spezifisch, zu viel Wartungsoverhead.

> **Hinweis:** Der Paketname `iil-aifw` sollte auf PyPI vorab reserviert werden
> (kostenlos, leeres Placeholder-Release), um Squatting zu verhindern.

#### Option B: Private PyPI Registry (empfohlen)

**Optionen:**
- **GitHub Packages** (bereits im Repo vorhanden, gratis für private Repos)
- **Gitea/Forgejo Registry** (Self-hosted)
- **AWS CodeArtifact** (wenn AWS-Stack vorhanden)

**GitHub Packages — konkrete Umsetzung:**

```toml
# pyproject.toml — keine Änderung nötig, hatchling kompatibel
[project]
name = "iil-aifw"
version = "0.8.0"
```

```yaml
# .github/workflows/publish.yml  ← liegt im aifw-Submodul-Repo, nicht in odoo-hub!
name: Publish iil-aifw to GitHub Packages

on:
  push:
    tags: ["v*"]  # im aifw-Repo: alle v*-Tags gehören zu iil-aifw

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.12"}
      - run: pip install hatch
      - run: hatch build
        working-directory: aifw
      - run: |
          pip install twine
          twine upload \
            --repository-url https://upload.pkg.github.com/achimdehnert/odoo-hub \
            --username ${{ github.actor }} \
            --password ${{ secrets.GITHUB_TOKEN }} \
            aifw/dist/*
```

**Installation in aifw_service:**
```dockerfile
# Dockerfile
RUN pip install iil-aifw \
    --index-url https://TOKEN@pkg.github.com/achimdehnert/odoo-hub/simple/
```

#### Option C: Plugin-Architektur (Zukunft)

Wenn `iil-aifw` wächst: Core + optionale Plugin-Packages:

```
iil-aifw          # Core: LLM Provider, Action, Usage — generisch
iil-aifw-nl2sql   # NL2SQL Engine + Schema + Clarification — Odoo-agnostisch  
iil-aifw-odoo     # Odoo-spezifische Integration (casting.*, ir.model.fields)
```

```toml
# pyproject.toml Core
[project.optional-dependencies]
nl2sql = ["iil-aifw-nl2sql>=0.1"]
odoo   = ["iil-aifw-nl2sql", "iil-aifw-odoo>=0.1"]
```

```bash
pip install "iil-aifw[nl2sql]"    # Django-Projekt mit NL2SQL, kein Odoo
pip install "iil-aifw[odoo]"      # Vollstack mit Odoo-Integration
```

**Wann sinnvoll:** Wenn ein zweites Projekt `iil-aifw` ohne Odoo nutzen will.  
**Aufwand:** ~3 Sprints für saubere Plugin-Separation.

### Entscheidung: GitHub Packages (Option B) — Sprint 15

**Begründung:**
- Privat → keine öffentliche Exposition von Odoo-Domänenwissen
- Versioniert → `pip install iil-aifw==0.8.0` statt `git+https://...`
- CI/CD-ready → Tag `v0.8.0` → automatisch publiziert
- Kein zusätzlicher Infrastrukturaufwand (GitHub bereits vorhanden)
- Offen für spätere Migration zu PyPI wenn Core generisch genug

### Migrationspfad zu öffentlichem PyPI

```
Heute (v0.7):   Lokales Wheel, manuell gebaut
Sprint 15:      GitHub Packages, automatisch via CI/CD
v1.0 (TBD):    iil-aifw Core öffentlich auf PyPI (Odoo-spezifisches in iil-aifw-odoo)
```

**Bedingungen für öffentliches PyPI:**
1. Core-Modul (`aifw.core`, `aifw.nl2sql.engine`) ist Odoo-unabhängig
2. Odoo-spezifischer Code vollständig in `iil-aifw-odoo` separiert
3. Test-Coverage > 80% für öffentliche API
4. Semantic Versioning mit CHANGELOG-Pflicht

---

## 3. Roadmap-Zusammenfassung

```
Sprint 14   Clarification-Agent (ambig-Detection + Frontend-Chips)
            Graph-Relations im Schema-XML (<relationships>-Block)

Sprint 15   GitHub Packages CI/CD-Pipeline
            iil-aifw 0.8.0 als erste versionierte Registry-Version

Sprint 16+  RAG für Schema-Retrieval (pgvector, erst ab 30+ Tabellen relevant)
            Conversation-State (Session-DB, 30-Min-TTL)

v1.0 TBD    Plugin-Architektur: iil-aifw-core / iil-aifw-nl2sql / iil-aifw-odoo
            Evaluation öffentliches PyPI für Core-Package
```

---

## Offene Punkte / Bekannte Einschränkungen

- **Kein User-Bypass**: Erfahrene User die wissen was sie fragen werden bei ambigen
  Formulierungen gebremst. Empfehlung für v0.9: Query-Prefix `!` oder User-Setting
  `clarification_enabled=False` in `SchemaSource`.
- **Clarification-Domains sind manuell zu pflegen**: Neue Odoo-Modelle müssen in
  `init_odoo_schema.py` ergänzt werden. Automatisierung via `sync_odoo_schema`
  (ADR-009) ist geplant.
- **Kein Conversation-State**: `session_history` ist aktuell stateless (kein persistenter
  Session-Store). Bis Conversation-State implementiert ist (ADR-009 Sprint 17+) wird
  `session_history=None` übergeben — der Detector arbeitet dann mit `threshold=0.65`.

## Abgelehnte Alternativen

| Alternative | Grund der Ablehnung |
|---|---|
| Öffentliches PyPI sofort | Zu früh, zu spezifisch, Wartungsoverhead — siehe ADR-011 |
| Kein Clarification-Agent | Zu viele falsche SQL bei allgemeinen Fragen |
| Clarification immer aktiv | Overhead bei klaren Fragen, nervt erfahrene User |
| Hardcodierter Domänen-Prompt in `aifw` | Koppelt `aifw.nl2sql` an Odoo — widerspricht ADR-011 |
| Separater LLM-Anbieter für Clarity-Check | Zusätzliche Konfiguration, kein Mehrwert |
| Neo4j für Graph-Schema | Overkill — JSON-Relationships im XML reichen für <50 Tabellen |
