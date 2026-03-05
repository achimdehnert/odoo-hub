---
description: Schneller Produktions-Fix
---

# Hotfix

Kein Refactoring. Kleinster moeglicher Fix.

```bash
git log --oneline -10
git checkout main && git pull
git checkout -b hotfix/$(date +%Y%m%d)-BESCHREIBUNG
```

Fix -> Regression Test -> pytest tests/ -q -> PR -> /deploy
