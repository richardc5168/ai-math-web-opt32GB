"""Tests for learning.remediation_flow module."""

import pytest

from learning.remediation_flow import (
    HintLevel,
    HintSession,
    RemediationAction,
    HintEffectivenessRecord,
    compute_hint_effectiveness,
    evaluate_remediation_need,
    get_next_hint,
    should_flag_teacher,
)


# ===== HintLevel =====

class TestHintLevel:
    def test_ordering(self):
        assert HintLevel.NONE < HintLevel.CONCEPT < HintLevel.STEP < HintLevel.SCAFFOLD < HintLevel.SOLUTION

    def test_values(self):
        assert HintLevel.NONE == 0
        assert HintLevel.SOLUTION == 4


# ===== get_next_hint =====

class TestGetNextHint:
    def _session(self, **kwargs):
        defaults = {"question_id": "q1", "concept_id": "fraction_add"}
        defaults.update(kwargs)
        return HintSession(**defaults)

    def test_first_hint_is_concept(self):
        session = self._session()
        action = get_next_hint(session)
        assert action.action_type == "show_hint"
        assert action.hint_level == HintLevel.CONCEPT
        assert session.current_level == HintLevel.CONCEPT

    def test_second_hint_is_step(self):
        session = self._session(current_level=HintLevel.CONCEPT)
        action = get_next_hint(session)
        assert action.hint_level == HintLevel.STEP

    def test_third_hint_is_scaffold(self):
        session = self._session(current_level=HintLevel.STEP)
        action = get_next_hint(session)
        assert action.hint_level == HintLevel.SCAFFOLD

    def test_fourth_hint_is_solution(self):
        session = self._session(current_level=HintLevel.SCAFFOLD)
        action = get_next_hint(session)
        assert action.hint_level == HintLevel.SOLUTION

    def test_after_solution_triggers_remediation(self):
        session = self._session(
            current_level=HintLevel.SOLUTION,
            total_wrong_this_concept=3,
        )
        action = get_next_hint(session)
        # Should recommend simpler_item (≥3 wrong, scaffold+ exhausted)
        assert action.action_type == "simpler_item"

    def test_hints_shown_tracks_levels(self):
        session = self._session()
        get_next_hint(session)
        get_next_hint(session)
        get_next_hint(session)
        assert session.hints_shown == [HintLevel.CONCEPT, HintLevel.STEP, HintLevel.SCAFFOLD]

    def test_hint_reason_contains_chinese(self):
        session = self._session()
        action = get_next_hint(session)
        assert "觀念" in action.reason


# ===== evaluate_remediation_need =====

class TestEvaluateRemediationNeed:
    def _session(self, **kwargs):
        defaults = {"question_id": "q1", "concept_id": "fraction_add"}
        defaults.update(kwargs)
        return HintSession(**defaults)

    def test_simpler_item_after_repeated_failure_and_hints(self):
        session = self._session(
            current_level=HintLevel.SCAFFOLD,
            total_wrong_this_concept=3,
            hints_shown=[HintLevel.CONCEPT, HintLevel.STEP, HintLevel.SCAFFOLD],
        )
        action = evaluate_remediation_need(session)
        assert action.action_type == "simpler_item"
        assert "簡單" in action.reason

    def test_escalate_hint_when_hints_not_exhausted(self):
        session = self._session(
            current_level=HintLevel.CONCEPT,
            total_wrong_this_concept=3,
        )
        action = evaluate_remediation_need(session)
        assert action.action_type == "show_hint"
        assert session.current_level == HintLevel.STEP

    def test_below_threshold_suggests_continue(self):
        session = self._session(
            current_level=HintLevel.NONE,
            total_wrong_this_concept=1,
        )
        action = evaluate_remediation_need(session)
        assert action.action_type == "show_hint"


# ===== should_flag_teacher =====

class TestShouldFlagTeacher:
    def test_flags_when_stuck_5_times_with_solution(self):
        session = HintSession(
            question_id="q1",
            concept_id="fraction_add",
            current_level=HintLevel.SOLUTION,
            total_wrong_this_concept=5,
        )
        assert should_flag_teacher(session) is True

    def test_no_flag_when_wrong_count_low(self):
        session = HintSession(
            question_id="q1",
            concept_id="fraction_add",
            current_level=HintLevel.SOLUTION,
            total_wrong_this_concept=3,
        )
        assert should_flag_teacher(session) is False

    def test_no_flag_when_hints_not_exhausted(self):
        session = HintSession(
            question_id="q1",
            concept_id="fraction_add",
            current_level=HintLevel.STEP,
            total_wrong_this_concept=5,
        )
        assert should_flag_teacher(session) is False


# ===== compute_hint_effectiveness =====

class TestComputeHintEffectiveness:
    def test_empty_records(self):
        result = compute_hint_effectiveness([])
        assert result == {}

    def test_single_concept_single_level(self):
        records = [
            HintEffectivenessRecord("frac_add", HintLevel.CONCEPT, True),
            HintEffectivenessRecord("frac_add", HintLevel.CONCEPT, False),
            HintEffectivenessRecord("frac_add", HintLevel.CONCEPT, True),
        ]
        result = compute_hint_effectiveness(records)
        assert "frac_add" in result
        level_data = result["frac_add"]["by_level"]["concept"]
        assert level_data["total"] == 3
        assert level_data["effective"] == 2
        assert abs(level_data["rate"] - 2 / 3) < 0.01

    def test_multiple_levels(self):
        records = [
            HintEffectivenessRecord("frac_sub", HintLevel.CONCEPT, True),
            HintEffectivenessRecord("frac_sub", HintLevel.STEP, False),
        ]
        result = compute_hint_effectiveness(records)
        assert "concept" in result["frac_sub"]["by_level"]
        assert "step" in result["frac_sub"]["by_level"]
        assert result["frac_sub"]["overall_effectiveness"] == 0.5

    def test_multiple_concepts(self):
        records = [
            HintEffectivenessRecord("frac_add", HintLevel.CONCEPT, True),
            HintEffectivenessRecord("decimal_mul", HintLevel.STEP, False),
        ]
        result = compute_hint_effectiveness(records)
        assert len(result) == 2
        assert result["frac_add"]["overall_effectiveness"] == 1.0
        assert result["decimal_mul"]["overall_effectiveness"] == 0.0
