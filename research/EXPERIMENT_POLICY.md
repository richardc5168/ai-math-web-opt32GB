# Experiment Policy — AI Math Web

> Last updated: 2026-03-22 | Governs all research iterations

## 1. Iteration Format

Every iteration follows a strict 10-step cycle:

```
1. Pre-read     → AGENTS.md, logs/*, reports/*, research/*
2. Hypothesis   → One clear, falsifiable statement
3. Scope        → Which files/modules will be touched
4. Risk check   → What could break, how to detect it
5. Implement    → Minimal code change for the hypothesis
6. Test         → pytest + node --test + bank validation
7. Measure      → Collect before/after metric data
8. Decide       → Keep (metric improved) or Revert (metric regressed)
9. Log          → Write to experiment_history.jsonl, change_history.jsonl, lessons_learned.jsonl
10. Report      → Update reports/latest_iteration_report.md
```

## 2. Experiment Selection Priority

Experiments are selected in this order of impact:

| Priority | Area | Rationale |
|----------|------|-----------|
| P0 | Learning trajectory integration | Wiring new modules into live flow — everything depends on this |
| P1 | Concept / mastery flow | Foundation for adaptive learning |
| P2 | Hint quality & remediation | Direct impact on learning outcomes |
| P3 | Report quality (teacher + parent) | Visibility into student progress |
| P4 | Next-item selector | Adaptive practice sequencing |
| P5 | Gamification | Engagement and retention |

## 3. One Axis Per Iteration

每輪只做一個主軸。Never change more than one subsystem per iteration.

**Good**: "Wire concept_taxonomy into recordAttempt to populate concept_ids_json"
**Bad**: "Wire concept_taxonomy + mastery_engine + error_classifier all at once"

## 4. Keep / Revert Criteria

### KEEP if:
- All existing tests pass (0 new failures)
- At least one North Star metric improved or baseline established
- No security regression

### REVERT if:
- Any existing test fails that was previously passing
- A North Star metric regressed beyond tolerance (>5% relative)
- Runtime errors in production paths

### DEFER if:
- The change works but exposes a deeper architectural issue
- Implementation is incomplete but direction is proven

## 5. Stop Conditions

Pause the iteration loop and escalate to human review when:
- 3 consecutive iterations fail to improve any metric
- A security vulnerability is discovered
- A fundamental architecture change is needed
- The experiment backlog is exhausted

## 6. Change Size Limits

| Change Type | Max Lines Changed | Max Files Changed |
|-------------|-------------------|-------------------|
| Integration wiring | 50 | 3 |
| New feature | 100 | 5 |
| Refactor | 80 | 4 |
| Bug fix | 30 | 2 |
| Test-only | unlimited | unlimited |

## 7. Required Validation Suite

Every iteration must run at minimum:

```bash
# Python tests
python -m pytest --tb=short -q

# JS tests
node --test tests_js/*.spec.mjs

# Bank validation
python tools/validate_all_elementary_banks.py

# Mirror sync
python scripts/verify_all.py
```

## 8. Experiment History Format

Each experiment is logged in `logs/experiment_history.jsonl`:

```json
{
  "iteration": 1,
  "ts": "2026-03-22T...",
  "hypothesis": "Wiring concept_taxonomy into recordAttempt will populate concept_ids_json",
  "area": "learning-trajectory-integration",
  "priority": "P0",
  "files_changed": ["learning/service.py"],
  "metrics_before": {"concept_ids_populated": 0},
  "metrics_after": {"concept_ids_populated": 100},
  "decision": "KEEP",
  "lesson": "...",
  "next_experiment": "..."
}
```

## 9. Rollback Protocol

1. `git stash` or `git checkout -- <files>` for uncommitted changes
2. Re-run full validation suite
3. Confirm all tests pass
4. Log the revert in experiment_history.jsonl with `decision: "REVERT"`

## 10. Backlog Management

- Experiment backlog lives in `research/EXPERIMENT_BACKLOG.md`
- Each experiment has: ID, priority, hypothesis, scope, estimated risk
- After each iteration, re-prioritize the backlog based on findings
- New experiment ideas discovered during iteration go to backlog, not inline
