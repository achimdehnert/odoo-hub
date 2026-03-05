# AGENT_HANDOVER — odoo-hub
> Lesen vor jeder Session. Aktualisieren nach jeder Session.

## Aktueller Stand
| Attribut | Wert |
|---|---|
| Zuletzt aktualisiert | 2026-03-05 |
| Branch | main |
| Phase | Development |

## Was wurde zuletzt getan?
- 2026-03-05 — GitHub-Infra eingerichtet (Issue Templates, Workflows, CORE_CONTEXT, AGENT_HANDOVER)

## Offene Aufgaben (Priorisiert)
- [ ] CORE_CONTEXT mit tatsächlicher App-Struktur befüllen
- [ ] /onboard-repo Workflow ausführen (Docker, CI/CD)
- [ ] Health-Endpoint /livez/ implementieren
- [ ] issue-triage.yml PROJECT_NUMBER + PROJECT_PAT setzen

## Bekannte Probleme / Technical Debt
| Problem | Priorität |
|---|---|
| CORE_CONTEXT Platzhalter — App-Struktur noch ausfüllen | Medium |

## Wichtige Befehle
```bash
pytest tests/ -q
python manage.py runserver
```
