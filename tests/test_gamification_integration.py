"""Tests for EXP-07: gamification wiring into recordAttempt.

Verifies that check_unlocks() and compute_badges() are called after
mastery updates and returned in the recordAttempt response.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from learning.service import recordAttempt
from learning.concept_state import get_concept_state, upsert_concept_state, MasteryLevel


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


class TestGamificationIntegration:
    """EXP-07: gamification data returned in recordAttempt response."""

    def test_unlocks_key_in_response(self, tmp_db):
        """Response must contain 'unlocks' list."""
        result = recordAttempt(_make_event(), db_path=tmp_db)
        assert "unlocks" in result
        assert isinstance(result["unlocks"], list)

    def test_badges_key_in_response(self, tmp_db):
        """Response must contain 'badges' list."""
        result = recordAttempt(_make_event(), db_path=tmp_db)
        assert "badges" in result
        assert isinstance(result["badges"], list)

    def test_unlock_structure(self, tmp_db):
        """Each unlock entry has required fields."""
        result = recordAttempt(_make_event(), db_path=tmp_db)
        if result["unlocks"]:
            u = result["unlocks"][0]
            assert "concept_id" in u
            assert "zone_unlocked" in u
            assert "boss_unlocked" in u
            assert "unlock_reason" in u

    def test_badge_structure(self, tmp_db):
        """Each badge entry has required fields."""
        # Feed many correct answers to earn FIRST_MASTERY
        for i in range(6):
            result = recordAttempt(
                _make_event(question_id=f"q{i}", timestamp=f"2026-03-22T12:{i:02d}:00+08:00"),
                db_path=tmp_db,
            )
        badges = result["badges"]
        if badges:
            b = badges[0]
            assert "badge_type" in b
            assert "display_name_zh" in b
            assert "icon" in b

    def test_first_attempt_no_zone_unlock(self, tmp_db):
        """A single correct answer shouldn't unlock zones (mastery too low)."""
        result = recordAttempt(_make_event(), db_path=tmp_db)
        zone_unlocked = [u for u in result["unlocks"] if u["zone_unlocked"]]
        assert len(zone_unlocked) == 0

    def test_mastery_progress_unlocks_zone(self, tmp_db):
        """After many correct answers, zone should unlock for the concept."""
        for i in range(8):
            result = recordAttempt(
                _make_event(question_id=f"q{i}", timestamp=f"2026-03-22T12:{i:02d}:00+08:00"),
                db_path=tmp_db,
            )
        zone_unlocked = [u for u in result["unlocks"] if u["zone_unlocked"]]
        # After 8 correct answers, at least some concept should have zone_unlocked
        assert len(zone_unlocked) > 0

    def test_first_mastery_badge_earned(self, tmp_db):
        """After enough correct answers to reach MASTERED, first_mastery badge earned."""
        for i in range(10):
            result = recordAttempt(
                _make_event(question_id=f"q{i}", timestamp=f"2026-03-22T12:{i:02d}:00+08:00"),
                db_path=tmp_db,
            )
        badge_types = [b["badge_type"] for b in result["badges"]]
        assert "first_mastery" in badge_types

    def test_no_concept_ids_returns_empty_gamification(self, tmp_db):
        """When no concepts resolved, unlocks and badges are empty."""
        result = recordAttempt(
            _make_event(skill_tags=["xyznonexistent"]),
            db_path=tmp_db,
        )
        assert result["unlocks"] == []
        assert result["badges"] == []
