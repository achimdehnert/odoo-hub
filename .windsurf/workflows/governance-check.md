---
description: Platform governance check
---

# Governance Check

Vor jeder neuen Funktionalitaet ausfuehren.

- Kein import anthropic/openai direkt -> iil-aifw
- Keine hardcodierten Credentials -> decouple.config()
- Kein Raw SQL -> Django ORM
- Keine Inline Prompt-Strings -> iil-promptfw
