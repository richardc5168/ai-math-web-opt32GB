"""R28/EXP-P3-03: Tests for zone_progress wiring in recordAttempt response."""

from __future__ import annotations

import os
import tempfile

import pytest

from learning.service import recordAttempt
from learning.concept_state import upsert_concept_state, MasteryLevel


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


class TestZoneProgressWiring:
    """Verify zone_progress appears in recordAttempt response."""

    def test_zone_progress_key_in_response(self, tmp_db):
        result = recordAttempt(_make_event(), db_path=tmp_db)
        assert "zone_progress" in result

    def test_zone_progress_is_list(self, tmp_db):
        result = recordAttempt(_make_event(), db_path=tmp_db)
        assert isinstance(result["zone_progress"], list)

    def test_zone_progress_has_expected_keys(self, tmp_db):
        result = recordAttempt(_make_event(), db_path=tmp_db)
        if result["zone_progress"]:
            zp = result["zone_progress"][0]
            expected_keys = {"zone_id", "display_name_zh", "total_concepts", "mastered_count", "progress_pct", "is_complete"}
            assert set(zp.keys()) == expected_keys

    def test_zone_progress_empty_when_no_concepts(self, tmp_db):
        # Event with skill_tags that don't resolve to any concept_ids
        result = recordAttempt(
            _make_event(skill_tags=["nonexistent_skill_xyz"]),
            db_path=tmp_db
        )
        assert result["zone_progress"] == []

    def test_zone_progress_has_zones(self, tmp_db):
        # After an attempt, zone progress should have at least one zone
        result = recordAttempt(_make_event(), db_path=tmp_db)
        if result["concept_ids"]:
            assert len(result["zone_progress"]) > 0

    def test_zone_progress_pct_bounded(self, tmp_db):
        result = recordAttempt(_make_event(), db_path=tmp_db)
        for zp in result["zone_progress"]:
            assert 0 <= zp["progress_pct"] <= 100

    def test_zone_progress_counts_non_negative(self, tmp_db):
        result = recordAttempt(_make_event(), db_path=tmp_db)
        for zp in result["zone_progress"]:
            assert zp["total_concepts"] >= 0
            assert zp["mastered_count"] >= 0


class TestZoneProgressImport:
    """Verify compute_zone_progress is importable from service."""

    def test_import_compute_zone_progress(self):
        from learning.gamification import compute_zone_progress
        assert callable(compute_zone_progress)

    def test_service_imports_compute_zone_progress(self):
        import learning.service as svc
        assert hasattr(svc, "compute_zone_progress")
