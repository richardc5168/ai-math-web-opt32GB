# Iteration R43+R44 — Hint Evidence Chain v2 + Mastery Scoring Calibration

**Date**: 2026-03-24
**Experiments**: EXP-P4-08b Hint Evidence Chain Enhancement + EXP-P4-09 Mastery Scoring Calibration
**Status**: KEEP

## Hypothesis (R43)
If we add `hint_open_ts`, `hint_sequence`, and derived `avg_hint_dwell_ms` metrics to the hint evidence chain, hint effectiveness reporting gains time-domain analysis capability without breaking existing hint flow.

## Hypothesis (R44)
If mastery scoring considers `first_answer_correct` and `attempts_count` evidence (not just final is_correct), adaptive decisions become more calibrated to actual student confidence.

## Changes

### R43 — Hint Evidence Chain Enhancement
- server.py: Extract `hint_open_ts` and `hint_sequence` from body.meta, pass to extra
- learning/analytics.py: Add `avg_hint_dwell_ms` metric from hint_open_ts spans
- tests/test_r43_hint_evidence_enhanced.py: 10 new tests

### R44 — Mastery Scoring Calibration
- server.py: Extract started_at, first_answer, attempts_count, selection_reason from submit body
- learning/validator.py: Add 5 new fields to ValidatedAttemptEvent
- learning/service.py: Populate 5 ghost DB columns; add `_is_first_answer_correct()` helper
- learning/mastery_engine.py: Add first_answer_correct_bonus and multi_attempt_penalty rules
- learning/mastery_config.py: Add 2 new score deltas (+0.05, -0.03)
- tests/test_r44_mastery_calibration.py: 24 new tests
- tests/test_transfer_review_deltas.py: Updated 5 expected scores

## Test Results
- R43 targeted: 10 passed, 0 failures
- R44 targeted: 24 passed, 0 failures
- Full regression: 1300 passed, 0 failures
- Delta from R42: +34 new tests

## Decision: KEEP
