"""Tests for learning.parent_report_enhanced module."""

import pytest

from learning.concept_state import MasteryLevel, StudentConceptState
from learning.error_classifier import ErrorType
from learning.remediation_flow import HintEffectivenessRecord, HintLevel
from learning.parent_report_enhanced import (
    generate_parent_concept_progress,
    format_parent_progress_section,
    progress_to_dict,
    ParentConceptReport,
)


def _state(concept_id, level, accuracy=0.5, hint_dep=0.2, attempts=10):
    return StudentConceptState(
        student_id="stu1",
        concept_id=concept_id,
        mastery_level=level,
        mastery_score=50.0,
        recent_accuracy=accuracy,
        hint_dependency=hint_dep,
        attempts_total=attempts,
        correct_total=int(attempts * accuracy),
    )


class TestGenerateParentConceptProgress:
    def test_empty_states(self):
        report = generate_parent_concept_progress(student_id="stu1", states=[])
        assert isinstance(report, ParentConceptReport)
        assert report.overall_mastery_pct == 0.0
        assert len(report.concepts) == 0

    def test_single_mastered_concept(self):
        states = [_state("fraction_add", MasteryLevel.MASTERED, accuracy=0.95)]
        report = generate_parent_concept_progress(student_id="stu1", states=states)
        assert report.overall_mastery_pct == 100.0
        assert report.concepts[0].mastery_label == "已掌握 ✓"
        assert "優秀" in report.encouragement

    def test_mixed_levels(self):
        states = [
            _state("fraction_add", MasteryLevel.MASTERED, accuracy=0.95),
            _state("fraction_sub", MasteryLevel.DEVELOPING, accuracy=0.4),
            _state("decimal_add", MasteryLevel.UNBUILT, accuracy=0.0, attempts=0),
        ]
        report = generate_parent_concept_progress(student_id="stu1", states=states)
        # 1 of 3 mastered = 33.3%
        assert 30 < report.overall_mastery_pct < 35
        assert report.total_concepts_active == 2  # fraction_add and fraction_sub have attempts > 0

    def test_accuracy_and_hint_dep_as_pct(self):
        states = [_state("fraction_add", MasteryLevel.DEVELOPING, accuracy=0.73, hint_dep=0.45)]
        report = generate_parent_concept_progress(student_id="stu1", states=states)
        c = report.concepts[0]
        assert c.accuracy_pct == 73.0
        assert c.hint_dependency_pct == 45.0

    def test_hint_effectiveness_integrated(self):
        states = [_state("fraction_add", MasteryLevel.DEVELOPING)]
        hint_records = [
            HintEffectivenessRecord("fraction_add", HintLevel.CONCEPT, True),
            HintEffectivenessRecord("fraction_add", HintLevel.CONCEPT, False),
        ]
        report = generate_parent_concept_progress(
            student_id="stu1", states=states, hint_records=hint_records,
        )
        assert report.concepts[0].hint_effectiveness == 0.5

    def test_error_history_integrated(self):
        states = [_state("fraction_add", MasteryLevel.DEVELOPING)]
        error_history = {
            "fraction_add": [ErrorType.CARELESS.value, ErrorType.CALCULATION_ERROR.value],
        }
        report = generate_parent_concept_progress(
            student_id="stu1", states=states, error_history=error_history,
        )
        c = report.concepts[0]
        assert len(c.recent_errors) == 2
        assert all("parent_action" in e for e in c.recent_errors)

    def test_encouragement_tiers(self):
        # 0% mastered
        states = [_state("c1", MasteryLevel.UNBUILT, accuracy=0.0, attempts=0)]
        r = generate_parent_concept_progress(student_id="s", states=states)
        assert "每天進步" in r.encouragement

        # 100% mastered
        states = [_state("c1", MasteryLevel.MASTERED, accuracy=0.95)]
        r = generate_parent_concept_progress(student_id="s", states=states)
        assert "優秀" in r.encouragement


class TestFormatParentProgressSection:
    def test_contains_chinese(self):
        states = [_state("fraction_add", MasteryLevel.DEVELOPING, accuracy=0.6)]
        report = generate_parent_concept_progress(student_id="stu1", states=states)
        md = format_parent_progress_section(report)
        assert "觀念掌握進度" in md
        assert "正確率" in md
        assert "60.0%" in md

    def test_sorted_needs_attention_first(self):
        states = [
            _state("c_mastered", MasteryLevel.MASTERED, accuracy=0.95),
            _state("c_review", MasteryLevel.REVIEW_NEEDED, accuracy=0.4),
        ]
        report = generate_parent_concept_progress(student_id="stu1", states=states)
        md = format_parent_progress_section(report)
        # REVIEW_NEEDED should appear before MASTERED
        review_pos = md.find("需要複習")
        mastered_pos = md.find("已掌握")
        assert review_pos < mastered_pos

    def test_hint_effectiveness_warning(self):
        states = [_state("fraction_add", MasteryLevel.DEVELOPING)]
        hint_records = [
            HintEffectivenessRecord("fraction_add", HintLevel.CONCEPT, False),
            HintEffectivenessRecord("fraction_add", HintLevel.CONCEPT, False),
            HintEffectivenessRecord("fraction_add", HintLevel.CONCEPT, True),
        ]
        report = generate_parent_concept_progress(
            student_id="stu1", states=states, hint_records=hint_records,
        )
        md = format_parent_progress_section(report)
        assert "偏低" in md


class TestProgressToDict:
    def test_serializable(self):
        states = [_state("fraction_add", MasteryLevel.DEVELOPING)]
        report = generate_parent_concept_progress(student_id="stu1", states=states)
        d = progress_to_dict(report)
        assert isinstance(d, dict)
        assert d["student_id"] == "stu1"
        assert len(d["concepts"]) == 1
        assert "mastery_label" in d["concepts"][0]

    def test_all_keys_present(self):
        report = generate_parent_concept_progress(student_id="stu1", states=[])
        d = progress_to_dict(report)
        expected = {"student_id", "overall_mastery_pct", "total_concepts_active", "encouragement", "concepts"}
        assert expected == set(d.keys())
