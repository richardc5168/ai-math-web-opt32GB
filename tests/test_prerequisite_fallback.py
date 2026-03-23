"""R21/EXP-S2-02: Prerequisite fallback tests.

Tests for prerequisite regression detection and transitive prerequisite
fallback in remediation.
"""

import random
from unittest.mock import patch
from learning.concept_state import MasteryLevel, StudentConceptState
from learning.next_item_selector import (
    QuestionItem,
    SelectionResult,
    detect_prerequisite_regression,
    select_next_item,
    select_remediation_item,
)


def _state(cid, level, score=0.0, last_seen=None, attempts=5):
    return StudentConceptState(
        student_id="s1",
        concept_id=cid,
        mastery_level=level,
        mastery_score=score,
        attempts_total=attempts,
        last_seen_at=last_seen,
    )


def _item(cid, difficulty="normal"):
    return QuestionItem(item_id=f"q_{cid}_{difficulty}", concept_ids=[cid], difficulty=difficulty)


# --- detect_prerequisite_regression ---

class TestPrerequisiteRegressionDetection:
    @patch("learning.next_item_selector.get_prerequisites")
    def test_detects_regressed_prerequisite(self, mock_prereqs):
        """When a prerequisite has REVIEW_NEEDED, detect it."""
        mock_prereqs.side_effect = lambda cid: {"B": ["A"]}.get(cid, [])
        states = {
            "A": _state("A", MasteryLevel.REVIEW_NEEDED, score=0.5, last_seen="2026-03-10"),
            "B": _state("B", MasteryLevel.DEVELOPING, score=0.3),
        }
        result = detect_prerequisite_regression(["B"], states)
        assert result == ["A"]

    @patch("learning.next_item_selector.get_prerequisites")
    def test_no_regression_when_prereqs_healthy(self, mock_prereqs):
        mock_prereqs.side_effect = lambda cid: {"B": ["A"]}.get(cid, [])
        states = {
            "A": _state("A", MasteryLevel.MASTERED, score=0.9),
            "B": _state("B", MasteryLevel.DEVELOPING, score=0.3),
        }
        result = detect_prerequisite_regression(["B"], states)
        assert result == []

    @patch("learning.next_item_selector.get_prerequisites")
    def test_multiple_regressed_sorted_stalest(self, mock_prereqs):
        mock_prereqs.side_effect = lambda cid: {"C": ["A", "B"]}.get(cid, [])
        states = {
            "A": _state("A", MasteryLevel.REVIEW_NEEDED, last_seen="2026-03-20"),
            "B": _state("B", MasteryLevel.REVIEW_NEEDED, last_seen="2026-03-10"),
            "C": _state("C", MasteryLevel.DEVELOPING, score=0.3),
        }
        result = detect_prerequisite_regression(["C"], states)
        assert result[0] == "B"  # stalest first

    @patch("learning.next_item_selector.get_prerequisites")
    def test_no_concepts_returns_empty(self, mock_prereqs):
        mock_prereqs.return_value = []
        result = detect_prerequisite_regression([], {})
        assert result == []


# --- Prerequisite regression integrated into select_next_item ---

class TestPrerequisiteRegressionInSelector:
    @patch("learning.next_item_selector.get_prerequisites")
    def test_regression_takes_priority_over_developing(self, mock_prereqs):
        """When prerequisite regressed, fix it before advancing."""
        mock_prereqs.side_effect = lambda cid: {"B": ["A"]}.get(cid, [])
        states = {
            "A": _state("A", MasteryLevel.REVIEW_NEEDED, score=0.5, last_seen="2026-03-10"),
            "B": _state("B", MasteryLevel.DEVELOPING, score=0.4),
        }
        items = [_item("A"), _item("B")]
        result = select_next_item("s1", states, items, rng=random.Random(42))
        assert result.target_concept == "A"
        assert result.strategy == "prerequisite_regression"


# --- Transitive prerequisite remediation ---

class TestTransitiveRemediation:
    @patch("learning.next_item_selector.get_all_prerequisites")
    def test_remediation_uses_transitive_prereqs(self, mock_all):
        """When stuck on C, and no easy C or direct prereq B items,
        fall back to transitive prereq A."""
        mock_all.return_value = ["B", "A"]  # B is direct, A is transitive
        states = {
            "A": _state("A", MasteryLevel.DEVELOPING, score=0.2),
            "B": _state("B", MasteryLevel.DEVELOPING, score=0.3),
            "C": _state("C", MasteryLevel.DEVELOPING, score=0.1),
        }
        # Only A items available (no easy C, no B items)
        items = [_item("A", "easy")]
        result = select_remediation_item(
            "C", states, items, rng=random.Random(0)
        )
        assert result is not None
        assert result.target_concept == "A"
        assert result.strategy == "remediation_prerequisite"

    @patch("learning.next_item_selector.get_all_prerequisites")
    def test_remediation_weakest_prereq_first(self, mock_all):
        """Among transitive prereqs, pick the one with lowest score."""
        mock_all.return_value = ["B", "A"]
        states = {
            "A": _state("A", MasteryLevel.DEVELOPING, score=0.1),  # weakest
            "B": _state("B", MasteryLevel.DEVELOPING, score=0.5),
        }
        items = [_item("A", "easy"), _item("B", "easy")]
        result = select_remediation_item(
            "C", states, items, rng=random.Random(0)
        )
        assert result.target_concept == "A"  # weakest first

    @patch("learning.next_item_selector.get_all_prerequisites")
    def test_remediation_simpler_still_preferred(self, mock_all):
        """Simpler isomorphic (same concept easy) still chosen first."""
        mock_all.return_value = ["A"]
        states = {}
        items = [
            QuestionItem(item_id="q_C_easy", concept_ids=["C"], difficulty="easy"),
            _item("A", "easy"),
        ]
        result = select_remediation_item(
            "C", states, items, rng=random.Random(0)
        )
        assert result.target_concept == "C"
        assert result.strategy == "remediation_simpler"

    @patch("learning.next_item_selector.get_all_prerequisites")
    def test_remediation_no_items_returns_none(self, mock_all):
        mock_all.return_value = []
        result = select_remediation_item("C", {}, [], rng=random.Random(0))
        assert result is None
