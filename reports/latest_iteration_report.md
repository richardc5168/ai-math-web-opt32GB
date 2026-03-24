# Iteration R46 - Hint Trace Shared Frontend Wiring

## Objective
Close the last low-risk gap in the hint evidence chain by making shared frontend hint UI automatically emit `hint_sequence` and `hint_open_ts`, instead of depending on page-by-page wiring.

## Main Hypothesis
If the shared hint engine records per-question hint-open order and timestamps, and shared attempt telemetry auto-attaches that trace during `appendAttempt()`, then existing question pages can start producing actionable hint evidence coverage without per-page submit rewrites.

## Why This One
- Candidate 3 and candidate 1 were already completed first, per the requested order.
- The remaining leverage point was candidate 2: frontend emission.
- Repo scan showed many pages already converge on `AIMathHintEngine.setCurrentQuestion(...)` and `AIMathAttemptTelemetry.appendAttempt(...)`.
- This made a shared-layer patch lower risk than editing dozens of pages.

## Files Inspected
- docs/shared/hint_engine.js
- docs/shared/attempt_telemetry.js
- docs/offline-math/index.html
- docs/interactive-decimal-g5/index.html
- docs/shared/adaptive_mastery_frontend.js
- tests_js/hintEngine.test.mjs
- reports/latest_iteration_report.md
- logs/experiment_history.jsonl
- logs/change_history.jsonl
- logs/lessons_learned.jsonl

## Files Changed
- docs/shared/hint_engine.js
- docs/shared/attempt_telemetry.js
- tests_js/attemptTelemetry.test.mjs
- reports/latest_iteration_report.md
- logs/experiment_history.jsonl
- logs/change_history.jsonl
- logs/lessons_learned.jsonl

## Experiment Design
- Keep the patch additive.
- Do not require page-specific submit payload changes.
- Reset trace on `setCurrentQuestion()`.
- Record each hint open through the existing shared button hooks.
- Auto-fill `hint_sequence`, `hint_open_ts`, and `hint_level_used` inside `appendAttempt()` only when the page did not already provide them.
- Add one focused JS regression test file for shared behavior.

## Tests Run
- Static validation: no editor errors in `docs/shared/hint_engine.js`, `docs/shared/attempt_telemetry.js`, `tests_js/attemptTelemetry.test.mjs`
- Runtime JS tests: blocked in this environment because `node` / `npm` are not installed or not on PATH

## Metrics Compared
- Before:
	- Hint evidence coverage was measurable in backend analytics, but many frontend pages still relied on manual `shown_levels` only.
	- `hint_sequence` and `hint_open_ts` were not emitted by the shared frontend telemetry layer.
- After:
	- Shared hint engine tracks per-question `hint_sequence` and `hint_open_ts`.
	- Shared attempt telemetry copies that trace into both `attempt.hint.*` and `attempt.extra.*`.
	- Existing pages that already use `setCurrentQuestion()` + `appendAttempt()` can emit richer hint evidence without page-local patches.

## Results
- Added shared hint trace state to `AIMathHintEngine` with `recordHintOpen()`, `getHintTrace()`, and `resetHintTrace()`.
- Hooked the existing shared hint buttons to record open order and timestamps.
- Updated `AIMathAttemptTelemetry.appendAttempt()` to auto-attach trace data when not already present.
- Preserved explicit per-page hint trace values when they exist.
- Added JS regression coverage for auto-attach, reset behavior, and explicit-value precedence.

## Decision (keep / partial keep / revert)
keep

## Lessons Learned
- The safest frontend telemetry fixes are at shared aggregation points, not inside individual question pages.
- `setCurrentQuestion()` was already widely adopted enough to serve as a trace reset boundary.
- When adding shared fallback data, preserving explicit page-provided values avoids surprising downstream behavior.

## Remaining Risk
- Runtime JS execution was not validated on this machine because `node.exe` is unavailable.
- Pages that do not use the shared hint engine or shared telemetry path still will not emit the new fields automatically.

## Next Candidates
1. Add one backend/cloud sync path that maps local attempt `extra.hint_sequence` and `extra.hint_open_ts` into server-side submit/report payloads.
2. Add a lightweight audit test that enumerates docs pages missing either `setCurrentQuestion()` or `appendAttempt()` so frontend evidence gaps are explicit.
3. After Node is available, run the JS regression suite and then commit the whole R45-R46 bundle.
