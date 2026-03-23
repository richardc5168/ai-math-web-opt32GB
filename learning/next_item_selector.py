"""Next-Item Selector — Adaptive question selection based on mastery state.

Selects the next question based on the student's concept mastery states,
available items, and concept prerequisites. Returns (item, selection_reason).

Strategies by mastery level:
- mastered: sparse spiral review, cross-concept items, variants
- approaching_mastery: same concept different representation, some application
- developing: standard items, simplified items
- unbuilt: prerequisite items first, simplest possible items
- review_needed: treated like approaching_mastery

Usage:
    from learning.next_item_selector import select_next_item
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .concept_state import MasteryLevel, StudentConceptState
from .concept_taxonomy import (
    CONCEPT_TAXONOMY,
    get_all_prerequisites,
    get_prerequisites,
    resolve_concept_ids,
)
from .mastery_config import MASTERY_CONFIG


# ---------------------------------------------------------------------------
# Question Item (lightweight view of a question for selection)
# ---------------------------------------------------------------------------

@dataclass
class QuestionItem:
    item_id: str
    concept_ids: List[str]
    difficulty: str = "normal"        # easy / normal / hard
    format: str = "numeric"           # numeric / word_problem / application / mixed
    variant_group: Optional[str] = None
    prerequisite_concepts: Optional[List[str]] = None
    remediation_target: Optional[str] = None  # concept_id this remediates
    topic_tags: Optional[List[str]] = None
    is_application: bool = False


# ---------------------------------------------------------------------------
# Selection Result
# ---------------------------------------------------------------------------

@dataclass
class SelectionResult:
    item: QuestionItem
    reason: str                      # human-readable reason for debug/reports
    strategy: str                    # machine-readable: spiral_review / same_concept_variant / ...
    target_concept: Optional[str] = None  # the concept being targeted


# ---------------------------------------------------------------------------
# Selector
# ---------------------------------------------------------------------------

def select_next_item(
    student_id: str,
    concept_states: Dict[str, StudentConceptState],
    available_items: List[QuestionItem],
    *,
    config: Optional[Dict[str, Any]] = None,
    recent_item_ids: Optional[List[str]] = None,
    rng: Optional[random.Random] = None,
) -> Optional[SelectionResult]:
    """Select the next item for a student.

    Args:
        student_id: Student identifier
        concept_states: {concept_id: StudentConceptState} — current student mastery
        available_items: Pool of items to select from
        config: Override mastery config
        recent_item_ids: Item IDs recently shown (to avoid repetition)
        rng: Random instance for deterministic testing

    Returns:
        SelectionResult with item and reason, or None if no items available.
    """
    if not available_items:
        return None

    cfg = config or MASTERY_CONFIG
    selector_cfg = cfg.get("selector", {})
    rng = rng or random.Random()
    recent = set(recent_item_ids or [])

    # --- Classify concepts by mastery level ---
    unbuilt: List[str] = []
    developing: List[str] = []
    approaching: List[str] = []
    mastered: List[str] = []
    review_needed: List[str] = []

    # Include all concepts that appear in available items
    item_concepts = set()
    for item in available_items:
        item_concepts.update(item.concept_ids)

    for concept_id in item_concepts:
        state = concept_states.get(concept_id)
        if state is None:
            unbuilt.append(concept_id)
            continue
        level = state.mastery_level
        if level == MasteryLevel.UNBUILT:
            unbuilt.append(concept_id)
        elif level == MasteryLevel.DEVELOPING:
            developing.append(concept_id)
        elif level == MasteryLevel.APPROACHING_MASTERY:
            approaching.append(concept_id)
        elif level == MasteryLevel.MASTERED:
            mastered.append(concept_id)
        elif level == MasteryLevel.REVIEW_NEEDED:
            review_needed.append(concept_id)

    # --- Strategy Priority ---

    # 0. Prerequisite regression: a prerequisite decayed while student advanced
    regressed = detect_prerequisite_regression(
        developing + approaching, concept_states
    )
    if regressed:
        result = _select_for_review(regressed, concept_states, available_items, recent, rng,
                                     strategy_override="prerequisite_regression")
        if result:
            return result

    # 1. Unbuilt concepts: find prerequisites first
    if unbuilt and selector_cfg.get("unbuilt_prerequisite_first", True):
        result = _select_for_unbuilt(unbuilt, concept_states, available_items, recent, rng)
        if result:
            return result

    # 2. Review needed concepts
    if review_needed:
        result = _select_for_review(review_needed, concept_states, available_items, recent, rng)
        if result:
            return result

    # 3. Developing concepts (priority focus area)
    if developing:
        result = _select_for_developing(developing, concept_states, available_items, recent, rng)
        if result:
            return result

    # 4. Approaching mastery
    if approaching:
        result = _select_for_approaching(approaching, concept_states, available_items, recent, rng, selector_cfg)
        if result:
            return result

    # 5. Spiral review for mastered concepts
    if mastered:
        prob = selector_cfg.get("mastered_spiral_review_prob", 0.15)
        if rng.random() < prob:
            result = _select_for_spiral_review(mastered, available_items, recent, rng)
            if result:
                return result

    # 6. Fallback: any non-recent item
    non_recent = [i for i in available_items if i.item_id not in recent]
    if non_recent:
        item = rng.choice(non_recent)
        return SelectionResult(
            item=item,
            reason="隨機選題（所有概念已達標或無適合題目）",
            strategy="fallback_random",
        )

    # 7. Last resort: any item
    item = rng.choice(available_items)
    return SelectionResult(
        item=item,
        reason="隨機選題（題庫有限）",
        strategy="fallback_any",
    )


# ---------------------------------------------------------------------------
# Strategy implementations
# ---------------------------------------------------------------------------

def _select_for_unbuilt(
    unbuilt_concepts: List[str],
    concept_states: Dict[str, StudentConceptState],
    items: List[QuestionItem],
    recent: set,
    rng: random.Random,
) -> Optional[SelectionResult]:
    """For unbuilt concepts: start with prerequisites, then simplest items."""

    # Find which unbuilt concept has its prerequisites most ready
    best_concept = None
    best_readiness = -1

    for concept_id in unbuilt_concepts:
        prereqs = get_prerequisites(concept_id)
        if not prereqs:
            # No prerequisites — can start directly
            best_concept = concept_id
            best_readiness = 999
            break

        # Check how many prerequisites are mastered/approaching
        ready_count = 0
        for p in prereqs:
            ps = concept_states.get(p)
            if ps and ps.mastery_level in (MasteryLevel.MASTERED, MasteryLevel.APPROACHING_MASTERY):
                ready_count += 1

        if ready_count == len(prereqs):
            # All prerequisites ready — can start this concept
            if best_readiness < 100:
                best_concept = concept_id
                best_readiness = 100
        elif ready_count > best_readiness:
            # Some prerequisites ready — teach the missing prerequisite
            missing = [p for p in prereqs if not concept_states.get(p) or
                       concept_states[p].mastery_level in (MasteryLevel.UNBUILT, MasteryLevel.DEVELOPING)]
            if missing:
                best_concept = missing[0]  # Teach the first missing prerequisite
                best_readiness = ready_count

    if best_concept is None:
        best_concept = unbuilt_concepts[0]

    # Find easiest items for this concept
    candidates = [
        i for i in items
        if best_concept in i.concept_ids and i.item_id not in recent
    ]
    if not candidates:
        return None

    # Prefer easy difficulty
    easy = [i for i in candidates if i.difficulty == "easy"]
    pool = easy if easy else candidates
    # Prefer non-application items
    non_app = [i for i in pool if not i.is_application and i.format != "word_problem"]
    pool = non_app if non_app else pool

    item = rng.choice(pool)
    concept_name = CONCEPT_TAXONOMY.get(best_concept, {}).get("display_name_zh", best_concept)
    return SelectionResult(
        item=item,
        reason=f"基礎建立：開始學習「{concept_name}」（從最基礎題型開始）",
        strategy="unbuilt_foundation",
        target_concept=best_concept,
    )


def _select_for_review(
    review_concepts: List[str],
    concept_states: Dict[str, StudentConceptState],
    items: List[QuestionItem],
    recent: set,
    rng: random.Random,
    strategy_override: Optional[str] = None,
) -> Optional[SelectionResult]:
    """For concepts needing review: stalest-first prioritization."""
    # Prioritise the concept not seen for the longest time
    def _stale_key(cid: str) -> str:
        st = concept_states.get(cid)
        return (st.last_seen_at or "") if st else ""
    concept_id = min(review_concepts, key=_stale_key)
    candidates = [
        i for i in items
        if concept_id in i.concept_ids and i.item_id not in recent
    ]
    if not candidates:
        return None

    item = rng.choice(candidates)
    concept_name = CONCEPT_TAXONOMY.get(concept_id, {}).get("display_name_zh", concept_id)

    if strategy_override == "prerequisite_regression":
        return SelectionResult(
            item=item,
            reason=f"前置觀念退化：「{concept_name}」需要重新複習（其他觀念的基礎）",
            strategy="prerequisite_regression",
            target_concept=concept_id,
        )

    return SelectionResult(
        item=item,
        reason=f"間隔複習：複習已學過的「{concept_name}」以確認記得",
        strategy="spaced_review",
        target_concept=concept_id,
    )


def _select_for_developing(
    developing_concepts: List[str],
    concept_states: Dict[str, StudentConceptState],
    items: List[QuestionItem],
    recent: set,
    rng: random.Random,
) -> Optional[SelectionResult]:
    """For developing concepts: closest-to-promotion first."""
    # Pick the concept with highest mastery_score (closest to promotion gate)
    def _score_key(cid: str) -> float:
        st = concept_states.get(cid)
        return st.mastery_score if st else 0.0
    concept_id = max(developing_concepts, key=_score_key)
    candidates = [
        i for i in items
        if concept_id in i.concept_ids and i.item_id not in recent
    ]
    if not candidates:
        return None

    # Prefer easy/normal difficulty (not hard application problems)
    standard = [i for i in candidates if i.difficulty in ("easy", "normal")]
    pool = standard if standard else candidates

    item = rng.choice(pool)
    concept_name = CONCEPT_TAXONOMY.get(concept_id, {}).get("display_name_zh", concept_id)
    return SelectionResult(
        item=item,
        reason=f"能力建立中：練習「{concept_name}」的標準題型",
        strategy="developing_standard",
        target_concept=concept_id,
    )


def _select_for_approaching(
    approaching_concepts: List[str],
    concept_states: Dict[str, StudentConceptState],
    items: List[QuestionItem],
    recent: set,
    rng: random.Random,
    selector_cfg: dict,
) -> Optional[SelectionResult]:
    """For approaching-mastery: highest-score first + variant practice."""
    # Pick the concept closest to MASTERED promotion
    def _score_key(cid: str) -> float:
        st = concept_states.get(cid)
        return st.mastery_score if st else 0.0
    concept_id = max(approaching_concepts, key=_score_key)
    candidates = [
        i for i in items
        if concept_id in i.concept_ids and i.item_id not in recent
    ]
    if not candidates:
        return None

    # Mix: variant_prob chance of picking a different format/variant
    variant_prob = selector_cfg.get("approaching_variant_prob", 0.3)

    if rng.random() < variant_prob:
        # Try to find a variant (different format or variant_group)
        variants = [i for i in candidates if i.format in ("word_problem", "application")]
        if variants:
            item = rng.choice(variants)
            concept_name = CONCEPT_TAXONOMY.get(concept_id, {}).get("display_name_zh", concept_id)
            return SelectionResult(
                item=item,
                reason=f"接近掌握：用不同情境練習「{concept_name}」",
                strategy="approaching_variant",
                target_concept=concept_id,
            )

    item = rng.choice(candidates)
    concept_name = CONCEPT_TAXONOMY.get(concept_id, {}).get("display_name_zh", concept_id)
    return SelectionResult(
        item=item,
        reason=f"接近掌握：繼續熟練「{concept_name}」",
        strategy="approaching_standard",
        target_concept=concept_id,
    )


def _select_for_spiral_review(
    mastered_concepts: List[str],
    items: List[QuestionItem],
    recent: set,
    rng: random.Random,
) -> Optional[SelectionResult]:
    """For mastered concepts: sparse review with cross-concept items."""
    concept_id = rng.choice(mastered_concepts)
    candidates = [
        i for i in items
        if concept_id in i.concept_ids and i.item_id not in recent
    ]
    if not candidates:
        return None

    # Prefer application/cross-concept items if available
    cross = [i for i in candidates if len(i.concept_ids) > 1 or i.is_application]
    pool = cross if cross else candidates

    item = rng.choice(pool)
    concept_name = CONCEPT_TAXONOMY.get(concept_id, {}).get("display_name_zh", concept_id)
    return SelectionResult(
        item=item,
        reason=f"螺旋複習：用進階題確認「{concept_name}」的掌握度",
        strategy="spiral_review",
        target_concept=concept_id,
    )


# ---------------------------------------------------------------------------
# Prerequisite regression detection
# ---------------------------------------------------------------------------

def detect_prerequisite_regression(
    active_concepts: List[str],
    concept_states: Dict[str, StudentConceptState],
) -> List[str]:
    """Find prerequisites that decayed to REVIEW_NEEDED while student advances.

    Returns list of regressed prerequisite concept_ids (deduped, sorted by
    staleness — oldest first).
    """
    regressed: set = set()
    for cid in active_concepts:
        for prereq_id in get_prerequisites(cid):
            ps = concept_states.get(prereq_id)
            if ps and ps.mastery_level == MasteryLevel.REVIEW_NEEDED:
                regressed.add(prereq_id)
    if not regressed:
        return []
    # Sort stalest first
    def _stale(pid: str) -> str:
        s = concept_states.get(pid)
        return (s.last_seen_at or "") if s else ""
    return sorted(regressed, key=_stale)


# ---------------------------------------------------------------------------
# Remediation selector (called when remediation is triggered)
# ---------------------------------------------------------------------------

def select_remediation_item(
    concept_id: str,
    concept_states: Dict[str, StudentConceptState],
    available_items: List[QuestionItem],
    *,
    recent_item_ids: Optional[List[str]] = None,
    rng: Optional[random.Random] = None,
) -> Optional[SelectionResult]:
    """Select a simpler or prerequisite item when student is stuck.

    Strategy:
    1. Try simpler isomorphic item (same concept, easier)
    2. Try direct prerequisite concept item (weakest first)
    3. Try transitive prerequisites (deepest dependency chain)
    """
    rng = rng or random.Random()
    recent = set(recent_item_ids or [])

    # 1. Simpler isomorphic item
    same_concept = [
        i for i in available_items
        if concept_id in i.concept_ids and i.item_id not in recent and i.difficulty == "easy"
    ]
    if same_concept:
        item = rng.choice(same_concept)
        concept_name = CONCEPT_TAXONOMY.get(concept_id, {}).get("display_name_zh", concept_id)
        return SelectionResult(
            item=item,
            reason=f"降階補救：用更簡單的題目練習「{concept_name}」",
            strategy="remediation_simpler",
            target_concept=concept_id,
        )

    # 2+3. Prerequisite items — transitive, weakest score first
    all_prereqs = get_all_prerequisites(concept_id)
    # Sort by mastery_score ascending (weakest first)
    def _score(pid: str) -> float:
        ps = concept_states.get(pid)
        return ps.mastery_score if ps else 0.0
    all_prereqs.sort(key=_score)

    for prereq_id in all_prereqs:
        prereq_items = [
            i for i in available_items
            if prereq_id in i.concept_ids and i.item_id not in recent
        ]
        if prereq_items:
            easy = [i for i in prereq_items if i.difficulty == "easy"]
            pool = easy if easy else prereq_items
            item = rng.choice(pool)
            prereq_name = CONCEPT_TAXONOMY.get(prereq_id, {}).get("display_name_zh", prereq_id)
            concept_name = CONCEPT_TAXONOMY.get(concept_id, {}).get("display_name_zh", concept_id)
            return SelectionResult(
                item=item,
                reason=f"前置補救：先複習「{prereq_name}」再回到「{concept_name}」",
                strategy="remediation_prerequisite",
                target_concept=prereq_id,
            )

    return None
