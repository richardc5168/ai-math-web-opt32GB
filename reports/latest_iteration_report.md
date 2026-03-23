---

# Iteration R29 / EXP-P3-04: Hint Escalation Wiring — Phase 3 Stage 2 exp 1/3

## 1. Hypothesis
Wiring `remediation_flow.py` hint escalation into the learning service replaces static hint fallback with adaptive, session-aware hints.

## 2. Scope
- `learning/service.py`: Added `getNextHint()` function + remediation_flow imports
- `learning/__init__.py`: Exported `getNextHint`
- `server.py`: Added `learning_get_next_hint` import, `student_id`/`concept_id` fields to `HintNextRequest`, adaptive escalation block in `/v1/hints/next`
- `tests/test_hint_escalation_wiring.py`: 12 new tests

## 3. Key Changes
- **`getNextHint(student_id, question_id, concept_id)`**: Builds `HintSession` from DB state (hints already shown, wrong count on concept), calls `remediation_flow.get_next_hint()`, returns `RemediationAction` as dict with `action_type`, `hint_level`, `reason`, `flag_teacher`, `session_state`
- **`/v1/hints/next` adaptive mode**: When `student_id` and `question_id` are provided, calls `getNextHint()` to determine escalation level, maps to `_build_hints()` text content, returns `mode: "adaptive"` with `action_type` and `flag_teacher`
- **Backward compatible**: Without `student_id`, falls through to existing static `mode: "fallback"`

## 4. Metrics
| Metric | Before | After |
|--------|--------|-------|
| Test count | 893 | 905 |
| Failures | 0 | 0 |
| Hint mode | static fallback only | adaptive + fallback |

## 5. Decision
**KEEP** — Clean wiring with full backward compatibility. Static fallback preserved as safety net.
