"""Tests for the next-item selector."""

import random

import pytest

from learning.concept_state import MasteryLevel, StudentConceptState
from learning.next_item_selector import (
    QuestionItem,
    SelectionResult,
    select_next_item,
    select_remediation_item,
)


def _state(concept_id: str, level: MasteryLevel, **kw) -> StudentConceptState:
    return StudentConceptState(student_id="s1", concept_id=concept_id, mastery_level=level, **kw)


def _item(item_id: str, concept_ids: list, difficulty="normal", **kw) -> QuestionItem:
    return QuestionItem(item_id=item_id, concept_ids=concept_ids, difficulty=difficulty, **kw)


# --- Basic Selection ---

def test_returns_none_for_empty_items():
    result = select_next_item("s1", {}, [])
    assert result is None


def test_selects_item_from_pool():
    items = [_item("q1", ["c1"]), _item("q2", ["c2"])]
    result = select_next_item("s1", {}, items, rng=random.Random(42))
    assert result is not None
    assert result.item in items


# --- Unbuilt Strategy ---

def test_unbuilt_prefers_easy_items():
    states = {}  # no states → all concepts are unbuilt
    items = [
        _item("q1", ["c1"], difficulty="hard"),
        _item("q2", ["c1"], difficulty="easy"),
        _item("q3", ["c1"], difficulty="normal"),
    ]

    # Run multiple times to ensure easy is preferred
    easy_count = 0
    for seed in range(20):
        result = select_next_item("s1", states, items, rng=random.Random(seed))
        if result.item.difficulty == "easy":
            easy_count += 1

    assert easy_count >= 15, f"Easy items should be strongly preferred, got {easy_count}/20"


def test_unbuilt_avoids_application_items():
    states = {}
    items = [
        _item("q1", ["c1"], difficulty="easy", is_application=True),
        _item("q2", ["c1"], difficulty="easy", is_application=False),
    ]

    non_app_count = 0
    for seed in range(20):
        result = select_next_item("s1", states, items, rng=random.Random(seed))
        if not result.item.is_application:
            non_app_count += 1

    assert non_app_count >= 15


# --- Developing Strategy ---

def test_developing_selects_standard_items():
    states = {"c1": _state("c1", MasteryLevel.DEVELOPING)}
    items = [
        _item("q1", ["c1"], difficulty="easy"),
        _item("q2", ["c1"], difficulty="normal"),
        _item("q3", ["c1"], difficulty="hard"),
    ]

    # Should avoid hard items
    hard_count = 0
    for seed in range(30):
        result = select_next_item("s1", states, items, rng=random.Random(seed))
        if result.item.difficulty == "hard":
            hard_count += 1

    assert hard_count < 5, "Hard items should be rare for developing concepts"


# --- Approaching Mastery Strategy ---

def test_approaching_sometimes_selects_variants():
    states = {"c1": _state("c1", MasteryLevel.APPROACHING_MASTERY)}
    items = [
        _item("q1", ["c1"], format="numeric"),
        _item("q2", ["c1"], format="word_problem"),
        _item("q3", ["c1"], format="application"),
    ]

    variant_count = 0
    for seed in range(50):
        result = select_next_item("s1", states, items, rng=random.Random(seed))
        if result.strategy == "approaching_variant":
            variant_count += 1

    # Should get some variants (30% probability)
    assert variant_count > 5, f"Expected some variants, got {variant_count}/50"


# --- Review Strategy ---

def test_review_needed_gets_priority():
    states = {
        "c1": _state("c1", MasteryLevel.MASTERED),
        "c2": _state("c2", MasteryLevel.REVIEW_NEEDED),
    }
    items = [
        _item("q1", ["c1"]),
        _item("q2", ["c2"]),
    ]

    review_count = 0
    for seed in range(20):
        result = select_next_item("s1", states, items, rng=random.Random(seed))
        if result.strategy == "spaced_review":
            review_count += 1

    assert review_count >= 15, "Review-needed concepts should get priority"


# --- Spiral Review ---

def test_mastered_gets_sparse_review():
    states = {"c1": _state("c1", MasteryLevel.MASTERED)}
    items = [_item("q1", ["c1"])]

    review_count = 0
    for seed in range(100):
        result = select_next_item("s1", states, items, rng=random.Random(seed))
        if result.strategy == "spiral_review":
            review_count += 1

    # ~15% should be spiral review (with fallback for remaining)
    assert 5 < review_count < 40, f"Expected ~15% spiral review, got {review_count}/100"


# --- Avoids Recent Items ---

def test_avoids_recently_shown_items():
    states = {}
    items = [
        _item("q1", ["c1"], difficulty="easy"),
        _item("q2", ["c1"], difficulty="easy"),
    ]

    result = select_next_item("s1", states, items, recent_item_ids=["q1"], rng=random.Random(42))
    assert result.item.item_id == "q2"


# --- Selection Reason ---

def test_selection_result_has_reason_and_strategy():
    states = {"c1": _state("c1", MasteryLevel.DEVELOPING)}
    items = [_item("q1", ["c1"])]

    result = select_next_item("s1", states, items, rng=random.Random(42))
    assert result.reason  # non-empty
    assert result.strategy  # non-empty
    assert result.target_concept == "c1"


# --- Remediation Selector ---

def test_remediation_picks_simpler_item():
    states = {"c1": _state("c1", MasteryLevel.DEVELOPING)}
    items = [
        _item("q1", ["c1"], difficulty="normal"),
        _item("q2", ["c1"], difficulty="easy"),
    ]

    result = select_remediation_item("c1", states, items, rng=random.Random(42))
    assert result is not None
    assert result.item.difficulty == "easy"
    assert result.strategy == "remediation_simpler"


def test_remediation_falls_back_to_prerequisite():
    # No easy items for c1, but prerequisite items available
    # frac_add_unlike has prerequisite frac_add_like in taxonomy
    states = {"frac_add_unlike": _state("frac_add_unlike", MasteryLevel.DEVELOPING)}
    items = [
        _item("q1", ["frac_add_unlike"], difficulty="normal"),
        _item("q2", ["frac_add_like"], difficulty="easy"),
    ]

    result = select_remediation_item("frac_add_unlike", states, items, rng=random.Random(42))
    assert result is not None
    assert result.strategy == "remediation_prerequisite"
    assert result.target_concept == "frac_add_like"


def test_remediation_returns_none_when_no_options():
    result = select_remediation_item("c1", {}, [], rng=random.Random(42))
    assert result is None
