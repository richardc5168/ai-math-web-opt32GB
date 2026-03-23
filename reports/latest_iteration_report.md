---

# Iteration R27 / EXP-P3-02: Remediation Plan API Endpoint

## 1. Hypothesis
Exposing `getRemediationPlan()` via `/v1/learning/remediation_plan` API endpoint enables teachers and parents to request targeted remediation plans.

## 2. Scope
- `server.py`: New endpoint + `RemediationPlanRequest` model + import
- `tests/test_remediation_plan_api.py`: 12 new tests

## 3. Key Changes
- **`/v1/learning/remediation_plan` POST endpoint**: Auth-verified, student-ownership-checked, delegates to `learning.service.getRemediationPlan()`
- **`RemediationPlanRequest`**: `student_id` (required), `dataset_name` (optional), `window_days` (default 14)
- **Bug fix**: `PracticeNextRequest` had `topic_key` and `seed` fields accidentally displaced during model insertion

## 4. Metrics
| Metric | Before | After |
|--------|--------|-------|
| Test count | 872 | 884 |
| Failures | 0 | 0 |
| Remediation API | None | /v1/learning/remediation_plan |

## 5. Decision
**KEEP** — Clean endpoint wiring with proper auth.
**gamification.py was listed in .gitignore** since project inception. All R23-R25 commits claimed to modify it but the file was silently skipped by `git add -A`. This commit:
- Removed `gamification.py` from `.gitignore`
- First-ever git tracking of `learning/gamification.py` (all R23-R25 implementations now in repo)

## 2. Hypothesis (EXP-P3-01)
Wiring `before_after_analytics.compare_pre_post()` into `service.py` via `getBeforeAfterComparison()` enables pre/post intervention comparison with concept-level breakdown and auto-determined intervention date.

## 3. Scope
- `.gitignore`: Removed `gamification.py` entry
- `learning/gamification.py`: Now tracked (contains ZoneProgress, BossChallenge, detect_new_badges from R23-R25)
- `learning/service.py`: Added `getBeforeAfterComparison()` (~60 lines)
- `tests/test_before_after_analytics.py`: 17 new tests
- `reports/experiment_scoreboard.json`: Phase 3 Stage 1 progress
- `research/EXPERIMENT_BACKLOG.md`: Phase 3 plan added, P3-01 marked complete

## 4. Key Changes
- **getBeforeAfterComparison(student_id, intervention_date)**: Queries `la_attempt_events`, splits by date, builds QuestionAttempt objects with concept metadata from `concept_ids_json`, calls `compare_pre_post()`. Auto-determines midpoint if no intervention_date provided.
- **before_after_analytics module**: Standalone. Groups by `equivalent_group_id`, computes per-concept pre/post accuracy, labels improved/flat/regressed/insufficient.

## 5. Metrics
| Metric | Before | After |
|--------|--------|-------|
| Test count | 855 | 872 |
| Failures | 0 | 0 |
| gamification.py tracked | No | Yes |
| Before/after API | None | getBeforeAfterComparison() |

## 6. Decision
**KEEP** — Critical .gitignore fix plus clean analytics wiring.
**KEEP** -- Simple set difference for delta detection. Wiring recovered_concepts and consecutive_no_hint_correct activates all 3 previously dead badge types.

## 6. Phase 2 Stage 3 Summary
All 3 Stage 3 experiments complete:
- R23/S3-01: Zone unlock domain-based progression (834 tests)
- R24/S3-02: Boss challenge mastery-gated (846 tests)
- R25/S3-03: Badge refinement with delta detection (855 tests)

Phase 2 (Stages 1-3, R11-R25) is now COMPLETE with 855 tests and 0 failures.
