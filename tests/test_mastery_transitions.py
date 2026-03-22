"""R15/EXP-B2: Mastery transition path tests.

Tests the full lifecycle transitions that R14 edge cases didn't cover:
transfer/delayed-review bonuses, remediation/calm flags, full lifecycle,
REVIEW_NEEDED re-mastery, and delayed_review_status tracking.
"""
from learning.concept_state import MasteryLevel, StudentConceptState
from learning.mastery_engine import AnswerEvent, MasteryActions, update_mastery, check_review_needed


def _state(score=0.0, level=MasteryLevel.UNBUILT, **kw):
    return StudentConceptState(student_id="s1", concept_id="c1",
                               mastery_score=score, mastery_level=level, **kw)


# --- Full lifecycle: UNBUILT → DEVELOPING → APPROACHING → MASTERED ---

def test_full_promotion_lifecycle():
    """Student progresses through all levels via correct answers."""
    s = _state()
    levels_seen = [s.mastery_level]
    for _ in range(30):
        s, a = update_mastery(s, AnswerEvent(is_correct=True))
        if a.promoted:
            levels_seen.append(s.mastery_level)
    assert MasteryLevel.DEVELOPING in levels_seen
    assert MasteryLevel.APPROACHING_MASTERY in levels_seen
    assert MasteryLevel.MASTERED in levels_seen


# --- Transfer item bonus ---

def test_transfer_success_bonus():
    """Transfer item correct gives correct_no_hint + transfer_success bonus."""
    s = _state(score=0.40, level=MasteryLevel.DEVELOPING,
               attempts_total=5, correct_total=4, correct_no_hint=4,
               recent_accuracy=0.8, consecutive_correct=2)
    s, a = update_mastery(s, AnswerEvent(is_correct=True, is_transfer_item=True))
    assert "transfer_success" in a.reasons
    assert "correct_no_hint" in a.reasons
    assert s.transfer_success_count == 1
    # +0.15 (correct) + 0.12 (transfer) = +0.27
    assert abs(a.score_delta - 0.27) < 0.01


def test_transfer_wrong_no_bonus():
    """Transfer item wrong gets no transfer bonus."""
    s = _state(score=0.50, level=MasteryLevel.APPROACHING_MASTERY,
               attempts_total=5, correct_total=3, correct_no_hint=3)
    s, a = update_mastery(s, AnswerEvent(is_correct=False, is_transfer_item=True))
    assert "transfer_success" not in a.reasons
    assert s.transfer_success_count == 0


# --- Delayed review bonus ---

def test_delayed_review_correct_bonus():
    """Delayed review correct gives correct + delayed_review_correct bonus."""
    s = _state(score=0.50, level=MasteryLevel.APPROACHING_MASTERY,
               attempts_total=8, correct_total=6, correct_no_hint=6,
               recent_accuracy=0.8, consecutive_correct=2)
    s, a = update_mastery(s, AnswerEvent(is_correct=True, is_delayed_review=True))
    assert "delayed_review_correct" in a.reasons
    assert s.delayed_review_status == "passed"
    # +0.15 correct + 0.10 delayed = +0.25
    assert abs(a.score_delta - 0.25) < 0.01


def test_delayed_review_failed_status():
    """Delayed review wrong sets status to failed, no bonus."""
    s = _state(score=0.50, level=MasteryLevel.APPROACHING_MASTERY,
               attempts_total=5, correct_total=3, correct_no_hint=3)
    s, a = update_mastery(s, AnswerEvent(is_correct=False, is_delayed_review=True))
    assert s.delayed_review_status == "failed"
    assert "delayed_review_correct" not in a.reasons


# --- Remediation and calm mode ---

def test_remediation_triggered_at_3_wrong():
    """3 consecutive wrong triggers remediation_needed."""
    s = _state(score=0.30, level=MasteryLevel.DEVELOPING,
               attempts_total=5, correct_total=2, consecutive_wrong=2)
    s, a = update_mastery(s, AnswerEvent(is_correct=False))
    assert a.remediation_needed
    assert "remediation_needed" in a.reasons


def test_calm_mode_triggered_at_3_wrong():
    """3 consecutive wrong triggers calm_mode_entered."""
    s = _state(score=0.30, level=MasteryLevel.DEVELOPING,
               attempts_total=5, correct_total=2, consecutive_wrong=2)
    s, a = update_mastery(s, AnswerEvent(is_correct=False))
    assert a.calm_mode_entered
    assert "calm_mode" in a.reasons


def test_no_remediation_at_2_wrong():
    """2 consecutive wrong does NOT trigger remediation."""
    s = _state(score=0.30, level=MasteryLevel.DEVELOPING,
               attempts_total=4, correct_total=2, consecutive_wrong=1)
    s, a = update_mastery(s, AnswerEvent(is_correct=False))
    assert not a.remediation_needed
    assert not a.calm_mode_entered


# --- REVIEW_NEEDED re-mastery ---

def test_review_needed_can_promote_back():
    """Student in REVIEW_NEEDED can re-promote to MASTERED if gate passes."""
    s = _state(score=0.79, level=MasteryLevel.REVIEW_NEEDED,
               attempts_total=15, correct_total=13,
               correct_no_hint=13, hint_dependency=0.0,
               recent_accuracy=0.90, consecutive_correct=3,
               needs_review=True)
    s, a = update_mastery(s, AnswerEvent(is_correct=True))
    assert s.mastery_score >= 0.80
    assert s.mastery_level == MasteryLevel.MASTERED
    assert a.promoted
    assert not s.needs_review


# --- Too slow penalty ---

def test_too_slow_penalty_applied():
    """Response exceeding max(30s, avg*2.5) gets too_slow penalty."""
    s = _state(score=0.50, level=MasteryLevel.APPROACHING_MASTERY,
               attempts_total=10, correct_total=7, correct_no_hint=7,
               recent_accuracy=0.7, avg_response_time_sec=10.0)
    s, a = update_mastery(s, AnswerEvent(is_correct=True,
                                          response_time_sec=60.0,
                                          avg_response_time_sec=10.0))
    assert "too_slow" in a.reasons
    # correct_no_hint(+0.15) + too_slow(-0.03) = +0.12
    assert abs(a.score_delta - 0.12) < 0.01


def test_not_too_slow_within_threshold():
    """Response within threshold gets no penalty."""
    s = _state(score=0.50, level=MasteryLevel.APPROACHING_MASTERY,
               attempts_total=10, correct_total=7, correct_no_hint=7,
               recent_accuracy=0.7, avg_response_time_sec=10.0)
    s, a = update_mastery(s, AnswerEvent(is_correct=True,
                                          response_time_sec=15.0,
                                          avg_response_time_sec=10.0))
    assert "too_slow" not in a.reasons
