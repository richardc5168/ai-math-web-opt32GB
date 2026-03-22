"""Tests for EXP-05: remediation_flow trigger signals in recordAttempt.

Verifies that remediation_needed and calm_mode signals are surfaced in
the recordAttempt response when students struggle.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from learning.service import recordAttempt


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


class TestRemediationSignals:
    """EXP-05: remediation signals should appear when student struggles."""

    def test_response_has_remediation_fields(self, tmp_db):
        """Every response should have remediation_concepts list."""
        result = recordAttempt(_make_event(), db_path=tmp_db)
        assert "remediation_concepts" in result
        assert isinstance(result["remediation_concepts"], list)

    def test_correct_answer_no_remediation(self, tmp_db):
        """Correct answers should not trigger remediation."""
        result = recordAttempt(_make_event(), db_path=tmp_db)
        assert result["remediation_concepts"] == []
        for m in result["mastery"]:
            assert m["remediation_needed"] is False

    def test_mastery_entries_have_calm_mode(self, tmp_db):
        """Mastery entries should include calm_mode flag."""
        result = recordAttempt(_make_event(), db_path=tmp_db)
        for m in result["mastery"]:
            assert "calm_mode" in m

    def test_single_wrong_no_remediation(self, tmp_db):
        """One wrong answer should not trigger remediation."""
        result = recordAttempt(
            _make_event(is_correct=False, answer_raw="bad"),
            db_path=tmp_db,
        )
        assert result["remediation_concepts"] == []

    def test_consecutive_wrong_triggers_remediation(self, tmp_db):
        """3+ consecutive wrong on same concept should trigger remediation."""
        for i in range(3):
            result = recordAttempt(
                _make_event(
                    question_id=f"q{i}",
                    is_correct=False,
                    answer_raw="bad",
                    timestamp=f"2026-03-22T12:0{i}:00+08:00",
                ),
                db_path=tmp_db,
            )
        # After 3 consecutive wrong, remediation should be triggered
        assert len(result["remediation_concepts"]) > 0

    def test_remediation_resets_after_correct(self, tmp_db):
        """Remediation should not be triggered after a correct answer breaks streak."""
        # 2 wrong
        for i in range(2):
            recordAttempt(
                _make_event(
                    question_id=f"q{i}",
                    is_correct=False,
                    answer_raw="bad",
                    timestamp=f"2026-03-22T12:0{i}:00+08:00",
                ),
                db_path=tmp_db,
            )
        # 1 correct breaks the streak
        recordAttempt(
            _make_event(
                question_id="q_correct",
                timestamp="2026-03-22T12:03:00+08:00",
            ),
            db_path=tmp_db,
        )
        # 1 wrong — should NOT trigger remediation (streak reset)
        result = recordAttempt(
            _make_event(
                question_id="q_after",
                is_correct=False,
                answer_raw="bad",
                timestamp="2026-03-22T12:04:00+08:00",
            ),
            db_path=tmp_db,
        )
        assert result["remediation_concepts"] == []

    def test_no_remediation_when_no_concepts(self, tmp_db):
        """If no concepts resolved, remediation_concepts should be empty."""
        result = recordAttempt(
            _make_event(skill_tags=["unknown_xyz"], is_correct=False, answer_raw="bad"),
            db_path=tmp_db,
        )
        assert result["remediation_concepts"] == []
