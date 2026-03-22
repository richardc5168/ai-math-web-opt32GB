"""Tests for EXP-06: /v1/student/concept-state API endpoint.

Verifies that concept mastery state can be read via GET request
after being populated by recordAttempt (EXP-02).
"""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from learning.service import recordAttempt
from learning.concept_state import get_all_states, MasteryLevel
from learning.db import connect, ensure_learning_schema


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
        "is_correct": True,
        "answer_raw": "42",
        "skill_tags": ["fraction"],
    }
    base.update(overrides)
    return base


class TestConceptStateReadback:
    """EXP-06: concept state should be readable after mastery updates."""

    def test_states_empty_before_attempts(self, tmp_db):
        """No states returned for student with no attempts."""
        conn = connect(tmp_db)
        try:
            ensure_learning_schema(conn)
            states = get_all_states("s_new", conn=conn)
            assert states == {}
        finally:
            conn.close()

    def test_states_populated_after_attempt(self, tmp_db):
        """After an attempt, concept states should exist."""
        recordAttempt(_make_event(), db_path=tmp_db)
        conn = connect(tmp_db)
        try:
            ensure_learning_schema(conn)
            states = get_all_states("s1", conn=conn)
            assert len(states) > 0
            for cid, state in states.items():
                assert state.attempts_total >= 1
                assert state.mastery_score > 0.0
        finally:
            conn.close()

    def test_multiple_concepts_tracked(self, tmp_db):
        """Multiple skill tags produce multiple concept states."""
        recordAttempt(
            _make_event(skill_tags=["fraction", "decimal"]),
            db_path=tmp_db,
        )
        conn = connect(tmp_db)
        try:
            ensure_learning_schema(conn)
            states = get_all_states("s1", conn=conn)
            assert len(states) > 1
        finally:
            conn.close()

    def test_state_accuracy_reflects_attempts(self, tmp_db):
        """Accuracy should reflect the mix of correct/incorrect attempts."""
        # 2 correct, 1 wrong
        for i in range(2):
            recordAttempt(
                _make_event(question_id=f"q{i}", timestamp=f"2026-03-22T12:0{i}:00+08:00"),
                db_path=tmp_db,
            )
        recordAttempt(
            _make_event(
                question_id="q_wrong",
                is_correct=False,
                answer_raw="bad",
                timestamp="2026-03-22T12:05:00+08:00",
            ),
            db_path=tmp_db,
        )

        conn = connect(tmp_db)
        try:
            ensure_learning_schema(conn)
            states = get_all_states("s1", conn=conn)
            for cid, state in states.items():
                assert state.attempts_total == 3
                assert state.correct_total == 2
                assert state.consecutive_wrong == 1
        finally:
            conn.close()

    def test_different_students_independent(self, tmp_db):
        """Each student has independent concept states."""
        recordAttempt(_make_event(student_id="alice"), db_path=tmp_db)
        recordAttempt(
            _make_event(student_id="bob", question_id="q2"),
            db_path=tmp_db,
        )

        conn = connect(tmp_db)
        try:
            ensure_learning_schema(conn)
            alice_states = get_all_states("alice", conn=conn)
            bob_states = get_all_states("bob", conn=conn)
            assert len(alice_states) > 0
            assert len(bob_states) > 0
            # Both should have 1 attempt each
            for s in alice_states.values():
                assert s.attempts_total == 1
            for s in bob_states.values():
                assert s.attempts_total == 1
        finally:
            conn.close()

    def test_mastery_level_in_state(self, tmp_db):
        """Mastery level should be a valid MasteryLevel value."""
        recordAttempt(_make_event(), db_path=tmp_db)
        conn = connect(tmp_db)
        try:
            ensure_learning_schema(conn)
            states = get_all_states("s1", conn=conn)
            for cid, state in states.items():
                assert isinstance(state.mastery_level, MasteryLevel)
        finally:
            conn.close()
