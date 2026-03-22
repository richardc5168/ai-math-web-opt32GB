"""Tests for EXP-03: error_classifier wiring into recordAttempt.

Verifies that error_type is populated when an incorrect attempt is recorded.
"""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from learning.service import recordAttempt
from learning.db import connect


@pytest.fixture
def tmp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


def _make_event(**overrides):
    base = {
        "student_id": "s1",
        "question_id": "q1",
        "timestamp": "2026-03-22T12:00:00+08:00",
        "is_correct": False,
        "answer_raw": "999",
        "skill_tags": ["fraction"],
    }
    base.update(overrides)
    return base


class TestErrorClassification:
    """EXP-03: error_type should be populated for incorrect attempts."""

    def test_incorrect_attempt_gets_error_type(self, tmp_db):
        """Any incorrect attempt should produce a non-None error_type."""
        result = recordAttempt(_make_event(), db_path=tmp_db)
        assert result["ok"]
        assert result["error_type"] is not None

    def test_correct_attempt_no_error_type(self, tmp_db):
        """Correct attempts should have error_type=None."""
        result = recordAttempt(
            _make_event(is_correct=True, answer_raw="42"),
            db_path=tmp_db,
        )
        assert result["error_type"] is None

    def test_error_type_persisted_in_db(self, tmp_db):
        """error_type column should be written to DB."""
        result = recordAttempt(_make_event(), db_path=tmp_db)
        conn = connect(tmp_db)
        try:
            row = conn.execute(
                "SELECT error_type FROM la_attempt_events WHERE rowid = ?",
                (result["attempt_id"],),
            ).fetchone()
            assert row is not None
            assert row[0] is not None
            assert row[0] == result["error_type"]
        finally:
            conn.close()

    def test_guess_pattern_fast_response(self, tmp_db):
        """Very fast incorrect response should be classified as guess_pattern."""
        result = recordAttempt(
            _make_event(duration_ms=1500),  # 1.5 sec = very fast
            db_path=tmp_db,
        )
        assert result["error_type"] == "guess_pattern"

    def test_stuck_after_hint(self, tmp_db):
        """Wrong answer after multiple hints should be stuck_after_hint."""
        result = recordAttempt(
            _make_event(
                duration_ms=15000,
                hints_viewed_count=3,
                hint_steps_viewed=[1, 2, 3],
            ),
            db_path=tmp_db,
        )
        assert result["error_type"] == "stuck_after_hint"

    def test_careless_close_answer(self, tmp_db):
        """Answer numerically close to correct should be careless."""
        result = recordAttempt(
            _make_event(
                answer_raw="101",
                duration_ms=10000,
                extra={"correct_answer": "100"},
            ),
            db_path=tmp_db,
        )
        assert result["error_type"] == "careless"

    def test_concept_misunderstanding_meta_signal(self, tmp_db):
        """Explicit method_wrong meta signal should be concept_misunderstanding."""
        result = recordAttempt(
            _make_event(
                duration_ms=10000,
                extra={"method_wrong": True},
            ),
            db_path=tmp_db,
        )
        assert result["error_type"] == "concept_misunderstanding"

    def test_default_concept_misunderstanding(self, tmp_db):
        """Distant wrong answer with no hints should default to concept_misunderstanding."""
        result = recordAttempt(
            _make_event(
                answer_raw="999",
                duration_ms=10000,
                extra={"correct_answer": "5"},
            ),
            db_path=tmp_db,
        )
        assert result["error_type"] == "concept_misunderstanding"

    def test_error_type_correct_attempt_db_null(self, tmp_db):
        """DB error_type should be NULL for correct attempts."""
        result = recordAttempt(
            _make_event(is_correct=True, answer_raw="42"),
            db_path=tmp_db,
        )
        conn = connect(tmp_db)
        try:
            row = conn.execute(
                "SELECT error_type FROM la_attempt_events WHERE rowid = ?",
                (result["attempt_id"],),
            ).fetchone()
            assert row[0] is None
        finally:
            conn.close()
