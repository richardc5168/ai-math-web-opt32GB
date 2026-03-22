# Stop Rules — AutoResearch

## Mandatory Revert Triggers
1. Core tests fail (>2 new failures) and cannot be fixed within the iteration
2. Existing question generation / grading / report flow is broken
3. Metric improvement is negligible but complexity/maintenance cost is high
4. Optimization is purely cosmetic with no educational value
5. Data schema change makes logs/reports un-trackable
6. Parent or teacher reports become harder to understand
7. Significant regression in unrelated test areas
8. One metric improves at the expense of other core metrics

## Partial Keep Rules
If full revert is too disruptive, keep only:
- Low-risk, proven-effective portions
- New analytics functions (read-only, no side effects)
- Test additions (never revert passing tests)

## Direction Priority Downgrade Triggers
1. Two consecutive rounds in the same direction show no measurable improvement
2. Direction has been explicitly marked as failed with still-valid root cause
3. Direction yields only cosmetic improvements

## Stop Conditions (Campaign Level)
1. Three consecutive iterations across all directions fail to improve any A/B metric
2. Security vulnerability discovered — pause and fix immediately
3. Fundamental architecture change needed — pause and plan
4. All backlog items completed or deferred

## Iteration Size Limits
- Integration wiring: max 50 lines changed, 3 files
- New analytics function: max 80 lines, 2 files
- New API endpoint: max 100 lines, 3 files + test
- Bug fix: max 30 lines, 2 files
- Test-only: unlimited
