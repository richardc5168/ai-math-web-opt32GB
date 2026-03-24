"""Mastery Update Engine — Rule-based mastery state transitions.

Pure functions that take a StudentConceptState + an answer event and return
updated state + actions. All thresholds come from mastery_config.py.

Usage:
    from learning.mastery_engine import update_mastery, AnswerEvent, MasteryActions
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .concept_state import MasteryLevel, StudentConceptState
from .mastery_config import MASTERY_CONFIG, get_level_for_score, get_promotion_gate, get_score_delta


# ---------------------------------------------------------------------------
# Answer Event (input to engine)
# ---------------------------------------------------------------------------

@dataclass
class AnswerEvent:
    is_correct: bool
    used_hint: bool = False
    hint_levels_shown: int = 0
    hint_level_used: Optional[int] = None   # R52: actual max hint level opened (1-4)
    response_time_sec: float = 0.0
    changed_answer: bool = False
    is_transfer_item: bool = False          # item tests concept in new context
    is_delayed_review: bool = False         # item is a spaced review
    error_type: Optional[str] = None        # from error classifier
    avg_response_time_sec: Optional[float] = None  # student's avg for this concept
    # R44: richer evidence
    first_answer_correct: bool = False      # first attempt was correct (before any change)
    attempts_count: int = 1                 # number of submissions for this question
    selection_reason: Optional[str] = None  # why this question was selected


# ---------------------------------------------------------------------------
# Actions (output from engine — what happened)
# ---------------------------------------------------------------------------

@dataclass
class MasteryActions:
    score_delta: float = 0.0
    new_level: Optional[MasteryLevel] = None   # set if level changed
    promoted: bool = False
    demoted: bool = False
    review_triggered: bool = False
    remediation_needed: bool = False
    calm_mode_entered: bool = False
    reasons: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def update_mastery(
    state: StudentConceptState,
    event: AnswerEvent,
    *,
    config: Optional[Dict[str, Any]] = None,
    now_iso: Optional[str] = None,
) -> Tuple[StudentConceptState, MasteryActions]:
    """Rule-based mastery update. Mutates and returns state + actions.

    This is a pure function (aside from now_iso default). All rules are
    driven by config, not hard-coded.
    """
    cfg = config or MASTERY_CONFIG
    actions = MasteryActions()
    now = now_iso or datetime.now().isoformat(timespec="seconds")

    old_level = state.mastery_level

    # --- Update counters ---
    state.attempts_total += 1
    state.last_seen_at = now

    if event.is_correct:
        state.correct_total += 1
        state.consecutive_correct += 1
        state.consecutive_wrong = 0
        if event.used_hint:
            state.correct_with_hint += 1
        else:
            state.correct_no_hint += 1
    else:
        state.consecutive_correct = 0
        state.consecutive_wrong += 1

    # --- Update recent accuracy (rolling window of last N) ---
    # Simple approach: exponential moving average
    alpha = 0.3  # weight of new observation
    new_value = 1.0 if event.is_correct else 0.0
    if state.recent_accuracy is None:
        state.recent_accuracy = new_value
    else:
        state.recent_accuracy = alpha * new_value + (1 - alpha) * state.recent_accuracy

    # --- Update hint dependency ---
    total_correct = state.correct_no_hint + state.correct_with_hint
    if total_correct > 0:
        state.hint_dependency = state.correct_with_hint / total_correct

    # --- Update avg response time ---
    if event.response_time_sec > 0:
        if state.avg_response_time_sec is None:
            state.avg_response_time_sec = event.response_time_sec
        else:
            state.avg_response_time_sec = (
                0.2 * event.response_time_sec + 0.8 * state.avg_response_time_sec
            )

    # --- Compute score delta ---
    delta = 0.0

    if event.is_correct and not event.used_hint:
        delta += get_score_delta("correct_no_hint")
        actions.reasons.append("correct_no_hint")
    elif event.is_correct and event.used_hint:
        delta += get_score_delta("correct_with_hint")
        actions.reasons.append("correct_with_hint")
        # R52: heavy hint penalty — if student needed L3+ hint, reduced credit
        _hl = event.hint_level_used
        if _hl is not None and _hl >= 3:
            heavy_penalty = get_score_delta("heavy_hint_penalty")
            delta += heavy_penalty
            actions.reasons.append("heavy_hint_L3+")
    elif not event.is_correct:
        delta += get_score_delta("wrong")
        actions.reasons.append("wrong")

    # Transfer success bonus
    if event.is_transfer_item and event.is_correct:
        delta += get_score_delta("transfer_success")
        state.transfer_success_count += 1
        actions.reasons.append("transfer_success")

    # Delayed review bonus
    if event.is_delayed_review and event.is_correct:
        delta += get_score_delta("delayed_review_correct")
        state.delayed_review_status = "passed"
        actions.reasons.append("delayed_review_correct")
    elif event.is_delayed_review and not event.is_correct:
        state.delayed_review_status = "failed"

    # Too slow penalty
    time_cfg = cfg.get("time", {})
    if event.response_time_sec > 0 and event.avg_response_time_sec and event.avg_response_time_sec > 0:
        threshold = max(
            time_cfg.get("min_too_slow_sec", 30),
            event.avg_response_time_sec * time_cfg.get("too_slow_multiplier", 2.5),
        )
        if event.response_time_sec >= threshold:
            delta += get_score_delta("too_slow_penalty")
            actions.reasons.append("too_slow")

    # Changed answer penalty
    if event.changed_answer:
        delta += get_score_delta("repeated_changes_penalty")
        actions.reasons.append("repeated_changes")

    # R44: First-answer-correct bonus — reward confident, correct first attempts
    if event.is_correct and event.first_answer_correct and not event.used_hint:
        delta += get_score_delta("first_answer_correct_bonus")
        actions.reasons.append("first_answer_correct")

    # R44: Multi-attempt penalty — student needed multiple submissions
    if event.attempts_count > 1:
        delta += get_score_delta("multi_attempt_penalty")
        actions.reasons.append("multi_attempt")

    # Repeated failure penalty
    failure_cfg = cfg.get("failure", {})
    if state.consecutive_wrong >= failure_cfg.get("repeated_failure_threshold", 3):
        delta += get_score_delta("repeated_failure")
        actions.reasons.append("repeated_failure")

    # --- Apply score delta ---
    state.mastery_score = max(0.0, min(1.0, state.mastery_score + delta))
    actions.score_delta = delta

    # --- Determine new level ---
    candidate_level_name = get_level_for_score(state.mastery_score)
    candidate_level = MasteryLevel(candidate_level_name)

    # Check promotion gates
    if _level_rank(candidate_level) > _level_rank(old_level):
        gate = get_promotion_gate(candidate_level_name)
        if _passes_gate(state, gate):
            state.mastery_level = candidate_level
            actions.promoted = True
            actions.new_level = candidate_level
            actions.reasons.append(f"promoted_to_{candidate_level_name}")
            if candidate_level == MasteryLevel.MASTERED:
                state.last_mastered_at = now
                state.needs_review = False
        else:
            # Score high enough but gate not passed — keep old level
            actions.reasons.append(f"gate_blocked_{candidate_level_name}")
    elif _level_rank(candidate_level) < _level_rank(old_level):
        # Demotion — no gate needed
        if old_level != MasteryLevel.REVIEW_NEEDED:
            state.mastery_level = candidate_level
            actions.demoted = True
            actions.new_level = candidate_level
            actions.reasons.append(f"demoted_to_{candidate_level_name}")

    # --- Remediation check ---
    if state.consecutive_wrong >= failure_cfg.get("remediation_trigger", 3):
        actions.remediation_needed = True
        actions.reasons.append("remediation_needed")

    # --- Calm mode ---
    if state.consecutive_wrong >= failure_cfg.get("calm_mode_threshold", 3):
        actions.calm_mode_entered = True
        actions.reasons.append("calm_mode")

    return state, actions


def check_review_needed(
    state: StudentConceptState,
    *,
    config: Optional[Dict[str, Any]] = None,
    now_iso: Optional[str] = None,
) -> Tuple[StudentConceptState, bool]:
    """Check if a mastered concept needs review based on time elapsed.

    Call this periodically (e.g., at session start).
    Returns (updated_state, review_triggered).
    """
    cfg = config or MASTERY_CONFIG
    review_cfg = cfg.get("review_trigger", {})

    if state.mastery_level != MasteryLevel.MASTERED:
        return state, False

    if not state.last_mastered_at:
        return state, False

    now = now_iso or datetime.now().isoformat(timespec="seconds")
    try:
        mastered_dt = datetime.fromisoformat(state.last_mastered_at)
        now_dt = datetime.fromisoformat(now)
        days_elapsed = (now_dt - mastered_dt).days
    except (ValueError, TypeError):
        return state, False

    days_threshold = review_cfg.get("days_since_mastered", 7)
    if days_elapsed >= days_threshold:
        state.mastery_level = MasteryLevel.REVIEW_NEEDED
        state.needs_review = True
        decay = review_cfg.get("review_decay_score", -0.05)
        state.mastery_score = max(0.0, state.mastery_score + decay)
        return state, True

    return state, False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_LEVEL_RANKS = {
    MasteryLevel.UNBUILT: 0,
    MasteryLevel.DEVELOPING: 1,
    MasteryLevel.APPROACHING_MASTERY: 2,
    MasteryLevel.MASTERED: 3,
    MasteryLevel.REVIEW_NEEDED: 2,  # same rank as approaching — needs re-proving
}


def _level_rank(level: MasteryLevel) -> int:
    return _LEVEL_RANKS.get(level, 0)


def _passes_gate(state: StudentConceptState, gate: Dict[str, Any]) -> bool:
    """Check if state passes a promotion gate."""
    if not gate:
        return True

    if state.attempts_total < gate.get("min_attempts", 0):
        return False

    if state.recent_accuracy is not None:
        if state.recent_accuracy < gate.get("min_recent_accuracy", 0.0):
            return False

    max_hint = gate.get("max_hint_dependency")
    if max_hint is not None and state.hint_dependency > max_hint:
        return False

    min_consec = gate.get("min_consecutive_correct")
    if min_consec is not None and state.consecutive_correct < min_consec:
        return False

    return True
