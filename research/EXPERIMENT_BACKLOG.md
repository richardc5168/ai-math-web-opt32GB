# Experiment Backlog — AI Math Web

> Last updated: 2026-03-22 | Ranked by priority × impact × feasibility

## Status Legend
- 🔴 Not started
- 🟡 In progress
- 🟢 Completed
- ⏸️ Deferred

---

## Top 10 Experiment Candidates

### EXP-01: Wire concept_taxonomy into recordAttempt (P0) �
- **Hypothesis**: Calling `resolve_concept_ids()` inside `recordAttempt()` will populate `concept_ids_json` on every attempt event, enabling downstream mastery tracking.
- **Scope**: `learning/service.py` (add 5-10 lines), `learning/db.py` (verify column exists)
- **Risk**: Low — pure data enrichment, no behavior change. Column already exists from migration 002.
- **Metrics**: D5 (integration coverage), A1 baseline (concept-tagged events exist)
- **Estimated lines**: ~10-15

### EXP-02: Wire mastery_engine into recordAttempt (P1) �
- **Hypothesis**: Calling `update_mastery()` after each attempt will maintain live `la_student_concept_state` rows, enabling adaptive item selection.
- **Scope**: `learning/service.py` (add ~15 lines)
- **Risk**: Medium — writes to concept_state table on every attempt. Needs EXP-01 first.
- **Metrics**: A2 (concept re-test accuracy baseline), D5
- **Depends on**: EXP-01

### EXP-03: Wire error_classifier into recordAttempt (P1) �
- **Hypothesis**: Calling `classify_error()` on incorrect attempts will populate `error_type` column, enabling error-pattern analysis.
- **Scope**: `learning/service.py` (add ~10 lines)
- **Risk**: Low — read-only classification, stored in existing column.
- **Metrics**: A4 (error_type classification accuracy), D5
- **Depends on**: EXP-01 (for concept context)

### EXP-04: Add /v1/practice/next API endpoint (P2) �
- **Hypothesis**: Exposing `select_next_item()` via API will enable frontends to request adaptive next questions based on student mastery state.
- **Scope**: `server.py` (add endpoint), wire to `next_item_selector.py`
- **Risk**: Medium — new API surface. Needs EXP-02 first (mastery data must exist).
- **Metrics**: C1 (practice completion rate), A1 (hint→success rate)
- **Depends on**: EXP-02

### EXP-05: Wire remediation_flow triggers (P2) �
- **Hypothesis**: Auto-triggering remediation when mastery drops below threshold will improve remediation pass rate.
- **Scope**: `learning/service.py` (add remediation check after mastery update)
- **Risk**: Medium — introduces branching logic. Needs EXP-02 first.
- **Metrics**: A3 (remediation pass rate)
- **Depends on**: EXP-02

### EXP-06: Add /v1/student/concept-state API endpoint (P2) �
- **Hypothesis**: Exposing concept mastery state via API will enable frontends to show progress dashboards and mastery badges.
- **Scope**: `server.py` (add endpoint), read from `la_student_concept_state`
- **Risk**: Low — read-only endpoint.
- **Metrics**: C4 (unlock rate), B2 (teacher report accuracy)
- **Depends on**: EXP-02

### EXP-07: Wire gamification into recordAttempt (P3) �
- **Hypothesis**: Calling `check_unlocks()` and `compute_badges()` after each attempt will generate badge/streak events, enabling engagement features.
- **Scope**: `learning/service.py` (add ~10 lines)
- **Risk**: Low — badge computation is pure, no side effects on learning flow.
- **Metrics**: C4 (gamification unlock rate)
- **Depends on**: EXP-02

### EXP-08: Wire teacher_report into API (P3) �
- **Hypothesis**: Exposing `generate_teacher_report()` via `/v1/teacher/report` will enable teacher-facing dashboards with blocking concepts and at-risk students.
- **Scope**: `server.py` (add endpoint)
- **Risk**: Low — read-only reporting.
- **Metrics**: B2 (teacher report blocking concept accuracy)
- **Depends on**: EXP-02

### EXP-09: Wire parent_report_enhanced into API (P3) �
- **Hypothesis**: Exposing `generate_parent_concept_progress()` will replace or augment existing parent report with concept-level mastery data.
- **Scope**: `server.py` (add endpoint or enrich existing parent report)
- **Risk**: Medium — may conflict with existing parent report flow.
- **Metrics**: B1 (parent report actionability)
- **Depends on**: EXP-02

### EXP-10: Fix 6 pre-existing test failures (P1) �
- **Hypothesis**: Fixing the 6 pre-existing test failures will establish a clean green baseline for all future experiments.
- **Scope**: Various test files and their targets
- **Risk**: Low — test fixes should not change production behavior.
- **Metrics**: D1 (test pass rate → 100%), D4 (pre-existing failures → 0)
- **Depends on**: Nothing

---

## Dependency Graph

```
EXP-01 (concept_taxonomy wiring)
  ├── EXP-02 (mastery_engine wiring)
  │     ├── EXP-04 (/v1/practice/next)
  │     ├── EXP-05 (remediation triggers)
  │     ├── EXP-06 (/v1/student/concept-state)
  │     ├── EXP-07 (gamification wiring)
  │     ├── EXP-08 (teacher_report API)
  │     └── EXP-09 (parent_report_enhanced API)
  └── EXP-03 (error_classifier wiring)

EXP-10 (fix pre-existing failures) — independent
```

## Iteration Plan (Phase 1 — COMPLETE)

| Iteration | Experiment | Rationale | Status |
|-----------|-----------|-----------|--------|
| 1 | EXP-01 | Foundation — all downstream modules need concept_ids | ✅ |
| 2 | EXP-03 | Low-risk, independent of mastery, establishes error data | ✅ |
| 3 | EXP-02 | Core mastery engine — unlocks 6 downstream experiments | ✅ |
| 4 | EXP-06 | concept-state API | ✅ |
| 5 | EXP-05 | remediation signals | ✅ |
| 6 | EXP-07 | gamification wiring | ✅ |
| 7 | EXP-08 | teacher_report API | ✅ |
| 8 | EXP-09 | parent_report_enhanced API | ✅ |
| 9 | EXP-04 | practice/concept-next API | ✅ |
| 10 | EXP-10 | Fix pre-existing failures | ✅ |

---

## Phase 2: Learning Effectiveness Optimization

### Stage 1 — Three Rounds Each (strict sequential)

#### Direction A: Hint Effectiveness

##### EXP-A1: Hint effectiveness analytics function (P0) �
- **Hypothesis**: Adding `get_hint_effectiveness_stats()` to analytics.py will enable measuring hint success rate, stuck-after-hint rate, and by-level distribution from existing data.
- **Scope**: `learning/analytics.py` (add ~50 lines)
- **Risk**: Low — read-only analytics, no behavior change
- **Metrics**: A1 (hint_success_rate), C4 (stuck_after_hint_rate)
- **Depends on**: None (data already collected)

##### EXP-A2: Hint effectiveness API endpoint (P1) �
- **Hypothesis**: Exposing hint effectiveness via `/v1/student/hint-effectiveness` enables teacher/parent dashboards to show hint quality.
- **Scope**: `server.py` (add endpoint)
- **Risk**: Low — read-only endpoint
- **Depends on**: EXP-A1

##### EXP-A3: Teacher-readable hint effectiveness summary (P1) �
- **Hypothesis**: Adding hint effectiveness data to teacher reports improves teacher ability to identify stuck students and ineffective hint levels.
- **Scope**: `learning/teacher_report.py` (integrate hint stats)
- **Risk**: Low — additive to existing report
- **Depends on**: EXP-A1

#### Direction B: Mastery Scoring Validation

##### EXP-B1: Mastery transition edge case audit (P1) �
- **Hypothesis**: Auditing mastery state transitions against edge cases (rapid correct→wrong, hint-heavy paths) will reveal scoring issues.
- **Scope**: `learning/mastery_engine.py`, tests
- **Risk**: Low — test-only or minimal scoring fix

##### EXP-B2: Mastery transition tests (P1) �
- **Hypothesis**: Adding targeted tests for all promotion/demotion paths ensures mastery scoring doesn't regress.
- **Scope**: `tests/test_mastery_transitions.py`
- **Risk**: None — test-only

##### EXP-B3: Mastery data in reports (P2) �
- **Hypothesis**: Adding mastery score distribution to teacher report increases visibility into class-wide mastery status.
- **Scope**: `learning/teacher_report.py`, `learning/class_report.py`
- **Depends on**: EXP-B1, EXP-B2

#### Direction C: Teacher Report Readability

##### EXP-C1: Teacher report field audit (P1) 🔴
- **Hypothesis**: Auditing teacher report output structure reveals missing or confusing fields.
- **Scope**: `learning/teacher_report.py`, tests
- **Risk**: Low — analysis + test

##### EXP-C2: One-page teacher summary (P2) 🔴
- **Hypothesis**: Adding a one-page summary section to teacher report improves teacher decision speed.
- **Scope**: `learning/teacher_report.py`
- **Depends on**: EXP-C1

##### EXP-C3: Blocking concept decision support (P2) 🔴
- **Hypothesis**: Enriching blocking concept entries with recommended actions improves teacher intervention quality.
- **Scope**: `learning/teacher_report.py`
- **Depends on**: EXP-C1

### Stage 2 — Only After Stage 1 Complete
- EXP-S2-01: Adaptive selector — refine select_next_item strategies
- EXP-S2-02: Prerequisite fallback — auto-detect missing prerequisites
- EXP-S2-03: Parent report — actionable concept-level progress

### Stage 3 — Only After Stage 2 Complete
- EXP-S3-01: Zone unlock (mastery-gated)
- EXP-S3-02: Boss (mastery-gated)
- EXP-S3-03: Badge refinement

## Phase 2 Iteration Plan

| Iteration | Experiment | Direction |
|-----------|-----------|-----------|
| 11 | EXP-A1 | Hint Effectiveness Round 1 |
| 12 | EXP-A2 | Hint Effectiveness Round 2 |
| 13 | EXP-A3 | Hint Effectiveness Round 3 |
| 14 | EXP-B1 | Mastery Scoring Round 1 |
| 15 | EXP-B2 | Mastery Scoring Round 2 |
| 16 | EXP-B3 | Mastery Scoring Round 3 |
| 17 | EXP-C1 | Teacher Report Round 1 |
| 18 | EXP-C2 | Teacher Report Round 2 |
| 19 | EXP-C3 | Teacher Report Round 3 |
