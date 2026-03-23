"""R32/EXP-P3-07: Tests for class_report v2 unified with learning DB."""

from __future__ import annotations

import os
import tempfile

import pytest

from learning.class_report import generate_class_report_v2
from learning.concept_state import upsert_concept_state, MasteryLevel, StudentConceptState
from learning.db import connect, ensure_learning_schema
from learning.service import recordAttempt


@pytest.fixture
def tmp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


def _make_event(student_id="s1", **overrides):
    base = {
        "student_id": student_id,
        "question_id": "q1",
        "timestamp": "2026-03-23T12:00:00+08:00",
        "is_correct": True,
        "answer_raw": "42",
        "skill_tags": ["fraction"],
    }
    base.update(overrides)
    return base


def _seed_data(db_path, student_ids=("s1", "s2")):
    """Seed a few attempts for multiple students."""
    for sid in student_ids:
        recordAttempt(_make_event(student_id=sid, is_correct=True), db_path=db_path)
        recordAttempt(_make_event(student_id=sid, is_correct=False, question_id="q2"), db_path=db_path)


class TestClassReportV2Structure:
    """Verify generate_class_report_v2 returns expected structure."""

    def test_empty_student_list(self, tmp_db):
        conn = connect(tmp_db)
        ensure_learning_schema(conn)
        result = generate_class_report_v2(conn, student_ids=[])
        assert result["summary"]["student_count"] == 0
        assert result["students"] == []
        assert result["concept_overview"] == []
        conn.close()

    def test_has_required_keys(self, tmp_db):
        _seed_data(tmp_db)
        conn = connect(tmp_db)
        result = generate_class_report_v2(conn, student_ids=["s1", "s2"])
        for key in ("class_name", "summary", "students", "high_risk_students", "concept_overview", "weakness_top"):
            assert key in result, f"Missing key: {key}"
        conn.close()

    def test_summary_fields(self, tmp_db):
        _seed_data(tmp_db)
        conn = connect(tmp_db)
        result = generate_class_report_v2(conn, student_ids=["s1", "s2"])
        s = result["summary"]
        assert s["student_count"] == 2
        assert s["active_students"] == 2
        assert s["total_attempts"] == 4  # 2 per student
        assert s["total_correct"] == 2  # 1 correct per student
        assert s["average_accuracy"] == 50.0
        conn.close()

    def test_class_name_passthrough(self, tmp_db):
        conn = connect(tmp_db)
        ensure_learning_schema(conn)
        result = generate_class_report_v2(conn, student_ids=[], class_name="5A")
        assert result["class_name"] == "5A"
        conn.close()


class TestClassReportV2Students:
    """Verify per-student data in v2 report."""

    def test_student_attempts_correct(self, tmp_db):
        _seed_data(tmp_db, student_ids=("s1",))
        conn = connect(tmp_db)
        result = generate_class_report_v2(conn, student_ids=["s1"])
        assert len(result["students"]) == 1
        st = result["students"][0]
        assert st["student_id"] == "s1"
        assert st["attempts"] == 2
        assert st["correct"] == 1
        assert st["accuracy"] == 50.0
        conn.close()

    def test_student_has_mastery_distribution(self, tmp_db):
        _seed_data(tmp_db, student_ids=("s1",))
        conn = connect(tmp_db)
        result = generate_class_report_v2(conn, student_ids=["s1"])
        st = result["students"][0]
        assert "mastery_distribution" in st
        assert isinstance(st["mastery_distribution"], dict)
        conn.close()

    def test_risk_score_present(self, tmp_db):
        _seed_data(tmp_db, student_ids=("s1",))
        conn = connect(tmp_db)
        result = generate_class_report_v2(conn, student_ids=["s1"])
        st = result["students"][0]
        assert "risk_score" in st
        assert 0 <= st["risk_score"] <= 100
        assert "recommended_action" in st
        conn.close()

    def test_inactive_student_included(self, tmp_db):
        conn = connect(tmp_db)
        ensure_learning_schema(conn)
        result = generate_class_report_v2(conn, student_ids=["s_new"])
        assert len(result["students"]) == 1
        assert result["students"][0]["attempts"] == 0
        assert result["summary"]["active_students"] == 0
        conn.close()


class TestClassReportV2Concepts:
    """Verify concept overview uses mastery levels."""

    def test_concept_overview_has_mastery_levels(self, tmp_db):
        _seed_data(tmp_db, student_ids=("s1",))
        conn = connect(tmp_db)
        result = generate_class_report_v2(conn, student_ids=["s1"])
        if result["concept_overview"]:
            co = result["concept_overview"][0]
            for key in ("concept_id", "student_count", "mastered_count", "developing_count", "unbuilt_count", "review_count"):
                assert key in co, f"Missing key in concept_overview: {key}"
        conn.close()

    def test_concept_overview_with_mastered_state(self, tmp_db):
        conn = connect(tmp_db)
        ensure_learning_schema(conn)
        state = StudentConceptState(
            student_id="s1",
            concept_id="frac_concept_basic",
            mastery_level=MasteryLevel.MASTERED,
            mastery_score=0.9,
        )
        upsert_concept_state(state, conn=conn)
        conn.commit()
        result = generate_class_report_v2(conn, student_ids=["s1"])
        co = [c for c in result["concept_overview"] if c["concept_id"] == "frac_concept_basic"]
        assert len(co) == 1
        assert co[0]["mastered_count"] == 1
        conn.close()


class TestClassReportV2Weakness:
    """Verify weakness detection uses error_type."""

    def test_weakness_top_uses_error_type(self, tmp_db):
        # Seed incorrect attempts (they get error_type from classifier)
        recordAttempt(
            _make_event(is_correct=False, extra={"correct_answer": "5"}),
            db_path=tmp_db,
        )
        conn = connect(tmp_db)
        result = generate_class_report_v2(conn, student_ids=["s1"])
        # weakness_top entries should use "error_type" key, not "error_tag"
        for w in result["weakness_top"]:
            assert "error_type" in w
            assert "error_tag" not in w
        conn.close()


class TestClassReportV2Import:
    """Verify the function is importable."""

    def test_importable(self):
        from learning.class_report import generate_class_report_v2
        assert callable(generate_class_report_v2)

    def test_v1_still_exists(self):
        from learning.class_report import generate_class_report
        assert callable(generate_class_report)
