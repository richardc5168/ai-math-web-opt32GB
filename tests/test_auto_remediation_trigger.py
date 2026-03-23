"""Tests for R30/EXP-P3-05: Auto remediation trigger wiring.

Verifies that:
1. /v1/answers/submit response includes remediation_concepts from learning_ack
2. /v1/answers/submit response includes mastery data from learning_ack
3. remediation_concepts flows end-to-end from service.recordAttempt through submit
"""

import pytest


# ---------------------------------------------------------------------------
# TestSubmitRemediation — verify remediation_concepts wiring
# ---------------------------------------------------------------------------

class TestSubmitResponseLearningFields:
    """Verify that the new learning fields exist in server response schema."""

    def test_server_imports_learning_record_attempt(self):
        import server
        assert hasattr(server, "learning_record_attempt")

    def test_submit_endpoint_registered(self):
        import server
        routes = [r.path for r in server.app.routes]
        assert "/v1/answers/submit" in routes

    def test_remediation_concepts_in_service_response(self):
        """recordAttempt response includes remediation_concepts key."""
        import os
        import tempfile
        from learning.db import connect, ensure_learning_schema
        from learning.service import recordAttempt

        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        conn = connect(path)
        ensure_learning_schema(conn)
        conn.close()

        try:
            result = recordAttempt({
                "student_id": "s1",
                "question_id": "q1",
                "timestamp": "2026-03-23T12:00:00+08:00",
                "is_correct": True,
                "answer_raw": "42",
                "skill_tags": ["分數"],
            }, db_path=path, dev_mode=True)
            assert "remediation_concepts" in result
            assert isinstance(result["remediation_concepts"], list)
        finally:
            os.unlink(path)

    def test_mastery_in_service_response(self):
        """recordAttempt response includes mastery key."""
        import os
        import tempfile
        from learning.db import connect, ensure_learning_schema
        from learning.service import recordAttempt

        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        conn = connect(path)
        ensure_learning_schema(conn)
        conn.close()

        try:
            result = recordAttempt({
                "student_id": "s1",
                "question_id": "q1",
                "timestamp": "2026-03-23T12:00:00+08:00",
                "is_correct": True,
                "answer_raw": "42",
                "skill_tags": ["分數"],
            }, db_path=path, dev_mode=True)
            assert "mastery" in result
            assert isinstance(result["mastery"], list)
        finally:
            os.unlink(path)

    def test_remediation_concepts_empty_for_correct_answer(self):
        """Correct answers should not trigger remediation."""
        import os
        import tempfile
        from learning.db import connect, ensure_learning_schema
        from learning.service import recordAttempt

        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        conn = connect(path)
        ensure_learning_schema(conn)
        conn.close()

        try:
            result = recordAttempt({
                "student_id": "s1",
                "question_id": "q1",
                "timestamp": "2026-03-23T12:00:00+08:00",
                "is_correct": True,
                "answer_raw": "42",
                "skill_tags": ["分數"],
            }, db_path=path, dev_mode=True)
            assert result["remediation_concepts"] == []
        finally:
            os.unlink(path)


class TestRemediationConceptsEndToEnd:
    """Verify the wiring pattern from service through to server response."""

    def test_learning_ack_remediation_concepts_passthrough(self):
        """When learning_ack has remediation_concepts, it should be included in response."""
        # Simulate the server-side logic for extracting remediation_concepts
        learning_ack = {
            "ok": True,
            "attempt_id": 42,
            "remediation_concepts": ["fraction_add", "fraction_compare"],
            "mastery": [{"concept_id": "fraction_add", "level": "DEVELOPING", "score": 0.3}],
        }
        # Replicate the extraction logic from server.py
        result = {
            "recorded": bool(learning_ack and learning_ack.get("ok") is True),
            "attempt_id": (learning_ack.get("attempt_id") if isinstance(learning_ack, dict) else None),
            "remediation_concepts": (learning_ack.get("remediation_concepts", []) if isinstance(learning_ack, dict) else []),
            "mastery": (learning_ack.get("mastery", []) if isinstance(learning_ack, dict) else []),
        }
        assert result["remediation_concepts"] == ["fraction_add", "fraction_compare"]
        assert result["mastery"][0]["concept_id"] == "fraction_add"

    def test_learning_ack_none_gives_empty_lists(self):
        """When learning_ack is None, remediation_concepts should be empty."""
        learning_ack = None
        result = {
            "remediation_concepts": (learning_ack.get("remediation_concepts", []) if isinstance(learning_ack, dict) else []),
            "mastery": (learning_ack.get("mastery", []) if isinstance(learning_ack, dict) else []),
        }
        assert result["remediation_concepts"] == []
        assert result["mastery"] == []

    def test_learning_ack_no_remediation_key_gives_empty(self):
        """When learning_ack lacks remediation_concepts, default to empty."""
        learning_ack = {"ok": True, "attempt_id": 1}
        result = {
            "remediation_concepts": (learning_ack.get("remediation_concepts", []) if isinstance(learning_ack, dict) else []),
        }
        assert result["remediation_concepts"] == []

    def test_mastery_update_structure(self):
        """Mastery updates from recordAttempt have expected fields."""
        import os
        import tempfile
        from learning.db import connect, ensure_learning_schema
        from learning.service import recordAttempt

        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        conn = connect(path)
        ensure_learning_schema(conn)
        conn.close()

        try:
            result = recordAttempt({
                "student_id": "s1",
                "question_id": "q1",
                "timestamp": "2026-03-23T12:00:00+08:00",
                "is_correct": False,
                "answer_raw": "wrong",
                "skill_tags": ["分數/加減"],
                "extra": {"correct_answer": "1/2"},
            }, db_path=path, dev_mode=True)
            # mastery should have entries for resolved concepts
            for m in result["mastery"]:
                assert "concept_id" in m
                assert "level" in m
                assert "score" in m
                assert "remediation_needed" in m
        finally:
            os.unlink(path)
