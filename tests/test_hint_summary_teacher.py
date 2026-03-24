"""Tests for EXP-A3: format_hint_summary_for_teacher().

Verifies that raw hint effectiveness stats are transformed into
teacher-readable Chinese summaries with recommendations and risk flags.
"""

from __future__ import annotations

import pytest

from learning.teacher_report import format_hint_summary_for_teacher


def _make_stats(**overrides):
    base = {
        "total_hinted_attempts": 0,
        "correct_with_hint": 0,
        "stuck_after_hint": 0,
        "hint_success_rate": 0.0,
        "stuck_after_hint_rate": 0.0,
        "avg_hints_before_success": 0.0,
        "hint_escalation_rate": 0.0,
        "avg_hint_dwell_ms": 0.0,
        "hint_level_used_coverage_rate": 0.0,
        "hint_sequence_coverage_rate": 0.0,
        "hint_open_ts_coverage_rate": 0.0,
        "evidence_chain_complete_rate": 0.0,
        "by_hint_level_at_submit": {},
        "by_level": {},
        "by_concept": {},
        "generated_at": "2026-03-23T10:00:00+08:00",
    }
    base.update(overrides)
    return base


class TestFormatHintSummaryEmpty:
    def test_empty_returns_structure(self):
        result = format_hint_summary_for_teacher(_make_stats())
        assert "overview" in result
        assert "by_concept" in result
        assert "by_level" in result
        assert "recommendations" in result
        assert "risk_flags" in result

    def test_empty_has_no_data_message(self):
        result = format_hint_summary_for_teacher(_make_stats())
        assert any("沒有使用提示" in r for r in result["recommendations"])


class TestFormatHintSummaryHighSuccess:
    def test_high_success_positive_message(self):
        stats = _make_stats(
            total_hinted_attempts=20,
            correct_with_hint=16,
            stuck_after_hint=4,
            hint_success_rate=0.8,
            stuck_after_hint_rate=0.2,
            hint_level_used_coverage_rate=1.0,
            hint_sequence_coverage_rate=1.0,
            hint_open_ts_coverage_rate=1.0,
            evidence_chain_complete_rate=1.0,
        )
        result = format_hint_summary_for_teacher(stats)
        assert result["overview"]["hint_success_rate_pct"] == "80%"
        assert any("有效" in r for r in result["recommendations"])
        assert len(result["risk_flags"]) == 0


class TestFormatHintSummaryLowSuccess:
    def test_low_success_generates_risk_flag(self):
        stats = _make_stats(
            total_hinted_attempts=20,
            correct_with_hint=4,
            stuck_after_hint=16,
            hint_success_rate=0.2,
            stuck_after_hint_rate=0.8,
        )
        result = format_hint_summary_for_teacher(stats)
        assert len(result["risk_flags"]) > 0
        assert any("偏低" in f for f in result["risk_flags"])

    def test_high_stuck_rate_generates_flag(self):
        stats = _make_stats(
            total_hinted_attempts=10,
            correct_with_hint=3,
            stuck_after_hint=7,
            hint_success_rate=0.3,
            stuck_after_hint_rate=0.7,
        )
        result = format_hint_summary_for_teacher(stats)
        assert any("仍然答錯" in f for f in result["risk_flags"])


class TestFormatHintSummaryByConcept:
    def test_weak_concept_flagged(self):
        stats = _make_stats(
            total_hinted_attempts=10,
            correct_with_hint=5,
            stuck_after_hint=5,
            hint_success_rate=0.5,
            stuck_after_hint_rate=0.5,
            by_concept={
                "frac_add": {"total": 5, "correct": 1},
                "frac_multiply": {"total": 5, "correct": 4},
            },
        )
        result = format_hint_summary_for_teacher(stats)
        # frac_add has 20% success rate with >=3 attempts → should be flagged
        assert len(result["by_concept"]) == 2
        # Sorted by success_rate ascending
        assert result["by_concept"][0]["concept_id"] == "frac_add"
        assert any("frac_add" in f or "分數加法" in f for f in result["risk_flags"])

    def test_no_flag_for_few_attempts(self):
        """Concepts with < 3 attempts should not be flagged as weak."""
        stats = _make_stats(
            total_hinted_attempts=2,
            correct_with_hint=0,
            stuck_after_hint=2,
            hint_success_rate=0.0,
            stuck_after_hint_rate=1.0,
            by_concept={
                "frac_add": {"total": 2, "correct": 0},
            },
        )
        result = format_hint_summary_for_teacher(stats)
        concept_flags = [f for f in result["risk_flags"] if "frac_add" in f or "分數加法" in f]
        assert len(concept_flags) == 0


class TestFormatHintSummaryByLevel:
    def test_level_labels_in_chinese(self):
        stats = _make_stats(
            total_hinted_attempts=10,
            correct_with_hint=5,
            stuck_after_hint=5,
            hint_success_rate=0.5,
            stuck_after_hint_rate=0.5,
            by_level={
                "1": {"total": 6, "correct": 4},
                "2": {"total": 3, "correct": 1},
                "3": {"total": 1, "correct": 0},
            },
        )
        result = format_hint_summary_for_teacher(stats)
        assert len(result["by_level"]) == 3
        assert result["by_level"][0]["label"] == "看了 1 個提示"
        assert result["by_level"][1]["hint_count"] == "2"

    def test_multi_hint_escalation_warning(self):
        stats = _make_stats(
            total_hinted_attempts=15,
            correct_with_hint=7,
            stuck_after_hint=8,
            hint_success_rate=0.47,
            stuck_after_hint_rate=0.53,
            by_level={
                "1": {"total": 5, "correct": 4},
                "2": {"total": 4, "correct": 2},
                "3": {"total": 6, "correct": 1},
            },
        )
        result = format_hint_summary_for_teacher(stats)
        assert any("3 個以上提示" in r for r in result["recommendations"])


class TestFormatHintSummaryOverview:
    def test_overview_fields(self):
        stats = _make_stats(
            total_hinted_attempts=10,
            correct_with_hint=7,
            stuck_after_hint=3,
            hint_success_rate=0.7,
            stuck_after_hint_rate=0.3,
        )
        result = format_hint_summary_for_teacher(stats)
        ov = result["overview"]
        assert ov["total_hinted_attempts"] == 10
        assert ov["correct_with_hint"] == 7
        assert ov["stuck_after_hint"] == 3
        assert ov["hint_success_rate"] == 0.7
        assert ov["hint_success_rate_pct"] == "70%"
        assert ov["stuck_after_hint_rate_pct"] == "30%"

    def test_overview_includes_evidence_coverage(self):
        stats = _make_stats(
            total_hinted_attempts=10,
            correct_with_hint=6,
            stuck_after_hint=4,
            hint_success_rate=0.6,
            stuck_after_hint_rate=0.4,
            avg_hints_before_success=2.2,
            hint_escalation_rate=0.5,
            avg_hint_dwell_ms=8500.0,
            hint_level_used_coverage_rate=1.0,
            hint_sequence_coverage_rate=0.7,
            hint_open_ts_coverage_rate=0.5,
            evidence_chain_complete_rate=0.5,
        )
        result = format_hint_summary_for_teacher(stats)
        ov = result["overview"]
        assert ov["avg_hints_before_success"] == pytest.approx(2.2)
        assert ov["hint_escalation_rate_pct"] == "50%"
        assert ov["avg_hint_dwell_sec"] == pytest.approx(8.5)
        assert ov["hint_sequence_coverage_rate_pct"] == "70%"
        assert ov["hint_open_ts_coverage_rate_pct"] == "50%"
        assert ov["evidence_chain_complete_rate_pct"] == "50%"

    def test_low_evidence_coverage_generates_risk_flag(self):
        stats = _make_stats(
            total_hinted_attempts=10,
            correct_with_hint=5,
            stuck_after_hint=5,
            hint_success_rate=0.5,
            stuck_after_hint_rate=0.5,
            hint_sequence_coverage_rate=0.3,
            hint_open_ts_coverage_rate=0.2,
            evidence_chain_complete_rate=0.2,
        )
        result = format_hint_summary_for_teacher(stats)
        assert any("evidence chain" in f for f in result["risk_flags"])
        assert any("hint_sequence 覆蓋率" in r for r in result["recommendations"])
        assert any("hint_open_ts 覆蓋率" in r for r in result["recommendations"])

    def test_by_submit_level_is_teacher_readable(self):
        stats = _make_stats(
            total_hinted_attempts=4,
            correct_with_hint=2,
            stuck_after_hint=2,
            hint_success_rate=0.5,
            stuck_after_hint_rate=0.5,
            by_hint_level_at_submit={
                "1": {"total": 2, "correct": 1, "rate": 0.5},
                "2": {"total": 2, "correct": 1, "rate": 0.5},
            },
        )
        result = format_hint_summary_for_teacher(stats)
        assert result["by_submit_level"][0]["label"] == "送出作答時最高提示 L1"
        assert result["by_submit_level"][1]["attempts"] == 2
