"""R16/EXP-B3: Tests for format_mastery_distribution().

Verifies level counts, percentages, avg score, and histogram from class states.
"""
from learning.concept_state import MasteryLevel, StudentConceptState
from learning.teacher_report import format_mastery_distribution


def _st(sid, cid, level=MasteryLevel.UNBUILT, score=0.0):
    return StudentConceptState(student_id=sid, concept_id=cid,
                               mastery_level=level, mastery_score=score)


def test_empty_class():
    result = format_mastery_distribution({})
    assert result["total_students"] == 0
    assert result["total_concept_entries"] == 0
    assert result["avg_mastery_score"] == 0.0


def test_single_student_single_concept():
    states = {"s1": {"c1": _st("s1", "c1", MasteryLevel.DEVELOPING, 0.35)}}
    r = format_mastery_distribution(states)
    assert r["total_students"] == 1
    assert r["total_concept_entries"] == 1
    assert r["level_counts"]["developing"] == 1
    assert r["avg_mastery_score"] == 0.35


def test_multiple_students_mixed_levels():
    states = {
        "s1": {
            "c1": _st("s1", "c1", MasteryLevel.MASTERED, 0.90),
            "c2": _st("s1", "c2", MasteryLevel.DEVELOPING, 0.30),
        },
        "s2": {
            "c1": _st("s2", "c1", MasteryLevel.APPROACHING_MASTERY, 0.60),
        },
    }
    r = format_mastery_distribution(states)
    assert r["total_students"] == 2
    assert r["total_concept_entries"] == 3
    assert r["level_counts"]["mastered"] == 1
    assert r["level_counts"]["developing"] == 1
    assert r["level_counts"]["approaching_mastery"] == 1
    assert abs(r["avg_mastery_score"] - 0.6) < 0.01


def test_level_percentages():
    states = {
        "s1": {"c1": _st("s1", "c1", MasteryLevel.MASTERED, 0.90)},
        "s2": {"c1": _st("s2", "c1", MasteryLevel.MASTERED, 0.85)},
        "s3": {"c1": _st("s3", "c1", MasteryLevel.DEVELOPING, 0.30)},
        "s4": {"c1": _st("s4", "c1", MasteryLevel.UNBUILT, 0.05)},
    }
    r = format_mastery_distribution(states)
    assert r["level_percentages"]["mastered"] == 0.5  # 2/4
    assert r["level_percentages"]["developing"] == 0.25  # 1/4


def test_score_histogram_buckets():
    states = {
        "s1": {"c1": _st("s1", "c1", MasteryLevel.UNBUILT, 0.10)},   # 0-20%
        "s2": {"c1": _st("s2", "c1", MasteryLevel.DEVELOPING, 0.35)},  # 20-40%
        "s3": {"c1": _st("s3", "c1", MasteryLevel.APPROACHING_MASTERY, 0.55)},  # 40-60%
        "s4": {"c1": _st("s4", "c1", MasteryLevel.APPROACHING_MASTERY, 0.75)},  # 60-80%
        "s5": {"c1": _st("s5", "c1", MasteryLevel.MASTERED, 0.95)},   # 80-100%
    }
    r = format_mastery_distribution(states)
    hist = {h["range"]: h["count"] for h in r["score_histogram"]}
    assert hist["0-20%"] == 1
    assert hist["20-40%"] == 1
    assert hist["40-60%"] == 1
    assert hist["60-80%"] == 1
    assert hist["80-100%"] == 1


def test_review_needed_counted():
    states = {
        "s1": {"c1": _st("s1", "c1", MasteryLevel.REVIEW_NEEDED, 0.70)},
    }
    r = format_mastery_distribution(states)
    assert r["level_counts"]["review_needed"] == 1


def test_all_same_level():
    states = {f"s{i}": {"c1": _st(f"s{i}", "c1", MasteryLevel.MASTERED, 0.90)}
              for i in range(5)}
    r = format_mastery_distribution(states)
    assert r["level_counts"]["mastered"] == 5
    assert r["level_percentages"]["mastered"] == 1.0
    assert r["level_percentages"]["developing"] == 0.0
