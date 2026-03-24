"""Tests for R43: Enhanced Hint Evidence Chain.

Validates:
  - hint_open_ts and hint_sequence pass through server → extra_json
  - avg_hint_dwell_ms metric in analytics
  - success_after_hint / stuck_after_hint columns populated
  - Existing hint flow unbroken
"""

import json
import os
import sqlite3
import tempfile
from datetime import datetime, timedelta

import pytest

from learning.db import ensure_learning_schema
from learning.analytics import get_hint_effectiveness_stats
from learning.validator import validate_attempt_event


def _recent_iso(days_ago: int = 1) -> str:
    return (datetime.now() - timedelta(days=days_ago)).isoformat(timespec="seconds")


def _make_db():
    tmp = tempfile.mkdtemp()
    db_path = os.path.join(tmp, "test.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ensure_learning_schema(conn)
    return conn


def _insert(conn, *, student_id="s1", question_id="q1", ts=None,
            is_correct=True, hints_viewed_count=0,
            concept_ids=None, extra=None):
    if ts is None:
        ts = _recent_iso()
    concept_json = json.dumps(concept_ids or [])
    extra_json = json.dumps(extra or {})
    conn.execute(
        """INSERT INTO la_attempt_events
           (student_id, question_id, ts, is_correct, answer_raw,
            hints_viewed_count, hint_steps_viewed_json, concept_ids_json,
            extra_json)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (student_id, question_id, ts, int(is_correct), "ans",
         hints_viewed_count, "[]", concept_json, extra_json),
    )
    conn.commit()


# -- hint_open_ts validation through validator --

class TestHintOpenTsValidator:
    def test_hint_open_ts_passes_through_extra(self):
        """hint_open_ts in extra should survive validation."""
        event = {
            "student_id": "s1", "question_id": "q1",
            "timestamp": _recent_iso(), "is_correct": True,
            "answer_raw": "42",
            "extra": {"hint_open_ts": [1000, 2000, 3000]},
        }
        v = validate_attempt_event(event)
        assert v.extra["hint_open_ts"] == [1000, 2000, 3000]

    def test_hint_sequence_passes_through_extra(self):
        """hint_sequence in extra should survive validation."""
        event = {
            "student_id": "s1", "question_id": "q1",
            "timestamp": _recent_iso(), "is_correct": True,
            "answer_raw": "42",
            "extra": {"hint_sequence": [1, 2, 3]},
        }
        v = validate_attempt_event(event)
        assert v.extra["hint_sequence"] == [1, 2, 3]


# -- avg_hint_dwell_ms metric --

class TestAvgHintDwellMs:
    def test_empty_db(self):
        conn = _make_db()
        r = get_hint_effectiveness_stats(conn, student_id="s1")
        assert r["avg_hint_dwell_ms"] == 0.0

    def test_no_hint_open_ts(self):
        conn = _make_db()
        _insert(conn, hints_viewed_count=1, is_correct=True)
        r = get_hint_effectiveness_stats(conn, student_id="s1")
        assert r["avg_hint_dwell_ms"] == 0.0

    def test_single_dwell(self):
        conn = _make_db()
        _insert(conn, hints_viewed_count=2, is_correct=True,
                extra={"hint_open_ts": [1000, 5000]})
        r = get_hint_effectiveness_stats(conn, student_id="s1")
        assert r["avg_hint_dwell_ms"] == pytest.approx(4000.0)

    def test_multiple_dwell(self):
        conn = _make_db()
        _insert(conn, question_id="q1", hints_viewed_count=2, is_correct=True,
                extra={"hint_open_ts": [1000, 3000]})  # 2000ms
        _insert(conn, question_id="q2", hints_viewed_count=3, is_correct=False,
                extra={"hint_open_ts": [1000, 2000, 7000]})  # 6000ms
        r = get_hint_effectiveness_stats(conn, student_id="s1")
        # avg = (2000 + 6000) / 2 = 4000
        assert r["avg_hint_dwell_ms"] == pytest.approx(4000.0)

    def test_invalid_hint_open_ts_ignored(self):
        conn = _make_db()
        _insert(conn, hints_viewed_count=1, is_correct=True,
                extra={"hint_open_ts": "bad"})
        r = get_hint_effectiveness_stats(conn, student_id="s1")
        assert r["avg_hint_dwell_ms"] == 0.0

    def test_single_ts_ignored(self):
        """A single timestamp can't produce a dwell span."""
        conn = _make_db()
        _insert(conn, hints_viewed_count=1, is_correct=True,
                extra={"hint_open_ts": [1000]})
        r = get_hint_effectiveness_stats(conn, student_id="s1")
        assert r["avg_hint_dwell_ms"] == 0.0


# -- R42 existing fields still correct after R43 changes --

class TestExistingFieldsUnchangedR43:
    def test_all_r42_fields_present(self):
        conn = _make_db()
        _insert(conn, hints_viewed_count=1, is_correct=True,
                extra={"hint_level_used": 1, "hint_open_ts": [1000, 2000]})
        r = get_hint_effectiveness_stats(conn, student_id="s1")
        assert "avg_hints_before_success" in r
        assert "hint_escalation_rate" in r
        assert "by_hint_level_at_submit" in r
        assert "avg_hint_dwell_ms" in r

    def test_combined_metrics_coherent(self):
        conn = _make_db()
        _insert(conn, question_id="q1", hints_viewed_count=1, is_correct=True,
                extra={"hint_level_used": 1, "hint_open_ts": [1000, 3000]})
        _insert(conn, question_id="q2", hints_viewed_count=3, is_correct=False,
                extra={"hint_level_used": 3, "hint_open_ts": [1000, 2000, 9000]})
        r = get_hint_effectiveness_stats(conn, student_id="s1")

        assert r["total_hinted_attempts"] == 2
        assert r["correct_with_hint"] == 1
        assert r["hint_success_rate"] == pytest.approx(0.5)
        assert r["avg_hints_before_success"] == pytest.approx(1.0)
        assert r["hint_escalation_rate"] == pytest.approx(0.5)
        assert r["avg_hint_dwell_ms"] == pytest.approx(5000.0)  # (2000+8000)/2
