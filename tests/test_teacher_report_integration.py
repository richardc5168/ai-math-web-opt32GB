"""Tests for EXP-08: teacher concept report endpoint wiring.

Verifies that generate_teacher_report produces correct reports
when fed real concept states created by recordAttempt + get_class_states.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from learning.service import recordAttempt
from learning.concept_state import get_class_states
from learning.teacher_report import generate_teacher_report, report_to_dict


@pytest.fixture
def tmp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


def _make_event(student_id="s1", question_id="q1", ts_minute=0, **overrides):
    base = {
        "student_id": student_id,
        "question_id": question_id,
        "timestamp": f"2026-03-22T12:{ts_minute:02d}:00+08:00",
        "is_correct": True,
        "answer_raw": "42",
        "skill_tags": ["fraction"],
    }
    base.update(overrides)
    return base


class TestTeacherReportIntegration:
    """EXP-08: teacher report from real concept states."""

    def test_empty_class_report(self, tmp_db):
        """Report with no students should return empty structure."""
        report = generate_teacher_report(
            class_id="c1", teacher_name="Teacher1",
            student_states={},
        )
        d = report_to_dict(report)
        assert d["class_id"] == "c1"
        assert d["student_count"] == 0
        assert d["top_blocking_concepts"] == []

    def test_single_student_report(self, tmp_db):
        """Report with one student who has concept states."""
        for i in range(3):
            recordAttempt(_make_event(question_id=f"q{i}", ts_minute=i), db_path=tmp_db)

        states_map = get_class_states(["s1"], db_path=tmp_db)
        student_states = {sid: list(m.values()) for sid, m in states_map.items()}
        report = generate_teacher_report(
            class_id="c1", teacher_name="T1",
            student_states=student_states,
        )
        d = report_to_dict(report)
        assert d["student_count"] == 1
        assert len(d["concept_distribution"]) > 0

    def test_multi_student_report(self, tmp_db):
        """Report with multiple students shows correct count."""
        for s in ["s1", "s2", "s3"]:
            for i in range(2):
                recordAttempt(
                    _make_event(student_id=s, question_id=f"q{i}", ts_minute=i),
                    db_path=tmp_db,
                )

        states_map = get_class_states(["s1", "s2", "s3"], db_path=tmp_db)
        student_states = {sid: list(m.values()) for sid, m in states_map.items()}
        report = generate_teacher_report(
            class_id="c1", teacher_name="T1",
            student_states=student_states,
        )
        d = report_to_dict(report)
        assert d["student_count"] == 3

    def test_report_has_insights(self, tmp_db):
        """Report should generate Chinese insights."""
        for i in range(5):
            recordAttempt(_make_event(question_id=f"q{i}", ts_minute=i), db_path=tmp_db)

        states_map = get_class_states(["s1"], db_path=tmp_db)
        student_states = {sid: list(m.values()) for sid, m in states_map.items()}
        report = generate_teacher_report(
            class_id="c1", teacher_name="T1",
            student_states=student_states,
        )
        d = report_to_dict(report)
        assert "insights" in d
        assert isinstance(d["insights"], list)

    def test_report_serialization_complete(self, tmp_db):
        """report_to_dict should include all expected keys."""
        report = generate_teacher_report(
            class_id="c1", teacher_name="T1",
            student_states={},
        )
        d = report_to_dict(report)
        expected_keys = {
            "class_id", "generated_for", "student_count",
            "active_student_count", "top_blocking_concepts",
            "students_needing_attention", "concept_distribution",
            "hint_effectiveness", "common_error_patterns", "insights",
        }
        assert expected_keys.issubset(set(d.keys()))

    def test_struggling_student_flagged(self, tmp_db):
        """Student with many wrong answers should appear in at-risk list."""
        for i in range(5):
            recordAttempt(
                _make_event(question_id=f"q{i}", ts_minute=i, is_correct=False, answer_raw="wrong"),
                db_path=tmp_db,
            )

        states_map = get_class_states(["s1"], db_path=tmp_db)
        student_states = {sid: list(m.values()) for sid, m in states_map.items()}
        report = generate_teacher_report(
            class_id="c1", teacher_name="T1",
            student_states=student_states,
        )
        d = report_to_dict(report)
        at_risk = d["students_needing_attention"]
        assert len(at_risk) > 0
        assert at_risk[0]["student_id"] == "s1"
