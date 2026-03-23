"""Contract tests for API endpoint registration and response shapes.

Validates that:
  - All documented routes exist in the FastAPI app
  - HTTP methods match expectations
  - Health endpoints return expected shapes
  - Route counts don't silently change (detect accidental removal)

Uses ``app.routes`` introspection — no HTTP calls or DB needed.
"""
import pytest
from fastapi.routing import APIRoute

import server

app = server.app


def _routes() -> dict[str, list[str]]:
    """Return {path: [methods]} for all APIRoute entries (merged)."""
    out: dict[str, list[str]] = {}
    for r in app.routes:
        if isinstance(r, APIRoute):
            if r.path in out:
                out[r.path] = sorted(set(out[r.path]) | r.methods)
            else:
                out[r.path] = sorted(r.methods)
    return out


# =====================================================================
# Auth endpoint contracts
# =====================================================================

_AUTH_PATHS = [
    ("/v1/app/auth/provision", ["POST"]),
    ("/v1/app/auth/login", ["POST"]),
    ("/v1/app/auth/whoami", ["GET"]),
    ("/v1/app/auth/bootstrap", ["POST"]),
    ("/v1/app/auth/exchange", ["POST"]),
]


@pytest.mark.parametrize("path, methods", _AUTH_PATHS, ids=[p for p, _ in _AUTH_PATHS])
def test_auth_route_exists(path, methods):
    routes = _routes()
    assert path in routes, f"Route {path} not registered"
    assert routes[path] == methods


def test_auth_route_count():
    auth_paths = [p for p in _routes() if p.startswith("/v1/app/auth")]
    assert len(auth_paths) == 5, f"Expected 5 auth routes, got {len(auth_paths)}: {auth_paths}"


# =====================================================================
# Learning endpoint contracts
# =====================================================================

_LEARNING_PATHS = [
    ("/v1/learning/weekly_report", ["POST"]),
    ("/v1/learning/practice_next", ["POST"]),
    ("/v1/learning/remediation_plan", ["POST"]),
    ("/v1/student/concept-state", ["GET"]),
    ("/v1/student/hint-effectiveness", ["GET"]),
    ("/v1/student/concept-progress", ["GET"]),
    ("/v1/student/before-after", ["POST"]),
    ("/v1/practice/concept-next", ["POST"]),
    ("/v1/adaptive/state", ["GET"]),
    ("/v1/adaptive/dashboard", ["GET"]),
]


@pytest.mark.parametrize("path, methods", _LEARNING_PATHS, ids=[p for p, _ in _LEARNING_PATHS])
def test_learning_route_exists(path, methods):
    routes = _routes()
    assert path in routes, f"Route {path} not registered"
    assert routes[path] == methods


def test_learning_route_count():
    learning_paths = [
        p for p in _routes()
        if any(p.startswith(pfx) for pfx in ["/v1/learning/", "/v1/student/", "/v1/practice/concept", "/v1/adaptive/"])
    ]
    assert len(learning_paths) == 10, f"Expected 10 learning routes, got {len(learning_paths)}: {learning_paths}"


# =====================================================================
# Core question/answer flow contracts
# =====================================================================

_CORE_FLOW_PATHS = [
    ("/v1/questions/next", ["POST"]),
    ("/v1/questions/hint", ["POST"]),
    ("/v1/hints/next", ["POST"]),
    ("/v1/answers/submit", ["POST"]),
    ("/v1/custom/solve", ["POST"]),
]


@pytest.mark.parametrize("path, methods", _CORE_FLOW_PATHS, ids=[p for p, _ in _CORE_FLOW_PATHS])
def test_core_flow_route_exists(path, methods):
    routes = _routes()
    assert path in routes, f"Route {path} not registered"
    assert routes[path] == methods


# =====================================================================
# Engine endpoint contracts
# =====================================================================

_ENGINE_PATHS = [
    ("/v1/quadratic/next", ["POST"]),
    ("/v1/quadratic/check", ["POST"]),
    ("/v1/linear/next", ["POST"]),
    ("/v1/linear/check", ["POST"]),
    ("/validate/quadratic", ["POST"]),
    ("/api/mixed-multiply/diagnose", ["POST"]),
    ("/v1/knowledge/graph", ["GET"]),
]


@pytest.mark.parametrize("path, methods", _ENGINE_PATHS, ids=[p for p, _ in _ENGINE_PATHS])
def test_engine_route_exists(path, methods):
    routes = _routes()
    assert path in routes, f"Route {path} not registered"
    assert routes[path] == methods


# =====================================================================
# Teacher endpoint contracts
# =====================================================================

_TEACHER_PATHS = [
    ("/v1/teacher/classes", "GET"),
    ("/v1/teacher/classes", "POST"),
    ("/v1/teacher/classes/{class_id}/students", "POST"),
    ("/v1/teacher/classes/{class_id}/report", "GET"),
    ("/v1/teacher/classes/{class_id}/concept-report", "GET"),
]


@pytest.mark.parametrize(
    "path, method",
    _TEACHER_PATHS,
    ids=[f"{m} {p}" for p, m in _TEACHER_PATHS],
)
def test_teacher_route_exists(path, method):
    routes = _routes()
    assert path in routes, f"Route {path} not registered"
    assert method in routes[path]


# =====================================================================
# Report & Snapshot endpoint contracts
# =====================================================================

_REPORT_PATHS = [
    ("/v1/report/{student_id}", ["GET"]),
    ("/v1/reports/summary", ["GET"]),
    ("/v1/reports/parent_weekly", ["GET"]),
    ("/v1/app/report_snapshots", ["POST"]),
    ("/v1/app/report_snapshots/latest", ["POST"]),
    ("/v1/app/practice_events", ["POST"]),
]


@pytest.mark.parametrize("path, methods", _REPORT_PATHS, ids=[p for p, _ in _REPORT_PATHS])
def test_report_route_exists(path, methods):
    routes = _routes()
    assert path in routes, f"Route {path} not registered"
    assert routes[path] == methods


# =====================================================================
# Parent report registry contracts
# =====================================================================

_PARENT_REGISTRY_PATHS = [
    ("/v1/parent-report/registry/fetch", ["POST"]),
    ("/v1/parent-report/registry/upsert", ["POST"]),
]


@pytest.mark.parametrize("path, methods", _PARENT_REGISTRY_PATHS, ids=[p for p, _ in _PARENT_REGISTRY_PATHS])
def test_parent_registry_route_exists(path, methods):
    routes = _routes()
    assert path in routes, f"Route {path} not registered"
    assert routes[path] == methods


# =====================================================================
# Health & utility endpoint contracts
# =====================================================================

_HEALTH_PATHS = [
    ("/health", ["GET"]),
    ("/healthz", ["GET"]),
]


@pytest.mark.parametrize("path, methods", _HEALTH_PATHS, ids=[p for p, _ in _HEALTH_PATHS])
def test_health_route_exists(path, methods):
    routes = _routes()
    assert path in routes, f"Route {path} not registered"
    assert routes[path] == methods


# ── Health response shape tests (use TestClient) ──

from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_response_shape():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "ok" in data
    assert data["ok"] is True
    assert "ts" in data


def test_healthz_response_shape():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_knowledge_graph_response_shape():
    resp = client.get("/v1/knowledge/graph")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    # Knowledge graph should have nodes and relationships
    assert len(data) > 0


# =====================================================================
# Admin endpoint contracts
# =====================================================================

_ADMIN_PATHS = [
    ("/admin/bootstrap", ["POST"]),
    ("/v1/app/admin/login-failures", ["GET"]),
    ("/v1/app/admin/reset-password", ["POST"]),
    ("/v1/subscription/verify", ["GET"]),
]


@pytest.mark.parametrize("path, methods", _ADMIN_PATHS, ids=[p for p, _ in _ADMIN_PATHS])
def test_admin_route_exists(path, methods):
    routes = _routes()
    assert path in routes, f"Route {path} not registered"
    assert routes[path] == methods


# =====================================================================
# Total route count guard — detect accidental removals
# =====================================================================


def test_minimum_route_count():
    """App must have at least 45 API routes (prevents mass route removal)."""
    route_count = len([r for r in app.routes if isinstance(r, APIRoute)])
    assert route_count >= 45, f"Only {route_count} routes — expected ≥45"
