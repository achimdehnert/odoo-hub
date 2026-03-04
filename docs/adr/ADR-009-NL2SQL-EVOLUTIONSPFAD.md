# ADR-009: NL2SQL Evolutionspfad — RAG, Graph-Schema und Clarification-Agent

**Status:** Konzept  
**Datum:** 2026-03-04  
**Autoren:** IIL Engineering  
**Verwandte ADRs:** ADR-007 (iil-Package-Architektur), ADR-008 (Vorab-Training + Fehlerlernen)

---

## Problemraum

Der aktuelle NL2SQL-Stack (v0.7.0) löst bekannte Fehlerklassen gut:
- Schema-Halluzinationen → Join-Hints + Negative Constraints
- Terminologie-Mismatch → Odoo-Labels aus `ir.model.fields`
- Wiederholte Fehler → Few-Shot-Beispiele aus `NL2SQLExample`
- Einzelne SQL-Fehler → Self-Healing Retry

**Neue Schwachstellen die noch nicht adressiert sind:**

1. **Kontextuelles Vergessen**: Jede Abfrage ist stateless — der Agent "weiß" nicht was der User vorher gefragt hat
2. **Schema-Skalierung**: Mit mehr Tabellen wird das Schema-XML zu groß für den Kontext-Window
3. **Ambiguität**: „Wie läuft es?" — Agent kann nicht wissen ob Maschinen, Aufträge oder Qualität gemeint sind
4. **Domänenwissen fehlt**: Geschäftsregeln, KPIs, Schwellenwerte sind nicht im Schema
5. **Folgefragen**: „Zeig mir mehr Details zu GA-2024-001" funktioniert nur wenn vorher GA-2024-001 im Kontext war

---

## Evolutionspfad: 3 Stufen

### Stufe 1: RAG (Retrieval-Augmented Generation) — Schema + Wissen

**Was ist RAG?**  
Statt das gesamte Schema-XML in jeden Prompt zu laden, werden nur die **relevanten Teile** dynamisch abgerufen — basierend auf der aktuellen Frage via Embedding-Ähnlichkeit.

```
Frage: "Zeige Maschinen mit Störung"
    ↓
Embedding der Frage
    ↓
Vector-Suche in Schema-Chunks (casting_machine, casting_order_line)
    ↓
Nur relevante Schema-Teile in Prompt laden (statt alle 18 Tabellen)
    ↓
Kleiner Prompt → bessere Genauigkeit, weniger Kosten
```

**Konkret implementierbar via:**
```python
# aifw/nl2sql/rag.py
class SchemaRAG:
    """Dynamisches Schema-Retrieval per Embedding-Ähnlichkeit."""
    
    def retrieve(self, question: str, top_k: int = 4) -> list[SchemaChunk]:
        q_embedding = embed(question)
        return vector_search(q_embedding, self.chunks, top_k=top_k)
```

**Neue Datenbankentität: `NL2SQLSchemaChunk`**
```python
class NL2SQLSchemaChunk(models.Model):
    source       = ForeignKey(SchemaSource)
    table_name   = CharField(max_length=100)
    chunk_text   = TextField()          # Schema-Abschnitt als Text
    embedding    = VectorField(dim=1536) # pgvector
    
    class Meta:
        db_table = "aifw_nl2sql_schema_chunks"
```

**Zusätzliche RAG-Quellen:**
- `NL2SQLExample` — verifizierte Beispiele als Retrieval-Pool (statt statisch in Prompt)
- Geschäftsregeln-Dokumente: „Ausschuss > 5% = kritisch", „Priorität A = sofortige Wartung"
- Benutzerhandbücher, Prozessbeschreibungen

**Aufwand:** 2-3 Sprints (pgvector Extension, Embedding-Pipeline, Schema-Chunker)

---

### Stufe 2: Graph-Schema — Beziehungswissen

**Problem mit flachem XML-Schema:**
Das aktuelle Schema-XML kennt nur Tabellen und Spalten, nicht die **semantischen Beziehungen** zwischen Domänen-Konzepten.

```
XML:  casting_order_line.machine_id → casting_machine.id
Graph: GießAuftrag --[produziert_auf]--> Maschine
                                              ↑
                                         [wartet]--> Wartungsauftrag
                                              ↑
                                         [produziert]--> Teil
```

**Warum Graph?**
- Multi-Hop-Abfragen: „Welche Teile wurden auf Maschinen produziert die diese Woche gewartet wurden?"
- Graph-Traversal generiert automatisch korrekte JOIN-Ketten
- Domänen-Konzepte (Maschine, Auftrag, Qualität) als Knoten mit semantischer Bedeutung

**Implementierung mit Neo4j oder pgvector + adjacency:**
```python
# Schema-Graph als JSON im Schema-XML eingebettet
<relationships>
  <rel from="casting_order" to="casting_order_line" type="has_lines" 
       join="casting_order_line.order_id = casting_order.id"/>
  <rel from="casting_order_line" to="casting_machine" type="produced_on"
       join="casting_order_line.machine_id = casting_machine.id"/>
  <rel from="casting_machine" to="casting_order_line" type="runs_jobs"
       inverse="true"/>
</relationships>
```

Der NL2SQLEngine nutzt den Graphen für automatisches Join-Path-Finding:
```python
def find_join_path(from_table: str, to_table: str) -> list[JoinStep]:
    """BFS durch Schema-Graph → generiert JOIN-Kette."""
    # casting_order → casting_order_line → casting_machine
    return bfs_path(graph, from_table, to_table)
```

**Aufwand:** 1 Sprint (Relationship-XML im Schema, Join-Path-Finder)  
→ Geringster Aufwand, höchster sofortiger Nutzen

---

### Stufe 3: Clarification-Agent — „Fragen bei Unsicherheit"

**Kernidee:** Der NL2SQL-Agent erkennt ambige Anfragen und fragt gezielt nach, bevor er SQL generiert.

```
User: "Wie läuft es aktuell?"
                ↓
Agent erkennt: Keine konkreten Entitäten, multiple Interpretationen möglich
                ↓
Agent fragt: "Ich bin unsicher was gemeint ist. Bitte wähle:
              🏭 Maschinen (Betriebsstatus)
              📋 Aufträge (Produktionsfortschritt)  
              🔍 Qualität (Ausschussquote)
              📦 Lager (Bestandssituation)"
                ↓
User wählt: "Aufträge"
                ↓
Agent generiert: präzises SQL mit richtigem Fokus
```

**Technische Implementierung:**

```python
# aifw/nl2sql/clarification.py
class ClarificationDetector:
    """Erkennt ob eine Frage zu ambig für direktes SQL ist."""
    
    AMBIG_SYSTEM_PROMPT = """
    Analysiere ob diese Frage eindeutig genug für eine SQL-Abfrage ist.
    
    Antworte mit JSON:
    {
      "is_ambiguous": true/false,
      "confidence": 0.0-1.0,
      "reason": "...",
      "clarification_options": [
        {"label": "Maschinen", "description": "...", "keywords": ["maschine", "anlage"]},
        ...
      ]
    }
    
    Frage ist EINDEUTIG wenn:
    - Konkrete Entität genannt (Maschine, Auftrag, Lieferant)
    - Konkreter Zeitraum oder Filter
    - Follow-up auf vorherige Frage im Gesprächsverlauf
    
    Frage ist AMBIG wenn:
    - Allgemeine Statusfragen ("Wie läuft es?", "Was ist kritisch?")
    - Mehrere Tabellen möglich ohne klaren Kontext
    - Pronomen ohne Referenz ("Diese", "Die")
    """
    
    def analyze(self, question: str, history: list[dict]) -> ClarificationResult:
        result = sync_completion(
            action_code="nl2sql_clarify",
            messages=[{"role":"user","content":question}],
        )
        return ClarificationResult.from_json(result.content)
```

**Frontend-Integration (OWL-Panel):**
```javascript
// nl2sql_panel.js — Clarification-Dialog
if (res.needs_clarification) {
    this.state.clarification = {
        question: res.clarification_question,
        options: res.clarification_options,
    };
    return; // Warte auf User-Antwort
}
```

**UX im NL2SQL-Panel:**
```
┌─────────────────────────────────────────────────────────┐
│ 🤔 Ich bin nicht sicher was du meinst.                  │
│                                                          │
│ Worüber möchtest du eine Übersicht?                     │
│                                                          │
│  [🏭 Maschinen]  [📋 Aufträge]  [🔍 Qualität]         │
│  [📦 Lager]      [💰 Einkauf]                          │
└─────────────────────────────────────────────────────────┘
```

**Aufwand:** 1-2 Sprints (Clarification-LLM-Call, Frontend-Erweiterung)

---

## Kombination: Conversational NL2SQL

Die drei Stufen zusammen ergeben einen **echten Konversations-Agenten**:

```
Gesprächsverlauf:
────────────────
User: "Wie läuft die Produktion?"
Agent: "Meinst du Maschinen, Aufträge oder Qualität?" [Clarification]
User: "Aufträge"
Agent: [RAG holt Auftrags-Schema] → SQL → "32 Aufträge in Produktion"

User: "Welche davon haben Ausschuss?"
Agent: [Versteht "davon" = Aufträge aus vorheriger Abfrage, Graph-Join zu casting_order] 
       → SQL → "8 Aufträge mit Ausschuss > 5%"

User: "Zeig mir Details zu GA-2024-001"
Agent: [Kontext: GA-2024-001 war in vorheriger Antwort, Graph-Traversal zu order_lines + machine]
       → SQL → Details-Abfrage mit allen relevanten Joins
```

**Technisch: Conversation-State im `NL2SQLEngine`:**
```python
class ConversationState:
    """Speichert Kontext zwischen Abfragen einer Session."""
    session_id:     str
    history:        list[dict]      # Frage + SQL + Ergebnis-Zusammenfassung
    mentioned_ids:  dict[str, list] # {"casting_order": ["GA-2024-001", ...]}
    last_tables:    list[str]       # Tabellen der letzten Abfrage
    
    class Meta:
        db_table = "aifw_nl2sql_sessions"
        # TTL: 30 Minuten Inaktivität → Session gelöscht
```

---

## Priorisierung und Empfehlung

| Stufe | Nutzen | Aufwand | Empfehlung |
|---|---|---|---|
| **Graph-Relations im Schema-XML** | Hoch (Join-Fehler eliminiert) | 1 Sprint | **Sofort — Sprint 14** |
| **Clarification-Agent** | Hoch (UX deutlich besser) | 1-2 Sprints | **Sprint 14-15** |
| **RAG für große Schemas** | Mittel (erst ab 30+ Tabellen relevant) | 2-3 Sprints | Sprint 16+ |
| **Vollständiger Conversation-State** | Hoch (echter Agent) | 3 Sprints | Sprint 17+ |

**Sofort umsetzbar (keine neuen Dependencies):**
- Graph-Relations als `<relationships>`-Block ins Schema-XML
- Ambiguity-Detection: zusätzlicher LLM-Call mit JSON-Response-Format
- Clarification-Options im Frontend als Chip-Buttons

**Später (neue Dependencies):**
- pgvector für Embedding-basiertes RAG
- Session-Store für Conversation-State (Redis oder DB)

---

## Nächste konkrete Schritte

### Sprint 14: Graph-Relations + Clarification (Basis)

**Tag 1-2: Graph-Relations**
```xml
<!-- Erweiterung init_odoo_schema: Relationships-Block -->
<relationships>
  <rel from="casting_order" to="casting_order_line"
       type="hat_positionen" join_col="order_id"/>
  <rel from="casting_order_line" to="casting_machine"
       type="produziert_auf" join_col="machine_id"/>
  <rel from="casting_order_line" to="casting_alloy"
       type="verwendet_legierung" join_col="alloy_id"/>
</relationships>
```

**Tag 3-4: Ambiguity-Detection**
```python
# In NL2SQLEngine._run() vor dem SQL-Prompt:
clarity = self._check_clarity(question, conversation_history)
if clarity.is_ambiguous and not conversation_history:
    return NL2SQLResult(
        success=False,
        needs_clarification=True,
        clarification_question=clarity.question,
        clarification_options=clarity.options,
    )
```

**Tag 5: Frontend-Erweiterung**
```javascript
// nl2sql_panel.js: Clarification-UI als Chip-Buttons
if (res.needs_clarification) {
    this.state.clarification = res;
}
```

---

## Abgrenzung zu bestehenden Systemen

| Was | Wo | Status |
|---|---|---|
| Schema-XML + Labels | `init_odoo_schema` + `sync_odoo_schema` | ✅ Live |
| Few-Shot Beispiele | `NL2SQLExample` + `seed_nl2sql_examples` | ✅ Live |
| Auto-Fehlererfassung | `NL2SQLFeedback` | ✅ Live |
| Self-Healing Retry | `NL2SQLEngine._run()` | ✅ Live |
| Graph-Relations | Schema-XML `<relationships>` | 🔲 Sprint 14 |
| Clarification-Agent | `ClarificationDetector` + Frontend | 🔲 Sprint 14-15 |
| RAG Schema-Retrieval | `SchemaRAG` + pgvector | 🔲 Sprint 16+ |
| Conversation-State | `ConversationState` + Session-DB | 🔲 Sprint 17+ |
