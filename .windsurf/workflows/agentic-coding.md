---
description: Agentic Coding Workflow
---

# Agentic Coding

Governance bei moderate+: /governance-check aufrufen

Ausfuehrung:
1. Service Layer: views -> services -> models
2. Tests: test_should_*
3. ruff check . --fix && pytest tests/ -q

PR:
```bash
git checkout -b feat/ISSUE-beschreibung
git commit -m "feat(scope): desc - Closes #ISSUE"
```
