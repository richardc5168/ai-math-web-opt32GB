"""Tests for EXP-09: parent_report_enhanced wiring.

Verifies that generate_parent_concept_progress produces correct reports
when fed real concept states created by recordAttempt.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from learning.service import recordAttempt
from learning.concept_state import get_all_states
from learning.parent_report_enhanced import (
    generate_parent_concept_progress,
    progress_to_dict,
    format_parent_progress_section,
)


@pytest.fixture
def tmp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


def _make_event(question_id="q1", ts_minute=0, **overrides):
    base = {
        "student_id": "s1",
        "question_id": question_id,
        "timestamp": f"2026-03-22T12:{ts_minute:02d}:00+08:00",
        "is_correct": True,
        "answer_raw": "42",
        "skill_tags": ["fraction"],
    }
    base.update(overrides)
    return base


class TestParentReportEnhanced:
    """EXP-09: parent concept progress from real mastery states."""

    def test_empty_states_report(self, tmp_db):
        """Report with no states returns empty concepts list."""
        report = generate_parent_concept_progress(student_id="s1", states=[])
        d = progress_to_dict(report)
        assert d["student_id"] == "s1"
        assert d["concepts"] == []
        assert d["overall_mastery_pct"] == 0.0

    def test_report_from_real_states(self, tmp_db):
        """Report from states created by recordAttempt."""
        for i in range(5):
            recordAttempt(_make_event(question_id=f"q{i}", ts_minute=i), db_path=tmp_db)

        states = get_all_states("s1", db_path=tmp_db)
        report = generate_parent_concept_progress(
            student_id="s1", states=list(states.values()),
        )
        d = progress_to_dict(report)
        assert d["student_id"] == "s1"
        assert len(d["concepts"]) > 0

    def test_concept_has_chinese_labels(self, tmp_db):
        """Each concept should have Chinese mastery label and parent tip."""
        for i in range(3):
            recordAttempt(_make_event(question_id=f"q{i}", ts_minute=i), db_path=tmp_db)

        states = get_all_states("s1", db_path=tmp_db)
        report = generate_parent_concept_progress(
            student_id="s1", states=list(states.values()),
        )
        d = progress_to_dict(report)
        c = d["concepts"][0]
        assert "mastery_label" in c
        assert len(c["mastery_label"]) > 0
        assert "parent_tip" in c
        assert len(c["parent_tip"]) > 0

    def test_encouragement_present(self, tmp_db):
        """Report should include encouragement text."""
        report = generate_parent_concept_progress(student_id="s1", states=[])
        d = progress_to_dict(report)
        assert "encouragement" in d

    def test_markdown_format(self, tmp_db):
        """format_parent_progress_section returns valid markdown."""
        for i in range(3):
            recordAttempt(_make_event(question_id=f"q{i}", ts_minute=i), db_path=tmp_db)

        states = get_all_states("s1", db_path=tmp_db)
        report = generate_parent_concept_progress(
            student_id="s1", states=list(states.values()),
        )
        md = format_parent_progress_section(report)
        assert "## 觀念掌握進度" in md
        assert "整體掌握率" in md

    def test_serialization_keys(self, tmp_db):
        """progress_to_dict should have all expected keys."""
        for i in range(3):
            recordAttempt(_make_event(question_id=f"q{i}", ts_minute=i), db_path=tmp_db)

        states = get_all_states("s1", db_path=tmp_db)
        report = generate_parent_concept_progress(
            student_id="s1", states=list(states.values()),
        )
        d = progress_to_dict(report)
        expected = {"student_id", "overall_mastery_pct", "total_concepts_active", "encouragement", "concepts"}
        assert expected.issubset(set(d.keys()))
        c = d["concepts"][0]
        concept_keys = {"concept_id", "display_name", "mastery_label", "mastery_level",
                        "accuracy_pct", "hint_dependency_pct", "attempts", "parent_tip"}
        assert concept_keys.issubset(set(c.keys()))
