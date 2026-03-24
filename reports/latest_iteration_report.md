# Iteration R52 — Hint Evidence Chain + Mastery Depth + Teacher Summary

## Objective
Three-theme overnight optimization focused on hint effectiveness:
1. **Hint Evidence Chain**: Promote hint_level_used to first-class DB column, validate in validator, fix analytics
2. **Mastery Scoring Evidence**: Add hint_level_used to AnswerEvent, heavy hint penalty for L3+
3. **Teacher Report One-Page Summary**: Add severity, struggling items, hint dependency, error summary

## Changes

### Theme 1: Hint Evidence Chain
| File | Change |
|------|--------|
| `db/migrations/004_hint_evidence_columns.sql` | NEW: adds `hint_level_used INTEGER`, `success_after_hint INTEGER` columns |
| `learning/validator.py` | ValidatedAttemptEvent gets `hint_level_used`, `hint_sequence`, `hint_open_ts` as first-class fields; validation with type checking, range limits, 10-item cap |
| `learning/service.py` | INSERT stores `hint_level_used` and `success_after_hint` as first-class columns; passes `hint_level_used` to AnswerEvent |
| `learning/analytics.py` | Uses first-class `hint_level_used` column with extra_json fallback; `hint_escalation_rate` now uses actual hint level not count; adds `by_question` breakdown (top 20) |

### Theme 2: Mastery Scoring Evidence
| File | Change |
|------|--------|
| `learning/mastery_engine.py` | AnswerEvent gets `hint_level_used: Optional[int]`; heavy hint penalty (-0.04) for L3+ when correct with hint |
| `learning/mastery_config.py` | Adds `heavy_hint_penalty: -0.04` to score_deltas |

### Theme 3: Teacher Report One-Page Summary
| File | Change |
|------|--------|
| `learning/teacher_report.py` | `format_one_page_summary()` adds: `severity` (良好/需要關注/需要立即介入), `struggling_items` (per-question lowest success rate), `hint_dependency_concepts` (concepts with ≥60% dependency), `error_summary` (top 3 error patterns) |

## Test Results
| File | Count | Status |
|------|-------|--------|
| test_hint_evidence_chain.py | 36 | All PASS (includes 15 new R52 tests) |
| test_mastery_engine.py | 17 | All PASS |
| test_sanitize_practice_event.py | 6 | All PASS |
| test_one_page_summary.py | 20 | All PASS (includes 9 new R52 tests) |
| test_teacher_report.py + others | varies | All PASS |
| **Total related** | **127** | **0 failures** |

## Risk Assessment
- **Low risk**: All changes are backward-compatible; new DB columns are nullable
- **No breaking changes**: Extra data in extra_json still works unchanged
- **Migration**: 004_hint_evidence_columns.sql adds columns via ALTER TABLE — non-destructive

## Residual Risks
- `hint_level_used` column will be NULL for historical data (analytics has extra_json fallback)
- `success_after_hint` derived at insert time — no backfill for historical rows
- Per-hint dwell time still blocked (no `hint_close_ts` at frontend)

## Next Iteration Recommendations
- Backfill: UPDATE hint_level_used FROM json_extract(extra_json) for historical rows
- Frontend: track hint_close_ts for per-level dwell analysis
- Teacher dashboard UI: wire format_one_page_summary() to actual dashboard

## Decision (keep / partial keep / revert)
keep — baseline established, no regressions from R48-R50

## Next Candidates
1. Fix 10 processHintHTML SVG rendering test failures (hint_engine.js vs test expectations mismatch)
2. Fix 3 source-level security spec failures
3. Install @playwright/test to run exam-sprint-gate.spec.mjs
4. Wire teacher dashboard to live concept-report API
