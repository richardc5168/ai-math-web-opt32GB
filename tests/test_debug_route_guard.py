"""R36/EXP-P4-02: Debug route guard tests.

Validates:
  1. _is_dev_mode() correctly reads DEV_MODE env var
  2. /_debug/accounts returns 404 when DEV_MODE is not set
  3. /_debug/students returns 404 when DEV_MODE is not set
  4. /_debug/* endpoints work when DEV_MODE=1
  5. Debug routes exist at module level (not nested inside other functions)
"""
import os
import inspect

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# 1. _is_dev_mode unit tests
# ---------------------------------------------------------------------------

class TestIsDevMode:
    def test_default_is_false(self, monkeypatch):
        monkeypatch.delenv("DEV_MODE", raising=False)
        import server
        assert server._is_dev_mode() is False

    def test_true_when_1(self, monkeypatch):
        monkeypatch.setenv("DEV_MODE", "1")
        import server
        assert server._is_dev_mode() is True

    def test_true_when_true(self, monkeypatch):
        monkeypatch.setenv("DEV_MODE", "true")
        import server
        assert server._is_dev_mode() is True

    def test_true_when_yes(self, monkeypatch):
        monkeypatch.setenv("DEV_MODE", "yes")
        import server
        assert server._is_dev_mode() is True

    def test_false_when_0(self, monkeypatch):
        monkeypatch.setenv("DEV_MODE", "0")
        import server
        assert server._is_dev_mode() is False

    def test_false_when_empty(self, monkeypatch):
        monkeypatch.setenv("DEV_MODE", "")
        import server
        assert server._is_dev_mode() is False

    def test_false_when_random(self, monkeypatch):
        monkeypatch.setenv("DEV_MODE", "maybe")
        import server
        assert server._is_dev_mode() is False


# ---------------------------------------------------------------------------
# 2. Debug endpoints return 404 without DEV_MODE
# ---------------------------------------------------------------------------

class TestDebugRoutesBlocked:
    @pytest.fixture(autouse=True)
    def _no_dev_mode(self, monkeypatch):
        monkeypatch.delenv("DEV_MODE", raising=False)

    @pytest.fixture
    def client(self):
        import server
        return TestClient(server.app)

    def test_debug_accounts_404(self, client):
        resp = client.get("/_debug/accounts")
        assert resp.status_code == 404

    def test_debug_students_404(self, client):
        resp = client.get("/_debug/students")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 3. Debug endpoints accessible with DEV_MODE=1
# ---------------------------------------------------------------------------

class TestDebugRoutesAccessible:
    @pytest.fixture(autouse=True)
    def _dev_mode_on(self, monkeypatch):
        monkeypatch.setenv("DEV_MODE", "1")

    @pytest.fixture
    def client(self):
        import server
        return TestClient(server.app)

    def test_debug_accounts_200(self, client):
        resp = client.get("/_debug/accounts")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_debug_students_200(self, client):
        resp = client.get("/_debug/students")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# 4. Debug routes are at module level (not nested)
# ---------------------------------------------------------------------------

class TestDebugRoutesModuleLevel:
    def test_debug_accounts_is_module_function(self):
        import server
        fn = server._debug_accounts
        # If it's a module-level function, its qualname has no dots (except class prefix)
        assert "." not in fn.__qualname__, (
            f"_debug_accounts should be a top-level function, got qualname={fn.__qualname__}"
        )

    def test_debug_students_is_module_function(self):
        import server
        fn = server._debug_students
        assert "." not in fn.__qualname__, (
            f"_debug_students should be a top-level function, got qualname={fn.__qualname__}"
        )

    def test_is_dev_mode_exists(self):
        import server
        assert callable(server._is_dev_mode)

    def test_debug_endpoints_check_dev_mode(self):
        """Source of debug endpoints must reference _is_dev_mode."""
        import server
        for fn_name in ("_debug_accounts", "_debug_students"):
            src = inspect.getsource(getattr(server, fn_name))
            assert "_is_dev_mode" in src, f"{fn_name} must check _is_dev_mode()"
