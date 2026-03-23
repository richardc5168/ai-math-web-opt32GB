
---

# Iteration R21 / EXP-S2-02: Prerequisite Fallback

## 1. Hypothesis
Adding transitive prerequisite fallback to remediation and prerequisite-regression detection to the selector improves remediation quality by targeting root prerequisite gaps.

## 2. Scope
- `learning/next_item_selector.py`: Added `detect_prerequisite_regression()`, updated `select_remediation_item()` to use transitive prereqs, added `strategy_override` to `_select_for_review()`
- `tests/test_prerequisite_fallback.py`: 9 new tests

## 3. Key Changes
- **Prerequisite regression detection**: New priority-0 strategy in `select_next_item()`  if any prerequisite of a developing/approaching concept has decayed to REVIEW_NEEDED, fix it first
- **Transitive remediation**: `select_remediation_item()` now uses `get_all_prerequisites()` (BFS transitive closure) instead of direct-only, sorted by weakest mastery_score
- **Strategy override**: `_select_for_review()` accepts `strategy_override` param to emit `prerequisite_regression` strategy label

## 4. Metrics
| Metric | Before | After |
|--------|--------|-------|
| Test count | 799 | 808 |
| Failures | 0 | 0 |
| Remediation prereq depth | Direct only | Transitive (weakest first) |
| Prereq regression detection | No | Yes (priority-0) |

## 5. Decision
**KEEP**  Addresses a real gap: students building on decayed prerequisites waste effort. Transitive fallback + regression detection ensures remediation targets root cause.

## 6. Next
EXP-S2-03: Parent report  actionable concept-level progress
