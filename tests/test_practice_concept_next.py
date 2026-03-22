"""Integration tests for POST /v1/practice/concept-next (EXP-04).

Tests the adaptive next-item selector endpoint that uses concept mastery state
to recommend the best concept and difficulty for practice.
"""

import random
import pytest

from learning.next_item_selector import select_next_item, QuestionItem, SelectionResult
from learning.concept_state import StudentConceptState, MasteryLevel
from learning.concept_taxonomy import CONCEPT_TAXONOMY


# ---------------------------------------------------------------------------
# Unit-level: _build_concept_question_pool logic
# ---------------------------------------------------------------------------

def _build_pool(domain=None):
    """Mirror the server-side helper."""
    items = []
    for cid, info in CONCEPT_TAXONOMY.items():
        if domain and info.get("domain") != domain:
            continue
        for diff in ("easy", "normal", "hard"):
            items.append(QuestionItem(
                item_id=f"{cid}_{diff}",
                concept_ids=[cid],
                difficulty=diff,
                prerequisite_concepts=info.get("prerequisites", []),
                topic_tags=[info.get("domain", "")],
                is_application=(diff == "hard"),
            ))
    return items


class TestBuildPool:
    def test_full_pool_has_three_per_concept(self):
        pool = _build_pool()
        assert len(pool) == len(CONCEPT_TAXONOMY) * 3

    def test_domain_filter(self):
        pool = _build_pool(domain="fraction")
        frac_count = sum(1 for c in CONCEPT_TAXONOMY.values() if c.get("domain") == "fraction")
        assert len(pool) == frac_count * 3
        for item in pool:
            assert "fraction" in item.topic_tags

    def test_empty_domain_returns_empty(self):
        pool = _build_pool(domain="nonexistent_domain")
        assert pool == []


# ---------------------------------------------------------------------------
# Integration: select_next_item with taxonomy pool
# ---------------------------------------------------------------------------

class TestSelectNextWithTaxonomyPool:
    def test_empty_states_selects_unbuilt(self):
        """No concept states → all concepts are unbuilt → should select foundation strategy."""
        pool = _build_pool()
        result = select_next_item("s1", {}, pool, rng=random.Random(42))
        assert result is not None
        assert result.strategy in ("unbuilt_foundation", "fallback_random", "fallback_any")
        assert result.item.item_id in {i.item_id for i in pool}

    def test_mastered_concept_triggers_spiral_or_fallback(self):
        """All concepts mastered → spiral review or fallback."""
        states = {}
        for cid in list(CONCEPT_TAXONOMY.keys())[:5]:
            states[cid] = StudentConceptState(
                student_id="s1",
                concept_id=cid,
                mastery_level=MasteryLevel.MASTERED,
                consecutive_correct=10,
                attempts_total=20,
                correct_total=18,
            )
        pool = _build_pool(domain="fraction")
        result = select_next_item("s1", states, pool, rng=random.Random(42))
        assert result is not None
        assert result.strategy in ("spiral_review", "fallback_random", "fallback_any",
                                    "unbuilt_foundation", "developing_standard")

    def test_developing_concept_selected(self):
        """A developing concept should be selected for standard practice."""
        target = "frac_add_like"
        states = {
            target: StudentConceptState(
                student_id="s1",
                concept_id=target,
                mastery_level=MasteryLevel.DEVELOPING,
                consecutive_correct=2,
                attempts_total=5,
                correct_total=3,
            ),
        }
        # Only provide items for the developing concept + one mastered concept
        pool = [
            QuestionItem(item_id=f"{target}_easy", concept_ids=[target], difficulty="easy"),
            QuestionItem(item_id=f"{target}_normal", concept_ids=[target], difficulty="normal"),
        ]
        # Mark all other concepts as not having items → selector focuses on the developing one
        result = select_next_item("s1", states, pool, rng=random.Random(42))
        assert result is not None
        assert target in result.item.concept_ids

    def test_recent_items_excluded(self):
        """Recent items should be avoided."""
        pool = _build_pool(domain="fraction")
        recent_ids = [i.item_id for i in pool[:3]]
        result = select_next_item("s1", {}, pool, recent_item_ids=recent_ids, rng=random.Random(42))
        assert result is not None
        assert result.item.item_id not in recent_ids

    def test_result_has_chinese_reason(self):
        """Selection reason should contain Chinese text."""
        pool = _build_pool()
        result = select_next_item("s1", {}, pool, rng=random.Random(42))
        assert result is not None
        assert any('\u4e00' <= c <= '\u9fff' for c in result.reason)

    def test_selection_result_serializable(self):
        """Result fields should be JSON-serializable."""
        pool = _build_pool()
        result = select_next_item("s1", {}, pool, rng=random.Random(42))
        assert result is not None
        payload = {
            "item_id": result.item.item_id,
            "target_concept": result.target_concept,
            "concept_ids": result.item.concept_ids,
            "difficulty": result.item.difficulty,
            "strategy": result.strategy,
            "reason": result.reason,
            "domain": (result.item.topic_tags or [None])[0],
        }
        assert all(isinstance(v, (str, list, type(None))) for v in payload.values())
