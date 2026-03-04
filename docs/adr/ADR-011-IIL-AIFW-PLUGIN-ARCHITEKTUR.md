# ADR-011: `iil-aifw` Plugin-Architektur und Breaking-Change-Analyse

**Status:** Entschieden  
**Datum:** 2026-03-04  
**Autoren:** IIL Engineering  
**Verwandte ADRs:** ADR-007 (iil-Package-Architektur), ADR-010 (PyPI-Strategie)

---

## Kontext

`iil-aifw` wird aktuell (v0.7.0) von **mindestens 4 Projekten** genutzt:

| Projekt | Nutzt | Odoo-Abhängigkeit? |
|---|---|---|
| `odoo-hub` / `aifw_service` | Core + NL2SQL + Odoo-Sync | ✅ Ja |
| `travel-beat` | Core (LLM Completion, UsageLog) | ❌ Nein |
| `writing-hub` | Core + quality_level Routing | ❌ Nein |
| `weltenhub` | Core (sync_completion, streaming) | ❌ Nein |

**Kernbeobachtung aus Code-Analyse:**

Die Grenze ist bereits faktisch sauber:

```
aifw/src/aifw/
├── service.py          ← Core: LLM completion, caching, routing — KEINE Odoo-Deps
├── models.py           ← Core: LLMProvider, LLMModel, AIActionType, UsageLog — KEINE Odoo-Deps
├── schema.py           ← Core: LLMResult, TypedDicts — KEINE Odoo-Deps
├── constants.py        ← Core: QualityLevel, VALID_PRIORITIES — KEINE Odoo-Deps
├── exceptions.py       ← Core: ConfigurationError — KEINE Odoo-Deps
├── types.py            ← Core: ActionConfig — KEINE Odoo-Deps
└── nl2sql/
    ├── engine.py       ← NL2SQL: SQL-Generierung — KEINE Odoo-Deps (!)
    ├── models.py       ← NL2SQL: SchemaSource, NL2SQLExample, NL2SQLFeedback — KEINE Odoo-Deps (!)
    └── results.py      ← NL2SQL: NL2SQLResult — KEINE Odoo-Deps
```

**Odoo-spezifischer Code existiert NUR in:**
- `addons/mfg_nl2sql/` — Odoo-Addon, nicht Teil von `iil-aifw`
- `services/aifw_service/management/commands/sync_odoo_schema.py` — Service-Layer, nicht `iil-aifw`

**→ `iil-aifw` hat heute keine Odoo-Abhängigkeiten. Die Plugin-Separation ist bereits faktisch vollzogen.**

---

## Ist-Zustand: Import-Grenzen

### Was `travel-beat`, `writing-hub`, `weltenhub` importieren (dürfen):

```python
# Core — stabil, kein Breaking Change geplant
from aifw.service import sync_completion, completion, sync_completion_with_fallback
from aifw.service import get_action_config, get_quality_level_for_tier
from aifw.service import invalidate_action_cache, invalidate_tier_cache
from aifw.schema import LLMResult
from aifw.constants import QualityLevel
from aifw.types import ActionConfig
from aifw.exceptions import ConfigurationError
```

### Was `aifw_service` (Odoo-Hub) zusätzlich importiert:

```python
# NL2SQL — stabil für aifw_service, nicht für andere Projekte empfohlen
from aifw.nl2sql import NL2SQLEngine
from aifw.nl2sql.models import SchemaSource, NL2SQLExample, NL2SQLFeedback
from aifw.nl2sql.results import NL2SQLResult
```

---

## Breaking-Change-Analyse

### Frage: Wären heutige Änderungen für `travel-beat` / `writing-hub` / `weltenhub` breaking?

**Antwort: NEIN — wenn folgende Regel gilt:**

> **Regel:** Das `aifw.nl2sql`-Subpaket wird nie in non-Odoo-Projekten importiert.
> Das Core-API (`aifw.service`, `aifw.schema`, `aifw.constants`) bleibt API-stabil.

### Konkrete Breaking-Change-Szenarien

| Änderung | Breaking für non-Odoo? | Breaking für odoo-hub? |
|---|---|---|
| `aifw.nl2sql.*` umbenennen zu `aifw_nl2sql.*` | ❌ Nein | ✅ JA — alle Imports |
| `sync_completion()` Signatur ändern | ✅ JA — alle Projekte | ✅ JA |
| `QualityLevel`-Werte ändern | ✅ JA — alle Projekte | ✅ JA |
| `NL2SQLEngine` intern refactorn | ❌ Nein | ✅ Nur wenn public API ändert |
| `SchemaSource` Felder hinzufügen (nullable) | ❌ Nein | ❌ Nein (rückwärtskompatibel) |
| `SchemaSource` Felder umbenennen | ❌ Nein | ✅ JA — Migrations + Code |
| Neue optionale Parameter in `sync_completion()` | ❌ Nein | ❌ Nein |

**→ Das Core-API ist heute bereits stabil. Die NL2SQL-Komponente ändert sich nur für `odoo-hub`.**

---

## Entscheidung: Plugin-Architektur — JA, aber ohne Package-Split

### Option A (abgelehnt): Separates PyPI-Package `iil-aifw-nl2sql`

```
iil-aifw          → PyPI (Core)
iil-aifw-nl2sql   → PyPI (NL2SQL Engine + Models)
iil-aifw-odoo     → privat (Odoo-Sync Commands)
```

**Problem:** 
- `aifw.nl2sql.models` teilt Django-App-Label `"aifw"` und Migrations mit Core
- Auftrennung würde Migrations-Split erfordern → hoher Aufwand, kein Nutzen
- `travel-beat` etc. nutzen `nl2sql` gar nicht → kein Bedarf für separates Package

### Option B (entschieden): Namespace-Konvention ohne Package-Split ✅

**Ein Package, klare Namespace-Grenzen durch Konvention:**

```
iil-aifw (ein Package, ein wheel)
├── aifw.*          → STABLE PUBLIC API — alle Projekte können das nutzen
│   ├── service     → completion, sync_completion, routing
│   ├── schema      → LLMResult, TypedDicts
│   ├── constants   → QualityLevel
│   └── exceptions  → ConfigurationError
│
└── aifw.nl2sql.*   → OPTIONAL API — nur für Projekte mit DB-Zugriff + NL2SQL-Bedarf
    ├── engine      → NL2SQLEngine
    ├── models      → SchemaSource, NL2SQLExample, NL2SQLFeedback
    └── results     → NL2SQLResult
```

**Formalisierung via `INSTALLED_APPS`:**

```python
# travel-beat, writing-hub, weltenhub — settings.py
INSTALLED_APPS = [
    "aifw",          # Core: LLMProvider, LLMModel, AIActionType, UsageLog
    # NICHT: aifw.nl2sql — kein NL2SQL benötigt
]

# aifw_service (odoo-hub) — settings.py
INSTALLED_APPS = [
    "aifw",          # Core
    "aifw.nl2sql",   # NL2SQL Engine + Schema + Feedback
]
```

**Migrationsfolge bleibt korrekt:**
- Core-Migrations: `0001_initial` … `0005_quality_level_routing`
- NL2SQL-Migrations: `0006_nl2sql_example_feedback` (hängt von `0005` ab)
- Projekte ohne `aifw.nl2sql` in `INSTALLED_APPS` erhalten keine NL2SQL-Tabellen

---

## optional-dependencies in `pyproject.toml`

Die `pyproject.toml` wird um `optional-dependencies` erweitert um explizit zu dokumentieren
welche Abhängigkeiten welches Feature benötigt:

```toml
[project]
name = "iil-aifw"
version = "0.8.0"
description = "Django AI Services Framework — DB-driven LLM routing, quality tiers, NL2SQL"

dependencies = [
    "Django>=5.0,<6.0",
    "litellm>=1.30",
    "tenacity>=8.2",
    "asgiref>=3.7",
]

[project.optional-dependencies]
nl2sql = [
    # Keine zusätzlichen Deps — aifw.nl2sql nutzt nur Django + litellm (bereits in core)
    # Optional: pgvector für RAG (ADR-009 Stufe 1)
]
rag = [
    "pgvector>=0.3",          # Für Schema-RAG (ADR-009 Stufe 1, Sprint 16+)
]
dev = [
    "pytest>=8.0",
    "pytest-django>=4.8",
    "pytest-asyncio>=0.23",
    "hatch",
    "ruff",
]
```

**Installation je Projekt:**

```bash
# travel-beat, writing-hub, weltenhub — nur Core
pip install "iil-aifw==0.8.0"

# aifw_service — Core + NL2SQL (nl2sql hat keine Extra-Deps, also identisch)
pip install "iil-aifw[nl2sql]==0.8.0"

# Zukunft: mit RAG-Unterstützung
pip install "iil-aifw[nl2sql,rag]==0.9.0"
```

---

## Breaking Changes beim Upgrade 0.7.0 → 0.8.0

### Für `travel-beat`, `writing-hub`, `weltenhub`: KEINE

Alle Core-APIs bleiben identisch:
- `sync_completion()` — unverändert
- `completion()` — unverändert  
- `get_action_config()` — unverändert
- `get_quality_level_for_tier()` — unverändert
- `QualityLevel` — unverändert
- `LLMResult` — unverändert

### Für `odoo-hub` / `aifw_service`: KEINE (wenn `aifw.nl2sql` in INSTALLED_APPS)

**Einzige Änderung:** `aifw.nl2sql` muss explizit in `INSTALLED_APPS` stehen:

```python
# Vor 0.8.0 (implizit via aifw):
INSTALLED_APPS = ["aifw"]  # nl2sql-Models wurden mitgeladen

# Ab 0.8.0 (explizit):
INSTALLED_APPS = [
    "aifw",
    "aifw.nl2sql",   # ← NEU erforderlich wenn nl2sql genutzt wird
]
```

**→ Das ist der einzige potenzielle Breaking Change, und er ist trivial.**

---

## Versionsstrategie

### Semantic Versioning — ab 0.8.0 verbindlich

```
MAJOR.MINOR.PATCH

MAJOR: Breaking Change in Core-API (sync_completion Signatur etc.)
MINOR: Neue Features, neue optional-dependencies, neue NL2SQL-Funktionen
PATCH: Bugfixes, Performance, interne Refactorings ohne API-Änderung
```

### CHANGELOG-Kategorien (ab 0.8.0)

```markdown
## [0.8.0] — YYYY-MM-DD

### Breaking Changes (MAJOR-Kandidaten)
- (keine)

### Migration Required
- `aifw.nl2sql` muss explizit in INSTALLED_APPS ergänzt werden

### Added
- GitHub Packages CI/CD-Pipeline (automatischer Publish bei Tag v*)
- optional-dependencies: nl2sql, rag, dev

### Changed
- pyproject.toml: optional-dependencies formalisiert

### Fixed
- ...
```

---

## GitHub Packages CI/CD — konkrete Implementierung

```yaml
# .github/workflows/publish-aifw.yml
name: Publish iil-aifw

on:
  push:
    tags:
      - "aifw/v*"   # Nur Tags die mit aifw/v beginnen → aifw/v0.8.0

jobs:
  build-and-publish:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install build tools
        run: pip install hatch twine

      - name: Build wheel + sdist
        run: hatch build
        working-directory: aifw

      - name: Publish to GitHub Packages
        run: |
          twine upload \
            --repository-url https://upload.pkg.github.com/achimdehnert/odoo-hub \
            --username ${{ github.actor }} \
            --password ${{ secrets.GITHUB_TOKEN }} \
            aifw/dist/*
```

**Tag-Konvention:**
```bash
git tag aifw/v0.8.0
git push origin aifw/v0.8.0
# → CI/CD publiziert automatisch iil-aifw==0.8.0 auf GitHub Packages
```

**Installation in Consumer-Projekten:**
```toml
# requirements.txt oder pyproject.toml der Consumer-Projekte
--index-url https://${GITHUB_TOKEN}@pkg.github.com/achimdehnert/odoo-hub/simple/
iil-aifw==0.8.0
```

---

## Migrationspfad zu öffentlichem PyPI

Bedingungen — frühestens v1.0:

1. ✅ `aifw.core.*` ist vollständig Odoo-unabhängig (heute bereits erfüllt)
2. 🔲 Test-Coverage `aifw.core.*` > 80%
3. 🔲 `aifw.nl2sql.*` vollständig als optional dokumentiert (INSTALLED_APPS)
4. 🔲 Semantic Versioning mit CHANGELOG mind. 3 Releases eingehalten
5. 🔲 Kein IIL-spezifisches Domänenwissen im Core (casting.*, ir.model.fields → bleiben in aifw_service)

**→ v1.0 + PyPI ist realistisch in Q3/Q4 2026 wenn Punkte 2-4 erfüllt.**

---

## Zusammenfassung

| Frage | Antwort |
|---|---|
| Plugin-Architektur jetzt? | **JA** — Namespace-Konvention, kein Package-Split |
| Breaking Changes für travel-beat etc.? | **NEIN** — Core-API unverändert |
| Breaking Changes für odoo-hub? | **Minimal** — `aifw.nl2sql` in INSTALLED_APPS ergänzen |
| PyPI jetzt? | **NEIN** — GitHub Packages (Sprint 15), PyPI frühestens v1.0 |
| Package-Split (`iil-aifw-nl2sql`)? | **NEIN** — erst wenn zweites Projekt NL2SQL ohne Odoo braucht |
| Wann Migrations-Issue? | **Nie** — `aifw.nl2sql` in INSTALLED_APPS steuert Migration |
