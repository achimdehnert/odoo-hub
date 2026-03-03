#!/usr/bin/env python3
"""
seed_nl2sql_demo.py — Umfangreiche Testdaten für NL2SQL Use-Case-Demonstrationen.

Aufruf (im odoo_db Container):
    docker exec -i odoo_db psql -U odoo -d odoo < scripts/seed_nl2sql_demo.sql
    # oder direkt:
    docker exec odoo_web python /mnt/extra-addons/seed_nl2sql_demo.py

Dieser Script läuft als reines SQL via psql — unabhängig von Odoo-Shell.
Erzeuge seed_nl2sql_demo.sql stattdessen.

HINWEIS: Dieses Wrapper-Script ruft das SQL-File auf.
"""
import subprocess, sys, os

SQL_FILE = os.path.join(os.path.dirname(__file__), "seed_nl2sql_demo.sql")
if not os.path.exists(SQL_FILE):
    print(f"ERROR: {SQL_FILE} nicht gefunden", file=sys.stderr)
    sys.exit(1)

result = subprocess.run(
    ["docker", "exec", "-i", "odoo_db", "psql", "-U", "odoo", "-d", "odoo", "-v", "ON_ERROR_STOP=1"],
    stdin=open(SQL_FILE),
    capture_output=False,
)
sys.exit(result.returncode)
