---

# Iteration R31 / EXP-P3-06: Transfer/Review Deltas — Phase 3 Stage 2 exp 3/3

## 1. Hypothesis
Activating `transfer_success` and `delayed_review_correct` score deltas in mastery_engine provides more nuanced scoring for transfer and spaced review scenarios.

## 2. Scope
- `learning/service.py`: Moved AnswerEvent inside per-concept loop, added transfer/review detection, wired `check_review_needed()`
- `tests/test_transfer_review_deltas.py`: 12 new tests

## 3. Key Changes
- **Per-concept AnswerEvent**: Moved construction inside the mastery loop so each concept gets unique `is_transfer_item` and `is_delayed_review` flags
- **Transfer detection**: `domain == "application"` (heuristic) OR `extra.is_transfer_item` (frontend signal) → `+0.12` bonus
- **Delayed review detection**: `state.mastery_level == REVIEW_NEEDED` → `+0.10` bonus on correct answer, `status = "failed"` on wrong
- **Auto-transition**: Calls `check_review_needed()` on MASTERED concepts → transitions to REVIEW_NEEDED after 7-day decay

## 4. Metrics
| Metric | Before | After |
|--------|--------|-------|
| Test count | 914 | 926 |
| Failures | 0 | 0 |
| transfer_success delta | dormant | active |
| delayed_review_correct delta | dormant | active |

## 5. Decision
**KEEP** — Phase 3 Stage 2 COMPLETE (3/3 experiments). All 8 mastery deltas now active end-to-end.
