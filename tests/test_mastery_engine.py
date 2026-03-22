"""Tests for the mastery update engine."""

import pytest

from learning.concept_state import MasteryLevel, StudentConceptState
from learning.mastery_engine import (
    AnswerEvent,
    MasteryActions,
    update_mastery,
    check_review_needed,
)


def _make_state(**kwargs) -> StudentConceptState:
    defaults = {"student_id": "s1", "concept_id": "c1"}
    defaults.update(kwargs)
    return StudentConceptState(**defaults)


# --- Score Deltas ---

def test_correct_no_hint_increases_score():
    state = _make_state(mastery_score=0.3)
    event = AnswerEvent(is_correct=True, used_hint=False)
    state, actions = update_mastery(state, event)
    assert actions.score_delta > 0
    assert state.mastery_score > 0.3
    assert "correct_no_hint" in actions.reasons


def test_correct_with_hint_increases_score_less():
    s1 = _make_state(mastery_score=0.3)
    s2 = _make_state(mastery_score=0.3)

    s1, a1 = update_mastery(s1, AnswerEvent(is_correct=True, used_hint=False))
    s2, a2 = update_mastery(s2, AnswerEvent(is_correct=True, used_hint=True))

    assert a1.score_delta > a2.score_delta
    assert "correct_with_hint" in a2.reasons


def test_wrong_decreases_score():
    state = _make_state(mastery_score=0.5)
    event = AnswerEvent(is_correct=False)
    state, actions = update_mastery(state, event)
    assert actions.score_delta < 0
    assert state.mastery_score < 0.5
    assert "wrong" in actions.reasons


def test_score_clamped_to_0_1():
    # Score can't go below 0
    state = _make_state(mastery_score=0.05)
    for _ in range(5):
        state, _ = update_mastery(state, AnswerEvent(is_correct=False))
    assert state.mastery_score >= 0.0

    # Score can't go above 1
    state = _make_state(mastery_score=0.95)
    for _ in range(5):
        state, _ = update_mastery(state, AnswerEvent(is_correct=True, used_hint=False))
    assert state.mastery_score <= 1.0


# --- Counter Updates ---

def test_counters_update_correctly():
    state = _make_state()
    state, _ = update_mastery(state, AnswerEvent(is_correct=True, used_hint=False))
    assert state.attempts_total == 1
    assert state.correct_total == 1
    assert state.correct_no_hint == 1
    assert state.consecutive_correct == 1

    state, _ = update_mastery(state, AnswerEvent(is_correct=True, used_hint=True))
    assert state.correct_with_hint == 1
    assert state.consecutive_correct == 2

    state, _ = update_mastery(state, AnswerEvent(is_correct=False))
    assert state.consecutive_correct == 0
    assert state.consecutive_wrong == 1


# --- Promotion ---

def test_promotion_to_developing():
    state = _make_state(mastery_score=0.15, attempts_total=2, recent_accuracy=0.5)
    event = AnswerEvent(is_correct=True, used_hint=False)
    state, actions = update_mastery(state, event)
    # Score should be 0.15 + 0.15 = 0.30 → developing range
    assert state.mastery_level == MasteryLevel.DEVELOPING
    assert actions.promoted


def test_promotion_blocked_by_gate():
    # Score in approaching range but too few attempts
    state = _make_state(
        mastery_score=0.48,
        attempts_total=3,  # gate requires 5
        recent_accuracy=0.4,
    )
    event = AnswerEvent(is_correct=True, used_hint=False)
    state, actions = update_mastery(state, event)
    # Score 0.48 + 0.15 = 0.63 → approaching range, but only 4 attempts (below gate)
    assert not actions.promoted or state.mastery_level != MasteryLevel.APPROACHING_MASTERY


def test_promotion_to_mastered_requires_consecutive_correct():
    state = _make_state(
        mastery_score=0.78,
        mastery_level=MasteryLevel.APPROACHING_MASTERY,
        attempts_total=9,
        correct_total=8,
        correct_no_hint=7,
        recent_accuracy=0.9,
        hint_dependency=0.1,
        consecutive_correct=2,  # gate requires 3
    )
    event = AnswerEvent(is_correct=True, used_hint=False)
    state, actions = update_mastery(state, event)
    # consecutive_correct becomes 3 (meets gate), score 0.78+0.15=0.93
    assert state.mastery_level == MasteryLevel.MASTERED
    assert actions.promoted
    assert state.last_mastered_at is not None


# --- Demotion ---

def test_demotion_on_score_drop():
    state = _make_state(
        mastery_score=0.22,
        mastery_level=MasteryLevel.DEVELOPING,
        attempts_total=5,
    )
    event = AnswerEvent(is_correct=False)
    state, actions = update_mastery(state, event)
    # Score 0.22 - 0.10 = 0.12 → unbuilt
    assert state.mastery_level == MasteryLevel.UNBUILT
    assert actions.demoted


# --- Repeated Failure ---

def test_repeated_failure_penalty():
    state = _make_state(mastery_score=0.5, consecutive_wrong=2)
    event = AnswerEvent(is_correct=False)
    state, actions = update_mastery(state, event)
    # consecutive_wrong becomes 3 → repeated_failure delta applied
    assert "repeated_failure" in actions.reasons
    assert actions.remediation_needed


def test_calm_mode_triggered():
    state = _make_state(consecutive_wrong=2)
    event = AnswerEvent(is_correct=False)
    state, actions = update_mastery(state, event)
    assert actions.calm_mode_entered
    assert "calm_mode" in actions.reasons


# --- Transfer & Delayed Review ---

def test_transfer_success_bonus():
    state = _make_state(mastery_score=0.5)
    event = AnswerEvent(is_correct=True, used_hint=False, is_transfer_item=True)
    state, actions = update_mastery(state, event)
    assert "transfer_success" in actions.reasons
    assert state.transfer_success_count == 1
    # Should get both correct_no_hint + transfer_success deltas
    assert actions.score_delta > 0.15


def test_delayed_review_correct():
    state = _make_state(mastery_score=0.7, delayed_review_status="pending")
    event = AnswerEvent(is_correct=True, used_hint=False, is_delayed_review=True)
    state, actions = update_mastery(state, event)
    assert "delayed_review_correct" in actions.reasons
    assert state.delayed_review_status == "passed"


# --- Changed Answer ---

def test_changed_answer_penalty():
    state = _make_state(mastery_score=0.5)
    event = AnswerEvent(is_correct=True, used_hint=False, changed_answer=True)
    state, actions = update_mastery(state, event)
    assert "repeated_changes" in actions.reasons
    # Net delta should be positive but reduced
    assert actions.score_delta < 0.15  # less than pure correct_no_hint


# --- Review Check ---

def test_review_triggered_after_days():
    state = _make_state(
        mastery_level=MasteryLevel.MASTERED,
        mastery_score=0.9,
        last_mastered_at="2026-03-01T00:00:00",
    )
    state, triggered = check_review_needed(state, now_iso="2026-03-10T00:00:00")
    assert triggered
    assert state.mastery_level == MasteryLevel.REVIEW_NEEDED
    assert state.needs_review
    assert state.mastery_score < 0.9


def test_review_not_triggered_if_recent():
    state = _make_state(
        mastery_level=MasteryLevel.MASTERED,
        mastery_score=0.9,
        last_mastered_at="2026-03-20T00:00:00",
    )
    state, triggered = check_review_needed(state, now_iso="2026-03-22T00:00:00")
    assert not triggered
    assert state.mastery_level == MasteryLevel.MASTERED


# --- Hint Dependency Tracking ---

def test_hint_dependency_updates():
    state = _make_state()
    # 2 correct with hint, 1 without
    state, _ = update_mastery(state, AnswerEvent(is_correct=True, used_hint=True))
    state, _ = update_mastery(state, AnswerEvent(is_correct=True, used_hint=True))
    state, _ = update_mastery(state, AnswerEvent(is_correct=True, used_hint=False))
    # hint_dependency = 2 / 3 ≈ 0.667
    assert abs(state.hint_dependency - 2/3) < 0.01
