# Latest Iteration Report

## Session Summary (Iterations 12–20)

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
11. `aggregate.js` — `AIMathReportAggregate` (not yet connected to parent-report)

### Test Coverage
- **49 regression tests** across 11 test files, all passing
- `validate_all_elementary_banks.py` → 7157 PASS, 0 FAIL
- `verify_all.py` → 4/4 OK (135 files mirrored)

### Remaining Inline Code in parent-report
- All remaining code is **view-layer**: DOM manipulation, event handlers, HTML template rendering
- Domain logic extraction is complete

### Residual Risks
1. `aggregate.js` not connected to parent-report (quadrant classification unused)
2. **Single-practice results not written back** — only quiz-3 mode calls `persistPractice`
3. **Practice results don't write to local AIMathAttemptTelemetry** — aggregate analytics can't see practice
4. Mixed number format (1 1/2) not supported in practice answer checker
5. Expand/collapse state not persisted across page reloads

### Next Iteration Priorities
1. Fix single-practice writeback so "再練一題" results are persisted
2. Write practice results to local attempt telemetry for aggregate analysis
3. Add writeback regression tests
4. Connect aggregate.js for richer weakness detection
