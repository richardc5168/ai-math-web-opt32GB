---

# Iteration R24 / EXP-S3-02: Boss Challenge (mastery-gated)

## 1. Hypothesis
Boss challenge generation with concept+transitive prerequisites as challenge pool and depth-scaled difficulty provides meaningful comprehensive assessment.

## 2. Scope
- `learning/gamification.py`: Added BossChallenge dataclass, generate_boss_challenge(), get_available_bosses()
- `tests/test_boss_challenge.py`: 12 new tests

## 3. Key Changes
- **BossChallenge dataclass**: concept_id, display_name_zh, challenge_concept_ids, difficulty (easy/normal/hard), is_available, is_completed, prereq_depth
- **generate_boss_challenge()**: Builds challenge pool from concept + all transitive prereqs. Difficulty scales by depth (0=easy, 1-3=normal, 4+=hard). Available only when concept + all prereqs MASTERED.
- **get_available_bosses()**: Filters to only currently available boss challenges.

## 4. Metrics
| Metric | Before | After |
|--------|--------|-------|
| Test count | 834 | 846 |
| Failures | 0 | 0 |
| Boss challenge | Boolean flag only | Full challenge structure |

## 5. Decision
**KEEP** -- Prerequisite depth maps naturally to difficulty. Challenge pool gives comprehensive mastery verification.

## 6. Next
EXP-S3-03: Badge refinement
