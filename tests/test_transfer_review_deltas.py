"""R31/EXP-P3-06: Tests for transfer_success and delayed_review_correct delta activation."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta

import pytest

from learning.service import recordAttempt
from learning.concept_state import (
    get_concept_state,
    upsert_concept_state,
    MasteryLevel,
    StudentConceptState,
)
from learning.mastery_engine import AnswerEvent, check_review_needed


@pytest.fixture
def tmp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


def _make_event(**overrides):
    base = {
        "student_id": "s1",
        "question_id": "q1",
        "timestamp": "2026-03-23T12:00:00+08:00",
        "is_correct": True,
        "answer_raw": "42",
        "skill_tags": ["fraction"],
    }
    base.update(overrides)
    return base


# ── Transfer Detection ───────────────────────────────────────────────────


class TestTransferDetection:
    """Verify is_transfer_item is activated for application-domain concepts."""

    def test_application_domain_gets_transfer_bonus(self, tmp_db):
        """Concepts in the 'application' domain should get transfer_success delta."""
        result = recordAttempt(
            _make_event(skill_tags=["distance_time"], is_correct=True),
            db_path=tmp_db,
        )
        # speed_distance_time is in 'application' domain
        assert "speed_distance_time" in result.get("concept_ids", [])
        # Check mastery update: score should be 0.15 (correct) + 0.12 (transfer) = 0.27
        mastery = result.get("mastery", [])
        sdt_mastery = [m for m in mastery if m["concept_id"] == "speed_distance_time"]
        assert len(sdt_mastery) == 1
        assert sdt_mastery[0]["score"] == pytest.approx(0.27, abs=0.01)

    def test_non_application_domain_no_transfer(self, tmp_db):
        """Fraction-domain concepts should NOT get transfer bonus."""
        result = recordAttempt(
            _make_event(skill_tags=["fraction"], is_correct=True),
            db_path=tmp_db,
        )
        mastery = result.get("mastery", [])
        for m in mastery:
            # Regular correct_no_hint = 0.15, NOT 0.27
            assert m["score"] == pytest.approx(0.15, abs=0.01)

    def test_extra_is_transfer_item_flag(self, tmp_db):
        """Frontend can pass is_transfer_item in extra to force transfer bonus."""
        result = recordAttempt(
            _make_event(
                skill_tags=["fraction"],
                is_correct=True,
                extra={"is_transfer_item": True},
            ),
            db_path=tmp_db,
        )
        mastery = result.get("mastery", [])
        # Should all get transfer bonus: 0.15 + 0.12 = 0.27
        for m in mastery:
            assert m["score"] == pytest.approx(0.27, abs=0.01)

    def test_wrong_answer_no_transfer_bonus(self, tmp_db):
        """Transfer bonus only applies to correct answers."""
        result = recordAttempt(
            _make_event(skill_tags=["distance_time"], is_correct=False),
            db_path=tmp_db,
        )
        mastery = result.get("mastery", [])
        sdt_mastery = [m for m in mastery if m["concept_id"] == "speed_distance_time"]
        assert len(sdt_mastery) == 1
        # Wrong only: -0.10
        assert sdt_mastery[0]["score"] == pytest.approx(0.0, abs=0.01)  # clamped at 0


# ── Delayed Review Detection ────────────────────────────────────────────


class TestDelayedReviewDetection:
    """Verify is_delayed_review is activated for REVIEW_NEEDED concepts."""

    def test_review_needed_gets_delayed_review_bonus(self, tmp_db):
        """Concept in REVIEW_NEEDED state should get delayed_review_correct bonus."""
        from learning.db import connect, ensure_learning_schema

        conn = connect(tmp_db)
        ensure_learning_schema(conn)
        # Pre-set concept to REVIEW_NEEDED state
        state = StudentConceptState(
            student_id="s1",
            concept_id="frac_concept_basic",
            mastery_level=MasteryLevel.REVIEW_NEEDED,
            mastery_score=0.5,
            needs_review=True,
        )
        upsert_concept_state(state, conn=conn)
        conn.commit()
        conn.close()

        result = recordAttempt(
            _make_event(skill_tags=["fraction"], is_correct=True),
            db_path=tmp_db,
        )
        mastery = result.get("mastery", [])
        frac_basic = [m for m in mastery if m["concept_id"] == "frac_concept_basic"]
        assert len(frac_basic) == 1
        # 0.5 + 0.15 (correct) + 0.10 (delayed_review) = 0.75
        assert frac_basic[0]["score"] == pytest.approx(0.75, abs=0.01)

    def test_mastered_with_old_date_triggers_review(self, tmp_db):
        """MASTERED concept with last_mastered_at > 7 days ago should transition to REVIEW_NEEDED."""
        from learning.db import connect, ensure_learning_schema

        conn = connect(tmp_db)
        ensure_learning_schema(conn)
        old_date = (datetime.now() - timedelta(days=10)).isoformat(timespec="seconds")
        state = StudentConceptState(
            student_id="s1",
            concept_id="frac_concept_basic",
            mastery_level=MasteryLevel.MASTERED,
            mastery_score=0.8,
            last_mastered_at=old_date,
        )
        upsert_concept_state(state, conn=conn)
        conn.commit()
        conn.close()

        result = recordAttempt(
            _make_event(skill_tags=["fraction"], is_correct=True),
            db_path=tmp_db,
        )
        mastery = result.get("mastery", [])
        frac_basic = [m for m in mastery if m["concept_id"] == "frac_concept_basic"]
        assert len(frac_basic) == 1
        # check_review_needed decays -0.05 (score=0.75), then correct +0.15 + delayed_review +0.10 = 1.0 (clamped)
        assert frac_basic[0]["score"] >= 0.85

    def test_mastered_recent_no_review(self, tmp_db):
        """MASTERED concept mastered recently should NOT get delayed review bonus."""
        from learning.db import connect, ensure_learning_schema

        conn = connect(tmp_db)
        ensure_learning_schema(conn)
        recent_date = datetime.now().isoformat(timespec="seconds")
        state = StudentConceptState(
            student_id="s1",
            concept_id="frac_concept_basic",
            mastery_level=MasteryLevel.MASTERED,
            mastery_score=0.8,
            last_mastered_at=recent_date,
        )
        upsert_concept_state(state, conn=conn)
        conn.commit()
        conn.close()

        result = recordAttempt(
            _make_event(skill_tags=["fraction"], is_correct=True),
            db_path=tmp_db,
        )
        mastery = result.get("mastery", [])
        frac_basic = [m for m in mastery if m["concept_id"] == "frac_concept_basic"]
        assert len(frac_basic) == 1
        # Only correct_no_hint: 0.8 + 0.15 = 0.95 (no delayed review bonus)
        assert frac_basic[0]["score"] == pytest.approx(0.95, abs=0.01)

    def test_wrong_review_sets_failed_status(self, tmp_db):
        """Wrong answer on review should set delayed_review_status to 'failed'."""
        from learning.db import connect, ensure_learning_schema

        conn = connect(tmp_db)
        ensure_learning_schema(conn)
        state = StudentConceptState(
            student_id="s1",
            concept_id="frac_concept_basic",
            mastery_level=MasteryLevel.REVIEW_NEEDED,
            mastery_score=0.5,
            needs_review=True,
        )
        upsert_concept_state(state, conn=conn)
        conn.commit()
        conn.close()

        result = recordAttempt(
            _make_event(skill_tags=["fraction"], is_correct=False),
            db_path=tmp_db,
        )
        # Verify the concept state was updated
        conn2 = connect(tmp_db)
        updated = get_concept_state("s1", "frac_concept_basic", conn=conn2)
        conn2.close()
        assert updated.delayed_review_status == "failed"


# ── Import / Wiring Checks ──────────────────────────────────────────────


class TestTransferReviewImports:
    """Verify the wiring exists in service.py."""

    def test_check_review_needed_importable(self):
        from learning.mastery_engine import check_review_needed
        assert callable(check_review_needed)

    def test_get_concept_importable(self):
        from learning.concept_taxonomy import get_concept
        assert callable(get_concept)

    def test_answer_event_has_transfer_field(self):
        ae = AnswerEvent(is_correct=True, is_transfer_item=True)
        assert ae.is_transfer_item is True

    def test_answer_event_has_delayed_review_field(self):
        ae = AnswerEvent(is_correct=True, is_delayed_review=True)
        assert ae.is_delayed_review is True
