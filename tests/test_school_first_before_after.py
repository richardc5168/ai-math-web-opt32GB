from fixtures.school_first_seed import build_school_first_fixture
from learning.before_after_analytics import build_parent_summary, build_teacher_summary, compare_pre_post


def test_before_after_fixture_has_expected_scale():
    fixture = build_school_first_fixture()
    assert len(fixture["teachers"]) == 2
    assert len(fixture["students"]) == 116
    assert len(fixture["parents"]) == 116
    assert len(fixture["interventions"]) == 2


def test_compare_pre_post_uses_equivalent_groups():
    fixture = build_school_first_fixture()
    student_id = fixture["students"][0]["student_id"]
    pre = [r for r in fixture["answer_records"] if r["student_id"] == student_id and r["assessment_id"].startswith("pre-")]
    post = [r for r in fixture["answer_records"] if r["student_id"] == student_id and r["assessment_id"].startswith("post-")]
    result = compare_pre_post(
        question_metadata=fixture["question_metadata"],
        pre_records=pre,
        post_records=post,
    )
    assert result["compared_group_count"] >= 2
    assert result["label"] in {"improved", "flat", "regressed", "insufficient_evidence"}
    assert all("equivalent_group_id" in row for row in result["groups"])


def test_teacher_summary_flags_high_risk_students():
    reports = [
        {"student_id": "s1", "label": "improved"},
        {"student_id": "s2", "label": "regressed"},
        {"student_id": "s3", "label": "insufficient_evidence"},
    ]
    summary = build_teacher_summary("Class 5A", reports)
    assert summary["status_counts"]["improved"] == 1
    assert summary["status_counts"]["regressed"] == 1
    assert set(summary["high_risk_students"]) == {"s2", "s3"}


def test_parent_summary_is_human_readable():
    text = build_parent_summary("Student 001", {"label": "improved"})
    assert "Student 001" in text
    assert "improvement" in text.lower()