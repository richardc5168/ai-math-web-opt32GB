"""Enhanced Parent Report — Concept-level mastery progress overlay.

Augments the existing parent weekly report with:
- Per-concept mastery progress (with level names in Chinese)
- Hint effectiveness for parent guidance
- Error-type explanations in parent-friendly language
- Weekly progress evidence summary

Does NOT modify the existing parent_report.py — this is an additive overlay.

Usage:
    from learning.parent_report_enhanced import (
        generate_parent_concept_progress,
        format_parent_progress_section,
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .concept_state import MasteryLevel, StudentConceptState
from .concept_taxonomy import get_display_name
from .error_classifier import ErrorType, get_parent_action
from .remediation_flow import HintEffectivenessRecord, compute_hint_effectiveness


# ---------------------------------------------------------------------------
# Chinese-friendly mastery level labels
# ---------------------------------------------------------------------------

MASTERY_LABELS_ZH = {
    MasteryLevel.UNBUILT: "尚未學習",
    MasteryLevel.DEVELOPING: "學習中",
    MasteryLevel.APPROACHING_MASTERY: "接近掌握",
    MasteryLevel.MASTERED: "已掌握 ✓",
    MasteryLevel.REVIEW_NEEDED: "需要複習",
}

MASTERY_PARENT_TIPS = {
    MasteryLevel.UNBUILT: "孩子還沒開始學這個觀念，不用擔心。",
    MasteryLevel.DEVELOPING: "孩子正在學習中，鼓勵他慢慢來，多做幾題。",
    MasteryLevel.APPROACHING_MASTERY: "快要掌握了！再多練習一些就能穩固。",
    MasteryLevel.MASTERED: "孩子已經掌握了，太棒了！偶爾複習維持即可。",
    MasteryLevel.REVIEW_NEEDED: "之前學過但有點忘了，做幾題複習就好。",
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ConceptProgress:
    """Single concept progress for parent report."""
    concept_id: str
    display_name: str
    mastery_label: str
    mastery_level: MasteryLevel
    accuracy_pct: float  # 0-100 scale for readability
    hint_dependency_pct: float  # 0-100 scale
    attempts: int
    parent_tip: str
    hint_effectiveness: Optional[float] = None  # 0-1 scale, None if no data
    recent_errors: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class ParentConceptReport:
    """Concept-level section for parent report."""
    student_id: str
    concepts: List[ConceptProgress] = field(default_factory=list)
    overall_mastery_pct: float = 0.0   # % of concepts at MASTERED level
    total_concepts_active: int = 0
    encouragement: str = ""


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def generate_parent_concept_progress(
    *,
    student_id: str,
    states: List[StudentConceptState],
    hint_records: Optional[List[HintEffectivenessRecord]] = None,
    error_history: Optional[Dict[str, List[str]]] = None,
) -> ParentConceptReport:
    """Generate concept-level progress for a parent report.

    Args:
        student_id: Student identifier.
        states: List of StudentConceptState for this student.
        hint_records: Optional hint effectiveness records for this student.
        error_history: Optional {concept_id: [error_type_value, ...]}.

    Returns:
        ParentConceptReport with concept-by-concept progress.
    """
    # Compute hint effectiveness by concept
    hint_eff = {}
    if hint_records:
        eff_data = compute_hint_effectiveness(hint_records)
        for cid, data in eff_data.items():
            hint_eff[cid] = data.get("overall_effectiveness", None)

    error_history = error_history or {}

    concepts = []
    mastered_count = 0

    for state in states:
        level = state.mastery_level
        label = MASTERY_LABELS_ZH.get(level, str(level.value))
        tip = MASTERY_PARENT_TIPS.get(level, "")

        acc_pct = round((state.recent_accuracy or 0.0) * 100, 1)
        hd_pct = round(state.hint_dependency * 100, 1)

        # Error descriptions for parent
        recent_errors = []
        for err_val in (error_history.get(state.concept_id) or [])[:3]:
            try:
                et = ErrorType(err_val)
                action = get_parent_action(et)
                if action:
                    recent_errors.append({
                        "error_type": err_val,
                        "parent_action": action,
                    })
            except ValueError:
                pass

        concepts.append(ConceptProgress(
            concept_id=state.concept_id,
            display_name=get_display_name(state.concept_id),
            mastery_label=label,
            mastery_level=level,
            accuracy_pct=acc_pct,
            hint_dependency_pct=hd_pct,
            attempts=state.attempts_total,
            parent_tip=tip,
            hint_effectiveness=hint_eff.get(state.concept_id),
            recent_errors=recent_errors,
        ))

        if level == MasteryLevel.MASTERED:
            mastered_count += 1

    active = len([c for c in concepts if c.attempts > 0])
    overall_pct = round(mastered_count / len(concepts) * 100, 1) if concepts else 0.0

    # Encouragement based on overall progress
    if overall_pct >= 80:
        encouragement = "孩子表現非常優秀！大部分觀念都已掌握。"
    elif overall_pct >= 50:
        encouragement = "孩子持續進步中，已經掌握一半以上的觀念了！"
    elif overall_pct >= 20:
        encouragement = "孩子正在努力學習，多給予鼓勵和陪伴。"
    else:
        encouragement = "學習需要時間，每天進步一點點就很棒了！"

    return ParentConceptReport(
        student_id=student_id,
        concepts=concepts,
        overall_mastery_pct=overall_pct,
        total_concepts_active=active,
        encouragement=encouragement,
    )


def format_parent_progress_section(report: ParentConceptReport) -> str:
    """Format concept progress as a Markdown section for the parent report."""
    lines = [
        "## 觀念掌握進度",
        f"- 整體掌握率：{report.overall_mastery_pct}%",
        f"- {report.encouragement}",
        "",
    ]

    # Sort: needs-attention first, mastered last
    level_order = {
        MasteryLevel.REVIEW_NEEDED: 0,
        MasteryLevel.UNBUILT: 1,
        MasteryLevel.DEVELOPING: 2,
        MasteryLevel.APPROACHING_MASTERY: 3,
        MasteryLevel.MASTERED: 4,
    }
    sorted_concepts = sorted(
        report.concepts,
        key=lambda c: level_order.get(c.mastery_level, 5),
    )

    for c in sorted_concepts:
        lines.append(f"### {c.display_name}")
        lines.append(f"- 狀態：{c.mastery_label}")
        lines.append(f"- 正確率：{c.accuracy_pct}%　提示依賴：{c.hint_dependency_pct}%　作答：{c.attempts} 題")
        lines.append(f"- 💡 {c.parent_tip}")

        if c.hint_effectiveness is not None:
            eff_pct = round(c.hint_effectiveness * 100)
            if eff_pct < 40:
                lines.append(f"- 提示效果偏低（{eff_pct}%），可能需要換個方式解釋")
            elif eff_pct >= 70:
                lines.append(f"- 提示對孩子很有幫助（{eff_pct}%）")

        if c.recent_errors:
            lines.append("- 近期常見錯誤：")
            for err in c.recent_errors:
                lines.append(f"  - {err['parent_action']}")

        lines.append("")

    return "\n".join(lines)


def progress_to_dict(report: ParentConceptReport) -> Dict[str, Any]:
    """Convert to JSON-serializable dict."""
    return {
        "student_id": report.student_id,
        "overall_mastery_pct": report.overall_mastery_pct,
        "total_concepts_active": report.total_concepts_active,
        "encouragement": report.encouragement,
        "concepts": [
            {
                "concept_id": c.concept_id,
                "display_name": c.display_name,
                "mastery_label": c.mastery_label,
                "mastery_level": c.mastery_level.value,
                "accuracy_pct": c.accuracy_pct,
                "hint_dependency_pct": c.hint_dependency_pct,
                "attempts": c.attempts,
                "parent_tip": c.parent_tip,
                "hint_effectiveness": c.hint_effectiveness,
                "recent_errors": c.recent_errors,
            }
            for c in report.concepts
        ],
    }
