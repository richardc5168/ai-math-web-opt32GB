import sqlite3
from datetime import datetime, timedelta

from learning.db import ensure_learning_schema
from learning.service import recordAttempt, getStudentAnalytics


def _recent_iso(days_ago: int) -> str:
    """Return ISO timestamp for N days ago, ensuring it falls within any reasonable analytics window."""
    return (datetime.now() - timedelta(days=days_ago)).isoformat(timespec="seconds")


def test_learning_analytics_by_skill_and_trend(tmp_path):
    db = tmp_path / "t.db"
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    ensure_learning_schema(conn)
    conn.close()

    # Insert attempts with recent timestamps so they fall within the 30-day window
    recordAttempt(
        {
            "student_id": "s1",
            "question_id": "q1",
            "timestamp": _recent_iso(3),
            "is_correct": False,
            "answer_raw": "1",
            "hints_viewed_count": 0,
            "mistake_code": "concept",
            "skill_tags": ["分數/小數"],
        },
        db_path=str(db),
    )
    recordAttempt(
        {
            "student_id": "s1",
            "question_id": "q2",
            "timestamp": _recent_iso(2),
            "is_correct": True,
            "answer_raw": "2",
            "hints_viewed_count": 2,
            "hint_steps_viewed": [1, 2],
            "skill_tags": ["分數/小數"],
        },
        db_path=str(db),
    )
    recordAttempt(
        {
            "student_id": "s1",
            "question_id": "q3",
            "timestamp": _recent_iso(1),
            "is_correct": True,
            "answer_raw": "3",
            "hints_viewed_count": 0,
            "skill_tags": ["比例"],
        },
        db_path=str(db),
    )

    analytics = getStudentAnalytics("s1", 30, db_path=str(db))
    by_skill = {x["skill_tag"]: x for x in analytics["by_skill"]}
    assert by_skill["分數/小數"]["attempts"] == 2
    assert by_skill["比例"]["attempts"] == 1
    assert 0.0 <= by_skill["分數/小數"]["accuracy"] <= 1.0

    assert isinstance(analytics["trend"], list) and len(analytics["trend"]) >= 1
