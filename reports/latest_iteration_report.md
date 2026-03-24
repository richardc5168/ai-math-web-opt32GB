# Iteration R48 - Cloud Sync Hint Evidence Pass-Through

## Objective
Fix the cloud sync pipeline so that hint evidence chain fields (hint_sequence, hint_open_ts, hint_level_used) survive normalization and reach the backend instead of being silently stripped.

## Main Hypothesis
If we preserve hint evidence fields through normalizeAttemptForCloud() on the frontend and _sanitize_practice_event() on the backend, then cloud-synced data will contain full hint evidence chains, enabling cloud-based hint effectiveness analytics.

## Why This One
- R42-R47 built the entire local hint evidence chain (frontend → localStorage → DB → analytics).
- R47 post-mortem identified critical gap: normalizeAttemptForCloud() strips hint_sequence/hint_open_ts/hint_level_used before POSTing to the server.
- Both cloud sync pathways were affected: (1) doCloudSync → buildReportData → normalizeAttemptForCloud; (2) recordPracticeResult → event construction.
- Backend _sanitize_practice_event() also had no allowlist entries for these fields.
- Without this fix, cloud analytics would never see hint evidence data.

## Root Cause
Three choke points:
1. **Frontend normalizeAttemptForCloud()** (student_auth.js, report_data_builder.js): Hard-coded return object with fixed keys — no hint fields.
2. **Frontend recordPracticeResult()** (student_auth.js): Event construction doesn't forward hint fields from result object.
3. **Backend _sanitize_practice_event()** (server.py): Allowlist-based sanitizer returns fixed dict without hint fields.

## Files Changed
- docs/shared/student_auth.js — normalizeAttemptForCloud: extract from extra/hint objects, conditionally add to return; recordPracticeResult: forward hint fields from result
- docs/shared/report/report_data_builder.js — normalizeAttemptForCloud: same pattern as student_auth.js
- server.py — _sanitize_practice_event: pass through hint_sequence (list, max 10), hint_open_ts (list, max 10), hint_level_used (int) with type coercion and size limits
- dist_ai_math_web_pages/docs/shared/student_auth.js — mirror of docs/ changes
- dist_ai_math_web_pages/docs/shared/report/report_data_builder.js — mirror of docs/ changes
- tests/test_sanitize_practice_event.py (NEW: 6 tests for backend sanitizer hint pass-through)
- reports/latest_iteration_report.md
- logs/experiment_history.jsonl
- logs/change_history.jsonl
- logs/lessons_learned.jsonl

## Tests Run
- `pytest tests/test_sanitize_practice_event.py -v` → 6/6 passed
- `pytest tests/test_hint_evidence_pipeline.py tests/test_hint_evidence_chain.py -v` → 30/30 passed (no regressions)

## Results
- normalizeAttemptForCloud() now reads hint evidence from attempt.extra and attempt.hint objects, conditionally includes in output.
- recordPracticeResult() now forwards hint_sequence, hint_open_ts, hint_level_used from the result parameter.
- _sanitize_practice_event() now accepts and type-coerces hint evidence fields with size limits (max 10 items per list).
- All docs/ changes mirrored to dist_ai_math_web_pages/.
- 6 new backend sanitizer tests confirm pass-through, omission, truncation, and type coercion.

## Decision (keep / partial keep / revert)
keep

## Lessons Learned
- Data normalization functions are natural choke points for new field propagation — they must be audited whenever new fields are added to the evidence chain.
- Two separate normalizeAttemptForCloud() implementations exist (student_auth.js and report_data_builder.js) — both must be updated together.
- Backend sanitizers using allowlists need explicit entries for new fields; this is by design (security) but creates a known gap pattern.
- Size limits on list fields prevent unbounded payload growth (max 10 hint steps per attempt is generous for typical usage).

## Remaining Risk
- No live cloud endpoint testing (requires deployed server and authenticated student).
- coach and mixed-multiply pages still don't emit hint evidence via shared path (separate issue, tracked since R47).
- Node.js unavailable on this machine: JS tests (tests_js/) cannot be validated.

## Next Candidates
1. **Legacy page migration** — Wire coach/mixed-multiply to shared hint engine (moderate effort).
2. **Teacher report hint evidence display** — Surface evidence chain completeness in teacher-facing reports.
3. **JS test validation** — Run tests_js/*.test.mjs once Node.js is available.
