---

# Iteration R30 / EXP-P3-05: Auto Remediation Trigger — Phase 3 Stage 2 exp 2/3

## 1. Hypothesis
Surfacing `remediation_concepts` and `mastery` arrays in `/v1/answers/submit` response enables frontend to auto-trigger remediation flows without extra API calls.

## 2. Scope
- `server.py`: Added `remediation_concepts` and `mastery` fields to submit response `learning` block
- `tests/test_auto_remediation_trigger.py`: 9 new tests

## 3. Key Changes
- **`/v1/answers/submit` response enrichment**: The `learning_ack` dict from `recordAttempt()` already contained `remediation_concepts` and `mastery` data, but these were discarded. Added 2 lines to pass them through with `.get(key, [])` and `isinstance` guard for safe defaults.
- **Backward compatible**: New fields are arrays, default to empty. No existing fields changed.

## 4. Metrics
| Metric | Before | After |
|--------|--------|-------|
| Test count | 905 | 914 |
| Failures | 0 | 0 |
| Submit learning fields | recorded, attempt_id | recorded, attempt_id, remediation_concepts, mastery |

## 5. Decision
**KEEP** — Minimal 2-line change surfaces already-computed data to the frontend.
