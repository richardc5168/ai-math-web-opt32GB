"""Tests for R44: Mastery Scoring Calibration.

Validates:
  - New validator fields: started_at, first_answer, attempts_count, changed_answer, selection_reason
  - Service layer populates ghost DB columns
  - Mastery engine new deltas: first_answer_correct_bonus, multi_attempt_penalty
  - _is_first_answer_correct helper logic
  - Existing mastery flow unbroken
"""

import json
import os
import sqlite3
import tempfile
from datetime import datetime, timedelta

import pytest

from learning.concept_state import MasteryLevel, StudentConceptState
from learning.mastery_engine import AnswerEvent, update_mastery
from learning.mastery_config import get_score_delta
from learning.validator import validate_attempt_event
from learning.service import _is_first_answer_correct, recordAttempt
from learning.db import ensure_learning_schema


def _recent_iso(days_ago: int = 0) -> str:
    return (datetime.now() - timedelta(days=days_ago)).isoformat(timespec="seconds")


def _make_state(**kwargs) -> StudentConceptState:
    defaults = {"student_id": "s1", "concept_id": "c1"}
    defaults.update(kwargs)
    return StudentConceptState(**defaults)


# -- Validator new fields --

class TestValidatorMasteryFields:
    def test_started_at_accepted(self):
        v = validate_attempt_event({
            "student_id": "s1", "question_id": "q1",
            "timestamp": _recent_iso(), "is_correct": True,
            "answer_raw": "42", "started_at": "2026-03-24T10:00:00",
        })
        assert v.started_at == "2026-03-24T10:00:00"

    def test_started_at_missing_default_none(self):
        v = validate_attempt_event({
            "student_id": "s1", "question_id": "q1",
            "timestamp": _recent_iso(), "is_correct": True,
            "answer_raw": "42",
        })
        assert v.started_at is None

    def test_first_answer_accepted(self):
        v = validate_attempt_event({
            "student_id": "s1", "question_id": "q1",
            "timestamp": _recent_iso(), "is_correct": True,
            "answer_raw": "42", "first_answer": "35",
        })
        assert v.first_answer == "35"

    def test_attempts_count_default_1(self):
        v = validate_attempt_event({
            "student_id": "s1", "question_id": "q1",
            "timestamp": _recent_iso(), "is_correct": True,
            "answer_raw": "42",
        })
        assert v.attempts_count == 1

    def test_attempts_count_accepted(self):
        v = validate_attempt_event({
            "student_id": "s1", "question_id": "q1",
            "timestamp": _recent_iso(), "is_correct": True,
            "answer_raw": "42", "attempts_count": 3,
        })
        assert v.attempts_count == 3

    def test_changed_answer_bool(self):
        v = validate_attempt_event({
            "student_id": "s1", "question_id": "q1",
            "timestamp": _recent_iso(), "is_correct": True,
            "answer_raw": "42", "changed_answer": True,
        })
        assert v.changed_answer is True

    def test_selection_reason_accepted(self):
        v = validate_attempt_event({
            "student_id": "s1", "question_id": "q1",
            "timestamp": _recent_iso(), "is_correct": True,
            "answer_raw": "42", "selection_reason": "developing_standard",
        })
        assert v.selection_reason == "developing_standard"


# -- _is_first_answer_correct helper --

class TestIsFirstAnswerCorrect:
    def test_correct_no_change(self):
        v = validate_attempt_event({
            "student_id": "s1", "question_id": "q1",
            "timestamp": _recent_iso(), "is_correct": True,
            "answer_raw": "42",
        })
        assert _is_first_answer_correct(v) is True

    def test_correct_with_change(self):
        v = validate_attempt_event({
            "student_id": "s1", "question_id": "q1",
            "timestamp": _recent_iso(), "is_correct": True,
            "answer_raw": "42", "changed_answer": True,
        })
        assert _is_first_answer_correct(v) is False

    def test_incorrect(self):
        v = validate_attempt_event({
            "student_id": "s1", "question_id": "q1",
            "timestamp": _recent_iso(), "is_correct": False,
            "answer_raw": "wrong",
        })
        assert _is_first_answer_correct(v) is False

    def test_first_answer_different(self):
        v = validate_attempt_event({
            "student_id": "s1", "question_id": "q1",
            "timestamp": _recent_iso(), "is_correct": True,
            "answer_raw": "42", "first_answer": "35",
        })
        assert _is_first_answer_correct(v) is False

    def test_first_answer_same(self):
        v = validate_attempt_event({
            "student_id": "s1", "question_id": "q1",
            "timestamp": _recent_iso(), "is_correct": True,
            "answer_raw": "42", "first_answer": "42",
        })
        assert _is_first_answer_correct(v) is True


# -- Mastery engine new deltas --

class TestMasteryNewDeltas:
    def test_first_answer_correct_bonus(self):
        state = _make_state(mastery_score=0.3)
        event = AnswerEvent(
            is_correct=True, used_hint=False,
            first_answer_correct=True,
        )
        state, actions = update_mastery(state, event)
        assert "first_answer_correct" in actions.reasons
        expected_delta = get_score_delta("correct_no_hint") + get_score_delta("first_answer_correct_bonus")
        assert actions.score_delta == pytest.approx(expected_delta)

    def test_no_bonus_when_hint_used(self):
        state = _make_state(mastery_score=0.3)
        event = AnswerEvent(
            is_correct=True, used_hint=True,
            first_answer_correct=True,
        )
        state, actions = update_mastery(state, event)
        assert "first_answer_correct" not in actions.reasons

    def test_no_bonus_when_not_first_answer_correct(self):
        state = _make_state(mastery_score=0.3)
        event = AnswerEvent(
            is_correct=True, used_hint=False,
            first_answer_correct=False,
        )
        state, actions = update_mastery(state, event)
        assert "first_answer_correct" not in actions.reasons

    def test_multi_attempt_penalty(self):
        state = _make_state(mastery_score=0.5)
        event = AnswerEvent(is_correct=True, attempts_count=2)
        state, actions = update_mastery(state, event)
        assert "multi_attempt" in actions.reasons

    def test_no_penalty_single_attempt(self):
        state = _make_state(mastery_score=0.5)
        event = AnswerEvent(is_correct=True, attempts_count=1)
        state, actions = update_mastery(state, event)
        assert "multi_attempt" not in actions.reasons

    def test_combined_first_correct_bonus_and_no_multi_penalty(self):
        """First answer correct + single attempt = bonus, no penalty."""
        state = _make_state(mastery_score=0.3)
        event = AnswerEvent(
            is_correct=True, used_hint=False,
            first_answer_correct=True, attempts_count=1,
        )
        state, actions = update_mastery(state, event)
        assert "first_answer_correct" in actions.reasons
        assert "multi_attempt" not in actions.reasons

    def test_config_deltas_exist(self):
        assert get_score_delta("first_answer_correct_bonus") > 0
        assert get_score_delta("multi_attempt_penalty") < 0


# -- Service layer DB column population --

class TestServicePopulatesGhostColumns:
    def test_record_attempt_populates_columns(self):
        event = {
            "student_id": "test_r44",
            "question_id": "q_r44",
            "timestamp": _recent_iso(),
            "is_correct": True,
            "answer_raw": "42",
            "started_at": "2026-03-24T10:00:00",
            "first_answer": "35",
            "attempts_count": 2,
            "changed_answer": True,
            "selection_reason": "developing_standard",
            "skill_tags": ["algebra"],
        }
        tmp = tempfile.mkdtemp()
        db_path = os.path.join(tmp, "test_r44.db")
        ack = recordAttempt(event, db_path=db_path)

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT started_at, first_answer, attempts_count, changed_answer, selection_reason FROM la_attempt_events WHERE student_id=?",
            ("test_r44",)
        ).fetchone()
        conn.close()

        assert row is not None
        assert row["started_at"] == "2026-03-24T10:00:00"
        assert row["first_answer"] == "35"
        assert row["attempts_count"] == 2
        assert row["changed_answer"] == 1
        assert row["selection_reason"] == "developing_standard"

    def test_record_attempt_defaults_without_new_fields(self):
        """Existing events without new fields should still work."""
        event = {
            "student_id": "test_r44_compat",
            "question_id": "q_compat",
            "timestamp": _recent_iso(),
            "is_correct": True,
            "answer_raw": "42",
            "skill_tags": ["algebra"],
        }
        tmp = tempfile.mkdtemp()
        db_path = os.path.join(tmp, "test_r44_compat.db")
        ack = recordAttempt(event, db_path=db_path)

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT started_at, first_answer, attempts_count, changed_answer, selection_reason FROM la_attempt_events WHERE student_id=?",
            ("test_r44_compat",)
        ).fetchone()
        conn.close()

        assert row is not None
        assert row["started_at"] is None
        assert row["first_answer"] is None
        assert row["attempts_count"] == 1
        assert row["changed_answer"] == 0
        assert row["selection_reason"] is None


# -- Existing mastery flow unbroken --

class TestExistingMasteryFlowUnbroken:
    def test_basic_correct_delta_unchanged(self):
        state = _make_state(mastery_score=0.3)
        event = AnswerEvent(is_correct=True, used_hint=False)
        state, actions = update_mastery(state, event)
        # Should still get correct_no_hint delta + first_answer_correct bonus (defaults to False)
        assert actions.score_delta == pytest.approx(get_score_delta("correct_no_hint"))

    def test_basic_wrong_delta_unchanged(self):
        state = _make_state(mastery_score=0.5)
        event = AnswerEvent(is_correct=False)
        state, actions = update_mastery(state, event)
        assert actions.score_delta == pytest.approx(get_score_delta("wrong"))

    def test_changed_answer_penalty_still_works(self):
        state = _make_state(mastery_score=0.5)
        event = AnswerEvent(is_correct=True, changed_answer=True)
        state, actions = update_mastery(state, event)
        assert "repeated_changes" in actions.reasons
