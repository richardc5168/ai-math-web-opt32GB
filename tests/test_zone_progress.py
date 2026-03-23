"""Tests for EXP-S3-01: Domain-based zone progression.

Verifies that compute_zone_progress() correctly aggregates per-concept
mastery into domain-level zone progress metrics.
"""

from __future__ import annotations

import pytest

from learning.concept_state import MasteryLevel, StudentConceptState
from learning.concept_taxonomy import list_domains, concepts_by_domain
from learning.gamification import (
    ZoneProgress,
    compute_zone_progress,
    ZONE_DISPLAY_NAMES,
    GamificationState,
    gamification_to_dict,
)


def _state(concept_id: str, level: MasteryLevel) -> StudentConceptState:
    return StudentConceptState(
        student_id="s1",
        concept_id=concept_id,
        mastery_level=level,
        mastery_score=0.5,
    )


class TestComputeZoneProgress:
    """EXP-S3-01: Domain-based zone progression tests."""

    def test_empty_states_returns_all_domains(self):
        """Even with no student data, all domains should appear."""
        result = compute_zone_progress([])
        domain_ids = {z.zone_id for z in result}
        for d in list_domains():
            assert d in domain_ids

    def test_all_unbuilt(self):
        """With no states, all concepts should be unbuilt."""
        result = compute_zone_progress([])
        for z in result:
            assert z.unbuilt_count == z.total_concepts
            assert z.mastered_count == 0
            assert z.approaching_count == 0
            assert z.developing_count == 0
            assert z.progress_pct == 0.0
            assert z.is_complete is False

    def test_single_mastered_concept(self):
        """Mastering one concept in a domain updates counts."""
        states = [_state("four_ops_order", MasteryLevel.MASTERED)]
        result = compute_zone_progress(states)
        arith = next(z for z in result if z.zone_id == "arithmetic")
        assert arith.mastered_count == 1
        assert arith.unbuilt_count == 1  # four_ops_mixed still unbuilt
        assert arith.total_concepts == 2
        assert arith.is_complete is False

    def test_domain_complete(self):
        """Mastering all concepts in a domain marks zone complete."""
        cids = concepts_by_domain("arithmetic")
        states = [_state(cid, MasteryLevel.MASTERED) for cid in cids]
        result = compute_zone_progress(states)
        arith = next(z for z in result if z.zone_id == "arithmetic")
        assert arith.is_complete is True
        assert arith.progress_pct == 100.0
        assert arith.mastered_count == arith.total_concepts

    def test_approaching_counts(self):
        """APPROACHING_MASTERY counted separately from MASTERED."""
        states = [_state("four_ops_order", MasteryLevel.APPROACHING_MASTERY)]
        result = compute_zone_progress(states)
        arith = next(z for z in result if z.zone_id == "arithmetic")
        assert arith.approaching_count == 1
        assert arith.mastered_count == 0
        assert arith.is_complete is False

    def test_developing_counts(self):
        """DEVELOPING counted as developing."""
        states = [_state("four_ops_order", MasteryLevel.DEVELOPING)]
        result = compute_zone_progress(states)
        arith = next(z for z in result if z.zone_id == "arithmetic")
        assert arith.developing_count == 1
        assert arith.mastered_count == 0

    def test_review_needed_counts_as_unbuilt(self):
        """REVIEW_NEEDED should count as unbuilt (needs work)."""
        states = [_state("four_ops_order", MasteryLevel.REVIEW_NEEDED)]
        result = compute_zone_progress(states)
        arith = next(z for z in result if z.zone_id == "arithmetic")
        assert arith.unbuilt_count == 2  # both counted as unbuilt

    def test_progress_pct_weighted(self):
        """Progress uses weighted formula: mastered=100, approaching=70, developing=30."""
        cids = concepts_by_domain("arithmetic")  # 2 concepts
        states = [
            _state(cids[0], MasteryLevel.MASTERED),       # 100
            _state(cids[1], MasteryLevel.APPROACHING_MASTERY),  # 70
        ]
        result = compute_zone_progress(states)
        arith = next(z for z in result if z.zone_id == "arithmetic")
        expected = round((100.0 + 70.0) / 2, 1)
        assert arith.progress_pct == expected

    def test_display_name_zh(self):
        """Each zone has a Chinese display name."""
        result = compute_zone_progress([])
        for z in result:
            assert z.display_name_zh
            assert z.display_name_zh == ZONE_DISPLAY_NAMES.get(z.zone_id, z.zone_id)

    def test_zone_display_names_cover_all_domains(self):
        """Every domain should have a display name defined."""
        for domain in list_domains():
            assert domain in ZONE_DISPLAY_NAMES, f"Missing display name for {domain}"

    def test_mixed_domains(self):
        """States spanning multiple domains produce correct zone stats."""
        states = [
            _state("four_ops_order", MasteryLevel.MASTERED),
            _state("decimal_basic", MasteryLevel.DEVELOPING),
            _state("area_basic", MasteryLevel.APPROACHING_MASTERY),
        ]
        result = compute_zone_progress(states)
        arith = next(z for z in result if z.zone_id == "arithmetic")
        decimal = next(z for z in result if z.zone_id == "decimal")
        geom = next(z for z in result if z.zone_id == "geometry")
        assert arith.mastered_count == 1
        assert decimal.developing_count == 1
        assert geom.approaching_count == 1

    def test_gamification_to_dict_includes_zones(self):
        """gamification_to_dict() should serialize zone_progress."""
        zones = [ZoneProgress(zone_id="arithmetic", display_name_zh="四則運算區",
                              total_concepts=2, mastered_count=1, progress_pct=50.0)]
        gs = GamificationState(zone_progress=zones)
        d = gamification_to_dict(gs)
        assert "zone_progress" in d
        assert len(d["zone_progress"]) == 1
        zd = d["zone_progress"][0]
        assert zd["zone_id"] == "arithmetic"
        assert zd["display_name_zh"] == "四則運算區"
        assert zd["mastered_count"] == 1
        assert zd["progress_pct"] == 50.0
