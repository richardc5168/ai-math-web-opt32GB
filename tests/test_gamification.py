"""Tests for learning.gamification module."""

import pytest

from learning.concept_state import MasteryLevel, StudentConceptState
from learning.gamification import (
    Badge,
    BadgeType,
    GamificationState,
    Streak,
    UnlockStatus,
    check_unlocks,
    compute_badges,
    gamification_to_dict,
    update_streak,
)


def _state(concept_id, level, attempts=10, **kwargs):
    defaults = dict(
        student_id="stu1",
        concept_id=concept_id,
        mastery_level=level,
        mastery_score=50.0,
        recent_accuracy=0.5,
        hint_dependency=0.2,
        attempts_total=attempts,
        correct_total=5,
    )
    defaults.update(kwargs)
    return StudentConceptState(**defaults)


# ===== check_unlocks =====

class TestCheckUnlocks:
    def test_zone_unlocked_at_approaching(self):
        states = [_state("fraction_add", MasteryLevel.APPROACHING_MASTERY)]
        unlocks = check_unlocks(states)
        assert len(unlocks) == 1
        assert unlocks[0].zone_unlocked is True

    def test_zone_not_unlocked_at_developing(self):
        states = [_state("fraction_add", MasteryLevel.DEVELOPING)]
        unlocks = check_unlocks(states)
        assert unlocks[0].zone_unlocked is False

    def test_boss_unlocked_when_mastered_no_prereqs(self):
        # fraction_add has no prerequisites in taxonomy
        states = [_state("fraction_add", MasteryLevel.MASTERED)]
        unlocks = check_unlocks(states)
        assert unlocks[0].boss_unlocked is True

    def test_boss_not_unlocked_when_prereqs_not_mastered(self):
        # frac_add_unlike requires frac_add_like and lcm_basic
        states = [
            _state("frac_add_like", MasteryLevel.DEVELOPING),
            _state("lcm_basic", MasteryLevel.MASTERED),
            _state("frac_add_unlike", MasteryLevel.MASTERED),
        ]
        unlocks = check_unlocks(states)
        unlike_unlock = [u for u in unlocks if u.concept_id == "frac_add_unlike"][0]
        assert unlike_unlock.boss_unlocked is False

    def test_boss_unlocked_when_prereqs_mastered(self):
        states = [
            _state("frac_add_like", MasteryLevel.MASTERED),
            _state("lcm_basic", MasteryLevel.MASTERED),
            _state("frac_add_unlike", MasteryLevel.MASTERED),
        ]
        unlocks = check_unlocks(states)
        unlike_unlock = [u for u in unlocks if u.concept_id == "frac_add_unlike"][0]
        assert unlike_unlock.boss_unlocked is True


# ===== compute_badges =====

class TestComputeBadges:
    def test_first_mastery(self):
        states = [_state("fraction_add", MasteryLevel.MASTERED)]
        badges = compute_badges(states)
        types = {b.badge_type for b in badges}
        assert BadgeType.FIRST_MASTERY in types

    def test_no_badges_if_nothing_mastered(self):
        states = [_state("fraction_add", MasteryLevel.DEVELOPING)]
        badges = compute_badges(states)
        assert BadgeType.FIRST_MASTERY not in {b.badge_type for b in badges}

    def test_streak_3(self):
        states = [_state("fraction_add", MasteryLevel.DEVELOPING)]
        streak = Streak(current_streak_days=3)
        badges = compute_badges(states, streak=streak)
        types = {b.badge_type for b in badges}
        assert BadgeType.STREAK_3 in types
        assert BadgeType.STREAK_7 not in types

    def test_streak_7(self):
        states = [_state("fraction_add", MasteryLevel.DEVELOPING)]
        streak = Streak(current_streak_days=7)
        badges = compute_badges(states, streak=streak)
        types = {b.badge_type for b in badges}
        assert BadgeType.STREAK_7 in types

    def test_streak_14(self):
        states = [_state("fraction_add", MasteryLevel.DEVELOPING)]
        streak = Streak(current_streak_days=14)
        badges = compute_badges(states, streak=streak)
        types = {b.badge_type for b in badges}
        assert BadgeType.STREAK_14 in types

    def test_no_hint_hero(self):
        states = [_state("fraction_add", MasteryLevel.DEVELOPING)]
        badges = compute_badges(states, consecutive_no_hint_correct=5)
        types = {b.badge_type for b in badges}
        assert BadgeType.NO_HINT_HERO in types

    def test_comeback_badge(self):
        states = [_state("fraction_add", MasteryLevel.MASTERED)]
        badges = compute_badges(states, recovered_concepts={"fraction_add"})
        types = {b.badge_type for b in badges}
        assert BadgeType.COMEBACK in types

    def test_ten_concepts_badge(self):
        states = [
            _state(f"concept_{i}", MasteryLevel.APPROACHING_MASTERY)
            for i in range(10)
        ]
        badges = compute_badges(states)
        types = {b.badge_type for b in badges}
        assert BadgeType.TEN_CONCEPTS in types

    def test_badge_has_chinese_display(self):
        states = [_state("fraction_add", MasteryLevel.MASTERED)]
        badges = compute_badges(states)
        first = badges[0]
        assert len(first.display_name_zh) > 0
        assert len(first.icon) > 0


# ===== update_streak =====

class TestUpdateStreak:
    def test_first_practice(self):
        s = Streak()
        result = update_streak(s, "2024-01-15")
        assert result.current_streak_days == 1
        assert result.last_practice_date == "2024-01-15"

    def test_same_day_no_change(self):
        s = Streak(current_streak_days=3, longest_streak_days=3, last_practice_date="2024-01-15")
        result = update_streak(s, "2024-01-15")
        assert result.current_streak_days == 3

    def test_consecutive_day(self):
        s = Streak(current_streak_days=3, longest_streak_days=3, last_practice_date="2024-01-15")
        result = update_streak(s, "2024-01-16")
        assert result.current_streak_days == 4
        assert result.longest_streak_days == 4

    def test_streak_broken(self):
        s = Streak(current_streak_days=5, longest_streak_days=5, last_practice_date="2024-01-10")
        result = update_streak(s, "2024-01-15")
        assert result.current_streak_days == 1
        assert result.longest_streak_days == 5  # longest preserved

    def test_longest_preserved(self):
        s = Streak(current_streak_days=1, longest_streak_days=10, last_practice_date="2024-01-15")
        result = update_streak(s, "2024-01-16")
        assert result.longest_streak_days == 10


# ===== gamification_to_dict =====

class TestGamificationToDict:
    def test_serializable(self):
        state = GamificationState(
            unlocks=[UnlockStatus("fraction_add", zone_unlocked=True)],
            badges=[Badge(BadgeType.FIRST_MASTERY, "初次掌握", "🌟", "第一個觀念掌握了！")],
            streak=Streak(current_streak_days=3),
        )
        d = gamification_to_dict(state)
        assert isinstance(d, dict)
        assert len(d["unlocks"]) == 1
        assert len(d["badges"]) == 1
        assert d["streak"]["current_streak_days"] == 3
