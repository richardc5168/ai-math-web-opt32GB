from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def _safe_accuracy(correct: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((correct / total) * 100.0, 2)


def _risk_score(*, accuracy: float, hint_dependency: float, flagged_concepts: int) -> int:
    score = 100 - int(accuracy)
    score += int(hint_dependency * 25)
    score += min(20, int(flagged_concepts) * 5)
    return max(0, min(100, score))


def generate_class_report(
    conn: sqlite3.Connection,
    *,
    class_id: int,
    teacher_account_id: int,
    window_days: int = 14,
) -> Dict[str, Any]:
    since = (datetime.now() - timedelta(days=max(1, int(window_days)))).isoformat(timespec="seconds")

    class_row = conn.execute(
        """
        SELECT c.id, c.name, c.grade, c.created_at,
               s.id AS school_id, s.name AS school_name, s.school_code
        FROM classes c
        JOIN schools s ON s.id = c.school_id
        WHERE c.id = ? AND c.teacher_account_id = ?
        """,
        (int(class_id), int(teacher_account_id)),
    ).fetchone()
    if not class_row:
        raise ValueError("class not found for teacher")

    student_rows = conn.execute(
        """
        SELECT
            st.id,
            st.display_name,
            st.grade,
            st.current_concept_id,
            COUNT(a.id) AS attempts,
            SUM(CASE WHEN a.is_correct = 1 THEN 1 ELSE 0 END) AS correct,
            SUM(CASE WHEN COALESCE(a.hint_level_used, 0) > 0 THEN 1 ELSE 0 END) AS hinted,
            SUM(COALESCE(a.time_spent_sec, 0)) AS practice_seconds,
            MAX(a.ts) AS last_attempt_at,
            SUM(CASE WHEN COALESCE(sc.flag_teacher, 0) = 1 THEN 1 ELSE 0 END) AS flagged_concepts,
            SUM(CASE WHEN COALESCE(sc.completed, 0) = 1 THEN 1 ELSE 0 END) AS completed_concepts
        FROM class_students cs
        JOIN students st ON st.id = cs.student_id
        LEFT JOIN attempts a ON a.student_id = st.id AND a.ts >= ?
        LEFT JOIN student_concepts sc ON sc.student_id = st.id
        WHERE cs.class_id = ?
        GROUP BY st.id, st.display_name, st.grade, st.current_concept_id
        ORDER BY st.id ASC
        """,
        (since, int(class_id)),
    ).fetchall()

    students: List[Dict[str, Any]] = []
    total_attempts = 0
    total_correct = 0
    active_students = 0
    total_practice_seconds = 0

    for row in student_rows:
        attempts = int(row["attempts"] or 0)
        correct = int(row["correct"] or 0)
        hinted = int(row["hinted"] or 0)
        practice_seconds = int(row["practice_seconds"] or 0)
        accuracy = _safe_accuracy(correct, attempts)
        hint_dependency = round(hinted / attempts, 4) if attempts else 0.0
        flagged_concepts = int(row["flagged_concepts"] or 0)
        risk_score = _risk_score(
            accuracy=accuracy,
            hint_dependency=hint_dependency,
            flagged_concepts=flagged_concepts,
        )
        if attempts > 0:
            active_students += 1
        total_attempts += attempts
        total_correct += correct
        total_practice_seconds += practice_seconds

        students.append(
            {
                "student_id": int(row["id"]),
                "display_name": row["display_name"],
                "grade": row["grade"],
                "current_concept_id": row["current_concept_id"],
                "attempts": attempts,
                "correct": correct,
                "accuracy": accuracy,
                "hint_dependency": hint_dependency,
                "practice_minutes": round(practice_seconds / 60.0, 2),
                "last_attempt_at": row["last_attempt_at"],
                "flagged_concepts": flagged_concepts,
                "completed_concepts": int(row["completed_concepts"] or 0),
                "risk_score": risk_score,
                "recommended_action": "targeted_reteach" if risk_score >= 70 else "monitor" if risk_score >= 40 else "advance",
            }
        )

    students.sort(key=lambda row: (-int(row["risk_score"]), row["display_name"]))

    concept_rows = conn.execute(
        """
        SELECT
            sc.concept_id,
            COUNT(*) AS student_count,
            SUM(CASE WHEN COALESCE(sc.completed, 0) = 1 THEN 1 ELSE 0 END) AS completed_count,
            SUM(CASE WHEN COALESCE(sc.flag_teacher, 0) = 1 THEN 1 ELSE 0 END) AS flagged_count
        FROM class_students cs
        JOIN student_concepts sc ON sc.student_id = cs.student_id
        WHERE cs.class_id = ?
        GROUP BY sc.concept_id
        ORDER BY sc.concept_id ASC
        """,
        (int(class_id),),
    ).fetchall()

    weakness_rows = conn.execute(
        """
        SELECT
            COALESCE(NULLIF(a.error_tag, ''), 'OTHER') AS error_tag,
            COUNT(*) AS cnt
        FROM class_students cs
        JOIN attempts a ON a.student_id = cs.student_id
        WHERE cs.class_id = ?
          AND a.ts >= ?
          AND COALESCE(a.is_correct, 0) != 1
        GROUP BY COALESCE(NULLIF(a.error_tag, ''), 'OTHER')
        ORDER BY cnt DESC, error_tag ASC
        LIMIT 5
        """,
        (int(class_id), since),
    ).fetchall()

    summary = {
        "student_count": len(students),
        "active_students": active_students,
        "window_days": int(window_days),
        "total_attempts": total_attempts,
        "total_correct": total_correct,
        "average_accuracy": _safe_accuracy(total_correct, total_attempts),
        "total_practice_minutes": round(total_practice_seconds / 60.0, 2),
    }

    return {
        "class": _row_to_dict(class_row),
        "summary": summary,
        "students": students,
        "high_risk_students": students[:10],
        "concept_overview": [
            {
                "concept_id": row["concept_id"],
                "student_count": int(row["student_count"] or 0),
                "completed_count": int(row["completed_count"] or 0),
                "flagged_count": int(row["flagged_count"] or 0),
            }
            for row in concept_rows
        ],
        "weakness_top": [
            {
                "error_tag": row["error_tag"],
                "count": int(row["cnt"] or 0),
            }
            for row in weakness_rows
        ],
    }
