"""Tests for EXP-P4-05: Auth Router Extraction.

Verifies that auth endpoints moved to routers/auth.py are properly
registered, use lazy imports for circular-import safety, and maintain
all original functionality.
"""

from __future__ import annotations

import inspect

import pytest


class TestAuthRouterRegistered:
    """Verify all 5 auth routes are registered via the router."""

    def test_routes_exist(self):
        import server
        routes = [r.path for r in server.app.routes if hasattr(r, "path")]
        expected = [
            "/v1/app/auth/provision",
            "/v1/app/auth/login",
            "/v1/app/auth/whoami",
            "/v1/app/auth/bootstrap",
            "/v1/app/auth/exchange",
        ]
        for path in expected:
            assert path in routes, f"Route {path} not registered"

    def test_route_count(self):
        import server
        auth_routes = [
            r.path for r in server.app.routes
            if hasattr(r, "path") and "/v1/app/auth/" in r.path
        ]
        assert len(auth_routes) == 5

    def test_provision_is_post(self):
        import server
        for r in server.app.routes:
            if hasattr(r, "path") and r.path == "/v1/app/auth/provision":
                assert "POST" in r.methods
                break

    def test_login_is_post(self):
        import server
        for r in server.app.routes:
            if hasattr(r, "path") and r.path == "/v1/app/auth/login":
                assert "POST" in r.methods
                break

    def test_whoami_is_get(self):
        import server
        for r in server.app.routes:
            if hasattr(r, "path") and r.path == "/v1/app/auth/whoami":
                assert "GET" in r.methods
                break

    def test_bootstrap_is_post(self):
        import server
        for r in server.app.routes:
            if hasattr(r, "path") and r.path == "/v1/app/auth/bootstrap":
                assert "POST" in r.methods
                break

    def test_exchange_is_post(self):
        import server
        for r in server.app.routes:
            if hasattr(r, "path") and r.path == "/v1/app/auth/exchange":
                assert "POST" in r.methods
                break


class TestAuthRouterModuleStructure:
    """Verify router module is properly structured."""

    def test_router_import(self):
        from routers.auth import auth_router
        assert auth_router is not None

    def test_router_prefix(self):
        from routers.auth import auth_router
        assert auth_router.prefix == "/v1/app/auth"

    def test_router_has_5_routes(self):
        from routers.auth import auth_router
        assert len(auth_router.routes) == 5

    def test_pydantic_models_in_router_module(self):
        from routers.auth import (
            AppAuthLoginRequest,
            AppAuthProvisionRequest,
            BootstrapRequest,
            ExchangeRequest,
        )
        assert AppAuthLoginRequest is not None
        assert AppAuthProvisionRequest is not None
        assert BootstrapRequest is not None
        assert ExchangeRequest is not None

    def test_models_removed_from_server(self):
        """Auth Pydantic models should no longer be in server module."""
        import server
        assert not hasattr(server, "AppAuthLoginRequest")
        assert not hasattr(server, "AppAuthProvisionRequest")
        assert not hasattr(server, "BootstrapRequest")
        assert not hasattr(server, "ExchangeRequest")


class TestLazyImportPattern:
    """Verify handlers use lazy imports to avoid circular imports."""

    def test_provision_lazy_import(self):
        from routers.auth import app_auth_provision
        src = inspect.getsource(app_auth_provision)
        assert "import server as _srv" in src

    def test_login_lazy_import(self):
        from routers.auth import app_auth_login
        src = inspect.getsource(app_auth_login)
        assert "import server as _srv" in src

    def test_whoami_lazy_import(self):
        from routers.auth import app_auth_whoami
        src = inspect.getsource(app_auth_whoami)
        assert "import server as _srv" in src

    def test_bootstrap_lazy_import(self):
        from routers.auth import app_auth_bootstrap
        src = inspect.getsource(app_auth_bootstrap)
        assert "import server as _srv" in src

    def test_exchange_lazy_import(self):
        from routers.auth import app_auth_exchange
        src = inspect.getsource(app_auth_exchange)
        assert "import server as _srv" in src


class TestServerPyReduced:
    """Verify server.py is smaller after extraction."""

    def test_no_auth_endpoint_decorators_in_server(self):
        """server.py should not have @app decorators for auth paths."""
        src = inspect.getsource(__import__("server"))
        assert '@app.post("/v1/app/auth/provision"' not in src
        assert '@app.post("/v1/app/auth/login"' not in src
        assert '@app.get("/v1/app/auth/whoami"' not in src
        assert '@app.post("/v1/app/auth/bootstrap"' not in src
        assert '@app.post("/v1/app/auth/exchange"' not in src

    def test_include_router_in_server(self):
        """server.py should include the auth router."""
        src = inspect.getsource(__import__("server"))
        assert "include_router" in src
        assert "auth_router" in src
