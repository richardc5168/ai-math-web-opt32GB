"""R20/EXP-S2-01: Adaptive selector priority refinement tests.

Verify score-aware concept selection: closest-to-promotion for developing,
stalest-first for review, highest-score for approaching.
"""

import random
from learning.concept_state import MasteryLevel, StudentConceptState
from learning.next_item_selector import (
    QuestionItem,
    select_next_item,
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


# --- Developing: closest-to-promotion first ---

class TestDevelopingPriority:
    def test_picks_highest_score_concept(self):
        """Among multiple developing concepts, pick the one closest to promotion."""
        states = {
            "A": _state("A", MasteryLevel.DEVELOPING, score=0.25),
            "B": _state("B", MasteryLevel.DEVELOPING, score=0.45),  # closest
            "C": _state("C", MasteryLevel.DEVELOPING, score=0.10),
        }
        items = [_item("A"), _item("B"), _item("C")]
        for seed in range(20):
            result = select_next_item("s1", states, items, rng=random.Random(seed))
            assert result is not None
            assert result.target_concept == "B", f"seed={seed}: got {result.target_concept}"

    def test_single_developing_always_picked(self):
        states = {"X": _state("X", MasteryLevel.DEVELOPING, score=0.30)}
        items = [_item("X")]
        result = select_next_item("s1", states, items, rng=random.Random(0))
        assert result.target_concept == "X"
        assert result.strategy == "developing_standard"

    def test_tied_scores_deterministic(self):
        """When scores are tied, max() picks consistently (first in list)."""
        states = {
            "A": _state("A", MasteryLevel.DEVELOPING, score=0.30),
            "B": _state("B", MasteryLevel.DEVELOPING, score=0.30),
        }
        items = [_item("A"), _item("B")]
        results = set()
        for seed in range(10):
            r = select_next_item("s1", states, items, rng=random.Random(seed))
            results.add(r.target_concept)
        # With tied scores, max() should consistently pick one
        assert len(results) == 1


# --- Review: stalest-first ---

class TestReviewPriority:
    def test_picks_stalest_concept(self):
        """Among review-needed concepts, pick the one not seen longest."""
        states = {
            "A": _state("A", MasteryLevel.REVIEW_NEEDED, score=0.7, last_seen="2026-03-20"),
            "B": _state("B", MasteryLevel.REVIEW_NEEDED, score=0.5, last_seen="2026-03-10"),  # stalest
            "C": _state("C", MasteryLevel.REVIEW_NEEDED, score=0.6, last_seen="2026-03-22"),
        }
        items = [_item("A"), _item("B"), _item("C")]
        for seed in range(20):
            result = select_next_item("s1", states, items, rng=random.Random(seed))
            assert result.target_concept == "B", f"seed={seed}: got {result.target_concept}"

    def test_none_last_seen_treated_as_stalest(self):
        """Concept with no last_seen_at should be considered most stale."""
        states = {
            "A": _state("A", MasteryLevel.REVIEW_NEEDED, last_seen="2026-03-22"),
            "B": _state("B", MasteryLevel.REVIEW_NEEDED, last_seen=None),  # stalest
        }
        items = [_item("A"), _item("B")]
        result = select_next_item("s1", states, items, rng=random.Random(0))
        assert result.target_concept == "B"

    def test_review_before_developing(self):
        """Review-needed concepts are prioritized over developing."""
        states = {
            "R": _state("R", MasteryLevel.REVIEW_NEEDED, score=0.5, last_seen="2026-03-10"),
            "D": _state("D", MasteryLevel.DEVELOPING, score=0.45),
        }
        items = [_item("R"), _item("D")]
        result = select_next_item("s1", states, items, rng=random.Random(42))
        assert result.target_concept == "R"
        assert result.strategy == "spaced_review"


# --- Approaching: highest-score first ---

class TestApproachingPriority:
    def test_picks_highest_score_approaching(self):
        """Among approaching concepts, pick the one closest to MASTERED."""
        states = {
            "A": _state("A", MasteryLevel.APPROACHING_MASTERY, score=0.65),
            "B": _state("B", MasteryLevel.APPROACHING_MASTERY, score=0.80),  # closest
            "C": _state("C", MasteryLevel.APPROACHING_MASTERY, score=0.55),
        }
        items = [_item("A"), _item("B"), _item("C")]
        for seed in range(20):
            result = select_next_item("s1", states, items, rng=random.Random(seed))
            assert result.target_concept == "B", f"seed={seed}: got {result.target_concept}"

    def test_approaching_after_developing(self):
        """Developing is prioritized over approaching."""
        states = {
            "D": _state("D", MasteryLevel.DEVELOPING, score=0.20),
            "A": _state("A", MasteryLevel.APPROACHING_MASTERY, score=0.80),
        }
        items = [_item("D"), _item("A")]
        result = select_next_item("s1", states, items, rng=random.Random(0))
        assert result.target_concept == "D"
        assert result.strategy == "developing_standard"


# --- Mixed scenario ---

class TestMixedPriority:
    def test_unbuilt_still_highest_priority(self):
        """Unbuilt beats review/developing/approaching in priority."""
        states = {
            "R": _state("R", MasteryLevel.REVIEW_NEEDED, score=0.5),
            "D": _state("D", MasteryLevel.DEVELOPING, score=0.4),
            "A": _state("A", MasteryLevel.APPROACHING_MASTERY, score=0.8),
            # "U" not in states → treated as UNBUILT
        }
        items = [_item("R"), _item("D"), _item("A"), _item("U")]
        result = select_next_item("s1", states, items, rng=random.Random(42))
        assert result.target_concept == "U"
        assert result.strategy == "unbuilt_foundation"

    def test_no_state_concept_treated_as_unbuilt(self):
        """Concept not in concept_states dict is treated as UNBUILT."""
        states = {"X": _state("X", MasteryLevel.MASTERED, score=1.0)}
        items = [_item("X"), _item("Y")]  # Y has no state
        result = select_next_item("s1", states, items, rng=random.Random(0))
        assert result.target_concept == "Y"
