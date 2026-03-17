# Latest Iteration Report

## Session Summary (Iterations 12–30)

### Iteration 12 (commit `43b4417ba`)
- Expanded TOPIC_LINK_MAP with 4 new entries: commercial-pack1-fraction-sprint, national-bank, midterm, grand-slam
- Fixed commercial-pack1-fraction-sprint falling through to generic fraction link
- +4 regression tests → **42 pass**

### Iteration 13 (commit `bb02692bb`)
- Added collapsible section groups to parent report dashboard (17 cards → 7 `<details>` groups)
- Groups: 24h (collapsed), Quick Summary (open), 7-Day Overview (collapsed), Learning Analysis (collapsed), Advanced Analysis (collapsed), Wrong Q & Practice (open), Advice & Export (open)
- **42 pass**

### Iteration 14 (commit `fd7a41b1b`)
- **Critical fix**: WoW identity mismatch — queried telemetry with `d.name` (display name) instead of device UUID
- Added `getDeviceUid()` helper using `AIMathCoachLog.getOrCreateUserId()`
- **43 pass**

### Iteration 15 (commit `8eb71d19c`)
- Added expand/collapse-all toggle button for collapsible groups
- **43 pass**

### Iteration 16 (commit `5da4885ed`)
- **Security fix**: `esc()` escapes `"` → `&quot;` and `'` → `&#39;` (prevents HTML attribute injection)
- **UX consistency**: parent copy wrong count changed from 3 → 5 to match dashboard
- **Stale state fix**: h24Modules element cleared when empty
- +2 regression tests → **45 pass**

### Iteration 17 (commit `25aad6e0e`)
- **Security fix**: exam-sprint `escapeHtml()` missing quote escaping — critical XSS in `data-qid` attribute context
- Audited all 8 escape functions across 8 pages
- +1 regression test → **46 pass**

### Iteration 18 (commit `3592ef3d3`)
- **Practice quality**: `parseFrac()` + `fractionsEqual()` for fraction equivalence via cross-multiplication
- Modified `checkNow()` to accept equivalent fractions with simplification reminder
- +1 regression test → **47 pass**

### Iteration 19 (commit `270c3a242`)
- Added `🔗 去練習模組` deep-link button to each wrong list item using `getTopicLink(w.t)`
- +1 regression test → **48 pass**

### Iteration 20 (commit `adf30d7e1`)
- Added `→ 前往練習模組` deep-link to each detailed analysis (補強方案) card
- +1 regression test → **49 pass**

### Iteration 21 (commit `bc396fe4f`)
- **Critical fix**: Single-practice mode ("再練一題") results were silently lost — only quiz-3 mode called `persistPractice`
- In `goNext()` for non-quiz mode: reset `quizRecorded`, call `persistPractice(isCorrect ? 1 : 0, 1)` per answered question
- Refreshed latest_iteration_report.md to cover iters 17-20
- +1 regression test → **50 pass**

### Iteration 22 (commit `8b8c60fb3`)
- Practice results now write to local `AIMathAttemptTelemetry.appendAttempt()` (before cloud write)
- Events tagged `source: 'parent-report-practice'`, `unit_id: 'parent-report-practice'`
- Uses `getDeviceUid()` for correct identity
- +1 regression test → **51 pass**

### Iteration 23 (commit `581cbcaa6`)
- Added 3 remediation regression tests: priority targeting weakest topic, action text presence, stable links for known topics
- Test count 51 → **54 pass**

### Iteration 24 (commit `54b031ff1`)
- **Critical UX fix**: Practice summary UI update was gated behind cloud write success — if cloud auth unavailable, `renderPracticeSummary()` never fired despite local telemetry being written
- Moved `r.practice.events.push()` + `renderPracticeSummary()` before cloud auth check in `persistPractice()`
- Cloud write is now "bonus persistence" — UI always updates immediately
- +1 regression test → **55 pass**

### Iteration 25 (commit `a28e0fe73`)
- **Feature**: Connected `aggregate.js` ABCD quadrant analysis to parent-report dashboard
- Added `<script src="aggregate.js">` and new "學習象限分析" card in 進階分析 group
- Stacked horizontal bar showing A=獨立答對 / B=提示答對 / C=提示仍錯 / D=無提示答錯 rates from local telemetry (7 days)
- Shows `recommend(stats)` tips below the bar
- +10 regression tests → **65 pass**

### Iteration 26 (commit `2b6502b8c`)
- **Practice quality**: Extended `parseFrac()` to handle mixed numbers (`1 1/2` → `3/2`) and whole numbers (`3` → `3/1`)
- Updated `normAns()` to preserve single spaces for mixed number parsing
- Updated tests with mixed/whole number assertions → **65 pass**

### Iteration 27 (commit `2d4c1c8a2`)
- Added `isComplete` parameter to `persistPractice` — early-exit passes `false`
- Practice events now have `completed: true|false` field
- Practice summary shows `提前結束 N 次` when early exits exist
- +1 regression test → **66 pass**

### Iteration 28 (commit `48f3b718d`)
- **Critical UX fix**: Decimal answers (0.5, 1.25) now equivalent to fractions (1/2, 5/4) using integer arithmetic
- Extended `parseFrac()` to convert decimals to integer fractions (0.5→5/10, no IEEE 754)
- `fractionsEqual('0.5', '1/2')` now returns `true` — unblocks decimal practice modules
- Extended test assertions with decimal↔fraction, decimal↔whole, decimal↔mixed → **66 pass**

### Iteration 29 (commit `5df57f0f2`)
- **Remediation breadth fix**: expanded `practice_from_wrong_engine.js` coverage for the existing bank families that were still falling back to generic remediation
- Added explicit explanation + deterministic practice generation for average, money, discount/percent, ratio, decimal, speed, area/perimeter, time, and multi-step families
- Added 3 regression tests covering family-level explanation coverage, targeted practice generation, and integer-answer safety → **69 pass**

### Iteration 30 (commit `working-tree`)
- **Commercial remediation coverage fix**: expanded `practice_from_wrong_engine.js` for the remaining commercial and life-bank families still falling through to generic remediation
- Added explicit explanation + deterministic fallback practice for commercial-pack1 fraction-sprint, decimal-unit4 operations, life-applications-g5, interactive-g5-empire `unit_convert`, and interactive-g5-life-pack1-empire conversion/add-sub kinds
- Added 2 bank-backed regression tests that load real `bank.js` payloads and verify these families resolve to non-generic explanations and usable fallback practice → **71 pass**

### Current Shared Engine Inventory (11 modules)
1. `weakness_engine.js` — `AIMathWeaknessEngine`
2. `recommendation_engine.js` — `AIMathRecommendationEngine` (TOPIC_LINK_MAP: 17 entries)
3. `report_data_builder.js` — `AIMathReportDataBuilder`
4. `practice_from_wrong_engine.js` — `AIMathPracticeFromWrongEngine`
5. `parent_copy_engine.js` — `AIMathParentCopyEngine` (5-wrong-item limit)
6. `wow_engine.js` — `AIMathWoWEngine`
7. `radar_engine.js` — `AIMathRadarEngine`
8. `progress_trend_engine.js` — `AIMathProgressTrendEngine`
9. `practice_summary_engine.js` — `AIMathPracticeSummaryEngine`
10. `parent_advice_engine.js` — `AIMathParentAdviceEngine`
11. `aggregate.js` — `AIMathReportAggregate` (**connected**: quadrant analysis card in parent-report)

### Test Coverage
- **71 regression tests** across 12 test files, all passing
- `validate_all_elementary_banks.py` → 7157 PASS, 0 FAIL
- `verify_all.py` → 4/4 OK (135 files mirrored)

### Remaining Inline Code in parent-report
- All remaining code is **view-layer**: DOM manipulation, event handlers, HTML template rendering
- Domain logic extraction is complete

### Residual Risks
1. ~`aggregate.js` not connected~ — **DONE** (iter 25)
2. ~Mixed number format~ — **DONE** (iter 26)
3. Expand/collapse state not persisted across page reloads
4. Practice events use `unit_id='parent-report-practice'` — separate from real quiz unit_ids in aggregate
5. Remediation coverage is still rule-based; future new or renamed `kind` values can still fall through until mapped or audited automatically

### Next Iteration Priorities
1. ~Connect aggregate.js~ — **DONE** (iter 25)
2. ~Mixed number support~ — **DONE** (iter 26)
3. ~Practice early-exit tracking~ — **DONE** (iter 27)
4. Add a source-level coverage audit that scans all current `bank.js` files against remediation mappings
5. Externalize kind→advice mappings to JSON for maintainability
