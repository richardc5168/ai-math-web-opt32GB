
---

# Iteration R20 / EXP-S2-01: Adaptive Selector Priority Refinement

## 1. Hypothesis
Replacing random concept selection with score-aware prioritization (closest-to-promotion for developing, stalest-first for review, highest-score for approaching) improves selection quality and learning efficiency.

## 2. Scope
- learning/next_item_selector.py: Modified 3 strategy functions + 1 call site
- 	ests/test_selector_priority.py: 10 new tests

## 3. Key Changes
- _select_for_developing(): Picks concept with highest mastery_score (closest to promotion gate)
- _select_for_review(): Picks concept with oldest last_seen_at (stalest, most at risk of forgetting)
- _select_for_approaching(): Picks concept with highest mastery_score (closest to MASTERED)
- All three now receive concept_states dict for data-driven decisions

## 4. Metrics
| Metric | Before | After |
|--------|--------|-------|
| Test count | 789 | 799 |
| Failures | 0 | 0 |
| Selector concept choice | Random | Score-aware |

## 5. Decision
**KEEP**  Minimal code change (rng.choice  min/max with key) yields deterministic, score-aware concept selection. Phase 2 Stage 2 experiment 1 of 3 complete.

## 6. Next
EXP-S2-02: Prerequisite fallback - auto-detect missing prerequisites
