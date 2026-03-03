#!/usr/bin/env python3
"""
_add-aifw-secrets.py — Fügt aifw-Keys zu secrets.enc.env hinzu (ADR-045)

Liest bestehende Werte via `sops --decrypt`, ergänzt fehlende aifw-Keys,
und verschlüsselt die gesamte Datei neu via `sops --encrypt`.
Plaintext wird NUR im Speicher gehalten — nie auf Disk geschrieben.

Usage:
    python3 scripts/_add-aifw-secrets.py [--anthropic-key sk-ant-...]
"""
import argparse
import secrets
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
ENCRYPTED_FILE = REPO_ROOT / "secrets.enc.env"


def sops_decrypt(path: Path) -> dict[str, str]:
    """Entschlüsselt SOPS dotenv-Datei, gibt dict zurück."""
    result = subprocess.run(
        ["sops", "--decrypt", str(path)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    if result.returncode != 0:
        print(f"ERROR: sops decrypt fehlgeschlagen:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    values = {}
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Skip sops metadata lines
        if line.startswith("sops_") or "=ENC[" in line:
            continue
        if "=" in line:
            key, _, val = line.partition("=")
            values[key.strip()] = val.strip()
    return values


def sops_encrypt(content: str, path: Path) -> None:
    """Verschlüsselt dotenv-String und schreibt in path."""
    result = subprocess.run(
        [
            "sops",
            "--encrypt",
            "--input-type", "dotenv",
            "--output-type", "dotenv",
            "--filename-override", "secrets.enc.env",
            "/dev/stdin",
        ],
        input=content,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    if result.returncode != 0:
        print(f"ERROR: sops encrypt fehlgeschlagen:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    path.write_text(result.stdout)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--anthropic-key", default="", help="ANTHROPIC_API_KEY Wert")
    parser.add_argument("--openai-key", default="", help="OPENAI_API_KEY Wert")
    args = parser.parse_args()

    print(f"==> Lese {ENCRYPTED_FILE.name}...")
    existing = sops_decrypt(ENCRYPTED_FILE)
    print(f"    {len(existing)} bestehende Keys gefunden: {', '.join(sorted(existing))}")

    # Neue aifw-Keys — bestehende Werte behalten, neue ergänzen
    aifw_secret_key = existing.get(
        "AIFW_SECRET_KEY", secrets.token_hex(32)
    )
    aifw_db_password = existing.get(
        "AIFW_DB_PASSWORD",
        existing.get("NL2SQL_USER_PASSWORD", "ODO2026odo."),
    )
    odoo_nl2sql_password = existing.get(
        "ODOO_NL2SQL_PASSWORD",
        existing.get("NL2SQL_USER_PASSWORD", "ODO2026odo."),
    )
    anthropic_key = args.anthropic_key or existing.get("ANTHROPIC_API_KEY", "")
    openai_key = args.openai_key or existing.get("OPENAI_API_KEY", "")

    # Kompletter neuer Inhalt — Reihenfolge ist kanonisch
    new_values = {
        "POSTGRES_USER":           existing.get("POSTGRES_USER", "odoo"),
        "POSTGRES_PASSWORD":       existing["POSTGRES_PASSWORD"],
        "POSTGRES_DB":             existing.get("POSTGRES_DB", "odoo"),
        "ODOO_ADMIN_PASSWD":       existing["ODOO_ADMIN_PASSWD"],
        "ODOO_DOMAIN":             existing["ODOO_DOMAIN"],
        "ACME_EMAIL":              existing["ACME_EMAIL"],
        "SCHUTZTAT_DJANGO_API_KEY": existing.get("SCHUTZTAT_DJANGO_API_KEY", ""),
        "DEPLOYMENT_MCP_ODOO":     existing.get("DEPLOYMENT_MCP_ODOO", ""),
        "NL2SQL_USER_PASSWORD":    existing.get("NL2SQL_USER_PASSWORD", ""),
        "AIFW_SECRET_KEY":         aifw_secret_key,
        "AIFW_DB_PASSWORD":        aifw_db_password,
        "ODOO_NL2SQL_PASSWORD":    odoo_nl2sql_password,
        "ANTHROPIC_API_KEY":       anthropic_key,
        "OPENAI_API_KEY":          openai_key,
    }

    content = "\n".join(f"{k}={v}" for k, v in new_values.items()) + "\n"

    print(f"==> Verschlüssele {len(new_values)} Keys...")
    sops_encrypt(content, ENCRYPTED_FILE)

    print(f"OK: {ENCRYPTED_FILE} aktualisiert.")
    print("Neue Keys:")
    new_keys = set(new_values) - set(existing)
    for k in sorted(new_keys):
        print(f"  + {k}")
    if not new_keys:
        print("  (keine neuen Keys — alle bereits vorhanden, Werte aktualisiert)")

    if not anthropic_key:
        print("\nWARN: ANTHROPIC_API_KEY ist leer!")
        print("  Nochmal ausführen mit:")
        print("  python3 scripts/_add-aifw-secrets.py --anthropic-key sk-ant-api03-...")

    print("\nNächste Schritte:")
    print("  git add secrets.enc.env")
    print("  git commit -m 'chore: add aifw secrets to SOPS (ADR-045)'")
    print("  git push")
    print("  ./scripts/deploy-addon.sh mfg_management")


if __name__ == "__main__":
    main()
