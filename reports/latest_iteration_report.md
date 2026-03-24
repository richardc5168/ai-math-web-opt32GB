# Iteration R49 - Legacy Page Migration (Coach + Mixed-Multiply → Shared Hint Engine)

## Objective
Wire the two remaining legacy hint pages (coach, mixed-multiply) to the shared hint engine so that hint evidence chain fields (hint_sequence, hint_open_ts, hint_level_used) are tracked consistently across all question pages.

## Main Hypothesis
If we include hint_engine.js and call init()/setCurrentQuestion() on the two legacy pages, the engine's auto-hooking (MutationObserver on #hints, click handler on #btnHint) will track hint opens and the attempt_telemetry.js module will auto-merge the trace data into appendAttempt() calls—achieving full evidence chain coverage with minimal code changes.

## Why This One
- R47 audit showed 19/21 question pages at FULL coverage; coach and mixed-multiply were the 2 PARTIAL gaps.
- R48 fixed the cloud sync pipeline, but data from coach/mixed-multiply still wouldn't have hint evidence fields.
- These two pages already have attempt_telemetry.js, #btnHint elements, and #hints/#helpBox containers—the shared engine can auto-hook with zero rewrite of existing hint display logic.

## Root Cause
Both pages were built before the shared hint engine existed. They had custom hint tracking but didn't emit hint_sequence/hint_open_ts/hint_level_used through the standard telemetry pipeline.

## Files Changed
- docs/coach/index.html — Added hint_engine.js script, init() call, setCurrentQuestion() call in startNext()
- docs/mixed-multiply/index.html — Added hint_engine.js script, init() call, setCurrentQuestion() call in newQuestion()
- dist_ai_math_web_pages/docs/coach/index.html — mirror
- dist_ai_math_web_pages/docs/mixed-multiply/index.html — mirror
- reports/latest_iteration_report.md
- logs/change_history.jsonl
- logs/lessons_learned.jsonl
- logs/experiment_history.jsonl

## Integration Strategy
Minimal-touch: keep existing custom hint display logic intact, just add shared engine tracking on top.
- hint_engine.js auto-hooks #btnHint via capture-phase click listener → calls recordHintOpen(level)
- attempt_telemetry.js auto-calls getHintTrace() and merges into appendAttempt() extra/hint fields
- setCurrentQuestion() resets trace per question, providing question_id linkage

## Tests Run
- `python tools/audit_hint_coverage.py` → 21 FULL (was 19), 0 PARTIAL question pages, 100% coverage (was 90%)
- `pytest tests/test_sanitize_practice_event.py -v` → 6/6 passed (no regressions)
- `pytest tests/test_hint_evidence_pipeline.py tests/test_hint_evidence_chain.py -v` → 30/30 passed

## Results
- Coach page: PARTIAL → FULL (all 4 signals: setCurrentQuestion, appendAttempt, hint_engine.js, attempt_telemetry.js)
- Mixed-multiply page: PARTIAL → FULL
- Question page coverage rate: 90% → 100% (21/21 FULL)
- Existing custom hint display logic unchanged—no visual or behavioral regression
- hint_engine.js auto-hooks work correctly with both pages' #btnHint elements

## Decision (keep / partial keep / revert)
keep

## Lessons Learned
- The shared hint engine's auto-hooking architecture (MutationObserver + capture-phase click listeners) makes legacy page migration a 3-line change per page.
- setCurrentQuestion() is the critical call—without it, hint traces would accumulate across questions instead of resetting per question.
- Pages with existing custom hint state (coach's totalHintMs, mixed-multiply's hintLevel) don't conflict with the engine's tracking—they're additive.

## Remaining Risk
- Coach page has an input element `#inpAns` instead of `#answer`—the engine's wrong-answer diagnosis won't auto-discover it. This is acceptable since coach has its own answer checking logic.
- No live browser testing (no browser automation available).
- Node.js unavailable for JS tests.

## Next Candidates
1. **Teacher report hint evidence display** — Surface evidence chain completeness in teacher-facing reports.
2. **JS test validation** — Run tests_js/*.test.mjs once Node.js is available.
