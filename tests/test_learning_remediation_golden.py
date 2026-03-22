import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from learning.db import ensure_learning_schema
from learning.service import recordAttempt
from learning.analytics import get_student_analytics
from learning.datasets import load_dataset
from learning.remediation import generate_remediation_plan


def test_remediation_plan_matches_golden(tmp_path):
    db = tmp_path / "t.db"
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    ensure_learning_schema(conn)
    conn.close()

    # Use a recent timestamp so data falls within the 30-day analytics window
    ts0 = (datetime.now() - timedelta(days=3)).isoformat(timespec="seconds")
    for i in range(3):
        recordAttempt(
            {
                "student_id": "s1",
                "question_id": f"qW{i}",
                "timestamp": ts0,
                "is_correct": False,
                "answer_raw": "x",
                "mistake_code": "concept",
                "skill_tags": ["分數/小數"],
            },
            db_path=str(db),
        )
    for i in range(2):
        recordAttempt(
            {
                "student_id": "s1",
                "question_id": f"qC{i}",
                "timestamp": ts0,
                "is_correct": True,
                "answer_raw": "y",
                "hints_viewed_count": 1,
                "hint_steps_viewed": [1],
                "skill_tags": ["分數/小數"],
            },
            db_path=str(db),
        )
    recordAttempt(
        {
            "student_id": "s1",
            "question_id": "qC_nohint",
            "timestamp": ts0,
            "is_correct": True,
            "answer_raw": "z",
            "hints_viewed_count": 0,
            "skill_tags": ["分數/小數"],
        },
        db_path=str(db),
    )

    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    analytics = get_student_analytics(conn, student_id="s1", window_days=30)
    # Force stable generated_at for golden
    analytics["generated_at"] = "2026-02-15T00:00:00"

    bp = load_dataset("mock_exam")
    plan = generate_remediation_plan(analytics, blueprint=bp, top_k=3)

    golden = json.loads(Path("tests/fixtures/learning_remediation_plan_golden.json").read_text(encoding="utf-8"))
    assert plan == golden
