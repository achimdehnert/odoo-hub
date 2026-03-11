# Odoo 18 → 19 Migration Notes — Custom Addons

Stand: 2026-03-11 | Getestet auf: `stagingv19-odoo.iil.pet` (Odoo 19.0)

## Status pro Addon

| Addon | V18 OK | V19 Lädt | Breaking Changes |
|-------|--------|----------|-----------------|
| `casting_foundry` | ✅ | ❌ | Siehe unten |
| `scm_manufacturing` | ✅ | ❌ | Siehe unten |
| `mfg_nl2sql` | ✅ | ❌ | Mehrere (dokumentiert) |
| `mfg_management` | ✅ | ❌ | OWL-Dependency fehlt |
| `mfg_machining` | ✅ | ❌ | Dependency fehlt |

---

## Breaking Changes Odoo 19 (gefunden)

### 1. `res.groups.category_id` entfernt
**Fehler:** `ValueError: Invalid field 'category_id' in 'res.groups'`
**Fix:** `category_id`-Field aus allen `<record model="res.groups">` XML-Records entfernen.
**Betroffene Dateien:**
- `mfg_nl2sql/security/security.xml` ✅ gefixt
- `casting_foundry/security/security.xml` — TODO
- `scm_manufacturing/security/security.xml` — TODO

### 2. `res.groups.comment` entfernt
**Fehler:** `ParseError` beim Laden von security.xml
**Fix:** `<field name="comment">` aus `res.groups` Records entfernen.
**Status:** ✅ gefixt in `mfg_nl2sql/security/security.xml`

### 3. `@route(type='json')` deprecated → `type='jsonrpc'`
**Fehler:** `DeprecationWarning: Since 19.0, @route(type='json') is deprecated alias to @route(type='jsonrpc')`
**Fix:** Alle `type='json'` in Controller-Decorators ersetzen durch `type='jsonrpc'`.
**Status:** ✅ gefixt in `mfg_nl2sql/controllers/nl2sql_controller.py` (6 Routes)
**Offen:** Alle anderen Addon-Controller prüfen.

### 4. XML View Validation — `<group expand>` + `<search>` Syntax
**Fehler:** `RELAXNG_ERR_INVALIDATTR: Invalid attribute expand for element group`
**Fehler:** `RELAXNG_ERR_EXTRACONTENT: Element search has extra content: field`
**Datei:** `mfg_nl2sql/views/query_history_views.xml:85`
**Fix:** View-XML anpassen:
- `<group expand="1">` → `<group>` (expand-Attribut entfernt)
- Search-View `<field>` Tags außerhalb von `<search>` Root prüfen
**Status:** TODO

### 5. Module-Version muss auf `19.0.x.x.x` gebumpt werden
**Fehler:** `incompatible version, setting installable=False`
**Fix:** `__manifest__.py` `version`-Feld auf `19.0.x.x.x` setzen.
**Status:** ✅ erledigt für alle Addons in `addons_v19/`

### 6. `ir.module.category` — Reihenfolge im Manifest wichtig
**Problem:** `ref="module_category_nl2sql"` schlägt fehl wenn Kategorie nicht vorher geladen.
**Fix:** Kategorie in separate Datei `security/module_category.xml` auslagern, vor `security.xml` in `data` Liste.
**Status:** ✅ erledigt für `mfg_nl2sql`

---

## Geschätzter Restaufwand

| Bereich | Aufwand |
|---------|---------|
| XML Security-Files (alle Addons) | 0.5 Tage |
| XML View-Syntax (group, search) | 1-2 Tage |
| OWL JS-Frontend (`mfg_management`) | 3-5 Tage |
| Controller-Route-Types | 0.5 Tage |
| Test + Stabilisierung | 2-3 Tage |
| **Gesamt** | **~7-11 Tage** |

---

## Vorgehen für vollständige Migration

1. Alle `security.xml`-Files: `category_id` + `comment` entfernen
2. Alle Views: `expand`-Attribut entfernen, `<search>`-Struktur prüfen
3. Alle Controller: `type='json'` → `type='jsonrpc'`
4. `mfg_management` OWL-Code: OWL 2 API (Odoo 19) — größter Aufwand
5. `casting_foundry` + `scm_manufacturing`: Nach Security-Fix testen

## Nützliche Ressourcen

- [Odoo 19 Upgrade Guide](https://www.odoo.com/documentation/19.0/developer/reference/upgrades.html)
- [OCA/OpenUpgrade](https://github.com/OCA/OpenUpgrade) — Community Migration Scripts
- Odoo 19 Changelog: `odoo/CHANGELOG.rst` im Core-Repo
