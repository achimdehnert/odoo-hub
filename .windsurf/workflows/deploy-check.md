---
description: Pre-deployment verification checklist
---

# Deploy-Check

```bash
git log --oneline -3 && git status
pytest tests/ -q --tb=short 2>&1 | tail -10
python manage.py migrate --check
```

- Tests gruen, CI gruen
- Destructive Migration? Backup zuerst via /backup
- .env.prod aktuell

```bash
curl -sf https://[DOMAIN]/livez/ && echo OK
```
