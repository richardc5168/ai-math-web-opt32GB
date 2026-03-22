"""Remediation Flow Engine — Manages hint escalation and fallback.

Implements 3-layer hint flow:
1. Concept hint — conceptual guidance, no numbers
2. Step hint — algebraic form, method
3. Scaffold hint — nearly complete, student fills last step

When student is stuck (≥3 consecutive wrong on same concept):
- Switch to simpler isomorphic item (same concept, easier numbers)
- Or prerequisite item (foundational concept)

All hint and remediation events are logged for effectiveness tracking.

Usage:
    from learning.remediation_flow import (
        HintLevel, RemediationAction, get_next_hint, evaluate_remediation_need
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional

from .mastery_config import MASTERY_CONFIG


# ---------------------------------------------------------------------------
# Hint Levels
# ---------------------------------------------------------------------------

class HintLevel(IntEnum):
    NONE = 0
    CONCEPT = 1      # Conceptual guidance (what approach to use)
    STEP = 2         # Step-by-step method (how to set up)
    SCAFFOLD = 3     # Nearly full solution (fill in last step)
    SOLUTION = 4     # Full solution shown


# ---------------------------------------------------------------------------
# Remediation Actions
# ---------------------------------------------------------------------------

@dataclass
class RemediationAction:
    action_type: str          # "show_hint" | "simpler_item" | "prerequisite_item" | "flag_teacher"
    hint_level: Optional[HintLevel] = None
    target_concept_id: Optional[str] = None
    reason: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Hint Session State (per question attempt)
# ---------------------------------------------------------------------------

@dataclass
class HintSession:
    """Tracks hint state for current question attempt."""
    question_id: str
    concept_id: str
    current_level: HintLevel = HintLevel.NONE
    hints_shown: List[HintLevel] = field(default_factory=list)
    attempts_at_level: int = 0
    total_wrong_this_concept: int = 0  # across multiple questions


# ---------------------------------------------------------------------------
# Core Functions
# ---------------------------------------------------------------------------

def get_next_hint(session: HintSession) -> RemediationAction:
    """Determine what hint to show next.

    Escalation: NONE → CONCEPT → STEP → SCAFFOLD → SOLUTION
    After SOLUTION, recommend remediation if still wrong.
    """
    if session.current_level >= HintLevel.SOLUTION:
        # Already shown full solution — trigger remediation
        return evaluate_remediation_need(session)

    next_level = HintLevel(session.current_level + 1)

    session.current_level = next_level
    session.hints_shown.append(next_level)

    level_names = {
        HintLevel.CONCEPT: "觀念提示",
        HintLevel.STEP: "步驟提示",
        HintLevel.SCAFFOLD: "鷹架提示",
        HintLevel.SOLUTION: "完整解答",
    }

    return RemediationAction(
        action_type="show_hint",
        hint_level=next_level,
        target_concept_id=session.concept_id,
        reason=f"提供{level_names.get(next_level, '提示')}",
    )


def evaluate_remediation_need(session: HintSession) -> RemediationAction:
    """Evaluate whether remediation is needed based on hint session state.

    Called when student exhausted hints or has too many consecutive wrong.
    """
    cfg = MASTERY_CONFIG.get("failure", {})
    remediation_trigger = cfg.get("remediation_trigger", 3)

    if session.total_wrong_this_concept >= remediation_trigger:
        if session.current_level >= HintLevel.SCAFFOLD:
            # Exhausted hints AND repeated failure → try simpler item
            return RemediationAction(
                action_type="simpler_item",
                target_concept_id=session.concept_id,
                reason=f"連續 {session.total_wrong_this_concept} 次答錯且提示已用完，切換到更簡單的同類題",
                details={
                    "wrong_count": session.total_wrong_this_concept,
                    "hints_used": [int(h) for h in session.hints_shown],
                },
            )
        else:
            # Repeated failure but hints not exhausted → escalate hint
            return get_next_hint(session)

    if session.total_wrong_this_concept >= remediation_trigger + 2:
        # Very stuck → suggest prerequisite
        return RemediationAction(
            action_type="prerequisite_item",
            target_concept_id=session.concept_id,
            reason=f"多次答錯，建議回到前置概念重新學習",
            details={
                "wrong_count": session.total_wrong_this_concept,
            },
        )

    # Not yet at remediation threshold
    return RemediationAction(
        action_type="show_hint",
        hint_level=HintLevel.CONCEPT,
        target_concept_id=session.concept_id,
        reason="繼續練習，可嘗試使用提示",
    )


def should_flag_teacher(session: HintSession) -> bool:
    """Check if student needs teacher intervention."""
    return (
        session.total_wrong_this_concept >= 5
        and session.current_level >= HintLevel.SOLUTION
    )


# ---------------------------------------------------------------------------
# Hint Effectiveness Tracking
# ---------------------------------------------------------------------------

@dataclass
class HintEffectivenessRecord:
    """Records whether a hint led to correct answer on next attempt."""
    concept_id: str
    hint_level: HintLevel
    led_to_correct: bool
    attempts_after_hint: int = 0


def compute_hint_effectiveness(
    records: List[HintEffectivenessRecord],
) -> Dict[str, Dict[str, Any]]:
    """Compute hint effectiveness stats by concept and level.

    Returns:
        {concept_id: {
            "by_level": {
                "concept": {"total": N, "effective": M, "rate": float},
                "step": {...},
                "scaffold": {...},
            },
            "overall_effectiveness": float,
        }}
    """
    by_concept: Dict[str, Dict[str, Any]] = {}

    for rec in records:
        cid = rec.concept_id
        if cid not in by_concept:
            by_concept[cid] = {"by_level": {}, "_total": 0, "_effective": 0}

        level_name = _hint_level_name(rec.hint_level)
        if level_name not in by_concept[cid]["by_level"]:
            by_concept[cid]["by_level"][level_name] = {"total": 0, "effective": 0}

        by_concept[cid]["by_level"][level_name]["total"] += 1
        by_concept[cid]["_total"] += 1

        if rec.led_to_correct:
            by_concept[cid]["by_level"][level_name]["effective"] += 1
            by_concept[cid]["_effective"] += 1

    # Compute rates
    result = {}
    for cid, data in by_concept.items():
        concept_result = {"by_level": {}}
        for level_name, stats in data["by_level"].items():
            total = stats["total"]
            effective = stats["effective"]
            concept_result["by_level"][level_name] = {
                "total": total,
                "effective": effective,
                "rate": effective / total if total > 0 else 0.0,
            }
        total = data["_total"]
        effective = data["_effective"]
        concept_result["overall_effectiveness"] = effective / total if total > 0 else 0.0
        result[cid] = concept_result

    return result


def _hint_level_name(level: HintLevel) -> str:
    names = {
        HintLevel.CONCEPT: "concept",
        HintLevel.STEP: "step",
        HintLevel.SCAFFOLD: "scaffold",
        HintLevel.SOLUTION: "solution",
    }
    return names.get(level, "unknown")
