# Iteration R56 — Cross-Device Student-Parent Data Flow Verification

## Objective
Verify and test the complete cross-device data flow: student logs in on Computer A, parent on Computer B can see the same student's practice records, reports, and weekly summary.

## Audit Findings

The entire cross-device chain is **ALREADY FULLY FUNCTIONAL**:

### Data Flow Chain (Verified)
```
Student (Device A)
  → Login: name + PIN stored in localStorage
  → Practice: attempts recorded in localStorage via attempt_telemetry.js
  → Auto Sync Triggers:
      • appendAttempt hook (3s delay)
      • setInterval (every 20s)
      • visibilitychange (tab hide)
      • beforeunload (page close)
  → doCloudSync(): collectLocalAttempts(7) → buildReportData() → POST /v1/parent-report/registry/upsert
  → Server: Validates PIN hash, stores JSON in parent_report_registry table

Parent (Device B)
  → /docs/parent-report/ page
  → Enters student name + PIN
  → POST /v1/parent-report/registry/fetch → server validates PIN hash → returns full report
  → Dashboard renders: KPI, modules, weakness, wrong questions, hints, daily charts, AI advice
  → 🔄 Refresh button re-fetches latest from cloud
  → ☁️ Sync timestamp shows data freshness
```

### Security Verified
- PIN stored as salted hash on server (not plaintext)
- Wrong PIN returns 403
- Different students' data isolated by normalized name + PIN
- No PIN leakage in fetch response

## Tests Added
10 new end-to-end tests in `tests/test_cross_device_data_flow.py`:
1. Full round-trip (upsert → fetch → verify all fields)
2. Incremental sync updates (latest upsert wins)
3. Name case-insensitive matching
4. Wrong PIN rejected (403)
5. Unknown student returns 404
6. Practice events accumulate across upserts
7. cloud_ts freshness updates
8. Students don't leak data across accounts
9. Unicode student names
10. Large payload (200 attempts) round-trips

## Validation
- `pytest tests/test_cross_device_data_flow.py -v`: 10 pass
- `pytest tests/test_parent_report_registry_endpoint.py -v`: 1 pass (existing)
- `fc.exe` comparison: docs/ and dist/ files in sync (parent-report/index.html, student_auth.js, report_sync_adapter.js)

## Residual Risk
- Cloud sync requires `?api=` URL parameter set once on the student's device to point to the backend. If student never connects to a backend-configured page, no sync occurs.
- Practice data stored as opaque JSON blob in `parent_report_registry.data_json`, not in the analytics DB (`la_attempt_events`).
- Switching devices as a student (not parent) loses localStorage data — only the cloud copy survives.

## Next Steps
- Consider adding API base auto-detection or configuration page
- Wire practice attempts into `la_attempt_events` for deeper server-side analytics
- Add device-sync indicator on student pages showing cloud sync status

## Next Step
- Question bank metadata integration for display_name resolution
- Dashboard UI consumption of one_page_summary_markdown
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
