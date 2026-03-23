---

# Iteration R25 / EXP-S3-03: Badge Refinement with Delta Detection

## 1. Hypothesis
Badge delta detection via detect_new_badges() plus wiring recovered_concepts and consecutive_no_hint_correct into compute_badges enables real-time new badge notifications and activates previously dead badge types (streak, no-hint, comeback).

## 2. Scope
- `learning/gamification.py`: Added detect_new_badges() function
- `learning/service.py`: Wired recovered_concepts tracking, consecutive_no_hint_correct, badge delta detection into recordAttempt
- `tests/test_badge_refinement.py`: 9 new tests

## 3. Key Changes
- **detect_new_badges(current_badges, previous_badge_types)**: Returns badges whose badge_type is not in the previous set. Simple set difference.
- **recovered_concepts tracking**: Compares old mastery level (before update_mastery) with new level. If old=REVIEW_NEEDED and new=MASTERED, adds concept_id to recovered set.
- **consecutive_no_hint_correct**: Reads from concept state extra field when answer is correct and no hints used.
- **prev_badge_types vs all_badges**: Computes basic badges first (prev), then full badges with all inputs, then delta for new_badges.
- **Response enhancement**: Returns new_badges list with is_new=True flag alongside existing badges.

## 4. Metrics
| Metric | Before | After |
|--------|--------|-------|
| Test count | 846 | 855 |
| Failures | 0 | 0 |
| Badge delta detection | None | Set-based detect_new_badges |
| Streak badge | Dead code | Wired via service.py |
| No-hint badge | Dead code | Wired via consecutive_no_hint_correct |
| Comeback badge | Dead code | Wired via recovered_concepts |

## 5. Decision
**KEEP** -- Simple set difference for delta detection. Wiring recovered_concepts and consecutive_no_hint_correct activates all 3 previously dead badge types.

## 6. Phase 2 Stage 3 Summary
All 3 Stage 3 experiments complete:
- R23/S3-01: Zone unlock domain-based progression (834 tests)
- R24/S3-02: Boss challenge mastery-gated (846 tests)
- R25/S3-03: Badge refinement with delta detection (855 tests)

Phase 2 (Stages 1-3, R11-R25) is now COMPLETE with 855 tests and 0 failures.
