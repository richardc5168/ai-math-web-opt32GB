# North Star Metrics — AI Math Web

> Last updated: 2026-03-22 | Auto-maintained by research iteration loop

## Purpose

This document defines the **measurable outcomes** that every experiment must improve
(or at least not regress). It is the single source of truth for "what matters" when
deciding whether a change is a keep or a revert.

---

## A. Learning Effectiveness (教學成效)

| Metric ID | Metric | Baseline | Target | Measurement Method |
|-----------|--------|----------|--------|--------------------|
| A1 | Hint → independent-correct rate | TBD (measure first) | +10% relative | After hint usage on topic X, % of next 3 same-topic items answered correctly without hints |
| A2 | Concept re-test accuracy | TBD | ≥70% | After mastery_engine marks concept "learned", accuracy on re-test items within 7 days |
| A3 | Remediation pass rate | TBD | ≥60% | After remediation_flow triggers, % of students who pass the remediation item set |
| A4 | Error-type classification accuracy | TBD | ≥80% | error_classifier output vs human-labeled golden set (to be built) |
| A5 | Transfer accuracy | TBD | +5% | After mastering concept X, accuracy on concept Y where X is prerequisite |

### How to measure
- A1–A3: Requires concept_taxonomy + mastery_engine + event enrichment to be wired into recordAttempt
- A4: Requires golden error labels — start with 50-item manual annotation
- A5: Requires prerequisite graph from concept_taxonomy to be active

---

## B. Teacher / Parent Readability (報表可讀性)

| Metric ID | Metric | Baseline | Target | Measurement Method |
|-----------|--------|----------|--------|--------------------|
| B1 | Parent report first-screen actionability | Qualitative | 3 weakness cards with evidence + CTA | Source-level test: summary has ≤3 cards, each with evidence_text and practice link |
| B2 | Teacher report blocking-concept accuracy | TBD | Top-3 blockers match teacher judgment | teacher_report.py generate_teacher_report() vs teacher survey (future) |
| B3 | Copy clarity score | Qualitative | No generic fallback text in visible UI | Bank audit gate: parent-report-bank-audit.spec.mjs 0 generic fallthrough |

### Current status
- B1: ✅ Implemented (iterations 32–35): 3 weakness summary cards with shared evidence formatter
- B3: ✅ Bank audit gate active (iteration 31): all bank kinds have non-generic remediation

---

## C. Product Interaction (產品互動)

| Metric ID | Metric | Baseline | Target | Measurement Method |
|-----------|--------|----------|--------|--------------------|
| C1 | Practice completion rate | TBD | ≥70% | `completed:true` vs total practice events in telemetry |
| C2 | Session abandonment rate | TBD | ≤30% | Sessions with <3 attempts / total sessions |
| C3 | Hint dependency ratio | TBD | ≤40% | Attempts requiring hints / total attempts (from aggregate.js ABCD quadrant) |
| C4 | Gamification unlock rate | TBD | ≥50% | Students who earn ≥1 badge per week / active students |
| C5 | Parent report refresh frequency | TBD | ≥2/week | Report load events per parent per week |

### How to measure
- C1: ✅ Already tracked (iteration 27: `isComplete` parameter in persistPractice)
- C2: Requires session-level analysis of la_attempt_events
- C3: ✅ Already computed (iteration 25: aggregate.js quadrant A/B/C/D)
- C4: Requires gamification.py to be wired into live flow
- C5: Requires server-side report-access logging

---

## D. Engineering Quality (工程品質)

| Metric ID | Metric | Baseline | Target | Measurement Method |
|-----------|--------|----------|--------|--------------------|
| D1 | Python test pass rate | 629/635 (98.9%) | 100% green | `pytest` — 0 new regressions |
| D2 | JS test pass rate | 108/108 (100%) | 100% green | `node --test tests_js/*.spec.mjs` |
| D3 | Bank validation pass rate | 7157/7157 (100%) | 100% | `python tools/validate_all_elementary_banks.py` |
| D4 | Pre-existing test failures | 6 | 0 | Fix: test_external_web, test_fraction_decimal_application, test_learning_analytics KeyError, test_learning_remediation_golden, 2× test_school_first_ui_contract |
| D5 | Integration test coverage | 0% of new modules | ≥80% | New Phase 1-5 modules wired into service.py with integration tests |

### Current status
- D1–D3: ✅ All gates green
- D4: 6 pre-existing failures — not caused by recent work, but should be fixed
- D5: ⚠️ CRITICAL GAP — new Phase 1-5 modules (mastery_engine, next_item_selector, error_classifier, remediation_flow, gamification, concept_state, concept_taxonomy, teacher_report, parent_report_enhanced) have unit tests but are NOT wired into server.py or service.py

---

## Integration Gap Summary

The most valuable single action for learning effectiveness is **wiring the new Phase 1-5 modules into the live recordAttempt flow** in `learning/service.py`. Without this:

- concept_ids_json column stays empty
- mastery levels never update
- error_type classification never fires
- remediation never triggers
- next_item_selector has no data to select from
- gamification badges never unlock
- teacher/parent enhanced reports have no input data

This is the **#1 experiment candidate** for Iteration 1.

---

## Metric Update Protocol

After each experiment iteration:
1. Re-measure affected metrics
2. Update Baseline column with new values
3. Record delta in `logs/experiment_history.jsonl`
4. If metric regressed beyond tolerance, revert the change
