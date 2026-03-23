"""R22/EXP-S2-03: Parent report actionable progress tests.

Tests for trend indicators, prerequisite gap warnings, and enriched
parent report output.
"""

from unittest.mock import patch
from learning.concept_state import MasteryLevel, StudentConceptState
from learning.parent_report_enhanced import (
    ConceptProgress,
    generate_parent_concept_progress,
    format_parent_progress_section,
    progress_to_dict,
    _compute_trend,
    _compute_trend_zh,
    _prereq_gap_warning,
)


def _state(cid, level, score=0.0, accuracy=None, attempts=5, hint_dep=0.0):
    return StudentConceptState(
        student_id="s1",
        concept_id=cid,
        mastery_level=level,
        mastery_score=score,
        recent_accuracy=accuracy,
        attempts_total=attempts,
        hint_dependency=hint_dep,
    )


# --- Trend computation ---

class TestTrendComputation:
    def test_improving_when_accuracy_above_score(self):
        s = _state("A", MasteryLevel.DEVELOPING, score=0.40, accuracy=0.55, attempts=10)
        assert _compute_trend(s) == "improving"

    def test_declining_when_accuracy_below_score(self):
        s = _state("A", MasteryLevel.DEVELOPING, score=0.50, accuracy=0.35, attempts=10)
        assert _compute_trend(s) == "declining"

    def test_stable_when_close(self):
        s = _state("A", MasteryLevel.DEVELOPING, score=0.50, accuracy=0.52, attempts=10)
        assert _compute_trend(s) == "stable"

    def test_none_for_few_attempts(self):
        s = _state("A", MasteryLevel.DEVELOPING, score=0.50, accuracy=0.90, attempts=2)
        assert _compute_trend(s) is None

    def test_trend_zh_labels(self):
        s = _state("A", MasteryLevel.DEVELOPING, score=0.40, accuracy=0.55, attempts=10)
        assert "進步" in _compute_trend_zh(s)

    def test_trend_zh_none_for_few_attempts(self):
        s = _state("A", MasteryLevel.DEVELOPING, score=0.40, accuracy=0.55, attempts=1)
        assert _compute_trend_zh(s) is None


# --- Prerequisite gap warning ---

class TestPrereqGapWarning:
    @patch("learning.parent_report_enhanced.get_prerequisites")
    @patch("learning.parent_report_enhanced.get_display_name")
    def test_warns_when_prereq_not_mastered(self, mock_name, mock_prereqs):
        mock_prereqs.return_value = ["A"]
        mock_name.return_value = "基礎分數"
        s = _state("B", MasteryLevel.DEVELOPING, score=0.3)
        states_by_id = {
            "A": _state("A", MasteryLevel.DEVELOPING, score=0.2),
            "B": s,
        }
        warning = _prereq_gap_warning(s, states_by_id)
        assert warning is not None
        assert "基礎分數" in warning

    @patch("learning.parent_report_enhanced.get_prerequisites")
    def test_no_warning_when_prereq_mastered(self, mock_prereqs):
        mock_prereqs.return_value = ["A"]
        s = _state("B", MasteryLevel.DEVELOPING, score=0.3)
        states_by_id = {
            "A": _state("A", MasteryLevel.MASTERED, score=0.9),
            "B": s,
        }
        assert _prereq_gap_warning(s, states_by_id) is None

    @patch("learning.parent_report_enhanced.get_prerequisites")
    def test_no_warning_for_unbuilt(self, mock_prereqs):
        mock_prereqs.return_value = ["A"]
        s = _state("B", MasteryLevel.UNBUILT)
        assert _prereq_gap_warning(s, {}) is None

    @patch("learning.parent_report_enhanced.get_prerequisites")
    def test_no_warning_for_mastered(self, mock_prereqs):
        mock_prereqs.return_value = ["A"]
        s = _state("B", MasteryLevel.MASTERED, score=1.0)
        assert _prereq_gap_warning(s, {}) is None


# --- Integration: generate + format ---

class TestParentReportIntegration:
    def test_report_includes_trend_fields(self):
        states = [
            _state("frac_concept_basic", MasteryLevel.DEVELOPING, score=0.4, accuracy=0.55, attempts=10),
        ]
        report = generate_parent_concept_progress(student_id="s1", states=states)
        assert len(report.concepts) == 1
        c = report.concepts[0]
        assert c.trend == "improving"
        assert c.trend_zh is not None

    def test_progress_to_dict_includes_new_fields(self):
        states = [
            _state("frac_concept_basic", MasteryLevel.DEVELOPING, score=0.4, accuracy=0.55, attempts=10),
        ]
        report = generate_parent_concept_progress(student_id="s1", states=states)
        d = progress_to_dict(report)
        concept = d["concepts"][0]
        assert "trend" in concept
        assert "trend_zh" in concept
        assert "prereq_gap_warning" in concept

    def test_format_includes_trend_suffix(self):
        states = [
            _state("frac_concept_basic", MasteryLevel.DEVELOPING, score=0.3, accuracy=0.50, attempts=10),
        ]
        report = generate_parent_concept_progress(student_id="s1", states=states)
        text = format_parent_progress_section(report)
        assert "進步" in text

    def test_empty_states_produces_report(self):
        report = generate_parent_concept_progress(student_id="s1", states=[])
        assert report.overall_mastery_pct == 0.0
        assert report.concepts == []
