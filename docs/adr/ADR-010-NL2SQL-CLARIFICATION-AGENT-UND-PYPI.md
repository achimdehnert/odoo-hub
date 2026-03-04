# ADR-010: NL2SQL Clarification-Agent und PyPI-Erweiterungsstrategie

**Status:** Entschieden  
**Datum:** 2026-03-04  
**Autoren:** IIL Engineering  
**Verwandte ADRs:** ADR-007 (iil-Package-Architektur), ADR-008 (Fehlerlernen), ADR-009 (Evolutionspfad)

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

### Implementierung

**`aifw/nl2sql/clarification.py`** (neues Modul):

```python
from dataclasses import dataclass, field
from typing import Optional
import json

from aifw.core.completion import sync_completion


@dataclass
class ClarificationOption:
    label: str           # "Maschinen"
    description: str     # "Betriebsstatus, Verfügbarkeit, Störungen"
    hint: str            # Appended to question: "— bezogen auf Maschinen"


@dataclass  
class ClarificationResult:
    is_ambiguous: bool
    confidence: float              # 0.0 = sicher eindeutig, 1.0 = sicher ambig
    reason: str
    question: str                  # Rückfrage an User
    options: list[ClarificationOption] = field(default_factory=list)

    @classmethod
    def from_json(cls, raw: str) -> "ClarificationResult":
        data = json.loads(raw)
        opts = [ClarificationOption(**o) for o in data.get("options", [])]
        return cls(
            is_ambiguous=data["is_ambiguous"],
            confidence=data.get("confidence", 0.5),
            reason=data.get("reason", ""),
            question=data.get("question", ""),
            options=opts,
        )


CLARITY_SYSTEM_PROMPT = """
Du analysierst ob eine NL2SQL-Frage eindeutig genug ist um direkt SQL zu generieren.

Antworte NUR mit validem JSON:
{
  "is_ambiguous": true/false,
  "confidence": 0.0-1.0,
  "reason": "Kurze Begründung",
  "question": "Rückfrage an den User (nur wenn ambig)",
  "options": [
    {
      "label": "Kurzer Name",
      "description": "Was dieser Bereich umfasst",
      "hint": "— bezogen auf [Bereich]"
    }
  ]
}

Verfügbare Domänen: Maschinen, Gießaufträge, Qualitätsprüfungen, Einkauf/SCM, Lager, Produkte.

EINDEUTIG: konkrete Entität, Zahl, Datum, Name, expliziter Filter
AMBIG: allgemeine Status-Fragen, fehlende Entität, Pronomen ohne Kontext
""".strip()


class ClarificationDetector:

    AMBIG_THRESHOLD = 0.65  # Ab hier wird nachgefragt

    def analyze(
        self,
        question: str,
        conversation_history: list[dict] | None = None,
    ) -> ClarificationResult:
        """Prüft ob die Frage zu ambig für direktes SQL ist."""
        history = conversation_history or []

        # Gesprächsverlauf gibt Kontext → senkt Ambiguität
        context_note = ""
        if history:
            last = history[-1]
            context_note = f"\nVorherige Frage war über: {last.get('tables', '')}"

        result = sync_completion(
            action_code="nl2sql_clarity_check",
            messages=[{
                "role": "user",
                "content": f"Frage: {question}{context_note}",
            }],
            system_override=CLARITY_SYSTEM_PROMPT,
            response_format={"type": "json_object"},
        )

        try:
            cr = ClarificationResult.from_json(result.content)
            # Mit Kontext: Schwelle höher setzen
            if history and cr.confidence < self.AMBIG_THRESHOLD + 0.15:
                cr.is_ambiguous = False
            return cr
        except Exception:
            return ClarificationResult(
                is_ambiguous=False,
                confidence=0.0,
                reason="Parse-Fehler — direktes SQL",
                question="",
            )
```

**Integration in `NL2SQLEngine._run()`:**

```python
# aifw/nl2sql/engine.py — in _run() vor SQL-Generierung

from aifw.nl2sql.clarification import ClarificationDetector

detector = ClarificationDetector()
clarity = detector.analyze(question, conversation_history=session_history)

if clarity.is_ambiguous and clarity.confidence >= ClarificationDetector.AMBIG_THRESHOLD:
    return NL2SQLResult(
        success=False,
        needs_clarification=True,
        clarification_question=clarity.question,
        clarification_options=[o.__dict__ for o in clarity.options],
        error=None,
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

### Kosten-Abschätzung

| Call | Modell | ~Token | ~Kosten/1000 Fragen |
|---|---|---|---|
| Clarity-Check (neu) | claude-3-haiku | ~80 | ~0,024 USD |
| SQL-Generierung (bestehend) | claude-3-haiku | ~600 | ~0,18 USD |
| **Gesamt** | | ~680 | **~0,20 USD** |

Bei ambigen Fragen (~15%): Clarity-Check verhindert falsche SQL → **Qualitätsgewinn ohne nennenswerte Mehrkosten**.

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
# .github/workflows/publish.yml
name: Publish iil-aifw to GitHub Packages

on:
  push:
    tags: ["v*"]

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

## Abgelehnte Alternativen

| Alternative | Grund der Ablehnung |
|---|---|
| Öffentliches PyPI sofort | Zu früh, zu Odoo-spezifisch, Wartungsoverhead |
| Kein Clarification-Agent | Zu viele falsche SQL bei allgemeinen Fragen |
| Clarification immer aktiv | Overhead bei klaren Fragen, nervt erfahrene User |
| Single-Package ohne Plugin-Option | Skaliert nicht wenn zweites Projekt iil-aifw nutzt |
| Neo4j für Graph-Schema | Overkill — JSON-Relationships im XML reichen für <50 Tabellen |
