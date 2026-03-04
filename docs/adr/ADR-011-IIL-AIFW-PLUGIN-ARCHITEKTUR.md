# ADR-011: `iil-aifw` Plugin-Architektur und Breaking-Change-Analyse

**Status:** Entschieden — Rev. 2 (2026-03-04, Review-Korrekturen)
**Datum:** 2026-03-04  
**Autoren:** IIL Engineering  
**Verwandte ADRs:** ADR-007 (iil-Package-Architektur), ADR-010 (PyPI-Strategie)

### Änderungshistorie

| Rev | Datum | Änderung |
|---|---|---|
| 1 | 2026-03-04 | Erstversion |
| 2 | 2026-03-04 | Review-Korrekturen: fehlende `AppConfig` + `app_label`-Strategie, `db_table`-Beibehaltung, CI/CD im richtigen Repo (Submodul), `__all__`-Policy, Deprecation-Policy, leere `nl2sql`-optional-dep semantisch präzisiert |

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

### Ist-Zustand: Public API (`__all__`)

Beide Pakete haben bereits korrekte `__all__`-Definitionen:

```python
# aifw/__init__.py — bereits vorhanden (v0.7.0)
__all__ = [
    "__version__", "QualityLevel", "ActionConfig", "LLMResult",
    "sync_completion", "completion", "get_action_config",
    "get_quality_level_for_tier", "invalidate_action_cache",
    # ... vollständig definiert
]

# aifw/nl2sql/__init__.py — bereits vorhanden (v0.7.0)
__all__ = [
    "NL2SQLEngine", "SchemaSource", "NL2SQLExample",
    "NL2SQLFeedback", "NL2SQLResult", "GenerationInfo",
    "FormattedResult", "ChartConfig",
]
```

→ Keine Arbeit nötig. `__all__` ist korrekt und vollständig definiert.

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
- `aifw.nl2sql.models` teilt aktuell Django-App-Label `"aifw"` mit Core
- Auftrennung erfordert Migrations-Split + neue Tabellen-Namen → hoher Aufwand
- `travel-beat` etc. nutzen `nl2sql` gar nicht → kein Bedarf für separates Package

### Option B (entschieden): Namespace-Konvention + eigene `AppConfig` ✅

**Ein Package, klare Namespace-Grenzen durch eigene Django-App-Konfiguration:**

```
iil-aifw (ein Package, ein wheel)
├── aifw.*          → STABLE PUBLIC API — alle Projekte
│   ├── service     → completion, sync_completion, routing
│   ├── schema      → LLMResult, TypedDicts
│   ├── constants   → QualityLevel
│   └── exceptions  → ConfigurationError
│
└── aifw.nl2sql.*   → OPTIONAL API — nur mit INSTALLED_APPS-Eintrag aktiv
    ├── apps.py     → NL2SQLConfig(AppConfig)  ← NEU erforderlich
    ├── engine      → NL2SQLEngine
    ├── models      → SchemaSource, NL2SQLExample, NL2SQLFeedback
    └── results     → NL2SQLResult
```

### Kritische Implementierungsvoraussetzung: `AppConfig` + `app_label`

**Problem (Review-Befund #11):** `aifw.nl2sql.models` hat aktuell `app_label = "aifw"`.
Wenn `"aifw.nl2sql"` in `INSTALLED_APPS` eingetragen wird, erwartet Django eine eigene
`AppConfig`-Klasse — sonst Fehler beim Start.

**Lösung: `aifw/nl2sql/apps.py` erstellen (fehlt komplett in v0.7.0):**

```python
# aifw/nl2sql/apps.py — NEU
from django.apps import AppConfig


class NL2SQLConfig(AppConfig):
    name = "aifw.nl2sql"
    label = "aifw_nl2sql"         # eigenes Label — kein Konflikt mit Core "aifw"
    verbose_name = "aifw NL2SQL"
    default_auto_field = "django.db.models.BigAutoField"
```

**Und `aifw/nl2sql/__init__.py` registrieren:**

```python
# aifw/nl2sql/__init__.py — Zeile ergänzen
default_app_config = "aifw.nl2sql.apps.NL2SQLConfig"  # Django <3.2 Compat
# Ab Django 3.2+ wird apps.py automatisch erkannt wenn name korrekt
```

**`app_label` in `nl2sql/models.py` aktualisieren:**

```python
# aifw/nl2sql/models.py — alle drei Modelle
class SchemaSource(models.Model):
    class Meta:
        app_label = "aifw_nl2sql"          # war: "aifw"
        db_table = "aifw_nl2sql_schema_sources"   # EXPLIZIT beibehalten!
        # ↑ Verhindert Tabellen-Umbenennung in Produktion (Review-Befund #14)

class NL2SQLExample(models.Model):
    class Meta:
        app_label = "aifw_nl2sql"
        db_table = "aifw_nl2sql_examples"         # EXPLIZIT beibehalten!

class NL2SQLFeedback(models.Model):
    class Meta:
        app_label = "aifw_nl2sql"
        db_table = "aifw_nl2sql_feedback"         # EXPLIZIT beibehalten!
```

> **Warum `db_table` explizit?**
> Django generiert Tabellennamen als `{app_label}_{model_name_lower}`. Bei
> `app_label="aifw"` → `aifw_nl2sql_schema_sources` (Zufall: passt). Bei
> `app_label="aifw_nl2sql"` → `aifw_nl2sql_nl2sql_schema_sources` (doppelt!).
> Explizite `db_table`-Angabe verhindert jede ungewollte Umbenennung in Produktion.

**Migration für `app_label`-Wechsel:**

```python
# aifw/migrations/0007_nl2sql_app_label.py
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [("aifw", "0006_nl2sql_example_feedback")]
    operations = [
        # Keine DB-Änderung nötig — db_table bleibt identisch
        # Migration informiert Django nur über app_label-Wechsel
        migrations.SeparateDatabaseAndState(
            database_operations=[],   # keine DDL
            state_operations=[
                migrations.DeleteModel(name="SchemaSource"),
                migrations.DeleteModel(name="NL2SQLExample"),
                migrations.DeleteModel(name="NL2SQLFeedback"),
            ],
        ),
    ]

# aifw/nl2sql/migrations/0001_initial_from_core.py
from django.db import migrations

class Migration(migrations.Migration):
    """Übernimmt NL2SQL-Modelle von aifw → aifw_nl2sql ohne DDL."""
    dependencies = [("aifw", "0007_nl2sql_app_label")]
    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],   # keine DDL — Tabellen existieren bereits
            state_operations=[
                # Alle drei Modelle hier als CreateModel auflisten
                # (identisch zu 0006, aber mit app_label=aifw_nl2sql)
            ],
        ),
    ]
```

**Formalisierung via `INSTALLED_APPS`:**

```python
# travel-beat, writing-hub, weltenhub — settings.py
INSTALLED_APPS = [
    "aifw",          # Core: LLMProvider, LLMModel, AIActionType, UsageLog
    # NICHT: aifw.nl2sql — kein NL2SQL benötigt, keine NL2SQL-Tabellen
]

# aifw_service (odoo-hub) — settings.py
INSTALLED_APPS = [
    "aifw",          # Core
    "aifw.nl2sql",   # NL2SQL — aktiviert NL2SQLConfig, eigene Migrations
]
```

**Migrationsfolge:**

```
aifw 0001_initial
  ↓
aifw 0005_quality_level_routing
  ↓
aifw 0006_nl2sql_example_feedback   ← entfällt in v0.8.0 (Modelle ziehen um)
  ↓
aifw 0007_nl2sql_app_label          ← NEU: SeparateDatabaseAndState, keine DDL
  ↓
aifw_nl2sql 0001_initial_from_core  ← NEU: Übernahme ohne DDL
  ↓
aifw_nl2sql 0002_...                ← Alle zukünftigen NL2SQL-Migrations hier
```

---

## optional-dependencies in `pyproject.toml`

`aifw.nl2sql` benötigt keine zusätzlichen Python-Packages gegenüber Core —
die `nl2sql`-optional-dependency signalisiert daher **Intention** ("dieses Feature ist
optional"), nicht zusätzliche Abhängigkeiten. `pgvector` kommt separat wenn RAG
implementiert wird.

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
    # Keine extra Python-Packages — aifw.nl2sql nutzt nur Core-Deps.
    # Aktivierung erfolgt ausschließlich via INSTALLED_APPS = [..., "aifw.nl2sql"].
    # Marker für Consumer-Projekte: pip install 'iil-aifw[nl2sql]' signalisiert
    # Absicht, kein zusätzliches Download-Gewicht.
]
rag = [
    # Sprint 16+: Schema-RAG via pgvector (ADR-009 Stufe 1)
    "pgvector>=0.3",
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

# aifw_service — signalisiert NL2SQL-Nutzung (kein Extra-Download)
pip install "iil-aifw[nl2sql]==0.8.0"

# Zukunft: mit RAG-Unterstützung (lädt pgvector)
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
- `invalidate_config_cache()` — bleibt als Alias auf `invalidate_action_cache()` erhalten

### Für `odoo-hub` / `aifw_service`: Migration Required (kein Data-Loss)

**Schritt 1:** `aifw.nl2sql` in `INSTALLED_APPS` ergänzen:

```python
INSTALLED_APPS = [
    "aifw",
    "aifw.nl2sql",   # ← NEU
]
```

**Schritt 2:** Migrations ausführen (keine DDL — nur Django-State-Update):

```bash
python manage.py migrate aifw 0007_nl2sql_app_label
python manage.py migrate aifw_nl2sql
```

**Schritt 3:** `app_label` in eigenem Code prüfen (falls irgendwo hartcodiert):

```python
# Vor 0.8.0:
SchemaSource._meta.app_label  # → "aifw"

# Ab 0.8.0:
SchemaSource._meta.app_label  # → "aifw_nl2sql"
```

**DB-Tabellen bleiben unverändert** — `db_table` ist explizit gesetzt:

```
aifw_nl2sql_schema_sources  ← identisch vor und nach Migration
aifw_nl2sql_examples        ← identisch vor und nach Migration
aifw_nl2sql_feedback        ← identisch vor und nach Migration
```

**→ Kein Data-Loss, kein DDL, keine Downtime. Migration dauert < 1 Sekunde.**

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

> **Wichtig (Review-Befund #16):** `aifw` ist ein eigenständiges Git-Submodul
> (`github.com:achimdehnert/aifw.git`). Der CI/CD-Workflow muss **im `aifw`-Repo**
> liegen, nicht in `odoo-hub`. Tags werden im Submodul-Repo gesetzt.

```yaml
# Datei: .github/workflows/publish.yml
# Repo:  github.com/achimdehnert/aifw  ← Submodul-Repo, NICHT odoo-hub!
name: Publish iil-aifw to GitHub Packages

on:
  push:
    tags:
      - "v*"    # Im aifw-Repo: alle v*-Tags gehören zu iil-aifw

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

      - name: Publish to GitHub Packages
        run: |
          twine upload \
            --repository-url https://upload.pkg.github.com/achimdehnert/aifw \
            --username ${{ github.actor }} \
            --password ${{ secrets.GITHUB_TOKEN }} \
            dist/*
```

**Tag-Workflow (im `aifw`-Submodul-Repo):**

```bash
# Im aifw-Submodul-Verzeichnis:
cd /home/dehnert/github/odoo-hub/aifw
git tag v0.8.0
git push origin v0.8.0
# → GitHub Actions publiziert iil-aifw==0.8.0 automatisch

# Dann Submodul-Referenz in odoo-hub aktualisieren:
cd ..
git add aifw
git commit -m "chore: bump iil-aifw submodule to v0.8.0"
```

**Installation in Consumer-Projekten:**

```toml
# requirements.txt
--index-url https://${GITHUB_TOKEN}@pkg.github.com/achimdehnert/aifw/simple/
iil-aifw==0.8.0

# oder pyproject.toml
[project]
dependencies = ["iil-aifw==0.8.0"]

[[tool.uv.sources]]  # uv-kompatibel
iil-aifw = {index = "github-achimdehnert-aifw"}
```

---

## Versionsstrategie und Deprecation-Policy

### Semantic Versioning — ab v0.8.0 verbindlich

```
MAJOR — Breaking Change in stabiler Public API
         Beispiel: sync_completion()-Signatur ändern
         Vorankündigung: mind. 1 MINOR-Release als deprecated
MINOR — Neue Features, neue optional-dependencies, neue NL2SQL-Funktionen
         Additive Änderungen — rückwärtskompatibel
PATCH — Bugfixes, Performance-Verbesserungen
         Keine API-Änderung
```

### Deprecation-Policy

Deprecated APIs bleiben **mindestens 2 MINOR-Releases** erhalten:

```python
# Beispiel: invalidate_config_cache() wurde umbenannt zu invalidate_action_cache()
# → bleibt als Alias bis v1.0 (aktuell in service.py, Zeile 188 bereits umgesetzt)
def invalidate_config_cache(action_code: str | None = None) -> None:
    """Backwards-compatible alias for invalidate_action_cache(). Deprecated since v0.6.0."""
    invalidate_action_cache(action_code)
```

Für neue Deprecations: `warnings.warn(..., DeprecationWarning, stacklevel=2)` hinzufügen.

## Migrationspfad zu öffentlichem PyPI

Bedingungen — frühestens v1.0:

1. ✅ `aifw` + `aifw.nl2sql` sind vollständig Odoo-unabhängig (heute bereits erfüllt)
2. ✅ `__all__` vollständig in `aifw/__init__.py` + `aifw/nl2sql/__init__.py` (heute bereits erfüllt)
3. 🔲 `aifw.nl2sql` als separate Django-App mit `AppConfig` + eigenen Migrations (v0.8.0)
4. 🔲 Test-Coverage `aifw.core.*` > 80%
5. 🔲 Semantic Versioning + Deprecation-Policy mind. 3 Releases eingehalten
6. 🔲 Paketname `iil-aifw` auf PyPI vorab reserviert (leerer Placeholder)

**→ v1.0 + PyPI ist realistisch in Q3/Q4 2026 wenn Punkte 3-6 erfüllt.**

---

## Zusammenfassung

| Frage | Antwort |
|---|---|
| Plugin-Architektur jetzt? | **JA** — eigene `AppConfig`, kein Package-Split |
| Breaking Changes für travel-beat etc.? | **NEIN** — Core-API unverändert |
| Breaking Changes für odoo-hub? | **Migration Required** — `AppConfig` + 2 Migrations (kein DDL, kein Data-Loss) |
| PyPI jetzt? | **NEIN** — GitHub Packages im `aifw`-Submodul-Repo (Sprint 15) |
| Package-Split (`iil-aifw-nl2sql`)? | **NEIN** — erst wenn zweites Projekt NL2SQL braucht |
| DB-Tabellen-Umbenennung? | **NEIN** — `db_table` explizit gesetzt, bleibt unverändert |
| Wo liegt CI/CD-Workflow? | **Im `aifw`-Submodul-Repo**, nicht in `odoo-hub` |
| Deprecation-Frist | **2 MINOR-Releases** vor Entfernung — `warnings.warn()` |
