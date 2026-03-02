#!/usr/bin/env bash
# scripts/create-secrets.sh — SOPS-Verschlüsselung für odoo-hub (ADR-045)
#
# Verschlüsselt Secrets via Pipe (Plaintext wird NIEMALS auf Disk geschrieben).
# Voraussetzungen:
#   - age >= 1.1.0  (brew install age / apt install age)
#   - sops >= 3.9.0 (brew install sops / apt install sops)
#   - age-Keypair in ~/.config/sops/age/keys.txt
#   - .sops.yaml mit age-Public-Keys befüllt
#
# Usage:
#   ./scripts/create-secrets.sh            # interaktiv (prompts für jeden Wert)
#   ./scripts/create-secrets.sh --verify   # überprüft ob secrets.enc.env lesbar ist
#   ./scripts/create-secrets.sh --show     # entschlüsselt + zeigt (nur lokal!)
#
# Nach Ausführung:
#   git add secrets.enc.env && git commit -m "chore: update encrypted secrets (ADR-045)"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENCRYPTED_FILE="${REPO_ROOT}/secrets.enc.env"
SOPS_YAML="${REPO_ROOT}/.sops.yaml"

# ── Präflight-Checks ──────────────────────────────────────────────────────────
check_dependencies() {
    local missing=()
    command -v age  >/dev/null 2>&1 || missing+=("age")
    command -v sops >/dev/null 2>&1 || missing+=("sops")

    if [[ ${#missing[@]} -gt 0 ]]; then
        echo "FEHLER: Fehlende Dependencies: ${missing[*]}"
        echo ""
        echo "Installation:"
        echo "  Ubuntu/WSL:   sudo apt install age && sudo apt install sops"
        echo "  macOS:        brew install age sops"
        echo "  Manual sops:  https://github.com/mozilla/sops/releases"
        exit 1
    fi

    if [[ ! -f "${SOPS_YAML}" ]]; then
        echo "FEHLER: .sops.yaml nicht gefunden in ${REPO_ROOT}"
        echo "  -> Bitte .sops.yaml befüllen (age-Public-Keys eintragen)"
        exit 1
    fi

    if grep -q "REPLACE_WITH" "${SOPS_YAML}"; then
        echo "FEHLER: .sops.yaml enthält noch Platzhalter (REPLACE_WITH_*_PUBLIC_KEY)"
        echo "  -> age-Keypair generieren: age-keygen -o ~/.config/sops/age/keys.txt"
        echo "  -> Public Key in .sops.yaml eintragen"
        exit 1
    fi

    if [[ -z "${SOPS_AGE_KEY:-}" ]] && [[ ! -f "${HOME}/.config/sops/age/keys.txt" ]]; then
        echo "FEHLER: Kein age-Private-Key gefunden."
        echo "  Setze SOPS_AGE_KEY oder lege ~/.config/sops/age/keys.txt an."
        exit 1
    fi
}

# ── Verify-Modus ─────────────────────────────────────────────────────────────
if [[ "${1:-}" == "--verify" ]]; then
    check_dependencies
    if [[ ! -f "${ENCRYPTED_FILE}" ]]; then
        echo "FEHLER: ${ENCRYPTED_FILE} existiert nicht."
        exit 1
    fi
    echo "Verifiziere secrets.enc.env..."
    if sops -d "${ENCRYPTED_FILE}" > /dev/null; then
        echo "OK: secrets.enc.env ist lesbar + entschlüsselbar."
        echo "Enthaltene Keys:"
        sops -d "${ENCRYPTED_FILE}" | grep -E "^[A-Z_]+" | cut -d= -f1 | sort | sed 's/^/  - /'
    else
        echo "FEHLER: Entschlüsselung fehlgeschlagen."
        exit 1
    fi
    exit 0
fi

# ── Show-Modus (nur lokal!) ───────────────────────────────────────────────────
if [[ "${1:-}" == "--show" ]]; then
    check_dependencies
    echo "WARNUNG: Zeigt Klartext-Secrets — nur auf vertrauenswürdigem Gerät ausführen!"
    echo ""
    sops -d "${ENCRYPTED_FILE}"
    exit 0
fi

# ── Interaktiver Verschlüsselungs-Modus ──────────────────────────────────────
check_dependencies

echo "=================================================="
echo " odoo-hub Secrets Verschlüsselung (ADR-045)"
echo "=================================================="
echo ""
echo "Werte werden interaktiv abgefragt. Kein Plaintext auf Disk."
echo "Abbrechen: CTRL+C"
echo ""

read_secret() {
    local prompt="$1"
    local var_name="$2"
    local is_required="${3:-true}"
    local value

    while true; do
        read -r -s -p "  ${prompt}: " value
        echo ""  # Newline nach silent input

        if [[ -z "${value}" ]]; then
            if [[ "${is_required}" == "true" ]]; then
                echo "  -> PFLICHTFELD — Wert darf nicht leer sein."
                continue
            else
                echo "  -> Übersprungen (optional)"
            fi
        fi
        echo "${var_name}=${value}"
        return
    done
}

echo "── PostgreSQL ────────────────────────────────────"
POSTGRES_USER_VAL=""
read -r -p "  POSTGRES_USER [odoo]: " POSTGRES_USER_VAL
POSTGRES_USER_VAL="${POSTGRES_USER_VAL:-odoo}"

# Secrets via Pipe zusammenbauen (kein tempfile!)
SECRETS_CONTENT=""

append_secret() {
    local key="$1"
    local prompt="$2"
    local required="${3:-true}"
    local value=""

    while true; do
        read -r -s -p "  ${prompt}: " value
        echo ""
        if [[ -z "${value}" && "${required}" == "true" ]]; then
            echo "  -> PFLICHTFELD"
            continue
        fi
        break
    done
    SECRETS_CONTENT+="${key}=${value}"$'\n'
}

SECRETS_CONTENT="POSTGRES_USER=${POSTGRES_USER_VAL}"$'\n'
append_secret "POSTGRES_PASSWORD"       "POSTGRES_PASSWORD (DB-Passwort)"
append_secret "POSTGRES_DB"             "POSTGRES_DB [odoo]: "

echo ""
echo "── Odoo ─────────────────────────────────────────"
append_secret "ODOO_ADMIN_PASSWD"       "ODOO_ADMIN_PASSWD (Master-Passwort für Odoo)"
append_secret "ODOO_DOMAIN"             "ODOO_DOMAIN (z.B. odoo.example.com)"
append_secret "ACME_EMAIL"              "ACME_EMAIL (Let's Encrypt)"

echo ""
echo "── Externe APIs ─────────────────────────────────"
append_secret "SCHUTZTAT_DJANGO_API_KEY" "SCHUTZTAT_DJANGO_API_KEY"         "false"
append_secret "DEPLOYMENT_MCP_ODOO"      "DEPLOYMENT_MCP_ODOO (Hetzner MCP)" "false"

echo ""
echo "── NL2SQL ───────────────────────────────────────"
append_secret "NL2SQL_USER_PASSWORD"    "NL2SQL_USER_PASSWORD (nl2sql_user DB-Password)" "false"

echo ""
echo "Verschlüssele mit SOPS + age..."
echo "${SECRETS_CONTENT}" | sops \
    --encrypt \
    --input-type dotenv \
    --output-type dotenv \
    --filename-override secrets.enc.env \
    /dev/stdin > "${ENCRYPTED_FILE}"

echo ""
echo "OK: ${ENCRYPTED_FILE} wurde verschlüsselt."
echo ""
echo "Verifizierung..."
if sops -d "${ENCRYPTED_FILE}" > /dev/null; then
    echo "OK: Entschlüsselung erfolgreich."
else
    echo "FEHLER: Verifizierung fehlgeschlagen — secrets.enc.env löschen und erneut versuchen."
    rm -f "${ENCRYPTED_FILE}"
    exit 1
fi

echo ""
echo "Nächste Schritte:"
echo "  git add secrets.enc.env"
echo "  git commit -m 'chore: update encrypted secrets (ADR-045)'"
echo "  git push"
echo ""
echo "GitHub Actions benötigt: SOPS_AGE_KEY in Repository Secrets"
echo "  -> Settings → Secrets → Actions → New repository secret"
echo "  -> Name: SOPS_AGE_KEY"
echo "  -> Value: Inhalt von ~/.config/sops/age/keys.txt"
