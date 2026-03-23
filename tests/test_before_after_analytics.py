"""Tests for EXP-P3-01: before_after_analytics module.

Validates compare_pre_post(), build_parent_summary(), and build_teacher_summary()
for correctness across various scenarios.
"""

from __future__ import annotations

import pytest

from learning.before_after_analytics import (
    compare_pre_post,
    build_parent_summary,
    build_teacher_summary,
)


# ---- Fixture data ----

def _meta(qid, group, skill="fraction", kp="frac_add"):
    return {
        "question_id": qid,
        "equivalent_group_id": group,
        "skill_tag": skill,
        "knowledge_point": kp,
    }


def _record(qid, correct=True):
    return {"question_id": qid, "correctness": correct}


METADATA = [
    _meta("q1", "g1", "fraction", "frac_add"),
    _meta("q2", "g1", "fraction", "frac_add"),
    _meta("q3", "g2", "decimal", "dec_mul"),
    _meta("q4", "g2", "decimal", "dec_mul"),
    _meta("q5", "g3", "percent", "pct_basic"),
]


class TestComparePrePost:
    """EXP-P3-01: Pre/post comparison tests."""

    def test_improved_label(self):
        """Substantial accuracy gain → 'improved'."""
        pre = [_record("q1", False), _record("q3", False)]
        post = [_record("q2", True), _record("q4", True)]
        result = compare_pre_post(
            question_metadata=METADATA, pre_records=pre, post_records=post
        )
        assert result["label"] == "improved"
        assert result["compared_group_count"] == 2

    def test_regressed_label(self):
        """Substantial accuracy drop → 'regressed'."""
        pre = [_record("q1", True), _record("q3", True)]
        post = [_record("q2", False), _record("q4", False)]
        result = compare_pre_post(
            question_metadata=METADATA, pre_records=pre, post_records=post
        )
        assert result["label"] == "regressed"

    def test_flat_label(self):
        """No significant change → 'flat'."""
        pre = [_record("q1", True), _record("q3", False)]
        post = [_record("q2", True), _record("q4", False)]
        result = compare_pre_post(
            question_metadata=METADATA, pre_records=pre, post_records=post
        )
        assert result["label"] == "flat"

    def test_insufficient_evidence(self):
        """Too few matched groups → 'insufficient_evidence'."""
        pre = [_record("q1", True)]
        post = [_record("q2", True)]
        result = compare_pre_post(
            question_metadata=METADATA, pre_records=pre, post_records=post, min_groups=2
        )
        assert result["label"] == "insufficient_evidence"
        assert len(result["uncertainty"]) > 0

    def test_empty_records(self):
        """No records → insufficient."""
        result = compare_pre_post(
            question_metadata=METADATA, pre_records=[], post_records=[]
        )
        assert result["label"] == "insufficient_evidence"
        assert result["compared_group_count"] == 0

    def test_groups_contain_detail(self):
        """Each group entry should have pre/post accuracy and delta."""
        pre = [_record("q1", True), _record("q3", False)]
        post = [_record("q2", False), _record("q4", True)]
        result = compare_pre_post(
            question_metadata=METADATA, pre_records=pre, post_records=post
        )
        for g in result["groups"]:
            assert "pre_accuracy" in g
            assert "post_accuracy" in g
            assert "delta" in g
            assert "equivalent_group_id" in g
            assert "skill_tag" in g

    def test_delta_calculation(self):
        """Delta = post_accuracy - pre_accuracy."""
        pre = [_record("q1", False)]  # acc = 0.0
        post = [_record("q2", True)]  # acc = 1.0
        result = compare_pre_post(
            question_metadata=METADATA, pre_records=pre, post_records=post, min_groups=1
        )
        g1 = [g for g in result["groups"] if g["equivalent_group_id"] == "g1"][0]
        assert g1["delta"] == 1.0

    def test_unknown_question_ids_ignored(self):
        """Records with question_ids not in metadata are skipped."""
        pre = [_record("unknown_q", True)]
        post = [_record("also_unknown", False)]
        result = compare_pre_post(
            question_metadata=METADATA, pre_records=pre, post_records=post
        )
        assert result["compared_group_count"] == 0

    def test_min_groups_threshold(self):
        """Custom min_groups threshold works."""
        pre = [_record("q1", True)]
        post = [_record("q2", True)]
        # min_groups=1 → should have evidence
        result = compare_pre_post(
            question_metadata=METADATA, pre_records=pre, post_records=post, min_groups=1
        )
        assert result["label"] != "insufficient_evidence"


class TestBuildParentSummary:
    """EXP-P3-01: Parent summary text tests."""

    def test_improved_message(self):
        msg = build_parent_summary("小明", {"label": "improved"})
        assert "小明" in msg
        assert "improvement" in msg

    def test_regressed_message(self):
        msg = build_parent_summary("小明", {"label": "regressed"})
        assert "小明" in msg
        assert "support" in msg

    def test_flat_message(self):
        msg = build_parent_summary("小明", {"label": "flat"})
        assert "小明" in msg

    def test_insufficient_message(self):
        msg = build_parent_summary("小明", {"label": "insufficient_evidence"})
        assert "小明" in msg
        assert "not enough" in msg.lower() or "evidence" in msg.lower()


class TestBuildTeacherSummary:
    """EXP-P3-01: Teacher class-level summary tests."""

    def test_counts_labels(self):
        reports = [
            {"student_id": "s1", "label": "improved"},
            {"student_id": "s2", "label": "improved"},
            {"student_id": "s3", "label": "regressed"},
            {"student_id": "s4", "label": "flat"},
        ]
        result = build_teacher_summary("五年甲班", reports)
        assert result["class_name"] == "五年甲班"
        assert result["status_counts"]["improved"] == 2
        assert result["status_counts"]["regressed"] == 1
        assert result["status_counts"]["flat"] == 1

    def test_high_risk_includes_regressed(self):
        reports = [
            {"student_id": "s1", "label": "regressed"},
            {"student_id": "s2", "label": "insufficient_evidence"},
        ]
        result = build_teacher_summary("class1", reports)
        assert "s1" in result["high_risk_students"]
        assert "s2" in result["high_risk_students"]

    def test_no_high_risk_when_all_ok(self):
        reports = [
            {"student_id": "s1", "label": "improved"},
            {"student_id": "s2", "label": "flat"},
        ]
        result = build_teacher_summary("class1", reports)
        assert result["high_risk_students"] == []

    def test_empty_reports(self):
        result = build_teacher_summary("class1", [])
        assert result["status_counts"]["improved"] == 0
        assert result["high_risk_students"] == []
