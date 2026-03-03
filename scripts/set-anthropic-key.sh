#!/bin/bash
# set-anthropic-key.sh — Trägt ANTHROPIC_API_KEY sicher in SOPS ein (ADR-045)
#
# Ausführen: ./scripts/set-anthropic-key.sh
# Nur lokal — nie auf dem Server ausführen (age-Key nur lokal vorhanden)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> ANTHROPIC_API_KEY via SOPS eintragen (ADR-045)"
echo "    Key wird NUR im Speicher verarbeitet — nie auf Disk geschrieben."
echo ""
read -r -s -p "    ANTHROPIC_API_KEY (sk-ant-api03-...): " API_KEY
echo ""

if [ -z "${API_KEY}" ]; then
    echo "ERROR: Key darf nicht leer sein." >&2
    exit 1
fi

if [[ ! "${API_KEY}" == sk-ant-* ]]; then
    echo "WARN: Key beginnt nicht mit 'sk-ant-' — bitte prüfen."
fi

cd "${REPO_ROOT}"
python3 scripts/_add-aifw-secrets.py --anthropic-key "${API_KEY}"

echo ""
echo "==> Committe + pushe..."
git add secrets.enc.env
git commit -m "chore: set ANTHROPIC_API_KEY in SOPS (ADR-045)"
git push origin main

echo ""
echo "==> Deploye auf Server..."
./scripts/deploy-addon.sh mfg_management
