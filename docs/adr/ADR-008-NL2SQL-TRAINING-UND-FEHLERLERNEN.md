# ADR-008: NL2SQL — Vorab-Training und kontinuierliches Fehlerlernen

**Status:** Konzept  
**Datum:** 2026-03-04  
**Autoren:** IIL Engineering  
**Verwandte ADRs:** ADR-006 (OWL2 JS), ADR-007 (iil-Package-Architektur)

---

## Kontext und Problem

Der aktuelle NL2SQL-Stack übersetzt natürlichsprachliche Fragen via LLM (Claude) + Schema-XML in SQL.
Beobachtete Fehlerklassen:

1. **Schema-Fehler**: LLM halluziniert Felder die nicht existieren (z.B. `casting_order.machine_id` → existiert nur in `casting_order_line`)
2. **Join-Fehler**: LLM wählt falschen Join-Pfad weil Schema-XML keine Join-Hints enthält
3. **Terminologie-Mismatch**: User fragt "aktive Aufträge" → LLM nimmt `state='active'` statt `state IN ('confirmed','in_production')`
4. **Kontext-Drift**: Ohne Gesprächsgedächtnis wiederholt die KI Fehler in Folgefragen

**Ziel:** Systematischer Ansatz um diese Fehlerklassen zu eliminieren — durch präzises Schema, Few-Shot-Beispiele und Fehler-Feedback-Loop.

---

## Säule 1: Präzises Schema-XML (Sofortmaßnahmen)

### Problem
Das Schema-XML ist die einzige Wissensquelle des LLM über die DB-Struktur. Jede Lücke führt zu Halluzinationen.

### Maßnahmen

**1.1 Join-Hints als explizite Schema-Elemente**
```xml
<!-- VORHER — LLM halluziniert casting_order.machine_id -->
<table name="casting_order">
  <column name="machine_id" .../>  <!-- FALSCH: existiert nicht! -->
</table>

<!-- NACHHER — expliziter Join-Hint -->
<table name="casting_order">
  <join_hint>Maschinen: JOIN casting_order_line col ON col.order_id = co.id
             JOIN casting_machine cm ON cm.id = col.machine_id</join_hint>
</table>
```

**1.2 Negative Constraints — was NICHT existiert**
```xml
<constraint type="no_column">casting_order hat KEIN machine_id-Feld</constraint>
<constraint type="no_column">casting_order hat KEIN alloy_id-Feld (nur in casting_order_line)</constraint>
```

**1.3 Domänen-Glossar — Terminologie-Mapping**
```xml
<glossary>
  <term user="aktive Aufträge" sql="state IN ('confirmed','in_production','quality_check')"/>
  <term user="Störung" sql="state = 'breakdown'"/>
  <term user="Wartung" sql="state = 'maintenance'"/>
  <term user="Betrieb" sql="state = 'operational'"/>
  <term user="diese Woche" sql="date_planned >= date_trunc('week', CURRENT_DATE)"/>
</glossary>
```

**Implementierungsort:** `services/aifw_service/management/commands/init_odoo_schema.py` → `ODOO_MFG_SCHEMA_XML`

---

## Säule 2: Few-Shot Training (Goldene SQL-Beispiele)

### Konzept
Few-Shot-Prompting gibt dem LLM verifizierte Frage→SQL-Paare direkt im System-Prompt. Das ist die **wirksamste Methode** ohne Fine-Tuning.

### DB-Modell: `NL2SQLExample`

```python
# In aifw/nl2sql/models.py (iil-aifw Paket)
class NL2SQLExample(models.Model):
    """Verifizierte Frage→SQL-Paare für Few-Shot-Prompting."""
    
    source        = ForeignKey(SchemaSource)          # z.B. odoo_mfg
    question      = TextField()                        # "Top 5 Maschinen nach aktiven Aufträgen"
    sql           = TextField()                        # verifiziertes SQL
    is_active     = BooleanField(default=True)
    domain        = CharField(max_length=50, blank=True)  # casting, scm, etc.
    difficulty    = IntegerField(default=1)            # 1=einfach, 3=komplex
    verified_by   = ForeignKey(User, null=True)
    verified_at   = DateTimeField(null=True)
    
    class Meta:
        db_table = "aifw_nl2sql_examples"
```

### System-Prompt-Integration

```python
# In engine.py — Few-Shot-Blöcke in System-Prompt einbauen
examples = NL2SQLExample.objects.filter(
    source=source, is_active=True
).order_by('difficulty')[:10]

few_shot_block = "\n\nBEWÄHRTE BEISPIELE (immer korrekt — als Vorlage verwenden):\n"
for ex in examples:
    few_shot_block += f"\nFRAGE: {ex.question}\nSQL:\n{ex.sql}\n"

system_prompt = BASE_PROMPT + schema_xml + few_shot_block
```

### Initiale Goldene Beispiele für `odoo_mfg`

| Frage | Kern-Pattern |
|---|---|
| Top 5 Maschinen nach aktiven Aufträgen | casting_order_line JOIN casting_machine JOIN casting_order WHERE state='in_production' |
| Maschinen in Störung | casting_machine WHERE state='breakdown' |
| Ausschussrate diese Woche | casting_order WHERE date_planned >= date_trunc('week',...) |
| Offene Bestellungen überfällig | scm_purchase_order WHERE date_expected < CURRENT_DATE |
| QS-Bestehensrate gesamt | COUNT FILTER WHERE result='pass' / COUNT(*) |

**Management-Command:** `python manage.py seed_nl2sql_examples --source odoo_mfg`

---

## Säule 3: Fehler-Feedback-Loop (Lernen aus Fehlern)

### Konzept
Jeder SQL-Ausführungsfehler wird automatisch erfasst und kann manuell oder automatisch in eine Korrektur überführt werden.

### DB-Modell: `NL2SQLFeedback`

```python
class NL2SQLFeedback(models.Model):
    """Fehler-Log + Korrekturen für kontinuierliches Lernen."""

    source           = ForeignKey(SchemaSource)
    question         = TextField()                    # Original-Frage
    bad_sql          = TextField()                    # Fehlerhaftes SQL
    error_message    = TextField()                    # Postgres-Fehler
    corrected_sql    = TextField(blank=True)          # Manuell korrigiert
    error_type       = CharField(max_length=50)       # schema_error | join_error | syntax_error
    promoted         = BooleanField(default=False)    # Als Example übernommen?
    created_at       = DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "aifw_nl2sql_feedback"
```

### Automatische Fehlererfassung

```python
# In engine.py — _run() Methode
except Exception as exc:
    # Fehler automatisch in NL2SQLFeedback speichern
    NL2SQLFeedback.objects.create(
        source=source,
        question=question,
        bad_sql=raw_sql,
        error_message=str(exc),
        error_type=_classify_error(str(exc)),
    )
    return NL2SQLResult(success=False, ...)
```

### Fehlerklassifikation

```python
def _classify_error(error_msg: str) -> str:
    msg = error_msg.lower()
    if "does not exist" in msg and "column" in msg:
        return "schema_error"      # Halluziniertes Feld
    if "does not exist" in msg and "table" in msg:
        return "table_error"       # Halluzinierte Tabelle
    if "syntax error" in msg:
        return "syntax_error"
    if "ambiguous" in msg:
        return "join_error"
    return "unknown"
```

### Fehler → Korrektur → Beispiel Pipeline

```
SQL-Fehler (automatisch erfasst)
    ↓
NL2SQLFeedback (error_type klassifiziert)
    ↓
Admin/Entwickler korrigiert SQL (corrected_sql befüllen)
    ↓
python manage.py promote_feedback --min-age-days 1
    ↓
NL2SQLExample (promoted=True, is_active=True)
    ↓
Nächste Abfragen nutzen korrigiertes SQL als Few-Shot
```

---

## Säule 4: Schema-Validierung beim Start (Regression Prevention)

### Problem
Schema-XML und tatsächliche DB können auseinanderlaufen (nach Migrationen).

### Lösung: `validate_schema` Management-Command

```python
# python manage.py validate_schema --source odoo_mfg
# Prüft: Jede im Schema referenzierte Tabelle/Spalte existiert in DB

for table in schema.tables:
    if not table_exists(table.name, db_alias):
        errors.append(f"FEHLER: Tabelle '{table.name}' nicht in DB")
    for col in table.columns:
        if not column_exists(table.name, col.name, db_alias):
            errors.append(f"FEHLER: '{table.name}.{col.name}' nicht in DB")
```

**Integration in CI/CD:** `validate_schema` als Teil des Deployments ausführen → bricht den Deploy ab wenn Schema-XML inkonsistent.

---

## Säule 5: Retry mit Fehler-Kontext (Self-Healing)

### Konzept
Bei SQL-Ausführungsfehler: Automatisch nochmal anfragen mit Fehler im Kontext.

```python
# engine.py — _run() mit Retry
try:
    columns, rows, elapsed_ms, truncated = _execute_query(sql, ...)
except Exception as exc:
    if retry_count < 1:
        # Zweiter Versuch: Fehler + schlechtes SQL als Kontext mitgeben
        retry_messages = messages + [
            {"role": "assistant", "content": f"```sql\n{raw_sql}\n```"},
            {"role": "user", "content": 
             f"Das SQL hat einen Fehler: {exc}\n"
             f"Bitte korrigiere das SQL. "
             f"Beachte: casting_order hat KEIN machine_id-Feld, "
             f"verwende casting_order_line als Zwischentabelle."},
        ]
        return self._run(question, retry_messages, retry_count=1)
```

---

## Implementierungsplan

### Phase 1 — Sofort (Schema-Fix, kein Code-Änderung nötig)
- [x] `casting_order.machine_id` aus Schema entfernen
- [x] `casting_order_line`-Tabelle mit `machine_id` ins Schema aufnehmen
- [x] Join-Hints für häufige Verknüpfungen hinzufügen
- [ ] `init_odoo_schema --update` auf Prod ausführen
- [ ] Glossar-Einträge für häufige Terminologie ergänzen

### Phase 2 — Sprint (Few-Shot + Feedback, ~3 Tage Entwicklung)
- [ ] `NL2SQLExample`-Modell + Migration in `iil-aifw` Paket
- [ ] `NL2SQLFeedback`-Modell + automatische Fehlererfassung in engine.py
- [ ] `seed_nl2sql_examples` Management-Command mit 10 initialen Beispielen
- [ ] `promote_feedback` Management-Command
- [ ] `validate_schema` Management-Command

### Phase 3 — Mittelfristig (Self-Healing Retry)
- [ ] Retry-Mechanismus mit Fehler-Kontext in `engine.py`
- [ ] CI/CD-Integration von `validate_schema`
- [ ] Dashboard für Feedback-Review (Odoo-Backend-View)

---

## Erwartete Wirkung

| Fehlerklasse | Vor ADR-008 | Nach Phase 1 | Nach Phase 2 |
|---|---|---|---|
| Schema-Halluzination | häufig | selten | sehr selten |
| Join-Fehler | häufig | selten | selten |
| Terminologie-Mismatch | gelegentlich | gelegentlich | kaum |
| Wiederholte Fehler | immer | immer | nie (Few-Shot) |

---

## Sofort-Maßnahme: Schema auf Prod aktualisieren

```bash
docker exec aifw_service python manage.py init_odoo_schema \
    --model claude-3-haiku-20240307 \
    --fallback-model claude-3-haiku-20240307
```

Danach SchemaSource in aifw-DB aktualisiert → nächste Abfrage verwendet korrektes Schema.
