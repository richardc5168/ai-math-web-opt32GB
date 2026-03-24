# Iteration R51 - JS Test Validation

## Objective
Run all JavaScript tests (tests_js/) using Node.js to establish a baseline and verify no R48-R50 regressions.

## Key Finding
Node.js v24.14.0 IS installed at `C:\Program Files\nodejs\node.exe` — it was not in PATH but is functional.

## Test Results Summary
| Test File | Pass | Fail | Notes |
|-----------|------|------|-------|
| attemptTelemetry.test.mjs | 3 | 0 | R46 hint trace auto-attach tests |
| diagnoseWrongAnswer.test.mjs | 6 | 0 | Wrong-answer diagnosis |
| hintEngine.test.mjs | 133 | 10 | Pre-existing: processHintHTML SVG rendering |
| 15 spec files (excl. Playwright) | 87 | 3 | Pre-existing: source-level security checks |
| exam-sprint-gate.spec.mjs | — | — | Skipped: requires @playwright/test |
| **Total** | **229** | **13** | **All 13 failures are pre-existing** |

## Pre-existing Failures (not introduced by R48-R50)
### hintEngine.test.mjs (10 failures)
All are `processHintHTML` tests expecting specific SVG content in rendered hints:
- fracRemain L2 SVG bar, decimal L2 place value SVG, percent L2 comparison bar
- L1 step indicator + keywords, fracWord L2 fraction circle
- fracAdd L2 fraction comparison, percent L2 step-by-step narration
- fracWord L3 narration, percent L3 percent grid, decimal L3 dual decomposition

### spec files (3 failures)
- bootstrap/exchange endpoints deny-by-default (source-level)
- bootstrap/exchange/login rate limiting + token cap (source-level)
- student selector UI for multi-student accounts (source-level)

## Decision (keep / partial keep / revert)
keep — baseline established, no regressions from R48-R50

## Next Candidates
1. Fix 10 processHintHTML SVG rendering test failures (hint_engine.js vs test expectations mismatch)
2. Fix 3 source-level security spec failures
3. Install @playwright/test to run exam-sprint-gate.spec.mjs
4. Wire teacher dashboard to live concept-report API
