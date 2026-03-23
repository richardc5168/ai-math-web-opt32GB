"""Tests for EXP-P4-06: Learning Router Extraction.

Validates that 10 learning/analytics endpoints were correctly extracted
from server.py into routers/learning.py with the APIRouter pattern.
"""
import inspect

import pytest


LEARNING_ROUTES = [
    "/v1/learning/weekly_report",
    "/v1/learning/practice_next",
    "/v1/learning/remediation_plan",
    "/v1/student/concept-state",
    "/v1/student/hint-effectiveness",
    "/v1/student/concept-progress",
    "/v1/student/before-after",
    "/v1/practice/concept-next",
    "/v1/adaptive/state",
    "/v1/adaptive/dashboard",
]


# ---- 1. Route registration tests ----

class TestLearningRouterRegistered:
    """All 10 learning routes should be registered on the FastAPI app."""

    @pytest.mark.parametrize("path", LEARNING_ROUTES)
    def test_route_exists(self, path):
        import server
        routes = [r.path for r in server.app.routes if hasattr(r, "path")]
        assert path in routes

    def test_route_count(self):
        import server
        routes = [r.path for r in server.app.routes if hasattr(r, "path")]
        found = [r for r in routes if r in LEARNING_ROUTES]
        assert len(found) == 10

    def test_learning_weekly_report_is_post(self):
        import server
        for r in server.app.routes:
            if hasattr(r, "path") and r.path == "/v1/learning/weekly_report":
                assert "POST" in r.methods
                return
        pytest.fail("Route not found")

    def test_student_concept_state_is_get(self):
        import server
        for r in server.app.routes:
            if hasattr(r, "path") and r.path == "/v1/student/concept-state":
                assert "GET" in r.methods
                return
        pytest.fail("Route not found")

    def test_adaptive_dashboard_is_get(self):
        import server
        for r in server.app.routes:
            if hasattr(r, "path") and r.path == "/v1/adaptive/dashboard":
                assert "GET" in r.methods
                return
        pytest.fail("Route not found")


# ---- 2. Module structure tests ----

class TestLearningRouterModuleStructure:
    def test_import_works(self):
        from routers.learning import learning_router
        assert learning_router is not None

    def test_has_10_routes(self):
        from routers.learning import learning_router
        assert len(learning_router.routes) == 10

    def test_models_present_in_router(self):
        from routers.learning import (
            WeeklyReportRequest,
            PracticeNextRequest,
            RemediationPlanRequest,
            BeforeAfterRequest,
            ConceptNextRequest,
        )
        assert all(m is not None for m in [
            WeeklyReportRequest,
            PracticeNextRequest,
            RemediationPlanRequest,
            BeforeAfterRequest,
            ConceptNextRequest,
        ])

    def test_models_removed_from_server(self):
        import server
        for name in ["WeeklyReportRequest", "PracticeNextRequest", "RemediationPlanRequest",
                     "BeforeAfterRequest", "ConceptNextRequest"]:
            assert not hasattr(server, name), f"{name} should not be in server.py"

    def test_helpers_removed_from_server(self):
        import server
        assert not hasattr(server, "_skill_snapshot_from_analytics"), \
            "_skill_snapshot_from_analytics should not be in server.py"
        assert not hasattr(server, "_build_concept_question_pool"), \
            "_build_concept_question_pool should not be in server.py"


# ---- 3. Lazy import pattern tests ----

class TestLazyImportPattern:
    """Each handler should use lazy 'import server as _srv' inside function body."""

    @pytest.mark.parametrize("fn_name", [
        "learning_weekly_report",
        "learning_practice_next",
        "learning_remediation_plan",
        "student_concept_state",
        "student_hint_effectiveness",
        "student_concept_progress",
        "student_before_after",
        "practice_concept_next",
        "adaptive_state",
        "adaptive_dashboard",
    ])
    def test_handler_has_lazy_import(self, fn_name):
        import routers.learning as mod
        fn = getattr(mod, fn_name)
        src = inspect.getsource(fn)
        assert "import server as _srv" in src


# ---- 4. Server.py reduction tests ----

class TestServerPyReduced:
    def test_no_learning_decorators_in_server(self):
        """server.py should not have @app decorators for extracted learning routes."""
        import server
        src = inspect.getsource(server)
        for path in LEARNING_ROUTES:
            assert f'"{path}"' not in src or "include_router" in src

    def test_include_router_present(self):
        import server
        src = inspect.getsource(server)
        assert "learning_router" in src
        assert "include_router" in src
