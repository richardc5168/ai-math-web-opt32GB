# Iteration R32  EXP-P3-07: Unify class_report with learning DB

## Status: COMPLETE

## Hypothesis
Switching class_report to query learning module la_attempt_events with concept enrichment and error classification improves class report quality.

## Changes Made
- learning/class_report.py: Added generate_class_report_v2() (~170 lines) querying la_attempt_events + la_student_concept_state with 5-level mastery distribution, error_type for weakness detection, risk scoring. Takes student_ids directly - no RBAC dependency. Old v1 preserved.
- tests/test_class_report_v2.py: 13 new tests across 5 test classes.

## Metrics
- Tests: 926 -> 939 (0 failures)
- class_report uses learning DB: No -> Yes (v2)
- Mastery model: Binary -> 5-level enum
- Error classification: error_tag -> error_type

## Decision: KEEP

## Next: R33/EXP-P3-08 Teaching Guide Expansion
