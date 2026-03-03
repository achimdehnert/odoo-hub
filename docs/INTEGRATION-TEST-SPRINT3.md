# Integrationstest-Plan — Sprint 1–3

**Stand:** 2026-03-03  
**Ziel:** Kontrolliertes Deployment der Sprint-1/2/3-Änderungen auf `https://odoo.iil.pet`  
**Durchführung:** Vor jedem Deployment-Schritt, in der angegebenen Reihenfolge

---

## Betroffene Module (Änderungsumfang)

| Modul | Typ | Änderung |
|---|---|---|
| `casting_foundry` | bestehend | `is_demo_data` Feld neu in `casting.order` + `casting.quality.check` |
| `mfg_nl2sql` | bestehend | Bugfixes C1/C3/C4 (savepoint, fields.Json, _rec_name) |
| `mfg_management` | bestehend | `panel_registry.js`, `dynamic_dashboard.js`, Template-Ergänzung |
| `iil_configurator` | **neu** | Komplettes Addon: Feature-Registry, Wizard, NL2SQL-Schema-Daten |
| `iil_mrp` | **neu** | Grundgerüst (leer) |
| `iil_stock` | **neu** | Grundgerüst (leer) |
| `mfg_machining` | **neu** | `machining.order`, `machining.machine`, Sequence, Menüs |
| `docker/db/init.sql` | Infra | H2+H3 Fix (current_schema() + AND) |

---

## Phase 0 — Pre-Flight (lokal, vor Deployment)

### 0.1 Git-Status sauber

```bash
git status
git diff --stat HEAD
```

**Erwartung:** Alle Sprint-1/2/3-Dateien sind staged/committed.  
**Abbruchkriterium:** uncommittete Fremddateien.

### 0.2 Python-Syntax aller geänderten Module

```bash
python3 -m py_compile \
  addons/casting_foundry/models/casting_order.py \
  addons/casting_foundry/models/casting_quality_check.py \
  addons/mfg_nl2sql/controllers/nl2sql_controller.py \
  addons/mfg_nl2sql/models/query_history.py \
  addons/mfg_nl2sql/models/schema_metadata.py \
  addons/iil_configurator/models/iil_product_feature.py \
  addons/iil_configurator/models/iil_seed_engine.py \
  addons/iil_configurator/wizard/iil_configurator_wizard.py \
  addons/mfg_machining/models/machining_order.py \
  addons/mfg_machining/models/machining_machine.py
echo "Syntax OK"
```

**Erwartung:** Kein Fehler, `Syntax OK` erscheint.

### 0.3 Manifest-Vollständigkeit prüfen

Für jedes neue Addon sicherstellen:
- [ ] `__manifest__.py` vorhanden und parsierbar
- [ ] Alle in `data:` referenzierten Dateien existieren
- [ ] Alle in `assets:` referenzierten Dateien existieren

```bash
# Dateipfade aus Manifests validieren (manuell):
for addon in iil_configurator mfg_machining iil_mrp iil_stock; do
  echo "=== $addon ==="
  python3 -c "
import ast, os
m = ast.literal_eval(open('addons/$addon/__manifest__.py').read())
for f in m.get('data', []):
    path = 'addons/$addon/' + f
    status = 'OK' if os.path.exists(path) else 'MISSING'
    print(status, path)
"
done
```

**Erwartung:** Alle Dateien `OK`.  
**Abbruchkriterium:** Jede `MISSING`-Zeile.

---

## Phase 1 — Deployment auf Produktion

### 1.1 Git push

```bash
git add -A
git commit -m "feat: Sprint 1-3 — bugfixes, iil_configurator, mfg_machining, panel-registry"
git push origin main
```

### 1.2 Server: Pull + Odoo-Update

```bash
# Auf dem Hetzner-Server (46.225.127.211):
ssh root@46.225.127.211

cd /opt/odoo-hub   # oder jeweiliger Pfad
git pull origin main

# Neue + geänderte Module updaten:
docker exec -it odoo odoo \
  -u casting_foundry,mfg_nl2sql,mfg_management,iil_configurator,mfg_machining \
  --stop-after-init \
  -d odoo
```

**Erwartung:** Odoo startet durch, keine `ERROR` im Log.  
**Prüfen:**

```bash
docker logs odoo --tail=50 | grep -E 'ERROR|WARNING|Module.*loaded'
```

### 1.3 Odoo-Service-Restart

```bash
docker restart odoo
docker logs odoo --tail=20
```

**Erwartung:** `odoo.service_1  | HTTP service (werkzeug) running on ...`

---

## Phase 2 — Smoke Tests (Browser)

URL: `https://odoo.iil.pet`  
Login: `admin / Admin2026!`

### T-01: Dashboard lädt ohne Fehler

- [ ] Navigiere zu **MFG Cockpit** (Hauptmenü)
- [ ] Dashboard lädt vollständig, kein JS-Fehler in Browser-Konsole
- [ ] `DynamicDashboard` fällt auf `MfgDashboard` zurück (iil_configurator installiert, aber keine Features aktiviert)

**Pass-Kriterium:** Alle KPI-Cards sichtbar, keine roten Fehlermeldungen.

### T-02: iil_configurator installiert

- [ ] Navigiere zu **Einstellungen → Apps**
- [ ] `IIL Konfigurator` ist aufgelistet und Status = **Installiert**
- [ ] `IIL Werkzeugmaschinen` ist aufgelistet und Status = **Installiert**

### T-03: Feature-Registry Menü

- [ ] Navigiere zu **MFG Cockpit → IIL Konfigurator → Produktmerkmale**
- [ ] Liste der Feature-Codes erscheint (mind. 11 Einträge aus `feature_defaults.xml`)
- [ ] Felder `code`, `label`, `is_active` sichtbar

### T-04: Konfigurator-Wizard öffnen

- [ ] Navigiere zu **MFG Cockpit → IIL Konfigurator → Konfiguration starten**
- [ ] Wizard öffnet sich auf Schritt 1 (Branchenauswahl)
- [ ] Navigation zwischen Schritten 1→2→3→4→5 funktioniert
- [ ] Schritt 5: Button **Demo-Daten generieren** sichtbar

**Pass-Kriterium:** Kein `ValidationError`, keine 500-Fehler.

### T-05: CNC-Fertigung Menü

- [ ] Navigiere zu **MFG Cockpit → CNC-Fertigung**
- [ ] Untermenü: **Fertigungsaufträge** und **Maschinenpark** erscheinen
- [ ] Beide Listen öffnen sich ohne Fehler (leer ist OK)

### T-06: casting_foundry — is_demo_data Feld

- [ ] Navigiere zu einem bestehenden **Gießauftrag**
- [ ] In der Form-Ansicht: Entwickler-Modus aktivieren (URL: `?debug=1`)
- [ ] Feld `is_demo_data` in den Feldinformationen sichtbar (`Technische Info`)

**Pass-Kriterium:** Kein Datenbankfehler, Feld vorhanden.

### T-07: NL2SQL — Savepoint-Fix (C1)

- [ ] Öffne NL2SQL-Panel im Dashboard
- [ ] Stelle eine fehlerhafte SQL-Abfrage: `ZEIGE ALLES` (kein gültiges SQL)
- [ ] Fehlermeldung erscheint, aber **Dashboard bleibt funktionsfähig**
- [ ] Zweite gültige Abfrage direkt danach funktioniert

**Pass-Kriterium:** Dashboard-Session nicht invalidiert nach SQL-Fehler.

### T-08: Schema-Metadaten geladen

- [ ] Navigiere zu **MFG Cockpit → NL2SQL → Schema-Tabellen** (falls Menü vorhanden)
- [ ] Oder via Debug: `nl2sql.schema.table` im Odoo-Backend prüfen
- [ ] Tabellen `casting_order`, `casting_order_line`, `casting_machine`, `casting_alloy`, `casting_quality_check` vorhanden
- [ ] `is_active = False` (noch nicht aktiviert — korrekt)

---

## Phase 3 — Regressions-Tests (bestehende Funktionen)

### T-09: Gießauftrag anlegen

- [ ] **Casting Foundry → Gießaufträge → Neu**
- [ ] Felder befüllen: Partner, Datum, mindestens eine Position
- [ ] Speichern → Auftragsnummer wird generiert (`CO/...`)
- [ ] Status-Übergänge: Draft → Bestätigt → In Fertigung

**Pass-Kriterium:** Keine DB-Fehler, Sequence funktioniert.

### T-10: Qualitätsprüfung anlegen

- [ ] Gießauftrag öffnen → **Prüfungen → Neu**
- [ ] Prüftyp und Ergebnis auswählen, speichern
- [ ] `is_demo_data` ist `False` (Standard)

### T-11: NL2SQL — erfolgreiche Abfrage

- [ ] Abfrage: `Wie viele Gießaufträge gibt es?`
- [ ] SQL wird generiert und ausgeführt
- [ ] Ergebnis erscheint als Tabelle

**Pass-Kriterium:** `row_count >= 0`, kein 500-Fehler.

---

## Phase 4 — Rollback-Plan

Falls eines der obigen Tests fehlschlägt:

### Rollback-Prozedur

```bash
# Auf dem Server:
git log --oneline -5
git revert HEAD --no-edit
git push origin main

# Dann nur die betroffenen stabilen Module zurückspielen:
docker exec -it odoo odoo \
  -u casting_foundry,mfg_nl2sql,mfg_management \
  --stop-after-init -d odoo

docker restart odoo
```

### Bekannte Risiken

| Risiko | Wahrscheinlichkeit | Mitigation |
|---|---|---|
| `is_demo_data` Migrationsfehler (Feld neu, DB-Schema-Änderung) | **mittel** | Odoo führt `ALTER TABLE` automatisch durch — kein manueller Migration-Script nötig |
| `nl2sql_schema_casting.xml` lädt nicht (`nl2sql.schema.table` fehlt ohne `mfg_nl2sql`) | ~~mittel~~ **gelöst** | `post_init_hook` prüft `mfg_nl2sql` State — lädt Schema nur wenn installiert |
| `mfg_management` JS-Fehler durch `dynamic_dashboard.js` | **niedrig** | Fallback auf `MfgDashboard` bei Exception |
| Menu-Konflikt `menu_mfg_root` (depends auf `mfg_management`) | **niedrig** | `mfg_machining` depends auf `mfg_management` → Lade-Reihenfolge korrekt |

---

## Hinweis: nl2sql_schema depends — GELÖST ✅

`iil_configurator/data/nl2sql_schema_casting.xml` und `nl2sql_schema_machining.xml`
referenzieren `nl2sql.schema.table` (nur vorhanden wenn `mfg_nl2sql` installiert).

**Implementierter Fix:** `post_init_hook` in `iil_configurator/__init__.py` —
Schema-XMLs werden via `convert_file()` geladen, **aber nur wenn**
`ir.module.module` den State `installed` für `mfg_nl2sql` zurückgibt.
Ohne `mfg_nl2sql`: Hook läuft durch, loggt Info, lädt keine Schema-Daten.
Keine Exception, kein Crash.

---

## Checkliste Deployment-Freigabe

- [ ] Phase 0 vollständig bestanden
- [ ] `nl2sql_schema depends`-Problem gelöst (siehe oben)
- [ ] Git-Commit sauber und beschreibend
- [ ] T-01 bis T-08 bestanden
- [ ] T-09 bis T-11 (Regression) bestanden
- [ ] Kein `ERROR` in `docker logs odoo` nach 5 Minuten Betrieb

---

*Erstellt: 2026-03-03 | Autor: Cascade/IIL*
