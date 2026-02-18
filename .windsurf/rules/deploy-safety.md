---
trigger: glob
globs:
  - "docker-compose*.yml"
  - ".env*"
  - "**/Dockerfile"
---

# Deploy Safety (deployment_mcp, Feb 2026)

## DeployLock

- Atomic `mkdir` lock at `{project_dir}/.deploy.lock/`
- Prevents concurrent deploys to same app
- Auto-breaks stale locks after 30 min
- Returns `{success: false, code: "deploy_locked"}` on conflict

## Timeouts

- Deploy tools: 900s, Compose ops: 600s, Default: 120s
- Configured in `timeout_config.py`, NOT hardcoded

## Shell Safety

- All SSH paths use `shlex.quote()`

## Rules

- Never bypass DeployLock when deploying via MCP tools
- Never commit `.env.prod` to git
