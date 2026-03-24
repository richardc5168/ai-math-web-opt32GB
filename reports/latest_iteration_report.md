# Iteration R47 - Hint Evidence Pipeline Audit & E2E Testing

## Objective
Close the verification gap in the hint evidence chain by (1) creating a permanent audit tool for page-level hint coverage, and (2) adding end-to-end pipeline tests that validate the full flow: frontend-shaped payload → recordAttempt → DB → analytics metrics.

## Main Hypothesis
If we formalize hint coverage auditing and add E2E pipeline tests, we can prove the evidence chain is complete at every layer and detect regressions automatically, enabling confident nightly optimization of hint effectiveness.

## Why This One
- R42-R46 built all the evidence fields (backend, analytics, frontend shared wiring).
- R46's remaining risks: (1) no permanent audit tool for page coverage, (2) no E2E test validating the full pipeline.
- Without E2E tests, changes to validator/service/analytics could silently break the evidence chain.
- The audit tool makes coverage trackable as new question pages are added.

## Files Inspected
- All 43 docs/*/index.html pages (coverage audit)
- learning/analytics.py (hint effectiveness metrics)
- learning/service.py (recordAttempt flow)
- learning/validator.py (field preservation)
- tests/test_hint_evidence_chain.py (R42 tests)
- tests/test_r43_hint_evidence_enhanced.py (R43 tests)
- tests/test_hint_effectiveness.py (R11-R13 tests)
- reports/latest_iteration_report.md
- logs/experiment_history.jsonl

## Files Changed
- tools/audit_hint_coverage.py (NEW: page coverage audit script)
- tests/test_hint_evidence_pipeline.py (NEW: 10 E2E pipeline tests)
- reports/latest_iteration_report.md
- logs/experiment_history.jsonl
- logs/change_history.jsonl
- logs/lessons_learned.jsonl

## Experiment Design
- Create `tools/audit_hint_coverage.py`: scans all docs pages for 4 shared component signals (setCurrentQuestion, appendAttempt, hint_engine.js, attempt_telemetry.js), classifies as FULL/PARTIAL/NONE.
- Create `tests/test_hint_evidence_pipeline.py`: 10 tests covering full roundtrip from frontend-shaped payloads through recordAttempt to analytics metrics.
- Test categories: full evidence chain, partial evidence, zero evidence, dwell time, level distribution, escalation rate, class-wide aggregation, validator preservation.

## Tests Run
- `pytest tests/test_hint_evidence_pipeline.py -v` → 10/10 passed
- `pytest tests/test_hint_*` → 52/52 passed (all hint tests)
- `pytest tests/ -q` → 1317 passed, 0 failed, exit 0
- `python tools/audit_hint_coverage.py` → 19 FULL, 2 PARTIAL (coach, mixed-multiply), 18 non-question

## Metrics Compared
- Before:
  - No permanent audit tool for page coverage
  - 0 E2E pipeline tests (only unit tests at each layer)
  - 1307 total tests
- After:
  - Permanent audit script with machine-readable output (--json)
  - 10 E2E pipeline tests covering all evidence chain fields
  - 1317 total tests
  - 90% page coverage rate (19/21 question pages FULL)

## Page Coverage Audit Results
| Category | Count | Pages |
|----------|-------|-------|
| FULL (all 4 signals) | 19 | commercial-pack1-fraction-sprint, decimal-unit4, exam-sprint, fraction-g5, fraction-word-g5, g5-grand-slam, interactive-decimal-g5, interactive-g5-empire, life-packs (4), interactive-g5-midterm1, interactive-g5-national-bank, interactive-g56-core-foundation, life-applications-g5, offline-math, ratio-percent-g5, volume-g5 |
| PARTIAL (custom hints) | 2 | coach (custom hint system), mixed-multiply (legacy custom hints) |
| Non-question (expected) | 22 | dashboards, reports, about, pricing, etc. |

## Results
- Created `tools/audit_hint_coverage.py` with human-readable table and `--json` mode.
- Created `tests/test_hint_evidence_pipeline.py` with 10 E2E tests covering the full hint evidence pipeline.
- All 52 hint-related tests pass (R42 + R43 + R47 + effectiveness).
- Full test suite: 1317 passed, 0 failed.
- 90% page coverage rate documented (coach/mixed-multiply use legacy custom hint systems).

## Decision (keep / partial keep / revert)
keep

## Lessons Learned
- E2E pipeline tests (frontend payload → DB → analytics) catch integration bugs that unit tests at each layer miss.
- Page coverage auditing reveals that custom/legacy pages are the main gap, not missing shared wiring.
- The 2 PARTIAL pages (coach, mixed-multiply) use custom hint implementations; migrating them to the shared engine would be a separate, larger effort with moderate risk.
- Permanent audit scripts enable CI-level regression detection for new page additions.

## Remaining Risk
- Node.js unavailable on this machine: JS tests (tests_js/) cannot be validated at runtime.
- coach and mixed-multiply pages don't emit hint_sequence/hint_open_ts via the shared path.
- R42-R46 commits are still unpushed to origin (3 commits ahead).

## Next Candidates
1. **Push R42-R47** — Push all unpushed commits to origin to sync remote.
2. **Cloud sync mapping** — Ensure frontend localStorage hint evidence fields reach backend when synced (the page→cloud→backend pathway).
3. **Legacy page migration** — Optionally wire coach/mixed-multiply to shared hint engine (moderate effort, moderate risk).
4. **Teacher report hint evidence display** — Surface evidence chain completeness in teacher-facing reports.
5. **JS test validation** — Run tests_js/*.test.mjs once Node.js is available.
