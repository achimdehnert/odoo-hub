---
description: Testing Conventions T-01/T-02/T-03
---

# Testing Conventions

Pflicht vor git tag vX.Y.Z.

T-01: pytest.importorskip fuer optionale Deps
T-02: AsyncMock(side_effect=) statt wraps=
T-03: pytest.raises() fuer Exception-Contracts

```bash
grep -rn "^from aifw" tests/
grep -rn "AsyncMock(wraps=" tests/
pytest tests/ -v --tb=short
```
