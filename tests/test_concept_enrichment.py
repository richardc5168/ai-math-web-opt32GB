"""Tests for EXP-01: concept_taxonomy wiring into recordAttempt.

Verifies that concept_ids_json is populated when skill_tags or topic
match entries in TOPIC_TAG_TO_CONCEPT.
"""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from learning.service import recordAttempt
from learning.db import connect, ensure_learning_schema


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
        "timestamp": "2026-03-22T12:00:00+08:00",
        "is_correct": True,
        "answer_raw": "42",
        "skill_tags": ["fraction"],
    }
    base.update(overrides)
    return base


class TestConceptEnrichment:
    """EXP-01: concept_ids should be populated from skill_tags and topic."""

    def test_skill_tag_resolves_to_concept_ids(self, tmp_db):
        """skill_tags=['fraction'] should resolve to fraction concepts."""
        result = recordAttempt(_make_event(skill_tags=["fraction"]), db_path=tmp_db)
        assert result["ok"]
        assert "concept_ids" in result
        assert len(result["concept_ids"]) > 0
        # 'fraction' maps to frac_multiply, frac_concept_basic, frac_word_problem
        assert "frac_concept_basic" in result["concept_ids"]

    def test_concept_ids_persisted_in_db(self, tmp_db):
        """concept_ids_json column should be written to DB."""
        result = recordAttempt(_make_event(skill_tags=["decimal"]), db_path=tmp_db)
        attempt_id = result["attempt_id"]

        conn = connect(tmp_db)
        try:
            row = conn.execute(
                "SELECT concept_ids_json FROM la_attempt_events WHERE rowid = ?",
                (attempt_id,),
            ).fetchone()
            assert row is not None
            stored_ids = json.loads(row[0])
            assert isinstance(stored_ids, list)
            assert len(stored_ids) > 0
            assert "decimal_basic" in stored_ids
        finally:
            conn.close()

    def test_topic_also_contributes_to_concept_ids(self, tmp_db):
        """topic field should also be used for concept resolution."""
        result = recordAttempt(
            _make_event(skill_tags=["unknown"], topic="volume"),
            db_path=tmp_db,
        )
        assert "volume_cube" in result["concept_ids"]

    def test_concept_points_in_extra(self, tmp_db):
        """concept_points in extra dict should resolve to concept_ids."""
        result = recordAttempt(
            _make_event(
                skill_tags=["unknown"],
                extra={"concept_points": ["分數乘法：分子乘分子、分母乘分母"]},
            ),
            db_path=tmp_db,
        )
        assert "frac_multiply" in result["concept_ids"]

    def test_unknown_tags_produce_empty_concept_ids(self, tmp_db):
        """Unknown skill_tags should produce an empty concept_ids list."""
        result = recordAttempt(
            _make_event(skill_tags=["unknown_xyz_tag"]),
            db_path=tmp_db,
        )
        assert result["concept_ids"] == []

    def test_empty_concept_ids_default_column_value(self, tmp_db):
        """When no concepts resolve, DB column should retain default '[]'."""
        result = recordAttempt(
            _make_event(skill_tags=["unknown_xyz_tag"]),
            db_path=tmp_db,
        )
        conn = connect(tmp_db)
        try:
            row = conn.execute(
                "SELECT concept_ids_json FROM la_attempt_events WHERE rowid = ?",
                (result["attempt_id"],),
            ).fetchone()
            stored = json.loads(row[0])
            assert stored == []
        finally:
            conn.close()

    def test_multiple_tags_combine_concepts(self, tmp_db):
        """Multiple skill_tags should combine their concept mappings."""
        result = recordAttempt(
            _make_event(skill_tags=["fraction", "decimal"]),
            db_path=tmp_db,
        )
        ids = result["concept_ids"]
        assert "frac_concept_basic" in ids
        assert "decimal_basic" in ids

    def test_deduplication(self, tmp_db):
        """Duplicate concept_ids from overlapping tags should be deduplicated."""
        result = recordAttempt(
            _make_event(skill_tags=["fraction", "fractions"]),
            db_path=tmp_db,
        )
        ids = result["concept_ids"]
        # Both 'fraction' and 'fractions' map to frac_concept_basic — should appear once
        assert ids.count("frac_concept_basic") == 1
