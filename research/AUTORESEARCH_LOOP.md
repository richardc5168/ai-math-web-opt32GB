# AutoResearch Loop — Phase 2

## Loop Steps (per iteration)

1. **Pre-read**: Read experiment_history.jsonl, lessons_learned.jsonl, failed_hypotheses.jsonl
2. **Hypothesis**: Propose 1-3 candidates from EXPERIMENT_BACKLOG
3. **Select**: Pick ONE hypothesis based on impact × risk × measurability
4. **Scope**: Define files to change (max limits from STOP_RULES.md)
5. **Implement**: Make minimal changes
6. **Test**: Run `pytest tests/ --tb=no -q` — must be zero failures
7. **Measure**: Compare metrics before/after
8. **Decide**: KEEP / PARTIAL KEEP / REVERT
9. **Log**: Update experiment_history.jsonl, change_history.jsonl, lessons_learned.jsonl
10. **Report**: Update latest_iteration_report.md

## Phase 2 Directions (strict order)

### Stage 1 — Three rounds each, sequential
| Direction | Round 1 | Round 2 | Round 3 |
|-----------|---------|---------|---------|
| A. Hint Effectiveness | Analytics function | API endpoint | Teacher summary |
| B. Mastery Scoring | Validate transitions | Edge case tests | Report integration |
| C. Teacher Report | Core field audit | One-page summary | Decision value |

### Stage 2 — Only after Stage 1 stable
- Adaptive selector refinement
- Prerequisite fallback
- Parent report enhancement

### Stage 3 — Only after Stage 2 stable
- Zone unlock (mastery-gated)
- Boss (mastery-gated)
- Badge (mastery-gated)

## Current State
- Phase 1 (R0-R10): COMPLETE — 10/10 modules wired, 704 tests, 0 failures
- Phase 2 Stage 1: STARTING — Direction A (Hint Effectiveness), Round 1
