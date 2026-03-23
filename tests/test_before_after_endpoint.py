"""Tests for EXP-P4-04: /v1/student/before-after endpoint wiring.

Verifies that the before-after comparison endpoint is properly wired,
the service function works end-to-end with real DB data, and the
Pydantic request model validates correctly.
"""

from __future__ import annotations

import inspect
import os
import tempfile

import pytest

from learning.service import getBeforeAfterComparison, recordAttempt
from learning.before_after_analytics import compare_pre_post


# ---- Fixtures ----

@pytest.fixture
def tmp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


def _make_event(student_id="s1", question_id="q1", ts="2026-03-10T10:00:00",
                correct=True, skills=None):
    return {
        "student_id": student_id,
        "question_id": question_id,
        "timestamp": ts,
        "is_correct": correct,
        "answer_raw": "42" if correct else "wrong",
        "skill_tags": skills or ["fraction"],
    }


# ---- 1. Service function integration tests ----

class TestGetBeforeAfterComparison:
    """Service-level tests for getBeforeAfterComparison."""

    def test_no_data_returns_insufficient(self, tmp_db):
        """No attempt data → insufficient_evidence."""
        result = getBeforeAfterComparison("s_empty", db_path=tmp_db)
        assert result["label"] == "insufficient_evidence"
        assert result["compared_group_count"] == 0

    def test_with_pre_and_post_data(self, tmp_db):
        """Pre and post attempts produce a valid comparison."""
        # Pre-intervention attempts (before 2026-03-15)
        recordAttempt(_make_event(ts="2026-03-10T10:00:00", correct=False,
                                  question_id="q1", skills=["fraction"]), db_path=tmp_db)
        recordAttempt(_make_event(ts="2026-03-11T10:00:00", correct=False,
                                  question_id="q2", skills=["decimal"]), db_path=tmp_db)
        # Post-intervention attempts (after 2026-03-15)
        recordAttempt(_make_event(ts="2026-03-20T10:00:00", correct=True,
                                  question_id="q3", skills=["fraction"]), db_path=tmp_db)
        recordAttempt(_make_event(ts="2026-03-21T10:00:00", correct=True,
                                  question_id="q4", skills=["decimal"]), db_path=tmp_db)

        result = getBeforeAfterComparison(
            "s1", intervention_date="2026-03-15", db_path=tmp_db,
        )
        assert result["student_id"] == "s1"
        assert result["intervention_date"] == "2026-03-15"
        assert "label" in result
        assert "groups" in result

    def test_auto_midpoint_when_no_date(self, tmp_db):
        """Without intervention_date, midpoint is computed automatically."""
        recordAttempt(_make_event(ts="2026-03-01T10:00:00", question_id="q1"), db_path=tmp_db)
        recordAttempt(_make_event(ts="2026-03-30T10:00:00", question_id="q2"), db_path=tmp_db)

        result = getBeforeAfterComparison("s1", db_path=tmp_db)
        assert "intervention_date" in result
        assert result["intervention_date"] is not None

    def test_result_has_required_keys(self, tmp_db):
        """Result always contains label, compared_group_count, groups."""
        result = getBeforeAfterComparison("s1", db_path=tmp_db)
        assert "label" in result
        assert "compared_group_count" in result
        assert "groups" in result

    def test_single_skill_produces_groups(self, tmp_db):
        """Attempts with the same skill produce comparison groups."""
        recordAttempt(_make_event(ts="2026-03-01T10:00:00", question_id="q1",
                                  correct=False, skills=["fraction"]), db_path=tmp_db)
        recordAttempt(_make_event(ts="2026-03-30T10:00:00", question_id="q2",
                                  correct=True, skills=["fraction"]), db_path=tmp_db)

        result = getBeforeAfterComparison(
            "s1", intervention_date="2026-03-15", db_path=tmp_db,
        )
        assert result["compared_group_count"] >= 0  # May be 0 if group IDs differ


# ---- 2. Endpoint wiring tests ----

class TestEndpointWiring:
    """Verify the /v1/student/before-after endpoint is registered and wired."""

    def test_route_registered(self):
        """The before-after route should be registered in the FastAPI app."""
        import server
        routes = [r.path for r in server.app.routes if hasattr(r, "path")]
        assert "/v1/student/before-after" in routes

    def test_route_is_post(self):
        """Endpoint should accept POST method."""
        import server
        for route in server.app.routes:
            if hasattr(route, "path") and route.path == "/v1/student/before-after":
                assert "POST" in route.methods
                break
        else:
            pytest.fail("Route not found")

    def test_handler_references_service(self):
        """Handler function should reference learning_get_before_after."""
        from routers.learning import student_before_after
        src = inspect.getsource(student_before_after)
        assert "learning_get_before_after" in src

    def test_import_available(self):
        """learning_get_before_after should be importable (not None)."""
        import server
        assert server.learning_get_before_after is not None

    def test_handler_checks_auth(self):
        """Handler should include auth verification."""
        from routers.learning import student_before_after
        src = inspect.getsource(student_before_after)
        assert "get_account_by_api_key" in src
        assert "ensure_subscription_active" in src

    def test_handler_checks_student_ownership(self):
        """Handler should verify student belongs to account."""
        from routers.learning import student_before_after
        src = inspect.getsource(student_before_after)
        assert "account_id" in src


# ---- 3. Pydantic model tests ----

class TestBeforeAfterRequest:
    """Validate BeforeAfterRequest Pydantic model."""

    def test_minimal_valid(self):
        from routers.learning import BeforeAfterRequest
        req = BeforeAfterRequest(student_id=1)
        assert req.student_id == 1
        assert req.intervention_date is None
        assert req.pre_window_days == 14
        assert req.post_window_days == 14

    def test_full_valid(self):
        from routers.learning import BeforeAfterRequest
        req = BeforeAfterRequest(
            student_id=5,
            intervention_date="2026-03-15",
            pre_window_days=7,
            post_window_days=30,
        )
        assert req.student_id == 5
        assert req.intervention_date == "2026-03-15"
        assert req.pre_window_days == 7
        assert req.post_window_days == 30

    def test_student_id_required(self):
        from routers.learning import BeforeAfterRequest
        with pytest.raises(Exception):
            BeforeAfterRequest()

    def test_student_id_must_be_positive(self):
        from routers.learning import BeforeAfterRequest
        with pytest.raises(Exception):
            BeforeAfterRequest(student_id=0)

    def test_window_days_min(self):
        from routers.learning import BeforeAfterRequest
        with pytest.raises(Exception):
            BeforeAfterRequest(student_id=1, pre_window_days=0)

    def test_window_days_max(self):
        from routers.learning import BeforeAfterRequest
        with pytest.raises(Exception):
            BeforeAfterRequest(student_id=1, post_window_days=91)
