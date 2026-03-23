# Iteration R42 - Hint Evidence Chain

**Date**: 2026-03-24
**Experiment**: EXP-P4-08 Hint Evidence Chain
**Status**: KEEP

## Hypothesis
Enriching hint telemetry with evidence fields (correct_answer, changed_answer, hint_level_used) in the learning bridge and adding analytics metrics (avg_hints_before_success, hint_escalation_rate, by_hint_level_at_submit) enables actionable hint effectiveness reporting without breaking existing hint flow.

## Changes
- server.py: Added 3 fields to learning_event extra (correct_answer, changed_answer, hint_level_used)
- learning/analytics.py: Added 3 new metrics (avg_hints_before_success, hint_escalation_rate, by_hint_level_at_submit), fixed double-counting bug
- tests/test_hint_evidence_chain.py: 20 new tests

## Test Results
- R42 targeted: 31 passed, 0 failures
- Full regression: 1266 passed, 0 failures  
- Delta from R41: +20 tests

## Decision: KEEP
