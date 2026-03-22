"""Mastery configuration — All thresholds and rules in one place.

This file centralizes every tunable parameter for the mastery engine,
next-item selector, and review triggers. Never hard-code thresholds in
UI or engine logic — read them from here.

To adjust behavior, modify MASTERY_CONFIG and run tests.
"""

from __future__ import annotations

from typing import Any, Dict

MASTERY_CONFIG: Dict[str, Any] = {
    # ----- Score Deltas -----
    # Applied to mastery_score (0.0 – 1.0) after each event.
    # Clamped to [0.0, 1.0] after application.
    "score_deltas": {
        "correct_no_hint": 0.15,
        "correct_with_hint": 0.08,
        "wrong": -0.10,
        "too_slow_penalty": -0.03,
        "repeated_changes_penalty": -0.05,
        "transfer_success": 0.12,
        "delayed_review_correct": 0.10,
        "repeated_failure": -0.15,  # >= 3 consecutive wrong
    },

    # ----- Level Boundaries -----
    # mastery_score ranges that map to mastery_level.
    # Checked after score update; highest matching level wins.
    "levels": {
        "unbuilt":             {"min_score": 0.00, "max_score": 0.19},
        "developing":          {"min_score": 0.20, "max_score": 0.49},
        "approaching_mastery": {"min_score": 0.50, "max_score": 0.79},
        "mastered":            {"min_score": 0.80, "max_score": 1.00},
    },

    # ----- Promotion Gates -----
    # Even if score is high enough, these extra conditions must be met
    # to promote to the next level. Prevents fluky promotion.
    "promotion_gates": {
        "to_developing": {
            "min_attempts": 3,
            "min_recent_accuracy": 0.30,
        },
        "to_approaching_mastery": {
            "min_attempts": 5,
            "min_recent_accuracy": 0.60,
            "max_hint_dependency": 0.50,
        },
        "to_mastered": {
            "min_attempts": 8,
            "min_recent_accuracy": 0.85,
            "max_hint_dependency": 0.25,
            "min_consecutive_correct": 3,
        },
    },

    # ----- Review Trigger -----
    "review_trigger": {
        "days_since_mastered": 7,
        "review_decay_score": -0.05,  # mastery_score penalty when review triggers
    },

    # ----- Hint Dependency Thresholds -----
    "hint_dependency": {
        # hint_dependency = correct_with_hint / (correct_no_hint + correct_with_hint)
        "high": 0.60,   # above this → flag as hint-dependent
        "low": 0.25,    # below this → independent learner
    },

    # ----- Consecutive Failure -----
    "failure": {
        "repeated_failure_threshold": 3,  # consecutive wrong to trigger repeated_failure delta
        "calm_mode_threshold": 3,         # consecutive wrong to enter calm mode
        "remediation_trigger": 3,         # consecutive wrong on same concept to trigger remediation
    },

    # ----- Time Thresholds -----
    "time": {
        "too_slow_multiplier": 2.5,  # time > avg * this → too_slow
        "min_too_slow_sec": 30,       # absolute minimum before too_slow applies
        "guess_threshold_sec": 2,     # time < this → likely guessing
    },

    # ----- Next-Item Selector Weights -----
    "selector": {
        # Probability of selecting from each pool when student has mixed mastery
        "mastered_spiral_review_prob": 0.15,
        "approaching_variant_prob": 0.30,
        "developing_standard_prob": 0.70,
        "unbuilt_prerequisite_first": True,
        # When application item fails but basic is stable,
        # reduce language complexity rather than full downgrade
        "smart_downgrade": True,
    },
}


def get_score_delta(event_type: str) -> float:
    """Get the score delta for an event type."""
    return MASTERY_CONFIG["score_deltas"].get(event_type, 0.0)


def get_level_for_score(score: float) -> str:
    """Map a mastery score to a mastery level name."""
    for level_name in ["mastered", "approaching_mastery", "developing", "unbuilt"]:
        bounds = MASTERY_CONFIG["levels"][level_name]
        if score >= bounds["min_score"]:
            return level_name
    return "unbuilt"


def get_promotion_gate(level_name: str) -> Dict[str, Any]:
    """Get the promotion gate requirements for a level."""
    key = f"to_{level_name}"
    return MASTERY_CONFIG["promotion_gates"].get(key, {})
