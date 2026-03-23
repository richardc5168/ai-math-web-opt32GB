"""Tests for R29/EXP-P3-04: Hint escalation wiring.

Verifies that:
1. getNextHint() in service.py calls remediation_flow.get_next_hint()
2. /v1/hints/next endpoint supports adaptive escalation via student_id
3. HintNextRequest model has new optional adaptive fields
"""

import importlib
import json
import os
import sqlite3
import tempfile

import pytest


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _init_db(path: str):
    """Initialize learning schema at *path* and return the path."""
    from learning.db import connect, ensure_learning_schema
    conn = connect(path)
    ensure_learning_schema(conn)
    conn.close()
    return path


@pytest.fixture
def tmp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    _init_db(path)
    yield path
    os.unlink(path)


def _insert_attempt(db_path, student_id, question_id, is_correct, concept_id=None, hints=0):
    """Insert a minimal attempt event row."""
    conn = sqlite3.connect(db_path)
    conn.execute("INSERT OR IGNORE INTO la_students(student_id, created_at, meta_json) VALUES (?,datetime('now'),'{}')", (student_id,))
    conn.execute("INSERT OR IGNORE INTO la_questions(question_id, created_at, meta_json) VALUES (?,datetime('now'),'{}')", (question_id,))
    concept_json = json.dumps([concept_id]) if concept_id else None
    conn.execute(
        """INSERT INTO la_attempt_events(
             student_id, question_id, ts, is_correct, answer_raw,
             duration_ms, hints_viewed_count, hint_steps_viewed_json,
             concept_ids_json
           ) VALUES (?,?,datetime('now'),?,?,?,?,?,?)""",
        (student_id, question_id, 1 if is_correct else 0, "ans", 5000, hints, "[]", concept_json),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# TestGetNextHintService — unit-level tests for service.getNextHint
# ---------------------------------------------------------------------------

class TestGetNextHintService:
    def test_returns_dict(self, tmp_db):
        from learning.service import getNextHint
        result = getNextHint("s1", "q1", "fraction_add", db_path=tmp_db)
        assert isinstance(result, dict)

    def test_has_required_keys(self, tmp_db):
        from learning.service import getNextHint
        result = getNextHint("s1", "q1", "fraction_add", db_path=tmp_db)
        for key in ("action_type", "hint_level", "reason", "flag_teacher", "session_state"):
            assert key in result, f"Missing key: {key}"

    def test_first_hint_is_concept_level(self, tmp_db):
        from learning.service import getNextHint
        result = getNextHint("s1", "q1", "fraction_add", db_path=tmp_db)
        assert result["action_type"] == "show_hint"
        assert result["hint_level"] == 1  # CONCEPT

    def test_escalates_after_previous_hints(self, tmp_db):
        from learning.service import getNextHint
        # Insert attempt with 2 hints already shown
        _insert_attempt(tmp_db, "s1", "q1", False, "fraction_add", hints=2)
        result = getNextHint("s1", "q1", "fraction_add", db_path=tmp_db)
        assert result["hint_level"] == 3  # SCAFFOLD (current=2 → next=3)

    def test_flag_teacher_false_initially(self, tmp_db):
        from learning.service import getNextHint
        result = getNextHint("s1", "q1", "fraction_add", db_path=tmp_db)
        assert result["flag_teacher"] is False

    def test_session_state_included(self, tmp_db):
        from learning.service import getNextHint
        result = getNextHint("s1", "q1", "fraction_add", db_path=tmp_db)
        ss = result["session_state"]
        assert "current_level" in ss
        assert "hints_shown" in ss
        assert "total_wrong_this_concept" in ss

    def test_wrong_count_from_db(self, tmp_db):
        from learning.service import getNextHint
        _insert_attempt(tmp_db, "s1", "q1", False, "fraction_add")
        _insert_attempt(tmp_db, "s1", "q2", False, "fraction_add")
        result = getNextHint("s1", "q3", "fraction_add", db_path=tmp_db)
        assert result["session_state"]["total_wrong_this_concept"] == 2

    def test_no_concept_id_still_works(self, tmp_db):
        from learning.service import getNextHint
        result = getNextHint("s1", "q1", "", db_path=tmp_db)
        assert result["action_type"] == "show_hint"


# ---------------------------------------------------------------------------
# TestHintEscalationImports — verify wiring at import level
# ---------------------------------------------------------------------------

class TestHintEscalationImports:
    def test_service_has_get_next_hint(self):
        from learning import service
        assert hasattr(service, "getNextHint")

    def test_init_exports_get_next_hint(self):
        import learning
        assert hasattr(learning, "getNextHint")

    def test_server_imports_learning_get_next_hint(self):
        import server
        assert hasattr(server, "learning_get_next_hint")

    def test_hint_next_request_has_student_id(self):
        import server
        fields = server.HintNextRequest.model_fields
        assert "student_id" in fields
        assert "concept_id" in fields
