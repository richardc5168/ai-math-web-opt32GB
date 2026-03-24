"""R18/EXP-C2: Tests for format_one_page_summary (one-page teacher summary)."""
from learning.teacher_report import (
    format_one_page_summary, report_to_dict, format_mastery_distribution,
    TeacherReport, ConceptClassSummary, StudentRisk,
)
import types


def _full_report_dict():
    """Build a complete report dict as the endpoint would produce."""
    concept = ConceptClassSummary(
        concept_id="add_sub", display_name="加減法",
        student_count=10, mastered_count=3, developing_count=4,
        approaching_count=2, unbuilt_count=1, review_needed_count=0,
        avg_accuracy=0.65, avg_hint_dependency=0.3, blocking_score=4.5,
    )
    high_risk = StudentRisk(
        student_id="s1", display_name="小明",
        struggling_concepts=["add_sub"], overall_accuracy=0.28,
        hint_dependency=0.6, risk_level="high",
        recommended_action="建議面對面個別指導",
    )
    medium_risk = StudentRisk(
        student_id="s2", display_name="小華",
        struggling_concepts=["add_sub"], overall_accuracy=0.45,
        hint_dependency=0.4, risk_level="medium",
        recommended_action="建議小組加強練習",
    )
    report = TeacherReport(
        class_id="c1", generated_for="teacher1",
        student_count=10, active_student_count=8,
        top_blocking_concepts=[concept],
        students_needing_attention=[high_risk, medium_risk],
        concept_distribution=[concept],
        hint_effectiveness={}, common_error_patterns=[],
        insights=["⚠ 有 1 位高風險學生", "最多學生卡住的概念：加減法"],
    )
    d = report_to_dict(report)
    # Add mastery_distribution
    states = {"s1": {"add_sub": types.SimpleNamespace(
        mastery_level=types.SimpleNamespace(value="developing"), mastery_score=0.35)}}
    d["mastery_distribution"] = format_mastery_distribution(states)
    # Add hint_summary stub
    d["hint_summary"] = {
        "overview": {
            "hint_success_rate_pct": "72%",
            "total_hinted_attempts": 50,
            "evidence_chain_complete_rate_pct": "64%",
            "hint_escalation_rate_pct": "42%",
            "avg_hints_before_success": 2.1,
        },
        "risk_flags": ["⚠ 加減法提示效果偏低"],
        "recommendations": ["目前提示 evidence chain 完整率為 64%，建議持續補齊 telemetry。"],
    }
    return d


def test_summary_has_required_keys():
    s = format_one_page_summary(_full_report_dict())
    for key in ("title", "class_id", "student_overview", "attention_summary",
                "blocking_summary", "mastery_summary", "mastery_levels",
                "hint_summary_line", "hint_decision_block", "key_insights", "recommended_actions"):
        assert key in s, f"Missing key: {key}"


def test_title_chinese():
    s = format_one_page_summary(_full_report_dict())
    assert s["title"] == "班級學習狀態摘要"


def test_student_overview():
    s = format_one_page_summary(_full_report_dict())
    assert "10" in s["student_overview"]
    assert "8" in s["student_overview"]


def test_attention_counts():
    s = format_one_page_summary(_full_report_dict())
    assert "高風險 1 位" in s["attention_summary"]
    assert "中等風險 1 位" in s["attention_summary"]


def test_blocking_concept():
    s = format_one_page_summary(_full_report_dict())
    assert "加減法" in s["blocking_summary"]
    assert "65%" in s["blocking_summary"]


def test_mastery_summary():
    s = format_one_page_summary(_full_report_dict())
    assert "35%" in s["mastery_summary"]


def test_hint_line():
    s = format_one_page_summary(_full_report_dict())
    assert "72%" in s["hint_summary_line"]
    assert "50" in s["hint_summary_line"]


def test_hint_decision_block():
    s = format_one_page_summary(_full_report_dict())
    block = s["hint_decision_block"]
    assert any("evidence 完整率：64%" in line for line in block)
    assert any("平均看 2.1 個提示後才成功" in line for line in block)
    assert any("高階提示升級率：42%" in line for line in block)
    assert any("決策提醒：⚠ 加減法提示效果偏低" in line for line in block)


def test_insights_limited():
    s = format_one_page_summary(_full_report_dict())
    assert len(s["key_insights"]) <= 3


def test_recommended_actions():
    s = format_one_page_summary(_full_report_dict())
    actions = s["recommended_actions"]
    assert any("小明" in a for a in actions)
    assert any("加減法" in a for a in actions)


def test_empty_report():
    d = report_to_dict(TeacherReport(class_id="c0", generated_for="t0"))
    s = format_one_page_summary(d)
    assert s["title"] == "班級學習狀態摘要"
    assert "0" in s["student_overview"]
    assert "無" in s["blocking_summary"]
    assert s["hint_decision_block"] == ["提示證據鏈：尚無資料"]
    assert len(s["recommended_actions"]) >= 1


# ── R52: one-page summary enhancements ──────────────────────────────────


def test_r52_has_severity():
    s = format_one_page_summary(_full_report_dict())
    assert "severity" in s
    assert s["severity"] in ("良好", "需要關注", "需要立即介入")


def test_r52_has_struggling_items_key():
    s = format_one_page_summary(_full_report_dict())
    assert "struggling_items" in s
    assert isinstance(s["struggling_items"], list)


def test_r52_struggling_items_populated():
    d = _full_report_dict()
    d["hint_summary"]["by_question"] = {
        "q1": {"total": 5, "correct": 1, "rate": 0.2},
        "q2": {"total": 3, "correct": 3, "rate": 1.0},
    }
    s = format_one_page_summary(d)
    assert len(s["struggling_items"]) >= 1
    assert "q1" in s["struggling_items"][0]
    assert "20%" in s["struggling_items"][0]


def test_r52_has_hint_dependency_concepts():
    s = format_one_page_summary(_full_report_dict())
    assert "hint_dependency_concepts" in s
    assert isinstance(s["hint_dependency_concepts"], list)


def test_r52_hint_dependency_high_flagged():
    d = _full_report_dict()
    d["concept_distribution"] = [
        {"concept_id": "c1", "display_name": "分數加法",
         "avg_hint_dependency": 0.8, "blocking_score": 50},
    ]
    s = format_one_page_summary(d)
    assert len(s["hint_dependency_concepts"]) >= 1
    assert "分數加法" in s["hint_dependency_concepts"][0]
    assert "80%" in s["hint_dependency_concepts"][0]


def test_r52_has_error_summary():
    s = format_one_page_summary(_full_report_dict())
    assert "error_summary" in s
    assert isinstance(s["error_summary"], list)


def test_r52_error_summary_populated():
    d = _full_report_dict()
    d["common_error_patterns"] = [
        {"error_type": "calculation", "count": 15, "concept_id": "c1",
         "concept_display_name": "分數加法"},
    ]
    s = format_one_page_summary(d)
    assert len(s["error_summary"]) >= 1
    assert "calculation" in s["error_summary"][0]
    assert "15" in s["error_summary"][0]


def test_r52_severity_high_risk():
    d = _full_report_dict()
    # Add 3+ high risk students
    from learning.teacher_report import StudentRisk
    d["students_needing_attention"] = [
        {"student_id": f"s{i}", "display_name": f"學生{i}",
         "risk_level": "high", "recommended_action": "介入"}
        for i in range(4)
    ]
    s = format_one_page_summary(d)
    assert s["severity"] == "需要立即介入"


def test_r52_severity_good():
    d = _full_report_dict()
    d["students_needing_attention"] = []
    d["top_blocking_concepts"] = []
    s = format_one_page_summary(d)
    assert s["severity"] == "良好"
