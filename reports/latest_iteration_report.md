---

# Iteration R23 / EXP-S3-01: Zone Unlock  Domain-based Progression

## 1. Hypothesis
Domain-based zone grouping with aggregate progress metrics (mastered/approaching/developing/unbuilt counts, weighted progress percentage) gives students clearer progression structure than per-concept boolean unlock flags.

## 2. Scope
- `learning/gamification.py`: Added ZoneProgress dataclass, ZONE_DISPLAY_NAMES, compute_zone_progress(), updated GamificationState and gamification_to_dict
- `tests/test_zone_progress.py`: 12 new tests

## 3. Key Changes
- **ZoneProgress dataclass**: zone_id, display_name_zh, total/mastered/approaching/developing/unbuilt counts, progress_pct (0-100), is_complete
- **ZONE_DISPLAY_NAMES**: Chinese names for all 10 domains (e.g. fraction -> ¤À¼Æ¤ý°ê)
- **compute_zone_progress()**: Aggregates per-concept mastery into domain-level stats with weighted progress
- **Weighted formula**: mastered=100, approaching=70, developing=30 (more informative than binary)
- **Serialization**: gamification_to_dict includes zone_progress list

## 4. Metrics
| Metric | Before | After |
|--------|--------|-------|
| Test count | 822 | 834 |
| Failures | 0 | 0 |
| Zone progress | Per-concept boolean | Domain-level aggregate |

## 5. Decision
**KEEP**  Natural mapping from taxonomy domains to zones. Weighted progress gives informative percentages.

## 6. Next
EXP-S3-02: Boss challenge (mastery-gated)
