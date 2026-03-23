"""Teacher Report — Concept-level class analytics.

Provides class-level insights based on the enhanced concept mastery system:
- Top blocking concepts (most students stuck)
- Students needing remediation
- Concept mastery distribution across class
- Hint effectiveness per concept
- Repeated failure patterns
- Class insight summary in Chinese

Usage:
    from learning.teacher_report import generate_teacher_report
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .concept_state import MasteryLevel, StudentConceptState
from .concept_taxonomy import CONCEPT_TAXONOMY, get_display_name
from .error_classifier import ERROR_DESCRIPTIONS, ErrorType
from .remediation_flow import HintEffectivenessRecord, compute_hint_effectiveness


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ConceptClassSummary:
    """Summary of one concept across all students."""
    concept_id: str
    display_name: str
    student_count: int = 0
    mastered_count: int = 0
    developing_count: int = 0
    approaching_count: int = 0
    unbuilt_count: int = 0
    review_needed_count: int = 0
    avg_accuracy: float = 0.0
    avg_hint_dependency: float = 0.0
    blocking_score: float = 0.0  # higher = more students stuck


@dataclass
class StudentRisk:
    """A student flagged for teacher attention."""
    student_id: str
    display_name: str
    struggling_concepts: List[str] = field(default_factory=list)
    overall_accuracy: float = 0.0
    hint_dependency: float = 0.0
    risk_level: str = "low"  # "low" | "medium" | "high"
    recommended_action: str = ""


@dataclass
class TeacherReport:
    """Full teacher report."""
    class_id: str
    generated_for: str  # teacher name or ID
    student_count: int = 0
    active_student_count: int = 0
    top_blocking_concepts: List[ConceptClassSummary] = field(default_factory=list)
    students_needing_attention: List[StudentRisk] = field(default_factory=list)
    concept_distribution: List[ConceptClassSummary] = field(default_factory=list)
    hint_effectiveness: Dict[str, Any] = field(default_factory=dict)
    common_error_patterns: List[Dict[str, Any]] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core report generation
# ---------------------------------------------------------------------------

def generate_teacher_report(
    *,
    class_id: str,
    teacher_name: str = "",
    student_states: Dict[str, List[StudentConceptState]],
    hint_records: Optional[List[HintEffectivenessRecord]] = None,
    error_counts: Optional[Dict[str, Dict[str, int]]] = None,
) -> TeacherReport:
    """Generate a comprehensive teacher report.

    Args:
        class_id: Class identifier.
        teacher_name: Teacher display name.
        student_states: {student_id: [StudentConceptState, ...]}.
        hint_records: Optional list of hint effectiveness records.
        error_counts: Optional {concept_id: {error_type: count}}.

    Returns:
        TeacherReport with all sections populated.
    """
    report = TeacherReport(
        class_id=class_id,
        generated_for=teacher_name,
        student_count=len(student_states),
    )

    # -- Concept distribution --
    concept_stats = _compute_concept_distribution(student_states)
    report.concept_distribution = concept_stats
    report.top_blocking_concepts = sorted(
        concept_stats, key=lambda c: -c.blocking_score
    )[:5]

    # -- Students needing attention --
    report.students_needing_attention = _identify_at_risk_students(student_states)
    report.active_student_count = sum(
        1 for states in student_states.values() if states
    )

    # -- Hint effectiveness --
    if hint_records:
        report.hint_effectiveness = compute_hint_effectiveness(hint_records)

    # -- Error patterns --
    if error_counts:
        report.common_error_patterns = _summarize_error_patterns(error_counts)

    # -- Insights --
    report.insights = _generate_insights(report)

    return report


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _compute_concept_distribution(
    student_states: Dict[str, List[StudentConceptState]],
) -> List[ConceptClassSummary]:
    """Aggregate concept mastery across all students."""
    concept_data: Dict[str, Dict[str, Any]] = {}

    for student_id, states in student_states.items():
        for state in states:
            cid = state.concept_id
            if cid not in concept_data:
                concept_data[cid] = {
                    "student_count": 0,
                    "mastered": 0,
                    "developing": 0,
                    "approaching": 0,
                    "unbuilt": 0,
                    "review_needed": 0,
                    "accuracy_sum": 0.0,
                    "hint_dep_sum": 0.0,
                }
            d = concept_data[cid]
            d["student_count"] += 1
            d["accuracy_sum"] += state.recent_accuracy
            d["hint_dep_sum"] += state.hint_dependency

            level = state.mastery_level
            if level == MasteryLevel.MASTERED:
                d["mastered"] += 1
            elif level == MasteryLevel.APPROACHING_MASTERY:
                d["approaching"] += 1
            elif level == MasteryLevel.DEVELOPING:
                d["developing"] += 1
            elif level == MasteryLevel.REVIEW_NEEDED:
                d["review_needed"] += 1
            else:
                d["unbuilt"] += 1

    summaries = []
    for cid, d in concept_data.items():
        n = d["student_count"]
        avg_acc = d["accuracy_sum"] / n if n > 0 else 0.0
        avg_hd = d["hint_dep_sum"] / n if n > 0 else 0.0

        # Blocking score: students NOT mastered / total, weighted by hint dependency
        not_mastered = n - d["mastered"]
        blocking = (not_mastered / n * 100) if n > 0 else 0.0
        blocking += avg_hd * 20  # boost if hints heavily used

        summaries.append(ConceptClassSummary(
            concept_id=cid,
            display_name=get_display_name(cid),
            student_count=n,
            mastered_count=d["mastered"],
            developing_count=d["developing"],
            approaching_count=d["approaching"],
            unbuilt_count=d["unbuilt"],
            review_needed_count=d["review_needed"],
            avg_accuracy=round(avg_acc, 4),
            avg_hint_dependency=round(avg_hd, 4),
            blocking_score=round(blocking, 2),
        ))

    summaries.sort(key=lambda s: -s.blocking_score)
    return summaries


def _identify_at_risk_students(
    student_states: Dict[str, List[StudentConceptState]],
) -> List[StudentRisk]:
    """Identify students who need teacher attention."""
    at_risk = []

    for student_id, states in student_states.items():
        if not states:
            continue

        struggling = []
        total_acc = 0.0
        total_hd = 0.0

        for state in states:
            total_acc += state.recent_accuracy
            total_hd += state.hint_dependency
            if state.mastery_level in (MasteryLevel.UNBUILT, MasteryLevel.REVIEW_NEEDED):
                struggling.append(state.concept_id)
            elif state.mastery_level == MasteryLevel.DEVELOPING and state.recent_accuracy < 0.4:
                struggling.append(state.concept_id)

        n = len(states)
        avg_acc = total_acc / n if n > 0 else 0.0
        avg_hd = total_hd / n if n > 0 else 0.0

        if not struggling:
            continue

        # Assign risk level
        if len(struggling) >= 3 or avg_acc < 0.3:
            risk_level = "high"
            action = "建議面對面個別指導，釐清多個概念的迷思"
        elif len(struggling) >= 2 or avg_acc < 0.5:
            risk_level = "medium"
            action = "建議小組加強練習，聚焦弱點概念"
        else:
            risk_level = "low"
            action = "持續觀察，提供額外練習機會"

        at_risk.append(StudentRisk(
            student_id=student_id,
            display_name=student_id,  # caller can enrich with actual name
            struggling_concepts=struggling,
            overall_accuracy=round(avg_acc, 4),
            hint_dependency=round(avg_hd, 4),
            risk_level=risk_level,
            recommended_action=action,
        ))

    at_risk.sort(key=lambda s: ({"high": 0, "medium": 1, "low": 2}.get(s.risk_level, 3), s.overall_accuracy))
    return at_risk


def _summarize_error_patterns(
    error_counts: Dict[str, Dict[str, int]],
) -> List[Dict[str, Any]]:
    """Summarize common error patterns across concepts.

    Args:
        error_counts: {concept_id: {error_type_value: count}}
    """
    type_totals: Dict[str, int] = {}
    concept_examples: Dict[str, List[str]] = {}

    for concept_id, errors in error_counts.items():
        for error_type_val, count in errors.items():
            type_totals[error_type_val] = type_totals.get(error_type_val, 0) + count
            if error_type_val not in concept_examples:
                concept_examples[error_type_val] = []
            concept_examples[error_type_val].append(concept_id)

    patterns = []
    for error_type_val, total in sorted(type_totals.items(), key=lambda x: -x[1]):
        try:
            et = ErrorType(error_type_val)
            info = ERROR_DESCRIPTIONS.get(et, {})
            zh = info.get("zh", error_type_val)
            teacher_action = info.get("teacher_action_zh", "")
        except ValueError:
            zh = error_type_val
            teacher_action = ""

        patterns.append({
            "error_type": error_type_val,
            "display_name_zh": zh,
            "total_count": total,
            "affected_concepts": concept_examples.get(error_type_val, [])[:5],
            "teacher_action_zh": teacher_action,
        })

    return patterns[:10]  # top 10


def _generate_insights(report: TeacherReport) -> List[str]:
    """Generate Chinese-language insights for the teacher."""
    insights = []

    # 1. Overall class status
    n = report.student_count
    at_risk = report.students_needing_attention
    high_risk = [s for s in at_risk if s.risk_level == "high"]

    if high_risk:
        names = "、".join(s.student_id for s in high_risk[:3])
        suffix = f"等 {len(high_risk)} 位" if len(high_risk) > 3 else ""
        insights.append(f"⚠ 有 {len(high_risk)} 位高風險學生需要立即關注：{names}{suffix}")

    # 2. Top blocking concept
    if report.top_blocking_concepts:
        top = report.top_blocking_concepts[0]
        pct = round((top.student_count - top.mastered_count) / max(1, top.student_count) * 100)
        insights.append(
            f"最多學生卡住的概念：{top.display_name}（{pct}% 尚未掌握）"
        )

    # 3. Hint effectiveness warning
    for cid, data in report.hint_effectiveness.items():
        eff = data.get("overall_effectiveness", 1.0)
        if eff < 0.3:
            name = get_display_name(cid)
            insights.append(f"「{name}」的提示有效率偏低（{round(eff * 100)}%），建議調整教學方式")

    # 4. Common error type
    if report.common_error_patterns:
        top_err = report.common_error_patterns[0]
        insights.append(
            f"最常見的錯誤類型：{top_err['display_name_zh']}（{top_err['total_count']} 次）"
        )

    if not insights:
        insights.append("班級整體表現良好，持續觀察即可。")

    return insights


# ---------------------------------------------------------------------------
# Serialization helper
# ---------------------------------------------------------------------------

_RISK_LEVEL_ZH = {"high": "高風險", "medium": "中等風險", "low": "低風險"}


def _pct_str(val: float) -> str:
    """Format a 0-1 float as e.g. '85%'."""
    return f"{round(val * 100)}%"


def report_to_dict(report: TeacherReport) -> Dict[str, Any]:
    """Convert TeacherReport to a JSON-serializable dict."""
    return {
        "class_id": report.class_id,
        "generated_for": report.generated_for,
        "student_count": report.student_count,
        "active_student_count": report.active_student_count,
        "top_blocking_concepts": [
            {
                "concept_id": c.concept_id,
                "display_name": c.display_name,
                "student_count": c.student_count,
                "mastered_count": c.mastered_count,
                "developing_count": c.developing_count,
                "approaching_count": c.approaching_count,
                "unbuilt_count": c.unbuilt_count,
                "review_needed_count": c.review_needed_count,
                "avg_accuracy": c.avg_accuracy,
                "avg_accuracy_pct": _pct_str(c.avg_accuracy),
                "blocking_score": c.blocking_score,
            }
            for c in report.top_blocking_concepts
        ],
        "students_needing_attention": [
            {
                "student_id": s.student_id,
                "display_name": s.display_name,
                "struggling_concepts": [
                    {"concept_id": cid, "display_name": get_display_name(cid)}
                    for cid in s.struggling_concepts
                ],
                "overall_accuracy": s.overall_accuracy,
                "overall_accuracy_pct": _pct_str(s.overall_accuracy),
                "hint_dependency": s.hint_dependency,
                "hint_dependency_pct": _pct_str(s.hint_dependency),
                "risk_level": s.risk_level,
                "risk_level_zh": _RISK_LEVEL_ZH.get(s.risk_level, s.risk_level),
                "recommended_action": s.recommended_action,
            }
            for s in report.students_needing_attention
        ],
        "concept_distribution": [
            {
                "concept_id": c.concept_id,
                "display_name": c.display_name,
                "mastered_count": c.mastered_count,
                "developing_count": c.developing_count,
                "approaching_count": c.approaching_count,
                "unbuilt_count": c.unbuilt_count,
                "review_needed_count": c.review_needed_count,
                "avg_accuracy": c.avg_accuracy,
                "avg_accuracy_pct": _pct_str(c.avg_accuracy),
            }
            for c in report.concept_distribution
        ],
        "hint_effectiveness": report.hint_effectiveness,
        "common_error_patterns": report.common_error_patterns,
        "insights": report.insights,
    }


# ---------------------------------------------------------------------------
# Hint effectiveness teacher summary (EXP-A3)
# ---------------------------------------------------------------------------

def format_hint_summary_for_teacher(stats: Dict[str, Any]) -> Dict[str, Any]:
    """Transform raw hint effectiveness stats into a teacher-readable summary.

    Takes the output of get_hint_effectiveness_stats() and produces a structured
    summary with Chinese labels, actionable recommendations, and risk flags.

    Returns a dict with:
      - overview: overall stats in teacher-readable format
      - by_concept: per-concept breakdown with display names and recommendations
      - by_level: hint level distribution with labels
      - recommendations: list of Chinese-language action items
      - risk_flags: list of concerns requiring attention
    """
    total = stats.get("total_hinted_attempts", 0)
    success_rate = stats.get("hint_success_rate", 0.0)
    stuck_rate = stats.get("stuck_after_hint_rate", 0.0)

    # --- Overview ---
    overview = {
        "total_hinted_attempts": total,
        "hint_success_rate": round(success_rate, 4),
        "hint_success_rate_pct": f"{round(success_rate * 100)}%",
        "stuck_after_hint_rate": round(stuck_rate, 4),
        "stuck_after_hint_rate_pct": f"{round(stuck_rate * 100)}%",
        "correct_with_hint": stats.get("correct_with_hint", 0),
        "stuck_after_hint": stats.get("stuck_after_hint", 0),
    }

    # --- By-concept breakdown ---
    by_concept_raw = stats.get("by_concept", {})
    by_concept = []
    weak_concepts = []
    for cid, cdata in by_concept_raw.items():
        c_total = cdata.get("total", 0)
        c_correct = cdata.get("correct", 0)
        c_rate = c_correct / c_total if c_total > 0 else 0.0
        display = get_display_name(cid)
        entry = {
            "concept_id": cid,
            "display_name": display,
            "hinted_attempts": c_total,
            "correct_with_hint": c_correct,
            "success_rate": round(c_rate, 4),
            "success_rate_pct": f"{round(c_rate * 100)}%",
        }
        by_concept.append(entry)
        if c_rate < 0.4 and c_total >= 3:
            weak_concepts.append(entry)
    by_concept.sort(key=lambda x: x["success_rate"])

    # --- By-level breakdown ---
    by_level_raw = stats.get("by_level", {})
    by_level = []
    for level_str, ldata in sorted(by_level_raw.items(), key=lambda x: x[0]):
        l_total = ldata.get("total", 0)
        l_correct = ldata.get("correct", 0)
        l_rate = l_correct / l_total if l_total > 0 else 0.0
        by_level.append({
            "hint_count": level_str,
            "label": f"看了 {level_str} 個提示",
            "attempts": l_total,
            "correct": l_correct,
            "success_rate": round(l_rate, 4),
            "success_rate_pct": f"{round(l_rate * 100)}%",
        })

    # --- Recommendations ---
    recommendations = []
    risk_flags = []

    if total == 0:
        recommendations.append("目前沒有使用提示的記錄，無法評估提示效果。")
    else:
        if success_rate >= 0.7:
            recommendations.append(f"提示整體有效率 {round(success_rate * 100)}%，學生使用提示後多數能答對。")
        elif success_rate >= 0.4:
            recommendations.append(f"提示有效率 {round(success_rate * 100)}%，部分學生看了提示仍答錯，建議檢視提示內容是否足夠清楚。")
        else:
            risk_flags.append(f"⚠ 提示有效率偏低（{round(success_rate * 100)}%），大部分學生看了提示仍答錯。")
            recommendations.append("建議重新設計提示內容，或改為面對面教學指導。")

        if stuck_rate > 0.5:
            risk_flags.append(f"⚠ {round(stuck_rate * 100)}% 的學生看了提示後仍然答錯，可能需要更基礎的概念引導。")

        for wc in weak_concepts[:3]:
            risk_flags.append(
                f"「{wc['display_name']}」提示效果差（{wc['success_rate_pct']}），"
                f"共 {wc['hinted_attempts']} 次使用提示後仍答錯比例高。"
            )

        # Multi-hint escalation
        high_level = [l for l in by_level if int(l["hint_count"]) >= 3]
        if high_level:
            total_high = sum(l["attempts"] for l in high_level)
            if total_high >= 5:
                recommendations.append(
                    f"有 {total_high} 次作答需要看 3 個以上提示，建議確認這些學生是否缺乏先備知識。"
                )

    if not recommendations:
        recommendations.append("持續觀察提示使用情況。")

    return {
        "overview": overview,
        "by_concept": by_concept,
        "by_level": by_level,
        "recommendations": recommendations,
        "risk_flags": risk_flags,
    }


# ---------------------------------------------------------------------------
# Mastery distribution summary (EXP-B3)
# ---------------------------------------------------------------------------

def format_mastery_distribution(
    class_states: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Summarise class-wide mastery level & score distribution.

    Takes the output of ``get_class_states()``
    (``{student_id: {concept_id: StudentConceptState}}``) and returns a dict
    with level counts, percentages, average score, and a score histogram.
    """
    from .concept_state import MasteryLevel  # avoid circular at module level

    _LEVEL_ZH = {
        "unbuilt": "未建立",
        "developing": "發展中",
        "approaching_mastery": "趨近精熟",
        "mastered": "已精熟",
        "review_needed": "需複習",
    }

    level_counts: Dict[str, int] = {lv.value: 0 for lv in MasteryLevel}
    scores: List[float] = []

    for sid, cid_map in class_states.items():
        for cid, state in cid_map.items():
            lv = state.mastery_level if hasattr(state, "mastery_level") else "unbuilt"
            lv_val = lv.value if hasattr(lv, "value") else str(lv)
            level_counts[lv_val] = level_counts.get(lv_val, 0) + 1
            sc = state.mastery_score if hasattr(state, "mastery_score") else 0.0
            scores.append(float(sc))

    total = len(scores)
    avg_score = round(sum(scores) / total, 4) if total else 0.0

    level_pct = {}
    for k, v in level_counts.items():
        level_pct[k] = round(v / total, 4) if total else 0.0

    # Score histogram: 5 buckets
    buckets = [(0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)]
    labels = ["0-20%", "20-40%", "40-60%", "60-80%", "80-100%"]
    histogram = []
    for (lo, hi), label in zip(buckets, labels):
        cnt = sum(1 for s in scores if lo <= s < hi)
        histogram.append({"range": label, "count": cnt})

    return {
        "total_students": len(class_states),
        "total_concept_entries": total,
        "level_counts": level_counts,
        "level_labels_zh": {k: _LEVEL_ZH.get(k, k) for k in level_counts},
        "level_percentages": level_pct,
        "level_percentages_pct": {k: _pct_str(v) for k, v in level_pct.items()},
        "avg_mastery_score": avg_score,
        "avg_mastery_score_pct": _pct_str(avg_score),
        "score_histogram": histogram,
    }


# ---------------------------------------------------------------------------
# One-page teacher summary (EXP-C2)
# ---------------------------------------------------------------------------

def format_one_page_summary(report_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Produce a compact one-page summary from a full report dict.

    Designed so a teacher can grasp the class status in 30 seconds.
    Returns Chinese-language fields only.
    """
    n_students = report_dict.get("student_count", 0)
    active = report_dict.get("active_student_count", 0)

    # --- Attention students ---
    attn = report_dict.get("students_needing_attention", [])
    high = [s for s in attn if s.get("risk_level") == "high"]
    medium = [s for s in attn if s.get("risk_level") == "medium"]

    attention_line = f"需關注學生：高風險 {len(high)} 位、中等風險 {len(medium)} 位"

    # --- Top blocking concept ---
    blocking = report_dict.get("top_blocking_concepts", [])
    if blocking:
        top = blocking[0]
        blocking_line = f"最大阻塞概念：{top['display_name']}（{top.get('avg_accuracy_pct', 'N/A')} 正確率）"
    else:
        blocking_line = "最大阻塞概念：無"

    # --- Mastery overview ---
    md = report_dict.get("mastery_distribution", {})
    mastery_line = f"全班平均精熟度：{md.get('avg_mastery_score_pct', 'N/A')}"
    lc = md.get("level_counts", {})
    lz = md.get("level_labels_zh", {})
    level_lines = [f"  {lz.get(k, k)}：{v} 筆" for k, v in lc.items() if v > 0]

    # --- Hint overview ---
    hs = report_dict.get("hint_summary", {})
    overview = hs.get("overview", {})
    if overview:
        hint_line = f"提示成功率：{overview.get('hint_success_rate_pct', 'N/A')}（共 {overview.get('total_hinted_attempts', 0)} 次使用提示）"
    else:
        hint_line = "提示成功率：尚無資料"

    # --- Insights (first 3) ---
    insights = report_dict.get("insights", [])[:3]

    # --- Actionable next steps ---
    actions = []
    if high:
        names = "、".join(s.get("display_name", s.get("student_id", "?")) for s in high[:3])
        actions.append(f"優先約談：{names}")
    if blocking:
        actions.append(f"重點複習：{blocking[0]['display_name']}")
    risk_flags = hs.get("risk_flags", [])
    if risk_flags:
        actions.append(risk_flags[0])
    if not actions:
        actions.append("班級狀態良好，持續觀察即可。")

    return {
        "title": "班級學習狀態摘要",
        "class_id": report_dict.get("class_id", ""),
        "student_overview": f"學生人數：{n_students}（活躍 {active} 位）",
        "attention_summary": attention_line,
        "blocking_summary": blocking_line,
        "mastery_summary": mastery_line,
        "mastery_levels": level_lines,
        "hint_summary_line": hint_line,
        "key_insights": insights,
        "recommended_actions": actions,
    }
