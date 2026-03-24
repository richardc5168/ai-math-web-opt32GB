# Iteration R50 - Teacher Report Hint Effectiveness Panel

## Objective
Surface hint evidence chain completeness and effectiveness metrics in the teacher-facing dashboard so teachers can see how well hints are working and where telemetry gaps exist.

## Main Hypothesis
If we add a hint effectiveness panel to the teacher dashboard showing success rate, evidence chain coverage, per-level performance, risk flags, and recommendations (matching the format_hint_summary_for_teacher() output shape), teachers gain actionable insight into hint quality without needing to access raw analytics.

## Why This One
- R42-R49 built the complete evidence chain: frontend tracking → cloud sync → backend → analytics → format_hint_summary_for_teacher().
- The backend already computes all needed metrics and generates Chinese-language summaries.
- The teacher dashboard had no hint data panel—it only showed pre/post accuracy and risk scores.
- This closes the "last mile" gap: data exists but teachers can't see it.

## Files Changed
- docs/shared/school_first_mock_data.js — Added buildHintSummary() fixture matching format_hint_summary_for_teacher() output shape
- docs/school-first/teacher-dashboard/index.html — Added "Hint Effectiveness" and "Decision Support" cards
- dist_ai_math_web_pages/docs/shared/school_first_mock_data.js — mirror
- reports/latest_iteration_report.md
- logs/change_history.jsonl, logs/lessons_learned.jsonl, logs/experiment_history.jsonl

## Panel Content
- **KPIs**: hint success rate, avg hints before success, evidence chain complete rate
- **Detail row**: escalation rate, avg dwell time, total hinted attempts
- **Per-level table**: attempts, correct, success rate per hint level
- **Risk flags**: Chinese-language warnings (e.g., high escalation rate)
- **Recommendations**: Chinese-language action items
- **Evidence chain coverage**: per-field breakdown (hint_level_used, hint_sequence, hint_open_ts)

## Tests Run
- No lint/compile errors in changed files
- Visual structure matches format_hint_summary_for_teacher() output shape

## Decision (keep / partial keep / revert)
keep

## Lessons Learned
- The mock data approach lets the teacher dashboard be functional even without a live backend, useful for demos and development.
- format_hint_summary_for_teacher() output shape serves as the contract between backend and frontend—the mock fixture mirrors it exactly.

## Remaining Risk
- Teacher dashboard still uses mock data, not live API. Wiring to /v1/teacher/classes/{id}/concept-report is needed for production use.
- school-first/ directory not present in dist/ mirror (newer feature, not yet deployed).
- Node.js unavailable for JS tests.

## Next Candidates
1. **Wire teacher dashboard to live concept-report API** — Replace mock data with fetch() calls.
2. **JS test validation** — Run tests_js/*.test.mjs once Node.js is available.
