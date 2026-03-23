"""R17/EXP-C1: Teacher report field audit tests.

Validates Chinese labels, _pct companions, and structured struggling_concepts.
"""
import types
from learning.teacher_report import report_to_dict, format_mastery_distribution, TeacherReport, ConceptClassSummary, StudentRisk


def _make_report():
    """Minimal TeacherReport with one blocking concept, one at-risk student."""
    concept = ConceptClassSummary(
        concept_id="add_sub", display_name="加減法",
        student_count=10, mastered_count=3, developing_count=4,
        approaching_count=2, unbuilt_count=1, review_needed_count=0,
        avg_accuracy=0.65, avg_hint_dependency=0.3, blocking_score=4.5,
    )
    student = StudentRisk(
        student_id="s1", display_name="小明",
        struggling_concepts=["add_sub", "mult_div"],
        overall_accuracy=0.42, hint_dependency=0.55,
        risk_level="high", recommended_action="建議面對面個別指導",
    )
    return TeacherReport(
        class_id="c1", generated_for="teacher1",
        student_count=10, active_student_count=8,
        top_blocking_concepts=[concept],
        students_needing_attention=[student],
        concept_distribution=[concept],
        hint_effectiveness={}, common_error_patterns=[], insights=["測試"],
    )


def test_blocking_concept_has_accuracy_pct():
    d = report_to_dict(_make_report())
    bc = d["top_blocking_concepts"][0]
    assert bc["avg_accuracy_pct"] == "65%"


def test_concept_distribution_has_accuracy_pct():
    d = report_to_dict(_make_report())
    cd = d["concept_distribution"][0]
    assert cd["avg_accuracy_pct"] == "65%"


def test_student_risk_level_zh():
    d = report_to_dict(_make_report())
    s = d["students_needing_attention"][0]
    assert s["risk_level_zh"] == "高風險"


def test_student_accuracy_pct():
    d = report_to_dict(_make_report())
    s = d["students_needing_attention"][0]
    assert s["overall_accuracy_pct"] == "42%"
    assert s["hint_dependency_pct"] == "55%"


def test_struggling_concepts_structured():
    d = report_to_dict(_make_report())
    sc = d["students_needing_attention"][0]["struggling_concepts"]
    assert isinstance(sc, list)
    assert isinstance(sc[0], dict)
    assert "concept_id" in sc[0]
    assert "display_name" in sc[0]
    assert sc[0]["concept_id"] == "add_sub"


def test_mastery_distribution_level_labels_zh():
    states = {"s1": {"c1": types.SimpleNamespace(mastery_level=types.SimpleNamespace(value="mastered"), mastery_score=0.9)}}
    dist = format_mastery_distribution(states)
    assert "level_labels_zh" in dist
    assert dist["level_labels_zh"]["mastered"] == "已精熟"
    assert dist["level_labels_zh"]["developing"] == "發展中"
    assert dist["level_labels_zh"]["unbuilt"] == "未建立"


def test_mastery_distribution_pct_companions():
    states = {"s1": {"c1": types.SimpleNamespace(mastery_level=types.SimpleNamespace(value="mastered"), mastery_score=0.85)}}
    dist = format_mastery_distribution(states)
    assert dist["avg_mastery_score_pct"] == "85%"
    assert "level_percentages_pct" in dist
    assert dist["level_percentages_pct"]["mastered"] == "100%"


def test_risk_level_zh_all_levels():
    report = _make_report()
    report.students_needing_attention[0].risk_level = "medium"
    d = report_to_dict(report)
    assert d["students_needing_attention"][0]["risk_level_zh"] == "中等風險"

    report.students_needing_attention[0].risk_level = "low"
    d = report_to_dict(report)
    assert d["students_needing_attention"][0]["risk_level_zh"] == "低風險"
