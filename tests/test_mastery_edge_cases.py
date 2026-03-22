"""R14/EXP-B1: Unit tests for mastery engine edge cases.

Directly tests update_mastery() for boundary conditions:
promotion gate blocking, demotion, score clamping, stacking penalties,
REVIEW_NEEDED blocking, hint-heavy paths, and counter resets.
"""
import copy

from learning.concept_state import MasteryLevel, StudentConceptState
from learning.mastery_engine import AnswerEvent, update_mastery, check_review_needed


def _fresh(score=0.0, level=MasteryLevel.UNBUILT, **kw):
    return StudentConceptState(student_id="s1", concept_id="c1",
                               mastery_score=score, mastery_level=level, **kw)


# --- Promotion gate blocking ---

def test_promotion_blocked_by_hint_dependency():
    """Score >= 0.50 but hint_dependency > 0.50 blocks APPROACHING_MASTERY."""
    s = _fresh(score=0.49, level=MasteryLevel.DEVELOPING,
               attempts_total=5, correct_total=5,
               correct_with_hint=5, correct_no_hint=0,
               hint_dependency=1.0, recent_accuracy=0.9,
               consecutive_correct=3)
    s, a = update_mastery(s, AnswerEvent(is_correct=True, used_hint=True))
    assert s.mastery_score >= 0.50
    assert s.mastery_level == MasteryLevel.DEVELOPING  # gate blocked
    assert not a.promoted
    assert any("gate_blocked" in r for r in a.reasons)


def test_promotion_to_mastered_requires_consecutive():
    """Score >= 0.80 but < 3 consecutive correct blocks MASTERED gate."""
    s = _fresh(score=0.79, level=MasteryLevel.APPROACHING_MASTERY,
               attempts_total=8, correct_total=7,
               correct_no_hint=7, hint_dependency=0.0,
               recent_accuracy=0.90, consecutive_correct=1)
    s, a = update_mastery(s, AnswerEvent(is_correct=True))
    assert s.mastery_score >= 0.80
    assert s.mastery_level == MasteryLevel.APPROACHING_MASTERY
    assert not a.promoted


def test_promotion_passes_gate():
    """When all gate conditions met, promotion succeeds."""
    s = _fresh(score=0.79, level=MasteryLevel.APPROACHING_MASTERY,
               attempts_total=10, correct_total=9,
               correct_no_hint=9, hint_dependency=0.0,
               recent_accuracy=0.95, consecutive_correct=3)
    s, a = update_mastery(s, AnswerEvent(is_correct=True))
    assert s.mastery_level == MasteryLevel.MASTERED
    assert a.promoted


# --- Demotion ---

def test_demotion_on_wrong_after_mastered():
    """Wrong answer at score boundary causes demotion from MASTERED."""
    s = _fresh(score=0.82, level=MasteryLevel.MASTERED,
               attempts_total=10, correct_total=9,
               correct_no_hint=9, recent_accuracy=0.85,
               consecutive_correct=0)
    s, a = update_mastery(s, AnswerEvent(is_correct=False))
    assert s.mastery_score < 0.80
    assert s.mastery_level == MasteryLevel.APPROACHING_MASTERY
    assert a.demoted


def test_review_needed_blocks_further_demotion():
    """REVIEW_NEEDED cannot demote even with low score."""
    s = _fresh(score=0.10, level=MasteryLevel.REVIEW_NEEDED,
               attempts_total=15, correct_total=5,
               correct_no_hint=5, recent_accuracy=0.1,
               consecutive_correct=0)
    s, a = update_mastery(s, AnswerEvent(is_correct=False))
    assert s.mastery_level == MasteryLevel.REVIEW_NEEDED
    assert not a.demoted


# --- Score clamping ---

def test_score_floor_at_zero():
    """Score never goes below 0.0 even with stacking penalties."""
    s = _fresh(score=0.05, level=MasteryLevel.UNBUILT,
               attempts_total=5, correct_total=0,
               consecutive_wrong=2, recent_accuracy=0.05,
               avg_response_time_sec=5.0)
    s, a = update_mastery(s, AnswerEvent(is_correct=False, changed_answer=True,
                                          response_time_sec=999.0,
                                          avg_response_time_sec=5.0))
    assert s.mastery_score == 0.0
    assert s.mastery_score >= 0.0


def test_score_ceiling_at_one():
    """Score never exceeds 1.0."""
    s = _fresh(score=0.95, level=MasteryLevel.MASTERED,
               attempts_total=20, correct_total=19,
               correct_no_hint=19, recent_accuracy=0.99,
               consecutive_correct=5)
    s, a = update_mastery(s, AnswerEvent(is_correct=True, is_transfer_item=True,
                                          is_delayed_review=True))
    assert s.mastery_score <= 1.0


# --- Stacking penalties ---

def test_stacking_penalties_single_event():
    """Wrong + too-slow + changed-answer + repeated-failure all stack."""
    s = _fresh(score=0.50, level=MasteryLevel.APPROACHING_MASTERY,
               attempts_total=10, correct_total=5,
               consecutive_wrong=2, recent_accuracy=0.5,
               avg_response_time_sec=5.0)
    s, a = update_mastery(s, AnswerEvent(is_correct=False, changed_answer=True,
                                          response_time_sec=999.0,
                                          avg_response_time_sec=5.0))
    # wrong(-0.10) + too_slow(-0.03) + changed(-0.05) + repeated_failure(-0.15) = -0.33
    assert a.score_delta <= -0.30


# --- Hint-heavy path ---

def test_hint_heavy_path_score_vs_level_mismatch():
    """All-hint student can reach high score but stays at DEVELOPING."""
    s = _fresh(score=0.0, level=MasteryLevel.UNBUILT)
    for _ in range(20):
        s, _ = update_mastery(s, AnswerEvent(is_correct=True, used_hint=True))
    assert s.mastery_score > 0.80  # score is high
    assert s.hint_dependency > 0.90  # but very hint-dependent
    # Cannot be MASTERED due to hint gate
    assert s.mastery_level != MasteryLevel.MASTERED


# --- Counter resets ---

def test_consecutive_counters_reset():
    """Correct resets consecutive_wrong and vice versa."""
    s = _fresh(attempts_total=3, correct_total=0, consecutive_wrong=3)
    s, _ = update_mastery(s, AnswerEvent(is_correct=True))
    assert s.consecutive_correct == 1
    assert s.consecutive_wrong == 0
    s, _ = update_mastery(s, AnswerEvent(is_correct=False))
    assert s.consecutive_correct == 0
    assert s.consecutive_wrong == 1


# --- check_review_needed ---

def test_check_review_triggers_after_7_days():
    """MASTERED student triggers review after 7+ days."""
    from datetime import datetime, timedelta
    old = (datetime.utcnow() - timedelta(days=8)).isoformat()
    s = _fresh(score=0.85, level=MasteryLevel.MASTERED,
               last_mastered_at=old, needs_review=False)
    s2, needed = check_review_needed(s)
    assert needed
    assert s2.mastery_level == MasteryLevel.REVIEW_NEEDED
    assert s2.needs_review


def test_check_review_not_triggered_if_recent():
    """MASTERED student within 7 days does not trigger review."""
    from datetime import datetime, timedelta
    recent = (datetime.utcnow() - timedelta(days=2)).isoformat()
    s = _fresh(score=0.90, level=MasteryLevel.MASTERED,
               last_mastered_at=recent, needs_review=False)
    s2, needed = check_review_needed(s)
    assert not needed
    assert s2.mastery_level == MasteryLevel.MASTERED
