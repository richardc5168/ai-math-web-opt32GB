"""Tests for get_hint_effectiveness_stats (EXP-A1).

Validates that the analytics function correctly computes hint success rate,
stuck-after-hint rate, by-level distribution, and by-concept breakdown
from existing la_attempt_events data.
"""

import json
import os
import sqlite3
import tempfile
from datetime import datetime, timedelta

import pytest

from learning.db import ensure_learning_schema
from learning.analytics import get_hint_effectiveness_stats


def _recent_iso(days_ago: int) -> str:
    return (datetime.now() - timedelta(days=days_ago)).isoformat(timespec="seconds")


def _make_db():
    tmp = tempfile.mkdtemp()
    db_path = os.path.join(tmp, "test.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ensure_learning_schema(conn)
    return conn


def _insert_attempt(conn, *, student_id="s1", question_id="q1", ts=None,
                    is_correct=True, hints_viewed_count=0,
                    concept_ids=None):
    if ts is None:
        ts = _recent_iso(1)
    concept_json = json.dumps(concept_ids or [])
    conn.execute(
        """INSERT INTO la_attempt_events
           (student_id, question_id, ts, is_correct, answer_raw,
            hints_viewed_count, hint_steps_viewed_json, concept_ids_json)
           VALUES (?,?,?,?,?,?,?,?)""",
        (student_id, question_id, ts, int(is_correct), "ans",
         hints_viewed_count, "[]", concept_json),
    )
    conn.commit()


class TestHintEffectivenessStats:
    def test_empty_returns_zeroes(self):
        conn = _make_db()
        result = get_hint_effectiveness_stats(conn, student_id="s1")
        assert result["total_hinted_attempts"] == 0
        assert result["hint_success_rate"] == 0.0
        assert result["stuck_after_hint_rate"] == 0.0
        assert result["by_level"] == {}
        assert result["by_concept"] == {}

    def test_no_hints_returns_empty(self):
        conn = _make_db()
        _insert_attempt(conn, hints_viewed_count=0, is_correct=True)
        _insert_attempt(conn, hints_viewed_count=0, is_correct=False)
        result = get_hint_effectiveness_stats(conn, student_id="s1")
        assert result["total_hinted_attempts"] == 0

    def test_single_hinted_correct(self):
        conn = _make_db()
        _insert_attempt(conn, hints_viewed_count=1, is_correct=True,
                        concept_ids=["fraction_add"])
        result = get_hint_effectiveness_stats(conn, student_id="s1")
        assert result["total_hinted_attempts"] == 1
        assert result["correct_with_hint"] == 1
        assert result["hint_success_rate"] == 1.0
        assert result["stuck_after_hint"] == 0
        assert result["stuck_after_hint_rate"] == 0.0

    def test_single_hinted_wrong(self):
        conn = _make_db()
        _insert_attempt(conn, hints_viewed_count=2, is_correct=False,
                        concept_ids=["fraction_sub"])
        result = get_hint_effectiveness_stats(conn, student_id="s1")
        assert result["total_hinted_attempts"] == 1
        assert result["correct_with_hint"] == 0
        assert result["hint_success_rate"] == 0.0
        assert result["stuck_after_hint"] == 1
        assert result["stuck_after_hint_rate"] == 1.0

    def test_mixed_success_rate(self):
        conn = _make_db()
        _insert_attempt(conn, question_id="q1", hints_viewed_count=1,
                        is_correct=True, concept_ids=["c1"])
        _insert_attempt(conn, question_id="q2", hints_viewed_count=2,
                        is_correct=False, concept_ids=["c1"])
        _insert_attempt(conn, question_id="q3", hints_viewed_count=1,
                        is_correct=True, concept_ids=["c2"])
        _insert_attempt(conn, question_id="q4", hints_viewed_count=3,
                        is_correct=False, concept_ids=["c2"])
        result = get_hint_effectiveness_stats(conn, student_id="s1")
        assert result["total_hinted_attempts"] == 4
        assert result["correct_with_hint"] == 2
        assert result["hint_success_rate"] == pytest.approx(0.5)
        assert result["stuck_after_hint"] == 2
        assert result["stuck_after_hint_rate"] == pytest.approx(0.5)

    def test_by_level_distribution(self):
        conn = _make_db()
        # Level 1: 2 attempts, 2 correct
        _insert_attempt(conn, question_id="q1", hints_viewed_count=1,
                        is_correct=True, concept_ids=["c1"])
        _insert_attempt(conn, question_id="q2", hints_viewed_count=1,
                        is_correct=True, concept_ids=["c1"])
        # Level 2: 1 attempt, 0 correct
        _insert_attempt(conn, question_id="q3", hints_viewed_count=2,
                        is_correct=False, concept_ids=["c1"])
        # Level 3: 1 attempt, 1 correct
        _insert_attempt(conn, question_id="q4", hints_viewed_count=3,
                        is_correct=True, concept_ids=["c1"])

        result = get_hint_effectiveness_stats(conn, student_id="s1")
        assert result["by_level"]["1"]["total"] == 2
        assert result["by_level"]["1"]["correct"] == 2
        assert result["by_level"]["1"]["rate"] == pytest.approx(1.0)
        assert result["by_level"]["2"]["total"] == 1
        assert result["by_level"]["2"]["correct"] == 0
        assert result["by_level"]["2"]["rate"] == pytest.approx(0.0)
        assert result["by_level"]["3"]["total"] == 1
        assert result["by_level"]["3"]["rate"] == pytest.approx(1.0)

    def test_by_concept_breakdown(self):
        conn = _make_db()
        _insert_attempt(conn, question_id="q1", hints_viewed_count=1,
                        is_correct=True, concept_ids=["fraction_add"])
        _insert_attempt(conn, question_id="q2", hints_viewed_count=1,
                        is_correct=False, concept_ids=["fraction_add"])
        _insert_attempt(conn, question_id="q3", hints_viewed_count=2,
                        is_correct=True, concept_ids=["decimal_mul"])

        result = get_hint_effectiveness_stats(conn, student_id="s1")
        fa = result["by_concept"]["fraction_add"]
        assert fa["total"] == 2
        assert fa["correct"] == 1
        assert fa["rate"] == pytest.approx(0.5)
        dm = result["by_concept"]["decimal_mul"]
        assert dm["total"] == 1
        assert dm["correct"] == 1

    def test_multi_concept_attempt(self):
        """An attempt with multiple concept_ids should count for each concept."""
        conn = _make_db()
        _insert_attempt(conn, hints_viewed_count=1, is_correct=True,
                        concept_ids=["c1", "c2", "c3"])
        result = get_hint_effectiveness_stats(conn, student_id="s1")
        assert len(result["by_concept"]) == 3
        for cid in ["c1", "c2", "c3"]:
            assert result["by_concept"][cid]["total"] == 1
            assert result["by_concept"][cid]["correct"] == 1

    def test_class_wide_no_student_id(self):
        """When student_id is None, aggregates across all students."""
        conn = _make_db()
        _insert_attempt(conn, student_id="s1", question_id="q1",
                        hints_viewed_count=1, is_correct=True, concept_ids=["c1"])
        _insert_attempt(conn, student_id="s2", question_id="q2",
                        hints_viewed_count=2, is_correct=False, concept_ids=["c1"])
        result = get_hint_effectiveness_stats(conn, student_id=None)
        assert result["total_hinted_attempts"] == 2
        assert result["hint_success_rate"] == pytest.approx(0.5)

    def test_window_days_filter(self):
        """Old attempts outside window_days should be excluded."""
        conn = _make_db()
        old_ts = (datetime.now() - timedelta(days=60)).isoformat(timespec="seconds")
        recent_ts = _recent_iso(1)
        _insert_attempt(conn, question_id="q1", ts=old_ts,
                        hints_viewed_count=1, is_correct=False, concept_ids=["c1"])
        _insert_attempt(conn, question_id="q2", ts=recent_ts,
                        hints_viewed_count=1, is_correct=True, concept_ids=["c1"])
        result = get_hint_effectiveness_stats(conn, student_id="s1", window_days=30)
        assert result["total_hinted_attempts"] == 1
        assert result["hint_success_rate"] == 1.0

    def test_generated_at_present(self):
        conn = _make_db()
        result = get_hint_effectiveness_stats(conn, student_id="s1")
        assert "generated_at" in result
        assert result["student_id"] == "s1"
        assert result["window_days"] == 30

    def test_evidence_chain_coverage_metrics(self):
        conn = _make_db()
        conn.execute(
            """INSERT INTO la_attempt_events
               (student_id, question_id, ts, is_correct, answer_raw,
                hints_viewed_count, hint_steps_viewed_json, concept_ids_json, extra_json)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                "s1", "q1", _recent_iso(1), 1, "ans",
                1, "[]", "[]",
                json.dumps({
                    "hint_level_used": 1,
                    "hint_sequence": [1],
                    "hint_open_ts": [1000, 2000],
                }),
            ),
        )
        conn.execute(
            """INSERT INTO la_attempt_events
               (student_id, question_id, ts, is_correct, answer_raw,
                hints_viewed_count, hint_steps_viewed_json, concept_ids_json, extra_json)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                "s1", "q2", _recent_iso(1), 0, "ans",
                2, "[]", "[]",
                json.dumps({"hint_level_used": 2}),
            ),
        )
        conn.commit()

        result = get_hint_effectiveness_stats(conn, student_id="s1")
        assert result["hint_level_used_coverage_count"] == 2
        assert result["hint_level_used_coverage_rate"] == pytest.approx(1.0)
        assert result["hint_sequence_coverage_count"] == 1
        assert result["hint_sequence_coverage_rate"] == pytest.approx(0.5)
        assert result["hint_open_ts_coverage_count"] == 1
        assert result["hint_open_ts_coverage_rate"] == pytest.approx(0.5)
        assert result["evidence_chain_complete_count"] == 1
        assert result["evidence_chain_complete_rate"] == pytest.approx(0.5)
