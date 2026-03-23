"""R27/EXP-P3-02: Tests for /v1/learning/remediation_plan endpoint wiring."""

from __future__ import annotations

import json
import types
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Minimal test for getRemediationPlan service function (unit)
# ---------------------------------------------------------------------------
from learning.service import getRemediationPlan


class TestGetRemediationPlanService:
    """Unit tests for the service-layer getRemediationPlan wrapper."""

    @patch("learning.service.generate_remediation_plan")
    @patch("learning.service.analytics_mod")
    @patch("learning.service.connect")
    def test_returns_plan_dict(self, mock_connect, mock_analytics, mock_gen_plan):
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_analytics.get_student_analytics.return_value = {"concepts": {}}
        mock_gen_plan.return_value = {"actions": [], "summary": "ok"}

        result = getRemediationPlan("stu1", db_path=":memory:", persist=False)
        assert isinstance(result, dict)
        assert result == {"actions": [], "summary": "ok"}

    @patch("learning.service.generate_remediation_plan")
    @patch("learning.service.analytics_mod")
    @patch("learning.service.connect")
    def test_passes_window_days(self, mock_connect, mock_analytics, mock_gen_plan):
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_analytics.get_student_analytics.return_value = {}
        mock_gen_plan.return_value = {}

        getRemediationPlan("stu1", windowDays=7, db_path=":memory:", persist=False)
        mock_analytics.get_student_analytics.assert_called_once()
        call_kwargs = mock_analytics.get_student_analytics.call_args
        assert call_kwargs[1]["window_days"] == 7

    @patch("learning.service.load_dataset")
    @patch("learning.service.generate_remediation_plan")
    @patch("learning.service.analytics_mod")
    @patch("learning.service.connect")
    def test_passes_dataset_name(self, mock_connect, mock_analytics, mock_gen_plan, mock_load):
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_analytics.get_student_analytics.return_value = {}
        mock_load.return_value = {"some": "blueprint"}
        mock_gen_plan.return_value = {}

        getRemediationPlan("stu1", datasetName="ds1", db_path=":memory:", persist=False)
        mock_load.assert_called_once_with("ds1")
        mock_gen_plan.assert_called_once()
        call_kwargs = mock_gen_plan.call_args
        assert call_kwargs[1]["blueprint"] == {"some": "blueprint"}

    @patch("learning.service.generate_remediation_plan")
    @patch("learning.service.analytics_mod")
    @patch("learning.service.connect")
    def test_no_dataset_uses_none_blueprint(self, mock_connect, mock_analytics, mock_gen_plan):
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_analytics.get_student_analytics.return_value = {}
        mock_gen_plan.return_value = {}

        getRemediationPlan("stu1", db_path=":memory:", persist=False)
        mock_gen_plan.assert_called_once()
        call_kwargs = mock_gen_plan.call_args
        assert call_kwargs[1]["blueprint"] is None

    @patch("learning.service.generate_remediation_plan")
    @patch("learning.service.analytics_mod")
    @patch("learning.service.connect")
    def test_persist_true_inserts_row(self, mock_connect, mock_analytics, mock_gen_plan):
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_analytics.get_student_analytics.return_value = {}
        mock_gen_plan.return_value = {"x": 1}

        getRemediationPlan("stu1", db_path=":memory:", persist=True)
        # Should have called execute for INSERT into la_students + la_remediation_plans
        insert_calls = [
            c for c in mock_conn.execute.call_args_list
            if "INSERT" in str(c)
        ]
        assert len(insert_calls) >= 2  # la_students + la_remediation_plans
        mock_conn.commit.assert_called()

    @patch("learning.service.generate_remediation_plan")
    @patch("learning.service.analytics_mod")
    @patch("learning.service.connect")
    def test_persist_false_no_insert(self, mock_connect, mock_analytics, mock_gen_plan):
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_analytics.get_student_analytics.return_value = {}
        mock_gen_plan.return_value = {}

        getRemediationPlan("stu1", db_path=":memory:", persist=False)
        # Only the schema ensure calls, no INSERT for plan
        insert_calls = [
            c for c in mock_conn.execute.call_args_list
            if "la_remediation_plans" in str(c)
        ]
        assert len(insert_calls) == 0

    @patch("learning.service.generate_remediation_plan")
    @patch("learning.service.analytics_mod")
    @patch("learning.service.connect")
    def test_connection_closed_on_success(self, mock_connect, mock_analytics, mock_gen_plan):
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_analytics.get_student_analytics.return_value = {}
        mock_gen_plan.return_value = {}

        getRemediationPlan("stu1", db_path=":memory:", persist=False)
        mock_conn.close.assert_called_once()

    @patch("learning.service.generate_remediation_plan")
    @patch("learning.service.analytics_mod")
    @patch("learning.service.connect")
    def test_connection_closed_on_error(self, mock_connect, mock_analytics, mock_gen_plan):
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_analytics.get_student_analytics.side_effect = RuntimeError("boom")

        with pytest.raises(RuntimeError):
            getRemediationPlan("stu1", db_path=":memory:", persist=False)
        mock_conn.close.assert_called_once()


# ---------------------------------------------------------------------------
# Endpoint wiring verification
# ---------------------------------------------------------------------------

class TestRemediationPlanEndpointWiring:
    """Verify server.py imports and endpoint registration."""

    def test_server_imports_get_remediation_plan(self):
        """server.py should import learning_get_remediation_plan."""
        import importlib
        # We just check the module attribute exists after import
        import server
        assert hasattr(server, "learning_get_remediation_plan")

    def test_request_model_exists(self):
        """RemediationPlanRequest model should exist in routers.learning module."""
        from routers.learning import RemediationPlanRequest
        assert RemediationPlanRequest is not None

    def test_request_model_fields(self):
        """RemediationPlanRequest should have student_id, dataset_name, window_days."""
        from routers.learning import RemediationPlanRequest
        model = RemediationPlanRequest
        fields = model.model_fields if hasattr(model, "model_fields") else model.__fields__
        assert "student_id" in fields
        assert "dataset_name" in fields
        assert "window_days" in fields

    def test_endpoint_registered(self):
        """The /v1/learning/remediation_plan route should be registered."""
        import server
        routes = [r.path for r in server.app.routes if hasattr(r, "path")]
        assert "/v1/learning/remediation_plan" in routes
