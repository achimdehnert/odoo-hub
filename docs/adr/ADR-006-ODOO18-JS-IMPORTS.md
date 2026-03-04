# ADR-006: Odoo 18 JavaScript Import-Regeln

**Status:** Accepted  
**Datum:** 2026-03-04  
**Kontext:** odoo-hub, alle Custom Addons  

---

## Hintergrund

Am 2026-03-04 wurde ein kritischer Bug diagnostiziert, der die gesamte OWL-Navigation
(Klicks auf Menüpunkte, Kacheln, URLs) einfrieren ließ. Root Cause: ungültige
Cross-Modul-JavaScript-Imports in Odoo 18.

**Symptom:** Seite rendert visuell korrekt, aber **nichts ist klickbar** — auch nicht
die Odoo-Topbar. OWL-App mountet nicht vollständig.

---

## Root Cause: Odoo 18 JS Bundler-Verhalten

Odoo 18 verwendet einen eigenen ES-Modul-Bundler (basierend auf RequireJS-ähnlicher
Transformation). Dieser transformiert **relative Imports innerhalb eines Moduls**
beim Bundling intern zu einem `@modulname/`-Namespace:

```
// In addons/mfg_management/static/src/js/file.js
import { X } from "./other_file"
// → wird intern zu: require("@mfg_management/js/other_file")
```

Diese internen `@modulname/`-Pfade sind **nur innerhalb desselben Moduls** auflösbar.
Cross-Modul-Imports über diesen Mechanismus **scheitern lautlos** (`require()` gibt
`undefined` zurück statt zu werfen). Das Ergebnis:

1. Die importierte Klasse/Funktion ist `undefined`
2. OWL-Komponenten-Registrierung schlägt fehl
3. Die gesamte OWL-App-Initialisierung schlägt fehl
4. **Alle Klicks sind blockiert** — auch Klicks die nichts mit dem fehlerhaften Modul zu tun haben

---

## Einzige gültige Import-Formen in Custom Addons

```js
// ✅ 1. Relativ innerhalb desselben Moduls
import { MyClass } from "./other_file";
import { util } from "../utils/helpers";

// ✅ 2. Odoo-Web-Framework (@web/ Alias)
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

// ✅ 3. OWL-Bibliothek (@odoo/ Alias)
import { Component, useState, onWillStart, onError } from "@odoo/owl";
```

```js
// ❌ VERBOTEN: @eigener_modul/ Alias
import { X } from "@mfg_management/js/nl2sql_query_bar";
import { X } from "@iil_dashboard_core/js/panel_registry";

// ❌ VERBOTEN: Voller Modulpfad
import { X } from "mfg_management/static/src/js/nl2sql_query_bar";
import { X } from "iil_dashboard_core/static/src/js/panel_error_boundary";
```

---

## OWL 2 Error Boundary mit `t-slot` bricht Event-Binding (behoben 2026-03-04)

Ein weiteres OWL-18-spezifisches Problem: Ein Error-Boundary-Wrapper mit `t-slot="default"`
und `onError()` verhindert das Event-Handler-Binding aller Kind-Komponenten:

```xml
<!-- ❌ VERBOTEN: PanelErrorBoundary als t-slot-Wrapper in dynamischen Grids -->
<PanelErrorBoundary>
    <t t-component="panel.component" t-props="..."/>
</PanelErrorBoundary>
```

**Symptom:** Panels rendern visuell korrekt (Daten sichtbar), aber **kein Klick, kein
Button, keine Interaktion** funktioniert innerhalb der Panels. Die Odoo-Topbar
(höherer z-index) bleibt klickbar.

**Root Cause:** `onError()` in OWL 2 in Kombination mit `t-slot="default"` und
dynamischen `t-component`-Aufrufen unterbricht das OWL-Event-Binding für den
Slot-Content. Die Komponenten werden gerendert aber Event-Handler werden nicht gebunden.

```xml
<!-- ✅ Korrekt: direkte t-component Aufrufe ohne Wrapper -->
<t t-component="panel.component" t-props="..."/>
```

**Regel:** Kein `t-slot`-basierter Error-Boundary-Wrapper um dynamische Komponenten
in OWL 2. OWL's eigenes Fehler-Handling reicht für Panel-Isolation aus.

---

## OWL 2 `useState` Proxy korrumpiert Component-Klassen (behoben 2026-03-04)

**Symptom:** Panels rendern korrekt, alle Daten sichtbar, aber **kein Event-Handler
feuert** — kein `t-on-click`, kein Button, keine Interaktion möglich.

**Root Cause:** OWL 2 wraps alle Werte in `useState()` in einen ES6 `Proxy`.
Wenn eine Component-Klasse in den State gesteckt wird, wird sie durch den Proxy
korrumpiert. `t-component="state.panels[i].component"` rendert dann ein Proxy-Objekt
statt der echten Klasse. OWL rendert das HTML korrekt (Fallback-Rendering) aber
**bindet keine Event-Listener**.

```javascript
// ❌ VERBOTEN: Component-Klasse in useState speichern
this.state = useState({
    panels: [{ code: "machining", component: MachiningPanel }]  // Proxy!
});
// Im Template: t-component="panel.component"  → Proxy-Objekt, kein Event-Binding
```

```javascript
// ✅ Korrekt: Component-Klassen außerhalb von useState
this._panelComponents = {};          // Plain object, kein Proxy
this.state = useState({
    panels: [{ code: "machining" }]  // Nur serialisierbare Daten im State
});
this._panelComponents["machining"] = MachiningPanel;

// Im Template: t-component="getPanelComponent(panel.code)"
// getPanelComponent() gibt die echte Klasse zurück — Event-Binding funktioniert
```

**Regel:** Niemals Component-Klassen, Funktionsreferenzen oder andere nicht-serialisierbare
Objekte in `useState()` speichern. Nur primitive Werte, Arrays von plain objects,
und serialisierbare Daten gehören in den reaktiven State.

---

## Bekannte Fehler (behoben 2026-03-04)

| Datei | Verbotener Import | Fix |
|---|---|---|
| `casting_foundry/casting_panel.js` | `@mfg_management/js/nl2sql_query_bar` | Import + Verwendung entfernt |
| `casting_foundry/machines_panel.js` | `@mfg_management/js/nl2sql_query_bar` | Import + Verwendung entfernt |
| `casting_foundry/quality_panel.js` | `@mfg_management/js/nl2sql_query_bar` | Import + Verwendung entfernt |
| `scm_manufacturing/scm_panel.js` | `@mfg_management/js/nl2sql_query_bar` | Import + Verwendung entfernt |
| `mfg_machining/machining_panel.js` | `@mfg_management/js/nl2sql_query_bar` | Import + Verwendung entfernt |
| `mfg_management/dynamic_dashboard.js` | `@iil_dashboard_core/js/iil_dynamic_dashboard` | Refactor rückgängig, self-contained |
| `mfg_management/panel_registry.js` | `@iil_dashboard_core/js/panel_registry` | Direkte Implementierung |

---

## XML-Template-Regel: Kein leeres `t-inherit-mode="primary"`

Ein weiterer Freeze-Trigger in Odoo 18 QWeb:

```xml
<!-- ❌ VERBOTEN: Leeres primary-inherit — erzeugt undefined Template -->
<t t-name="my_module.MyComponent"
   t-inherit="other_module.BaseComponent"
   t-inherit-mode="primary"/>

<!-- ✅ Korrekt: Entweder vollständiges Template ... -->
<t t-name="my_module.MyComponent">
    <div>...</div>
</t>

<!-- ✅ ... oder Extension-Inherit mit Body -->
<t t-name="my_module.MyComponent"
   t-inherit="other_module.BaseComponent"
   t-inherit-mode="extension">
    <xpath expr="//div[@class='title']" position="replace">
        <div class="title">Überschrieben</div>
    </xpath>
</t>
```

---

## Strategie für Code-Wiederverwendung über Module hinweg

Da direkte Cross-Modul-JS-Imports in Odoo 18 nicht funktionieren, gibt es diese Alternativen:

### Option A: Duplizieren (empfohlen für kleine Helpers)
Gleiche Funktion/Klasse in jedem Modul separat definieren.
- Vorteil: Einfach, keine Abhängigkeit
- Nachteil: Code-Duplikat

### Option B: OWL-Registry-Pattern (empfohlen für Plugins)
```js
// Anbieter-Modul registriert:
registry.category("iil_panels").add("my_code", { component: MyPanel });

// Konsument liest aus Registry — kein direkter Import nötig:
const component = registry.category("iil_panels").get("my_code").component;
```
Dies ist das Pattern das `mfg_management` für Panels verwendet.

### Option C: Odoo-Asset-Bundle-Reihenfolge + `window`-Global (Notlösung)
Nur wenn A und B nicht möglich sind. Nicht empfohlen.

### Option D: In `@web/` integrieren (für Odoo-Core-Patches)
Nicht praktikabel für custom addons ohne Fork.

---

## CI-Enforcement

Dieser Regelverstoß wird automatisch in CI erkannt:

```
tests/test_js_imports.py::TestJsImports::test_no_forbidden_cross_module_imports
tests/test_js_imports.py::TestXmlTemplates::test_no_empty_primary_inherit
```

Jeder Pull Request auf `main` schlägt fehl wenn verbotene Imports eingebracht werden.

---

## Übertragbarkeit auf andere Repos

Dieses ADR gilt für **alle Odoo-18-Projekte** ohne Ausnahme. Die CI-Tests aus
`tests/test_js_imports.py` können direkt in andere Repos kopiert werden.

Getestete Odoo-Version: **18.0** (Community + Enterprise, Stand März 2026)
