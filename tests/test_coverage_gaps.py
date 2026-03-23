"""R34/EXP-P3-09: Coverage tests for under-tested learning modules.

Targets: mastery_config, validator, remediation, datasets, parent_report.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta

import pytest

# ---------------------------------------------------------------------------
# 1. mastery_config  (previously 0 tests)
# ---------------------------------------------------------------------------
from learning.mastery_config import (
    MASTERY_CONFIG,
    get_level_for_score,
    get_promotion_gate,
    get_score_delta,
)


class TestMasteryConfig:
    def test_score_deltas_present(self):
        for key in ("correct_no_hint", "correct_with_hint", "wrong", "transfer_success", "delayed_review_correct"):
            assert key in MASTERY_CONFIG["score_deltas"]

    def test_get_score_delta_known(self):
        assert get_score_delta("correct_no_hint") == 0.15
        assert get_score_delta("wrong") == -0.10

    def test_get_score_delta_unknown(self):
        assert get_score_delta("nonexistent") == 0.0

    def test_get_level_for_score_mastered(self):
        assert get_level_for_score(0.90) == "mastered"

    def test_get_level_for_score_approaching(self):
        assert get_level_for_score(0.60) == "approaching_mastery"

    def test_get_level_for_score_developing(self):
        assert get_level_for_score(0.30) == "developing"

    def test_get_level_for_score_unbuilt(self):
        assert get_level_for_score(0.10) == "unbuilt"
        assert get_level_for_score(0.0) == "unbuilt"

    def test_get_level_for_score_boundaries(self):
        assert get_level_for_score(0.80) == "mastered"
        assert get_level_for_score(0.50) == "approaching_mastery"
        assert get_level_for_score(0.20) == "developing"
        assert get_level_for_score(0.19) == "unbuilt"

    def test_get_promotion_gate_mastered(self):
        gate = get_promotion_gate("mastered")
        assert gate["min_attempts"] == 8
        assert gate["min_recent_accuracy"] == 0.85
        assert gate["min_consecutive_correct"] == 3

    def test_get_promotion_gate_developing(self):
        gate = get_promotion_gate("developing")
        assert gate["min_attempts"] == 3

    def test_get_promotion_gate_unknown(self):
        assert get_promotion_gate("nonexistent") == {}

    def test_review_trigger_config(self):
        assert MASTERY_CONFIG["review_trigger"]["days_since_mastered"] == 7
        assert MASTERY_CONFIG["review_trigger"]["review_decay_score"] == -0.05

    def test_failure_thresholds(self):
        assert MASTERY_CONFIG["failure"]["repeated_failure_threshold"] == 3


# ---------------------------------------------------------------------------
# 2. validator  (previously 3 tests — add edge cases)
# ---------------------------------------------------------------------------
from learning.validator import ValidatedAttemptEvent, validate_attempt_event


class TestValidatorEdgeCases:
    def test_camel_case_keys(self):
        v = validate_attempt_event({
            "studentId": "s1",
            "questionId": "q1",
            "timestamp": "2026-01-01T00:00:00",
            "isCorrect": True,
            "answerRaw": "42",
        })
        assert v.student_id == "s1"
        assert v.question_id == "q1"

    def test_numeric_timestamp_seconds(self):
        v = validate_attempt_event({
            "student_id": "s1",
            "question_id": "q1",
            "timestamp": 1700000000,
            "is_correct": False,
            "answer_raw": "x",
        })
        assert "2023" in v.timestamp_iso

    def test_numeric_timestamp_milliseconds(self):
        v = validate_attempt_event({
            "student_id": "s1",
            "question_id": "q1",
            "timestamp": 1700000000000,
            "is_correct": True,
            "answer_raw": "42",
        })
        assert "2023" in v.timestamp_iso

    def test_is_correct_as_int(self):
        v = validate_attempt_event({
            "student_id": "s1",
            "question_id": "q1",
            "timestamp": "2026-01-01T00:00:00",
            "is_correct": 1,
            "answer_raw": "y",
        })
        assert v.is_correct is True

    def test_duration_ms_validation(self):
        v = validate_attempt_event({
            "student_id": "s1",
            "question_id": "q1",
            "timestamp": "2026-01-01T00:00:00",
            "is_correct": True,
            "answer_raw": "42",
            "duration_ms": 5000,
        })
        assert v.duration_ms == 5000

    def test_negative_duration_ms_rejected(self):
        with pytest.raises(ValueError, match="duration_ms"):
            validate_attempt_event({
                "student_id": "s1",
                "question_id": "q1",
                "timestamp": "2026-01-01T00:00:00",
                "is_correct": True,
                "answer_raw": "42",
                "duration_ms": -1,
            })

    def test_missing_question_id_rejected(self):
        with pytest.raises(ValueError, match="question_id"):
            validate_attempt_event({
                "student_id": "s1",
                "timestamp": "2026-01-01T00:00:00",
                "is_correct": True,
                "answer_raw": "x",
            })

    def test_empty_timestamp_rejected(self):
        with pytest.raises(ValueError, match="timestamp"):
            validate_attempt_event({
                "student_id": "s1",
                "question_id": "q1",
                "timestamp": "",
                "is_correct": True,
                "answer_raw": "x",
            })

    def test_valid_mistake_codes(self):
        for code in ("concept", "calculation", "unit", "reading", "careless"):
            v = validate_attempt_event({
                "student_id": "s1",
                "question_id": "q1",
                "timestamp": "2026-01-01T00:00:00",
                "is_correct": False,
                "answer_raw": "x",
                "mistake_code": code,
            })
            assert v.mistake_code == code

    def test_hint_steps_auto_count(self):
        v = validate_attempt_event({
            "student_id": "s1",
            "question_id": "q1",
            "timestamp": "2026-01-01T00:00:00",
            "is_correct": True,
            "answer_raw": "42",
            "hints_viewed_count": 0,
            "hint_steps_viewed": [1, 2],
        })
        assert v.hints_viewed_count == 2

    def test_skill_tags_fallback(self):
        v = validate_attempt_event({
            "student_id": "s1",
            "question_id": "q1",
            "timestamp": "2026-01-01T00:00:00",
            "is_correct": True,
            "answer_raw": "42",
        })
        assert v.skill_tags == ["unknown"]

    def test_non_dict_event_rejected(self):
        with pytest.raises(ValueError, match="dict"):
            validate_attempt_event("not a dict")

    def test_extra_field_as_meta(self):
        v = validate_attempt_event({
            "student_id": "s1",
            "question_id": "q1",
            "timestamp": "2026-01-01T00:00:00",
            "is_correct": True,
            "answer_raw": "42",
            "meta": {"key": "val"},
        })
        assert v.extra == {"key": "val"}


# ---------------------------------------------------------------------------
# 3. remediation  (previously 1 golden test — add unit tests)
# ---------------------------------------------------------------------------
from learning.remediation import (
    generate_remediation_plan,
    get_practice_items_for_skill,
)


class TestRemediationUnit:
    def test_practice_items_known_skill(self):
        items = get_practice_items_for_skill("四則運算")
        assert len(items) >= 1
        assert all("id" in it for it in items)

    def test_practice_items_unknown_skill(self):
        items = get_practice_items_for_skill("nonexistent")
        assert len(items) >= 1
        assert items[0]["id"] == "general_practice"

    def test_practice_items_defensive_copy(self):
        a = get_practice_items_for_skill("四則運算")
        b = get_practice_items_for_skill("四則運算")
        assert a is not b
        assert a[0] is not b[0]

    def test_generate_plan_structure(self):
        analytics = {
            "student_id": "s1",
            "generated_at": "2026-01-01",
            "window_days": 14,
            "skills": [
                {"skill_tag": "四則運算", "attempts": 10, "accuracy": 0.3, "hint_dependency": 0.8,
                 "top_mistake": {"code": "concept", "count": 5}},
                {"skill_tag": "分數/小數", "attempts": 8, "accuracy": 0.5, "hint_dependency": 0.4,
                 "top_mistake": {"code": "calculation", "count": 2}},
            ],
        }
        plan = generate_remediation_plan(analytics)
        assert plan["student_id"] == "s1"
        assert "weak_skills_top3" in plan
        assert "suggested_practice_sequence" in plan
        assert "student_selectable_goals" in plan
        assert len(plan["suggested_practice_sequence"]) <= 10
        assert len(plan["student_selectable_goals"]) <= 5

    def test_generate_plan_empty_analytics(self):
        plan = generate_remediation_plan({"student_id": "s1", "skills": []})
        assert plan["weak_skills_top3"] == []
        assert plan["suggested_practice_sequence"] == []


# ---------------------------------------------------------------------------
# 4. datasets  (previously 1 test — add edge cases)
# ---------------------------------------------------------------------------
from learning.datasets import DatasetBlueprint, get_skill_weight


class TestDatasetsUnit:
    def test_get_skill_weight_none_blueprint(self):
        assert get_skill_weight(None, "anything") == 1.0

    def test_get_skill_weight_present(self):
        bp = DatasetBlueprint(
            name="test",
            version="1",
            skill_weights={"math": 2.0},
            topic_weights={},
            sample_question_ids=[],
        )
        assert get_skill_weight(bp, "math") == 2.0

    def test_get_skill_weight_missing(self):
        bp = DatasetBlueprint(
            name="test",
            version="1",
            skill_weights={"math": 2.0},
            topic_weights={},
            sample_question_ids=[],
        )
        assert get_skill_weight(bp, "science") == 1.0

    def test_blueprint_frozen(self):
        bp = DatasetBlueprint(
            name="test",
            version="1",
            skill_weights={},
            topic_weights={},
            sample_question_ids=[],
        )
        with pytest.raises(Exception):
            bp.name = "changed"


# ---------------------------------------------------------------------------
# 5. parent_report  (previously 0 direct tests)
# ---------------------------------------------------------------------------
from learning.parent_report import (
    compute_skill_status,
    mastery_targets_for_skill,
)


class TestParentReport:
    def test_mastery_targets_returns_dict(self):
        t = mastery_targets_for_skill("四則運算")
        assert "min_attempts" in t
        assert "min_accuracy" in t
        assert "max_hint_dependency" in t

    def test_skill_status_mastered(self):
        r = compute_skill_status(attempts=15, accuracy=0.90, hint_dependency=0.1, skill_tag="四則運算")
        assert r["code"] == "MASTERED"
        assert r["is_mastered"] is True

    def test_skill_status_need_focus(self):
        r = compute_skill_status(attempts=15, accuracy=0.40, hint_dependency=0.8, skill_tag="四則運算")
        assert r["code"] == "NEED_FOCUS"
        assert r["is_mastered"] is False

    def test_skill_status_improving(self):
        r = compute_skill_status(attempts=15, accuracy=0.78, hint_dependency=0.5, skill_tag="四則運算")
        assert r["code"] == "IMPROVING"

    def test_skill_status_not_enough_data(self):
        r = compute_skill_status(attempts=3, accuracy=1.0, hint_dependency=0.0, skill_tag="四則運算")
        assert r["code"] == "NOT_ENOUGH_DATA"

    def test_status_label_is_chinese(self):
        r = compute_skill_status(attempts=15, accuracy=0.90, hint_dependency=0.1, skill_tag="四則運算")
        assert r["label"] == "已掌握"

    def test_targets_line_format(self):
        r = compute_skill_status(attempts=15, accuracy=0.90, hint_dependency=0.1, skill_tag="四則運算")
        assert "≥" in r["targets_line"]
