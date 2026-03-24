"""Tests for R47: Hint Evidence Pipeline end-to-end.

Validates the full evidence chain:
  1. Frontend-shaped attempt payload with hint_sequence, hint_open_ts,
     hint_level_used arrives at recordAttempt()
  2. Fields survive validation and persist in extra_json
  3. get_hint_effectiveness_stats() reads them correctly and produces
     all coverage and dwell metrics
  4. Multiple attempts produce correct aggregated coverage rates

This closes the verification gap noted in R46's remaining risks.
"""

import json
import os
import sqlite3
import tempfile
from datetime import datetime, timedelta

import pytest

from learning.db import ensure_learning_schema
from learning.analytics import get_hint_effectiveness_stats
from learning.service import recordAttempt
from learning.validator import validate_attempt_event


def _recent_iso(days_ago: float = 0.5) -> str:
    return (datetime.now() - timedelta(days=days_ago)).isoformat(timespec="seconds")


@pytest.fixture
def tmp_db(tmp_path):
    db_path = str(tmp_path / "pipeline_test.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ensure_learning_schema(conn)
    conn.close()
    return db_path


def _make_attempt_event(*, student_id="s1", question_id="q1",
                        is_correct=True, hints_viewed_count=0,
                        hint_level_used=None, hint_sequence=None,
                        hint_open_ts=None, extra=None):
    """Build a frontend-shaped attempt event dict."""
    ev = {
        "student_id": student_id,
        "question_id": question_id,
        "timestamp": _recent_iso(),
        "is_correct": is_correct,
        "answer_raw": "42",
        "hints_viewed_count": hints_viewed_count,
        "extra": extra or {},
    }
    if hint_level_used is not None:
        ev["extra"]["hint_level_used"] = hint_level_used
    if hint_sequence is not None:
        ev["extra"]["hint_sequence"] = hint_sequence
    if hint_open_ts is not None:
        ev["extra"]["hint_open_ts"] = hint_open_ts
    return ev


# ── Pipeline: frontend payload → recordAttempt → analytics ─────────


class TestHintEvidencePipeline:
    """End-to-end: attempt event → DB → analytics metrics."""

    def test_full_evidence_chain_roundtrip(self, tmp_db):
        """All three evidence fields survive the full pipeline."""
        event = _make_attempt_event(
            hints_viewed_count=2,
            hint_level_used=2,
            hint_sequence=[1, 2],
            hint_open_ts=[1000, 5000],
            is_correct=True,
        )
        result = recordAttempt(event, db_path=tmp_db)
        assert "attempt_id" in result

        # Read back via analytics
        conn = sqlite3.connect(tmp_db)
        conn.row_factory = sqlite3.Row
        stats = get_hint_effectiveness_stats(conn, student_id="s1")

        assert stats["total_hinted_attempts"] == 1
        assert stats["hint_level_used_coverage_rate"] == pytest.approx(1.0)
        assert stats["hint_sequence_coverage_rate"] == pytest.approx(1.0)
        assert stats["hint_open_ts_coverage_rate"] == pytest.approx(1.0)
        assert stats["evidence_chain_complete_rate"] == pytest.approx(1.0)

    def test_partial_evidence_lowers_coverage(self, tmp_db):
        """An attempt with only hint_level_used (no sequence/ts) reduces coverage."""
        # Attempt 1: full evidence
        recordAttempt(_make_attempt_event(
            question_id="q1", hints_viewed_count=2,
            hint_level_used=2, hint_sequence=[1, 2], hint_open_ts=[1000, 5000],
        ), db_path=tmp_db)

        # Attempt 2: only hint_level_used
        recordAttempt(_make_attempt_event(
            question_id="q2", hints_viewed_count=1,
            hint_level_used=1,
        ), db_path=tmp_db)

        conn = sqlite3.connect(tmp_db)
        conn.row_factory = sqlite3.Row
        stats = get_hint_effectiveness_stats(conn, student_id="s1")

        assert stats["total_hinted_attempts"] == 2
        assert stats["hint_level_used_coverage_rate"] == pytest.approx(1.0)
        assert stats["hint_sequence_coverage_rate"] == pytest.approx(0.5)
        assert stats["hint_open_ts_coverage_rate"] == pytest.approx(0.5)
        assert stats["evidence_chain_complete_rate"] == pytest.approx(0.5)

    def test_no_evidence_fields_zero_coverage(self, tmp_db):
        """An attempt with hints but no evidence fields → 0% coverage."""
        recordAttempt(_make_attempt_event(
            hints_viewed_count=1,
        ), db_path=tmp_db)

        conn = sqlite3.connect(tmp_db)
        conn.row_factory = sqlite3.Row
        stats = get_hint_effectiveness_stats(conn, student_id="s1")

        assert stats["total_hinted_attempts"] == 1
        assert stats["evidence_chain_complete_rate"] == pytest.approx(0.0)

    def test_dwell_ms_from_timestamps(self, tmp_db):
        """avg_hint_dwell_ms computed from hint_open_ts span."""
        recordAttempt(_make_attempt_event(
            question_id="q1", hints_viewed_count=3,
            hint_level_used=3,
            hint_sequence=[1, 2, 3],
            hint_open_ts=[1000, 3000, 8000],
        ), db_path=tmp_db)

        conn = sqlite3.connect(tmp_db)
        conn.row_factory = sqlite3.Row
        stats = get_hint_effectiveness_stats(conn, student_id="s1")

        # Dwell = last - first = 8000 - 1000 = 7000ms
        assert stats["avg_hint_dwell_ms"] == pytest.approx(7000.0)

    def test_by_hint_level_at_submit_distribution(self, tmp_db):
        """by_hint_level_at_submit groups correctly."""
        recordAttempt(_make_attempt_event(
            question_id="q1", hints_viewed_count=1,
            hint_level_used=1, is_correct=True,
        ), db_path=tmp_db)
        recordAttempt(_make_attempt_event(
            question_id="q2", hints_viewed_count=2,
            hint_level_used=2, is_correct=False,
        ), db_path=tmp_db)
        recordAttempt(_make_attempt_event(
            question_id="q3", hints_viewed_count=2,
            hint_level_used=2, is_correct=True,
        ), db_path=tmp_db)

        conn = sqlite3.connect(tmp_db)
        conn.row_factory = sqlite3.Row
        stats = get_hint_effectiveness_stats(conn, student_id="s1")

        assert stats["by_hint_level_at_submit"]["1"]["total"] == 1
        assert stats["by_hint_level_at_submit"]["1"]["correct"] == 1
        assert stats["by_hint_level_at_submit"]["2"]["total"] == 2
        assert stats["by_hint_level_at_submit"]["2"]["correct"] == 1

    def test_escalation_rate_calculation(self, tmp_db):
        """hint_escalation_rate = attempts with hints_viewed_count >= 2."""
        recordAttempt(_make_attempt_event(
            question_id="q1", hints_viewed_count=1,
        ), db_path=tmp_db)
        recordAttempt(_make_attempt_event(
            question_id="q2", hints_viewed_count=3,
        ), db_path=tmp_db)

        conn = sqlite3.connect(tmp_db)
        conn.row_factory = sqlite3.Row
        stats = get_hint_effectiveness_stats(conn, student_id="s1")

        assert stats["hint_escalation_rate"] == pytest.approx(0.5)

    def test_class_wide_aggregation(self, tmp_db):
        """student_id=None aggregates across all students."""
        recordAttempt(_make_attempt_event(
            student_id="alice", question_id="q1", hints_viewed_count=2,
            hint_level_used=2, hint_sequence=[1, 2], hint_open_ts=[1000, 3000],
        ), db_path=tmp_db)
        recordAttempt(_make_attempt_event(
            student_id="bob", question_id="q1", hints_viewed_count=1,
            hint_level_used=1,
        ), db_path=tmp_db)

        conn = sqlite3.connect(tmp_db)
        conn.row_factory = sqlite3.Row
        stats = get_hint_effectiveness_stats(conn, student_id=None)

        assert stats["total_hinted_attempts"] == 2
        assert stats["hint_level_used_coverage_rate"] == pytest.approx(1.0)
        assert stats["evidence_chain_complete_rate"] == pytest.approx(0.5)


# ── Validator preserves evidence fields ────────────────────────────


class TestValidatorPreservesEvidence:
    """Ensure validation layer does not strip evidence fields."""

    def test_all_evidence_fields_survive_validation(self):
        event = _make_attempt_event(
            hints_viewed_count=3,
            hint_level_used=3,
            hint_sequence=[1, 2, 3],
            hint_open_ts=[100, 200, 300],
        )
        v = validate_attempt_event(event)
        assert v.extra["hint_level_used"] == 3
        assert v.extra["hint_sequence"] == [1, 2, 3]
        assert v.extra["hint_open_ts"] == [100, 200, 300]

    def test_empty_extra_no_crash(self):
        event = _make_attempt_event(hints_viewed_count=1)
        v = validate_attempt_event(event)
        assert v.extra is not None  # extra dict exists even if empty

    def test_extra_with_other_fields_preserved(self):
        event = _make_attempt_event(
            hints_viewed_count=1,
            extra={"custom_field": "value", "hint_level_used": 1},
        )
        v = validate_attempt_event(event)
        assert v.extra["custom_field"] == "value"
        assert v.extra["hint_level_used"] == 1
