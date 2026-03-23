"""R37/EXP-P4-03: CORS & Config Extraction tests.

Validates:
  1. CORS origins read from CORS_ORIGINS env var
  2. Auth/rate-limit constants read from env vars with safe defaults
  3. Default values match original hardcoded values
"""
import os
import inspect

import pytest


class TestCorsConfig:
    def test_default_cors_is_wildcard(self, monkeypatch):
        monkeypatch.delenv("CORS_ORIGINS", raising=False)
        # Need to check the middleware configuration
        import server
        # Inspect the CORS middleware
        for mw in server.app.user_middleware:
            if "CORSMiddleware" in str(mw):
                # The middleware kwargs contain allow_origins
                origins = mw.kwargs.get("allow_origins", [])
                assert origins == ["*"], f"Default CORS should be ['*'], got {origins}"
                return
        pytest.fail("CORSMiddleware not found in app middleware")

    def test_cors_reads_env_var(self):
        """Source of CORS middleware setup references CORS_ORIGINS env var."""
        import server
        src = inspect.getsource(server)
        assert "CORS_ORIGINS" in src, "CORS setup must reference CORS_ORIGINS env var"


class TestAuthConfigDefaults:
    """Verify env-var-driven constants have correct default values."""

    def test_bootstrap_token_ttl_default(self, monkeypatch):
        monkeypatch.delenv("BOOTSTRAP_TOKEN_TTL_S", raising=False)
        # Re-evaluate: since module already loaded, check current value
        import server
        # Default should be 300 (5 minutes) when env not set
        assert server._BOOTSTRAP_TOKEN_TTL_S == 300

    def test_max_outstanding_tokens_default(self, monkeypatch):
        monkeypatch.delenv("MAX_OUTSTANDING_TOKENS", raising=False)
        import server
        assert server._MAX_OUTSTANDING_TOKENS_PER_ACCOUNT == 5

    def test_rate_limit_window_default(self, monkeypatch):
        monkeypatch.delenv("RATE_LIMIT_WINDOW_S", raising=False)
        import server
        assert server._RATE_LIMIT_WINDOW_S == 60

    def test_rate_limit_login_default(self, monkeypatch):
        monkeypatch.delenv("RATE_LIMIT_LOGIN", raising=False)
        import server
        assert server._RATE_LIMIT_LOGIN == 5

    def test_rate_limit_bootstrap_default(self):
        import server
        assert server._RATE_LIMIT_BOOTSTRAP == 10

    def test_rate_limit_exchange_default(self):
        import server
        assert server._RATE_LIMIT_EXCHANGE == 20

    def test_lockout_threshold_default(self):
        import server
        assert server._LOGIN_LOCKOUT_THRESHOLD == 5

    def test_lockout_duration_default(self):
        import server
        assert server._LOGIN_LOCKOUT_DURATION_S == 300


class TestConfigEnvVarReferences:
    """Verify that source code references environment variable names."""

    def test_all_config_env_vars_in_source(self):
        import server
        src = inspect.getsource(server)
        env_vars = [
            "CORS_ORIGINS",
            "BOOTSTRAP_TOKEN_TTL_S",
            "MAX_OUTSTANDING_TOKENS",
            "RATE_LIMIT_WINDOW_S",
            "RATE_LIMIT_LOGIN",
            "RATE_LIMIT_BOOTSTRAP",
            "RATE_LIMIT_EXCHANGE",
            "LOGIN_LOCKOUT_THRESHOLD",
            "LOGIN_LOCKOUT_DURATION_S",
        ]
        for var in env_vars:
            assert var in src, f"Config var {var} must be referenced in server.py source"

    def test_constants_are_int(self):
        import server
        int_constants = [
            "_BOOTSTRAP_TOKEN_TTL_S",
            "_MAX_OUTSTANDING_TOKENS_PER_ACCOUNT",
            "_RATE_LIMIT_WINDOW_S",
            "_RATE_LIMIT_LOGIN",
            "_RATE_LIMIT_BOOTSTRAP",
            "_RATE_LIMIT_EXCHANGE",
            "_LOGIN_LOCKOUT_THRESHOLD",
            "_LOGIN_LOCKOUT_DURATION_S",
        ]
        for name in int_constants:
            val = getattr(server, name)
            assert isinstance(val, int), f"{name} should be int, got {type(val)}"
