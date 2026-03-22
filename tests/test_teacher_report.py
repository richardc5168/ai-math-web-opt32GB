"""Tests for learning.teacher_report module."""

import pytest

from learning.concept_state import MasteryLevel, StudentConceptState
from learning.error_classifier import ErrorType
from learning.remediation_flow import HintEffectivenessRecord, HintLevel
from learning.teacher_report import (
    TeacherReport,
    generate_teacher_report,
    report_to_dict,
)


def _make_state(concept_id, mastery_level, accuracy=0.5, hint_dep=0.2, **kwargs):
    """Helper to create a StudentConceptState with defaults."""
    defaults = dict(
        student_id="stu1",
        concept_id=concept_id,
        mastery_level=mastery_level,
        mastery_score=50.0,
        attempts_total=10,
        correct_total=5,
        consecutive_correct=2,
        consecutive_wrong=0,
        recent_accuracy=accuracy,
        hint_dependency=hint_dep,
        updated_at="2024-01-15T10:00:00",
    )
    defaults.update(kwargs)
    return StudentConceptState(**defaults)


class TestGenerateTeacherReport:
    def test_empty_class(self):
        report = generate_teacher_report(
            class_id="c1",
            teacher_name="Teacher A",
            student_states={},
        )
        assert isinstance(report, TeacherReport)
        assert report.student_count == 0
        assert report.insights  # should have at least a fallback insight

    def test_single_student_mastered(self):
        states = {
            "stu1": [
                _make_state("fraction_add", MasteryLevel.MASTERED, accuracy=0.95, hint_dep=0.1),
            ],
        }
        report = generate_teacher_report(
            class_id="c1",
            student_states=states,
        )
        assert report.student_count == 1
        assert report.active_student_count == 1
        assert len(report.concept_distribution) == 1
        assert report.concept_distribution[0].mastered_count == 1
        assert len(report.students_needing_attention) == 0

    def test_at_risk_student_detected(self):
        states = {
            "stu_weak": [
                _make_state("fraction_add", MasteryLevel.UNBUILT, accuracy=0.2, hint_dep=0.8, student_id="stu_weak"),
                _make_state("fraction_sub", MasteryLevel.REVIEW_NEEDED, accuracy=0.3, hint_dep=0.7, student_id="stu_weak"),
                _make_state("decimal_add", MasteryLevel.UNBUILT, accuracy=0.1, hint_dep=0.9, student_id="stu_weak"),
            ],
        }
        report = generate_teacher_report(class_id="c1", student_states=states)
        assert len(report.students_needing_attention) == 1
        risk = report.students_needing_attention[0]
        assert risk.risk_level == "high"
        assert len(risk.struggling_concepts) >= 3

    def test_multiple_students_blocking_concept(self):
        states = {
            "stu1": [
                _make_state("fraction_add", MasteryLevel.DEVELOPING, accuracy=0.4, student_id="stu1"),
            ],
            "stu2": [
                _make_state("fraction_add", MasteryLevel.UNBUILT, accuracy=0.2, student_id="stu2"),
            ],
            "stu3": [
                _make_state("fraction_add", MasteryLevel.MASTERED, accuracy=0.95, student_id="stu3"),
            ],
        }
        report = generate_teacher_report(class_id="c1", student_states=states)
        # fraction_add should appear in blocking concepts
        assert len(report.top_blocking_concepts) >= 1
        top = report.top_blocking_concepts[0]
        assert top.concept_id == "fraction_add"
        assert top.mastered_count == 1  # only stu3

    def test_hint_effectiveness_integrated(self):
        states = {
            "stu1": [_make_state("fraction_add", MasteryLevel.DEVELOPING)],
        }
        hint_records = [
            HintEffectivenessRecord("fraction_add", HintLevel.CONCEPT, True),
            HintEffectivenessRecord("fraction_add", HintLevel.CONCEPT, False),
        ]
        report = generate_teacher_report(
            class_id="c1",
            student_states=states,
            hint_records=hint_records,
        )
        assert "fraction_add" in report.hint_effectiveness

    def test_error_patterns_integrated(self):
        states = {
            "stu1": [_make_state("fraction_add", MasteryLevel.DEVELOPING)],
        }
        error_counts = {
            "fraction_add": {
                ErrorType.CARELESS.value: 5,
                ErrorType.CALCULATION_ERROR.value: 3,
            },
        }
        report = generate_teacher_report(
            class_id="c1",
            student_states=states,
            error_counts=error_counts,
        )
        assert len(report.common_error_patterns) >= 1
        top_err = report.common_error_patterns[0]
        assert top_err["error_type"] == ErrorType.CARELESS.value
        assert top_err["total_count"] == 5

    def test_insights_contain_chinese(self):
        states = {
            "stu1": [
                _make_state("fraction_add", MasteryLevel.UNBUILT, accuracy=0.1, student_id="stu1"),
                _make_state("fraction_sub", MasteryLevel.UNBUILT, accuracy=0.1, student_id="stu1"),
                _make_state("decimal_add", MasteryLevel.UNBUILT, accuracy=0.1, student_id="stu1"),
            ],
        }
        report = generate_teacher_report(class_id="c1", student_states=states)
        # Should have insights about at-risk students or blocking concepts
        combined = " ".join(report.insights)
        assert any(c > '\u4e00' for c in combined)  # contains Chinese characters

    def test_top_blocking_limited_to_5(self):
        # Create 10 concepts, all unbuilt
        states = {
            "stu1": [
                _make_state(f"concept_{i}", MasteryLevel.UNBUILT, accuracy=0.1, student_id="stu1")
                for i in range(10)
            ],
        }
        report = generate_teacher_report(class_id="c1", student_states=states)
        assert len(report.top_blocking_concepts) <= 5


class TestReportToDict:
    def test_serializable(self):
        states = {
            "stu1": [_make_state("fraction_add", MasteryLevel.DEVELOPING)],
        }
        report = generate_teacher_report(class_id="c1", student_states=states)
        d = report_to_dict(report)
        assert isinstance(d, dict)
        assert d["class_id"] == "c1"
        assert isinstance(d["top_blocking_concepts"], list)
        assert isinstance(d["insights"], list)

    def test_all_keys_present(self):
        report = generate_teacher_report(class_id="c1", student_states={})
        d = report_to_dict(report)
        expected_keys = {
            "class_id", "generated_for", "student_count", "active_student_count",
            "top_blocking_concepts", "students_needing_attention",
            "concept_distribution", "hint_effectiveness",
            "common_error_patterns", "insights",
        }
        assert expected_keys == set(d.keys())
