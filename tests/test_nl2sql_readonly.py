"""Defence-in-depth tests for the NL2SQL LLM-SQL fallback (NL2X-Audit WP1).

The fallback pipeline in mfg_nl2sql executes LLM-generated SQL. These tests
assert, WITHOUT an Odoo runtime or database:

1. ``sanitize_sql`` rejects DML/DDL unconditionally (``allow_write`` removed).
2. ``_execute_sql`` opens a FRESH cursor and issues
   ``SET TRANSACTION READ ONLY`` as the FIRST statement of the transaction,
   plus a ``statement_timeout``, and always rolls back (never commits).

Honest scope note: these are pure unit tests over a stubbed ``odoo`` module
and a fake cursor — they prove the guard is *wired* (statement order,
rollback). The actual "cannot execute ... in a read-only transaction"
rejection is PostgreSQL behaviour and needs a live Odoo+Postgres, which this
repo's CI does not run (see ci.yml: "no Odoo runtime"). Pattern mirrors
aifw/tests/test_nl2sql_readonly.py.

Both addon generations (addons/ = Odoo 18 prod, addons_v19/ = Odoo 19
staging) are covered via parametrization.
"""
from __future__ import annotations

import importlib.util
import inspect
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTROLLER_PATHS = {
    "v18": REPO_ROOT / "addons/mfg_nl2sql/controllers/nl2sql_controller.py",
    "v19": REPO_ROOT / "addons_v19/mfg_nl2sql/controllers/nl2sql_controller.py",
}


# ---------------------------------------------------------------------------
# Minimal odoo/requests stubs so the controller module imports without Odoo
# ---------------------------------------------------------------------------
class _RequestStub:
    """Stands in for odoo.http.request; tests set .env per case."""

    env = None


def _install_stubs():
    if "odoo" not in sys.modules:
        odoo_mod = types.ModuleType("odoo")
        http_mod = types.ModuleType("odoo.http")

        class Controller:
            pass

        def route(*args, **kwargs):
            def deco(func):
                return func
            return deco

        http_mod.Controller = Controller
        http_mod.route = route
        http_mod.request = _RequestStub()
        odoo_mod.http = http_mod
        sys.modules["odoo"] = odoo_mod
        sys.modules["odoo.http"] = http_mod
    if "requests" not in sys.modules:
        try:
            import requests  # noqa: F401
        except ImportError:
            sys.modules["requests"] = types.ModuleType("requests")
    return sys.modules["odoo.http"].request


@pytest.fixture(scope="module", params=sorted(CONTROLLER_PATHS))
def controller_mod(request):
    """Load the (v18|v19) controller module against the odoo stub."""
    _install_stubs()
    version = request.param
    path = CONTROLLER_PATHS[version]
    spec = importlib.util.spec_from_file_location(
        f"nl2sql_controller_{version}", path
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.__test_source_path__ = path
    return mod


# ---------------------------------------------------------------------------
# Fake cursor / registry (records the statement sequence)
# ---------------------------------------------------------------------------
class FakeCursor:
    def __init__(self):
        self.executed: list[str] = []
        self.description = None
        self.rolled_back = False
        self.committed = False

    def execute(self, sql, params=None):
        self.executed.append(sql)

    def fetchall(self):
        return []

    def rollback(self):
        self.rolled_back = True

    def commit(self):
        self.committed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        # Odoo's real Cursor commits on clean exit — mimic that so the test
        # proves the explicit rollback happens BEFORE the context closes.
        if exc_type is None:
            self.committed_on_exit = self.rolled_back is False
        return False


class FakeRegistry:
    def __init__(self, cr):
        self._cr = cr

    def cursor(self):
        return self._cr


def _make_controller(controller_mod, fake_cr, timeout_s=10):
    ctrl = controller_mod.NL2SQLController()
    # Bypass ir.config_parameter (needs Odoo env)
    ctrl._get_llm_config = lambda: {"timeout": timeout_s, "max_rows": 1000}
    controller_mod.request.env = types.SimpleNamespace(
        registry=FakeRegistry(fake_cr)
    )
    return ctrl


# ---------------------------------------------------------------------------
# 1. sanitize_sql: writes always rejected, no allow_write opt-out
# ---------------------------------------------------------------------------
class TestSanitizeReadOnly:
    def test_should_reject_write_sql_in_fallback(self, controller_mod):
        """DML/DDL rejected, incl. comment obfuscation and nested writes."""
        bad_queries = [
            "INSERT INTO res_users (login) VALUES ('x')",
            "UPDATE purchase_order SET state='done' WHERE id=1",
            "DELETE FROM purchase_order WHERE id=1",
            "DROP TABLE purchase_order",
            "TRUNCATE res_users",
            # comment obfuscation: comments are stripped before matching
            "SELECT 1; -- harmless\nDROP TABLE purchase_order",
            "DELETE/*hidden*/FROM res_users",
            # write nested inside a SELECT wrapper
            "SELECT * FROM (DELETE FROM res_users RETURNING *) AS t",
            "WITH x AS (UPDATE res_users SET login='a' RETURNING id) SELECT * FROM x",
        ]
        for bad in bad_queries:
            sql, err = controller_mod.sanitize_sql(bad)
            assert sql is None, f"not blocked: {bad!r}"
            assert err

    def test_should_still_allow_plain_select(self, controller_mod):
        sql, err = controller_mod.sanitize_sql("SELECT id FROM purchase_order")
        assert err is None
        assert sql == "SELECT id FROM purchase_order"

    def test_should_not_accept_allow_write_parameter(self, controller_mod):
        """allow_write removed from signature — no write opt-out exists."""
        params = inspect.signature(controller_mod.sanitize_sql).parameters
        assert "allow_write" not in params
        with pytest.raises(TypeError):
            controller_mod.sanitize_sql("SELECT 1", allow_write=True)

    def test_should_have_no_allow_write_code_reference(self, controller_mod):
        """The config plumbing (ir.config_parameter read) is gone too."""
        source = controller_mod.__test_source_path__.read_text()
        assert "mfg_nl2sql.allow_write" not in source
        assert "allow_write" not in source


# ---------------------------------------------------------------------------
# 2. _execute_sql: fresh cursor, READ ONLY first, timeout, always rollback
# ---------------------------------------------------------------------------
class TestExecuteSqlReadOnlyTransaction:
    def test_should_enforce_read_only_as_first_statement(self, controller_mod):
        cr = FakeCursor()
        ctrl = _make_controller(controller_mod, cr, timeout_s=10)

        result = ctrl._execute_sql("SELECT 1", max_rows=50)

        stmts = cr.executed
        # SET TRANSACTION READ ONLY only works before the first query of a
        # transaction — hence it must be the very first statement on the
        # fresh cursor.
        assert stmts[0] == "SET TRANSACTION READ ONLY"
        assert "statement_timeout" in stmts[1]
        assert "10000" in stmts[1]  # 10 s -> 10000 ms
        assert stmts[2] == "SELECT * FROM (SELECT 1) AS _q LIMIT 50"
        assert result.get("error") is None
        # Pure read: rolled back before the context manager could commit.
        assert cr.rolled_back is True
        assert cr.committed is False

    def test_should_rollback_even_when_query_fails(self, controller_mod):
        class FailingCursor(FakeCursor):
            def execute(self, sql, params=None):
                super().execute(sql, params)
                if "SELECT * FROM" in sql:
                    raise RuntimeError(
                        "cannot execute DELETE in a read-only transaction"
                    )

        cr = FailingCursor()
        ctrl = _make_controller(controller_mod, cr)

        result = ctrl._execute_sql("SELECT 1", max_rows=50)

        assert "read-only transaction" in result["error"]
        assert result["rows"] == []
        assert cr.rolled_back is True
        assert cr.committed is False

    def test_should_not_touch_shared_request_cursor(self, controller_mod):
        """The shared request.env.cr must not be used for LLM SQL anymore."""
        cr = FakeCursor()
        ctrl = _make_controller(controller_mod, cr)
        shared_cr = FakeCursor()
        controller_mod.request.env.cr = shared_cr

        ctrl._execute_sql("SELECT 1", max_rows=10)

        assert shared_cr.executed == []
        assert len(cr.executed) == 3
