"""R19/EXP-C3: Tests for enrich_blocking_concepts (decision support)."""
from learning.teacher_report import enrich_blocking_concepts, report_to_dict, TeacherReport, ConceptClassSummary, StudentRisk


def _bc(mastered=3, developing=2, approaching=2, unbuilt=1, review=0, acc=0.65, n=None):
    """Build a blocking concept dict."""
    if n is None:
        n = mastered + developing + approaching + unbuilt + review
    return {
        "concept_id": "add_sub", "display_name": "加減法",
        "student_count": n, "mastered_count": mastered,
        "developing_count": developing, "approaching_count": approaching,
        "unbuilt_count": unbuilt, "review_needed_count": review,
        "avg_accuracy": acc, "avg_accuracy_pct": f"{round(acc*100)}%",
        "blocking_score": 4.5,
    }


def test_enriched_has_required_keys():
    result = enrich_blocking_concepts([_bc()])
    assert len(result) == 1
    bc = result[0]
    assert "severity_zh" in bc
    assert "pattern_zh" in bc
    assert "recommended_actions_zh" in bc


def test_severe_when_mostly_unbuilt():
    bc = _bc(mastered=1, developing=1, approaching=0, unbuilt=8, review=0, acc=0.2)
    result = enrich_blocking_concepts([bc])[0]
    assert result["severity_zh"] == "嚴重"
    assert "未建立" in result["pattern_zh"]


def test_moderate_severity():
    bc = _bc(mastered=4, developing=3, approaching=2, unbuilt=1, review=0, acc=0.6)
    result = enrich_blocking_concepts([bc])[0]
    assert result["severity_zh"] == "中等"


def test_mild_severity():
    bc = _bc(mastered=7, developing=1, approaching=1, unbuilt=0, review=0, acc=0.85)
    result = enrich_blocking_concepts([bc])[0]
    assert result["severity_zh"] == "輕微"


def test_review_needed_pattern():
    bc = _bc(mastered=2, developing=1, approaching=0, unbuilt=0, review=4, acc=0.5)
    result = enrich_blocking_concepts([bc])[0]
    assert "複習" in result["pattern_zh"]


def test_developing_heavy_pattern():
    bc = _bc(mastered=1, developing=6, approaching=1, unbuilt=1, review=0, acc=0.45)
    result = enrich_blocking_concepts([bc])[0]
    assert "發展" in result["pattern_zh"]


def test_low_accuracy_recommendation():
    bc = _bc(mastered=2, developing=3, approaching=2, unbuilt=2, review=0, acc=0.35)
    result = enrich_blocking_concepts([bc])[0]
    actions = result["recommended_actions_zh"]
    assert any("正確率" in a for a in actions)


def test_unbuilt_recommendation():
    bc = _bc(mastered=5, developing=1, approaching=0, unbuilt=3, review=0, acc=0.6)
    result = enrich_blocking_concepts([bc])[0]
    actions = result["recommended_actions_zh"]
    assert any("未建立" in a for a in actions)


def test_report_to_dict_includes_enrichment():
    concept = ConceptClassSummary(
        concept_id="add_sub", display_name="加減法",
        student_count=10, mastered_count=2, developing_count=4,
        approaching_count=2, unbuilt_count=2, review_needed_count=0,
        avg_accuracy=0.45, avg_hint_dependency=0.3, blocking_score=6.0,
    )
    report = TeacherReport(
        class_id="c1", generated_for="teacher1",
        student_count=10, active_student_count=8,
        top_blocking_concepts=[concept],
    )
    d = report_to_dict(report)
    bc = d["top_blocking_concepts"][0]
    assert "severity_zh" in bc
    assert "pattern_zh" in bc
    assert "recommended_actions_zh" in bc


def test_empty_list():
    assert enrich_blocking_concepts([]) == []


def test_multiple_concepts():
    result = enrich_blocking_concepts([
        _bc(mastered=1, unbuilt=8, developing=1, acc=0.2),
        _bc(mastered=7, unbuilt=0, developing=1, approaching=1, acc=0.85),
    ])
    assert len(result) == 2
    assert result[0]["severity_zh"] == "嚴重"
    assert result[1]["severity_zh"] == "輕微"
