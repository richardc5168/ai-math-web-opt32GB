# Iteration R33  EXP-P3-08: Teaching Guide Expansion

## Status: COMPLETE

## Hypothesis
Adding teaching guides for all 10 concept domains eliminates generic fallback guides.

## Changes Made
- learning/teaching.py: Added 7 new TeachingGuide entries (decimal, volume, geometry, linear, quadratic, application/average). Added 10 English key aliases so both Chinese and English skill_tags work.
- tests/test_teaching_guide_expansion.py: 42 new tests covering all domains, structure, fallback, and alias behavior.

## Metrics
- Tests: 939 -> 981 (0 failures)
- Domains with guides: 6 -> 10 (100% coverage)

## Decision: KEEP

## Next: R34/EXP-P3-09 Test Coverage
