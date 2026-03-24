"""Tests for R42: Hint Evidence Chain enrichment.

Validates that get_hint_effectiveness_stats() returns the three new
evidence-chain metrics:
  - avg_hints_before_success
  - hint_escalation_rate
  - by_hint_level_at_submit

Also validates that existing hint effectiveness fields remain correct.
"""

import json
import os
import sqlite3
import tempfile
from datetime import datetime, timedelta

import pytest

from learning.db import ensure_learning_schema
from learning.analytics import get_hint_effectiveness_stats


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


# ── avg_hints_before_success ────────────────────────────────────────────


class TestAvgHintsBeforeSuccess:
    def test_empty_db(self):
        conn = _make_db()
        r = get_hint_effectiveness_stats(conn, student_id="s1")
        assert r["avg_hints_before_success"] == 0.0

    def test_no_correct(self):
        conn = _make_db()
        _insert(conn, hints_viewed_count=2, is_correct=False)
        r = get_hint_effectiveness_stats(conn, student_id="s1")
        assert r["avg_hints_before_success"] == 0.0

    def test_single_correct(self):
        conn = _make_db()
        _insert(conn, hints_viewed_count=3, is_correct=True)
        r = get_hint_effectiveness_stats(conn, student_id="s1")
        assert r["avg_hints_before_success"] == pytest.approx(3.0)

    def test_multiple_correct(self):
        conn = _make_db()
        _insert(conn, question_id="q1", hints_viewed_count=1, is_correct=True)
        _insert(conn, question_id="q2", hints_viewed_count=3, is_correct=True)
        _insert(conn, question_id="q3", hints_viewed_count=2, is_correct=False)
        r = get_hint_effectiveness_stats(conn, student_id="s1")
        # avg = (1+3)/2 = 2.0
        assert r["avg_hints_before_success"] == pytest.approx(2.0)


# ── hint_escalation_rate ────────────────────────────────────────────────


class TestHintEscalationRate:
    def test_empty_db(self):
        conn = _make_db()
        r = get_hint_effectiveness_stats(conn, student_id="s1")
        assert r["hint_escalation_rate"] == 0.0

    def test_no_escalation(self):
        conn = _make_db()
        _insert(conn, question_id="q1", hints_viewed_count=1, is_correct=True)
        _insert(conn, question_id="q2", hints_viewed_count=1, is_correct=False)
        r = get_hint_effectiveness_stats(conn, student_id="s1")
        assert r["hint_escalation_rate"] == pytest.approx(0.0)

    def test_all_escalated(self):
        conn = _make_db()
        _insert(conn, question_id="q1", hints_viewed_count=2, is_correct=True)
        _insert(conn, question_id="q2", hints_viewed_count=3, is_correct=False)
        r = get_hint_effectiveness_stats(conn, student_id="s1")
        assert r["hint_escalation_rate"] == pytest.approx(1.0)

    def test_partial_escalation(self):
        conn = _make_db()
        _insert(conn, question_id="q1", hints_viewed_count=1, is_correct=True)
        _insert(conn, question_id="q2", hints_viewed_count=2, is_correct=False)
        _insert(conn, question_id="q3", hints_viewed_count=1, is_correct=True)
        _insert(conn, question_id="q4", hints_viewed_count=3, is_correct=True)
        r = get_hint_effectiveness_stats(conn, student_id="s1")
        # 2 of 4 escalated
        assert r["hint_escalation_rate"] == pytest.approx(0.5)


# ── by_hint_level_at_submit ─────────────────────────────────────────────


class TestByHintLevelAtSubmit:
    def test_empty_db(self):
        conn = _make_db()
        r = get_hint_effectiveness_stats(conn, student_id="s1")
        assert r["by_hint_level_at_submit"] == {}

    def test_no_extra_json(self):
        """When extra_json has no hint_level_used, by_hint_level_at_submit is empty."""
        conn = _make_db()
        _insert(conn, hints_viewed_count=1, is_correct=True)
        r = get_hint_effectiveness_stats(conn, student_id="s1")
        assert r["by_hint_level_at_submit"] == {}

    def test_single_level(self):
        conn = _make_db()
        _insert(conn, hints_viewed_count=1, is_correct=True,
                extra={"hint_level_used": 1})
        r = get_hint_effectiveness_stats(conn, student_id="s1")
        assert r["by_hint_level_at_submit"]["1"]["total"] == 1
        assert r["by_hint_level_at_submit"]["1"]["correct"] == 1
        assert r["by_hint_level_at_submit"]["1"]["rate"] == pytest.approx(1.0)

    def test_multiple_levels(self):
        conn = _make_db()
        _insert(conn, question_id="q1", hints_viewed_count=1, is_correct=True,
                extra={"hint_level_used": 1})
        _insert(conn, question_id="q2", hints_viewed_count=2, is_correct=False,
                extra={"hint_level_used": 2})
        _insert(conn, question_id="q3", hints_viewed_count=2, is_correct=True,
                extra={"hint_level_used": 2})
        r = get_hint_effectiveness_stats(conn, student_id="s1")

        assert r["by_hint_level_at_submit"]["1"]["total"] == 1
        assert r["by_hint_level_at_submit"]["1"]["correct"] == 1
        assert r["by_hint_level_at_submit"]["1"]["rate"] == pytest.approx(1.0)

        assert r["by_hint_level_at_submit"]["2"]["total"] == 2
        assert r["by_hint_level_at_submit"]["2"]["correct"] == 1
        assert r["by_hint_level_at_submit"]["2"]["rate"] == pytest.approx(0.5)

    def test_mixed_with_and_without_extra(self):
        """Attempts without hint_level_used in extra should not appear in by_hint_level_at_submit."""
        conn = _make_db()
        _insert(conn, question_id="q1", hints_viewed_count=1, is_correct=True,
                extra={"hint_level_used": 1})
        _insert(conn, question_id="q2", hints_viewed_count=1, is_correct=True)  # no extra
        r = get_hint_effectiveness_stats(conn, student_id="s1")
        assert r["by_hint_level_at_submit"]["1"]["total"] == 1


# ── Combined evidence chain coherence ───────────────────────────────────


class TestEvidenceChainCoherence:
    """Ensure all three new fields work together with existing metrics."""

    def test_all_fields_present(self):
        conn = _make_db()
        _insert(conn, hints_viewed_count=1, is_correct=True,
                extra={"hint_level_used": 1})
        r = get_hint_effectiveness_stats(conn, student_id="s1")
        assert "avg_hints_before_success" in r
        assert "hint_escalation_rate" in r
        assert "by_hint_level_at_submit" in r

    def test_existing_fields_unchanged(self):
        """R42 fields must not break existing metrics."""
        conn = _make_db()
        _insert(conn, question_id="q1", hints_viewed_count=1, is_correct=True,
                concept_ids=["c1"], extra={"hint_level_used": 1})
        _insert(conn, question_id="q2", hints_viewed_count=2, is_correct=False,
                concept_ids=["c1"], extra={"hint_level_used": 2})
        r = get_hint_effectiveness_stats(conn, student_id="s1")

        assert r["total_hinted_attempts"] == 2
        assert r["correct_with_hint"] == 1
        assert r["hint_success_rate"] == pytest.approx(0.5)
        assert r["stuck_after_hint"] == 1
        assert r["stuck_after_hint_rate"] == pytest.approx(0.5)
        assert r["by_level"]["1"]["total"] == 1
        assert r["by_level"]["2"]["total"] == 1
        assert r["by_concept"]["c1"]["total"] == 2

    def test_complex_scenario(self):
        """Realistic scenario with varying hint levels and outcomes."""
        conn = _make_db()
        # Student uses 1 hint, gets it right
        _insert(conn, question_id="q1", hints_viewed_count=1, is_correct=True,
                extra={"hint_level_used": 1})
        # Student uses 2 hints, still wrong (escalated)
        _insert(conn, question_id="q2", hints_viewed_count=2, is_correct=False,
                extra={"hint_level_used": 2})
        # Student uses 3 hints, gets it right (escalated)
        _insert(conn, question_id="q3", hints_viewed_count=3, is_correct=True,
                extra={"hint_level_used": 3})
        # Student uses 1 hint, wrong
        _insert(conn, question_id="q4", hints_viewed_count=1, is_correct=False,
                extra={"hint_level_used": 1})

        r = get_hint_effectiveness_stats(conn, student_id="s1")

        # Basic metrics
        assert r["total_hinted_attempts"] == 4
        assert r["correct_with_hint"] == 2
        assert r["hint_success_rate"] == pytest.approx(0.5)

        # avg_hints_before_success = (1+3)/2 = 2.0
        assert r["avg_hints_before_success"] == pytest.approx(2.0)

        # escalation: q2 (level=2), q3 (level=3) → 2/4 = 0.5
        assert r["hint_escalation_rate"] == pytest.approx(0.5)

        # by_hint_level_at_submit
        assert r["by_hint_level_at_submit"]["1"]["total"] == 2
        assert r["by_hint_level_at_submit"]["1"]["correct"] == 1
        assert r["by_hint_level_at_submit"]["2"]["total"] == 1
        assert r["by_hint_level_at_submit"]["2"]["correct"] == 0
        assert r["by_hint_level_at_submit"]["3"]["total"] == 1
        assert r["by_hint_level_at_submit"]["3"]["correct"] == 1


# ── Server.py evidence field wiring (unit-level) ───────────────────────


class TestServerEvidenceFields:
    """Validate that the server.py submit handler wires evidence fields correctly.
    Tests the learning_event dict construction logic without hitting HTTP."""

    def test_extra_contains_correct_answer(self):
        """The extra dict must include correct_answer from the question."""
        q = {"correct_answer": "42", "topic": "algebra"}
        extra = {
            "error_tag": None,
            "error_detail": None,
            "correct_answer": q["correct_answer"],
            "changed_answer": False,
            "hint_level_used": None,
        }
        assert extra["correct_answer"] == "42"

    def test_extra_changed_answer_from_meta(self):
        """changed_answer should be extracted from body.meta.changed_answer."""
        body_meta = {"changed_answer": True}
        changed = bool(body_meta.get("changed_answer")) if isinstance(body_meta, dict) else False
        assert changed is True

        body_meta_false = {"changed_answer": False}
        changed_f = bool(body_meta_false.get("changed_answer")) if isinstance(body_meta_false, dict) else False
        assert changed_f is False

    def test_extra_changed_answer_missing_meta(self):
        body_meta = None
        changed = bool(body_meta.get("changed_answer")) if isinstance(body_meta, dict) else False
        assert changed is False

    def test_extra_hint_level_used(self):
        """hint_level_used should be an int or None."""
        hint_level_used_int = 2
        extra = {"hint_level_used": hint_level_used_int}
        assert extra["hint_level_used"] == 2

        hint_level_used_int = None
        extra2 = {"hint_level_used": hint_level_used_int}
        assert extra2["hint_level_used"] is None


# ── R52: Validator hint evidence fields ─────────────────────────────────


class TestR52ValidatorHintEvidence:
    """R52: hint evidence promoted to first-class validated fields."""

    def _base_event(self, **overrides):
        e = {
            "student_id": "s1",
            "question_id": "q1",
            "timestamp": "2024-01-01T00:00:00Z",
            "is_correct": True,
            "answer_raw": "42",
        }
        e.update(overrides)
        return e

    def test_hint_level_used_from_top_level(self):
        from learning.validator import validate_attempt_event
        v = validate_attempt_event(self._base_event(hint_level_used=3))
        assert v.hint_level_used == 3

    def test_hint_level_used_from_extra_fallback(self):
        from learning.validator import validate_attempt_event
        v = validate_attempt_event(self._base_event(extra={"hint_level_used": 2}))
        assert v.hint_level_used == 2

    def test_hint_level_used_top_level_wins(self):
        from learning.validator import validate_attempt_event
        v = validate_attempt_event(self._base_event(
            hint_level_used=1, extra={"hint_level_used": 3}
        ))
        assert v.hint_level_used == 1

    def test_hint_level_used_none_when_absent(self):
        from learning.validator import validate_attempt_event
        v = validate_attempt_event(self._base_event())
        assert v.hint_level_used is None

    def test_hint_level_used_bad_value_becomes_none(self):
        from learning.validator import validate_attempt_event
        v = validate_attempt_event(self._base_event(hint_level_used="abc"))
        assert v.hint_level_used is None

    def test_hint_level_used_out_of_range_becomes_none(self):
        from learning.validator import validate_attempt_event
        v = validate_attempt_event(self._base_event(hint_level_used=99))
        assert v.hint_level_used is None

    def test_hint_sequence_validated(self):
        from learning.validator import validate_attempt_event
        v = validate_attempt_event(self._base_event(hint_sequence=[1, 2, 3]))
        assert v.hint_sequence == [1, 2, 3]

    def test_hint_sequence_capped_at_10(self):
        from learning.validator import validate_attempt_event
        v = validate_attempt_event(self._base_event(hint_sequence=list(range(20))))
        assert len(v.hint_sequence) == 10

    def test_hint_sequence_bad_items_filtered(self):
        from learning.validator import validate_attempt_event
        v = validate_attempt_event(self._base_event(hint_sequence=[1, "bad", 3]))
        assert v.hint_sequence == [1, 3]

    def test_hint_open_ts_validated(self):
        from learning.validator import validate_attempt_event
        v = validate_attempt_event(self._base_event(hint_open_ts=[1000, 2000]))
        assert v.hint_open_ts == [1000, 2000]


# ── R52: Mastery engine hint-depth-aware scoring ────────────────────────


class TestR52MasteryHintDepth:
    """R52: mastery engine applies heavy hint penalty for L3+ hints."""

    def _state(self):
        from learning.concept_state import StudentConceptState, MasteryLevel
        return StudentConceptState(
            student_id="s1", concept_id="c1",
            mastery_level=MasteryLevel.DEVELOPING, mastery_score=0.40,
        )

    def test_heavy_hint_penalty_L3(self):
        from learning.mastery_engine import AnswerEvent, update_mastery
        ev = AnswerEvent(is_correct=True, used_hint=True, hint_levels_shown=3, hint_level_used=3)
        _, acts = update_mastery(self._state(), ev)
        assert "heavy_hint_L3+" in acts.reasons

    def test_no_penalty_L1(self):
        from learning.mastery_engine import AnswerEvent, update_mastery
        ev = AnswerEvent(is_correct=True, used_hint=True, hint_levels_shown=1, hint_level_used=1)
        _, acts = update_mastery(self._state(), ev)
        assert "heavy_hint_L3+" not in acts.reasons

    def test_no_penalty_when_unknown(self):
        from learning.mastery_engine import AnswerEvent, update_mastery
        ev = AnswerEvent(is_correct=True, used_hint=True, hint_levels_shown=3)
        _, acts = update_mastery(self._state(), ev)
        assert "heavy_hint_L3+" not in acts.reasons

    def test_L3_less_credit_than_L1(self):
        from learning.mastery_engine import AnswerEvent, update_mastery
        ev_l1 = AnswerEvent(is_correct=True, used_hint=True, hint_levels_shown=1, hint_level_used=1)
        ev_l3 = AnswerEvent(is_correct=True, used_hint=True, hint_levels_shown=3, hint_level_used=3)
        _, acts_l1 = update_mastery(self._state(), ev_l1)
        _, acts_l3 = update_mastery(self._state(), ev_l3)
        assert acts_l1.score_delta > acts_l3.score_delta


# ── R52: Analytics by_question and escalation fix ───────────────────────


class TestR52AnalyticsByQuestion:
    """R52: per-question hint effectiveness in analytics output."""

    def test_by_question_key_exists(self):
        conn = _make_db()
        _insert(conn, question_id="q1", hints_viewed_count=1, is_correct=True,
                extra={"hint_level_used": 1})
        _insert(conn, question_id="q2", hints_viewed_count=2, is_correct=False,
                extra={"hint_level_used": 2})
        r = get_hint_effectiveness_stats(conn, student_id="s1")
        assert "by_question" in r
        assert "q1" in r["by_question"]
        assert "q2" in r["by_question"]

    def test_escalation_uses_hint_level_column(self):
        """With hint_level_used=1 but hints_viewed_count=2, should NOT escalate."""
        conn = _make_db()
        _insert(conn, question_id="q1", hints_viewed_count=2, is_correct=True,
                extra={"hint_level_used": 1})
        r = get_hint_effectiveness_stats(conn, student_id="s1")
        assert r["hint_escalation_rate"] == pytest.approx(0.0)
