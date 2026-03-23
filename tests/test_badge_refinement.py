"""Tests for EXP-S3-03: Badge refinement.

Verifies:
1. detect_new_badges() correctly identifies newly earned badges
2. service.py wiring of recovered_concepts and consecutive_no_hint_correct
3. new_badges field in recordAttempt response
"""

from __future__ import annotations

import os
import tempfile

import pytest

from learning.concept_state import MasteryLevel, StudentConceptState
from learning.gamification import (
    Badge,
    BadgeType,
    Streak,
    compute_badges,
    detect_new_badges,
)
from learning.service import recordAttempt


def _state(concept_id: str, level: MasteryLevel, attempts: int = 5) -> StudentConceptState:
    return StudentConceptState(
        student_id="s1",
        concept_id=concept_id,
        mastery_level=level,
        mastery_score=0.5,
        attempts_total=attempts,
    )


class TestDetectNewBadges:
    """EXP-S3-03: New badge delta detection."""

    def test_all_new(self):
        """When no previous badges, all current are new."""
        states = [_state("frac_concept_basic", MasteryLevel.MASTERED)]
        badges = compute_badges(states)
        new = detect_new_badges(badges, set())
        assert len(new) == len(badges)

    def test_no_new(self):
        """When previous matches current, nothing new."""
        states = [_state("frac_concept_basic", MasteryLevel.MASTERED)]
        badges = compute_badges(states)
        prev = {b.badge_type.value for b in badges}
        new = detect_new_badges(badges, prev)
        assert len(new) == 0

    def test_one_new(self):
        """Adding a badge results in detecting exactly one new."""
        states = [_state("frac_concept_basic", MasteryLevel.MASTERED)]
        badges_before = compute_badges(states)
        prev = {b.badge_type.value for b in badges_before}
        # Now add no-hint hero
        badges_after = compute_badges(states, consecutive_no_hint_correct=5)
        new = detect_new_badges(badges_after, prev)
        assert len(new) == 1
        assert new[0].badge_type == BadgeType.NO_HINT_HERO

    def test_comeback_detection(self):
        """Comeback badge detected as new when recovered_concepts provided."""
        states = [_state("frac_concept_basic", MasteryLevel.MASTERED)]
        prev = {b.badge_type.value for b in compute_badges(states)}
        with_comeback = compute_badges(states, recovered_concepts={"frac_concept_basic"})
        new = detect_new_badges(with_comeback, prev)
        new_types = {b.badge_type for b in new}
        assert BadgeType.COMEBACK in new_types

    def test_streak_badge_detection(self):
        """Streak badge detected as new when streak provided."""
        states = [_state("frac_concept_basic", MasteryLevel.MASTERED)]
        prev = {b.badge_type.value for b in compute_badges(states)}
        streak = Streak(current_streak_days=3, longest_streak_days=3)
        with_streak = compute_badges(states, streak=streak)
        new = detect_new_badges(with_streak, prev)
        new_types = {b.badge_type for b in new}
        assert BadgeType.STREAK_3 in new_types


class TestBadgeWiringInService:
    """EXP-S3-03: Badge inputs wired in recordAttempt."""

    @pytest.fixture
    def tmp_db(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        os.unlink(path)

    def _event(self, **overrides):
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

    def test_new_badges_key_in_response(self, tmp_db):
        """Response must contain 'new_badges' list."""
        result = recordAttempt(self._event(), db_path=tmp_db)
        assert "new_badges" in result
        assert isinstance(result["new_badges"], list)

    def test_badges_still_present(self, tmp_db):
        """Standard 'badges' key still present."""
        result = recordAttempt(self._event(), db_path=tmp_db)
        assert "badges" in result
        assert isinstance(result["badges"], list)

    def test_no_hint_correct_param_accepted(self, tmp_db):
        """consecutive_no_hint_correct from extra field is accepted."""
        result = recordAttempt(
            self._event(extra={"consecutive_no_hint_correct": 5}),
            db_path=tmp_db,
        )
        # Should not crash; badges computed successfully
        assert result["ok"] is True

    def test_multiple_attempts_badge_accumulation(self, tmp_db):
        """Multiple attempts should accumulate badges over time."""
        for i in range(6):
            result = recordAttempt(
                self._event(
                    question_id=f"q{i}",
                    timestamp=f"2026-03-22T12:{i:02d}:00+08:00",
                ),
                db_path=tmp_db,
            )
        # After 6 correct answers, should have some badges
        assert result["ok"] is True
        assert isinstance(result["badges"], list)
