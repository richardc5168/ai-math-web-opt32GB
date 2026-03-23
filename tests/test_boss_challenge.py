"""Tests for EXP-S3-02: Boss challenge (mastery-gated).

Verifies that generate_boss_challenge() and get_available_bosses()
correctly build challenge pools and gate availability on mastery.
"""

from __future__ import annotations

import pytest

from learning.concept_state import MasteryLevel, StudentConceptState
from learning.concept_taxonomy import get_all_prerequisites
from learning.gamification import (
    BossChallenge,
    generate_boss_challenge,
    get_available_bosses,
)


def _state(concept_id: str, level: MasteryLevel) -> StudentConceptState:
    return StudentConceptState(
        student_id="s1",
        concept_id=concept_id,
        mastery_level=level,
        mastery_score=0.5,
    )


class TestGenerateBossChallenge:
    """EXP-S3-02: Boss challenge generation tests."""

    def test_no_prereqs_easy(self):
        """Concept with no prerequisites produces an easy boss."""
        states = [_state("frac_concept_basic", MasteryLevel.MASTERED)]
        boss = generate_boss_challenge("frac_concept_basic", states)
        assert boss.difficulty == "easy"
        assert boss.prereq_depth == 0
        assert boss.challenge_concept_ids == ["frac_concept_basic"]

    def test_one_prereq_normal(self):
        """Concept with 1 direct prereq produces normal difficulty."""
        states = [
            _state("frac_add_like", MasteryLevel.MASTERED),
            _state("frac_concept_basic", MasteryLevel.MASTERED),
        ]
        boss = generate_boss_challenge("frac_add_like", states)
        assert boss.difficulty == "normal"
        assert "frac_concept_basic" in boss.challenge_concept_ids
        assert "frac_add_like" in boss.challenge_concept_ids

    def test_deep_prereqs_hard(self):
        """Concept with 4+ transitive prereqs is hard."""
        # frac_divide -> frac_multiply -> frac_simplify -> frac_concept_basic
        #                               -> frac_mixed_improper -> frac_concept_basic
        all_prereqs = get_all_prerequisites("frac_divide")
        assert len(all_prereqs) >= 4  # Should have deep chain
        states = [_state(cid, MasteryLevel.MASTERED) for cid in ["frac_divide"] + all_prereqs]
        boss = generate_boss_challenge("frac_divide", states)
        assert boss.difficulty == "hard"
        assert boss.prereq_depth >= 4

    def test_available_when_all_mastered(self):
        """Boss is available only when concept + all prereqs are MASTERED."""
        all_prereqs = get_all_prerequisites("frac_add_like")
        states = [_state("frac_add_like", MasteryLevel.MASTERED)]
        states += [_state(p, MasteryLevel.MASTERED) for p in all_prereqs]
        boss = generate_boss_challenge("frac_add_like", states)
        assert boss.is_available is True

    def test_not_available_concept_not_mastered(self):
        """Boss unavailable if the concept itself is not MASTERED."""
        states = [
            _state("frac_add_like", MasteryLevel.APPROACHING_MASTERY),
            _state("frac_concept_basic", MasteryLevel.MASTERED),
        ]
        boss = generate_boss_challenge("frac_add_like", states)
        assert boss.is_available is False

    def test_not_available_prereq_not_mastered(self):
        """Boss unavailable if any prereq is not MASTERED."""
        states = [
            _state("frac_add_like", MasteryLevel.MASTERED),
            _state("frac_concept_basic", MasteryLevel.DEVELOPING),
        ]
        boss = generate_boss_challenge("frac_add_like", states)
        assert boss.is_available is False

    def test_display_name_zh(self):
        """Boss challenge has Chinese display name from taxonomy."""
        states = [_state("frac_concept_basic", MasteryLevel.MASTERED)]
        boss = generate_boss_challenge("frac_concept_basic", states)
        assert boss.display_name_zh == "分數基本概念"

    def test_challenge_includes_all_transitive_prereqs(self):
        """Challenge concept list includes all transitive prereqs."""
        all_prereqs = get_all_prerequisites("frac_add_unlike")
        states = [_state(c, MasteryLevel.MASTERED) for c in ["frac_add_unlike"] + all_prereqs]
        boss = generate_boss_challenge("frac_add_unlike", states)
        for p in all_prereqs:
            assert p in boss.challenge_concept_ids
        assert "frac_add_unlike" in boss.challenge_concept_ids


class TestGetAvailableBosses:
    """EXP-S3-02: Available boss filtering tests."""

    def test_no_states_empty(self):
        """No states means no available bosses."""
        assert get_available_bosses([]) == []

    def test_all_developing_none_available(self):
        """All DEVELOPING states means no bosses available."""
        states = [_state("frac_concept_basic", MasteryLevel.DEVELOPING)]
        assert get_available_bosses(states) == []

    def test_mastered_no_prereqs_available(self):
        """Mastered concept with no prereqs has an available boss."""
        states = [_state("frac_concept_basic", MasteryLevel.MASTERED)]
        bosses = get_available_bosses(states)
        assert len(bosses) == 1
        assert bosses[0].concept_id == "frac_concept_basic"

    def test_multiple_available(self):
        """Multiple mastered concepts generate multiple available bosses."""
        states = [
            _state("frac_concept_basic", MasteryLevel.MASTERED),
            _state("decimal_basic", MasteryLevel.MASTERED),
            _state("linear_one_step", MasteryLevel.MASTERED),
        ]
        bosses = get_available_bosses(states)
        boss_ids = {b.concept_id for b in bosses}
        assert "frac_concept_basic" in boss_ids
        assert "decimal_basic" in boss_ids
        assert "linear_one_step" in boss_ids
