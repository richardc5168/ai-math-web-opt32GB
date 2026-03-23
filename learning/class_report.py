from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


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


# ---------------------------------------------------------------------------
# V2: Class report from learning-analytics tables (EXP-P3-07)
# ---------------------------------------------------------------------------

def generate_class_report_v2(
    conn: sqlite3.Connection,
    *,
    student_ids: List[str],
    window_days: int = 14,
    class_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate class report from la_attempt_events + la_student_concept_state.

    Unlike v1, this function does not depend on RBAC tables (classes, class_students).
    The caller provides a list of student_ids directly.
    """
    if not student_ids:
        return {
            "class_name": class_name or "",
            "summary": _empty_summary(window_days),
            "students": [],
            "high_risk_students": [],
            "concept_overview": [],
            "weakness_top": [],
        }

    since = (datetime.now() - timedelta(days=max(1, int(window_days)))).isoformat(timespec="seconds")
    placeholders = ",".join("?" for _ in student_ids)

    # -- Per-student attempt aggregation from la_attempt_events --
    student_rows = conn.execute(
        f"""
        SELECT
            student_id,
            COUNT(*) AS attempts,
            SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) AS correct,
            SUM(CASE WHEN hints_viewed_count > 0 THEN 1 ELSE 0 END) AS hinted,
            SUM(COALESCE(duration_ms, 0)) AS total_duration_ms,
            MAX(ts) AS last_attempt_at
        FROM la_attempt_events
        WHERE student_id IN ({placeholders})
          AND ts >= ?
        GROUP BY student_id
        """,
        (*student_ids, since),
    ).fetchall()

    student_map: Dict[str, Dict[str, Any]] = {}
    for row in student_rows:
        sid = str(row["student_id"])
        attempts = int(row["attempts"] or 0)
        correct = int(row["correct"] or 0)
        hinted = int(row["hinted"] or 0)
        total_ms = int(row["total_duration_ms"] or 0)
        accuracy = _safe_accuracy(correct, attempts)
        hint_dep = round(hinted / attempts, 4) if attempts else 0.0
        student_map[sid] = {
            "student_id": sid,
            "attempts": attempts,
            "correct": correct,
            "accuracy": accuracy,
            "hint_dependency": hint_dep,
            "practice_minutes": round(total_ms / 60000.0, 2),
            "last_attempt_at": row["last_attempt_at"],
        }

    # -- Per-student mastery overview from la_student_concept_state --
    mastery_rows = conn.execute(
        f"""
        SELECT
            student_id,
            mastery_level,
            COUNT(*) AS cnt,
            SUM(CASE WHEN needs_review = 1 THEN 1 ELSE 0 END) AS review_count
        FROM la_student_concept_state
        WHERE student_id IN ({placeholders})
        GROUP BY student_id, mastery_level
        """,
        student_ids,
    ).fetchall()

    mastery_dist: Dict[str, Dict[str, int]] = {}
    review_counts: Dict[str, int] = {}
    for row in mastery_rows:
        sid = str(row["student_id"])
        level = str(row["mastery_level"])
        if sid not in mastery_dist:
            mastery_dist[sid] = {}
        mastery_dist[sid][level] = int(row["cnt"] or 0)
        review_counts[sid] = review_counts.get(sid, 0) + int(row["review_count"] or 0)

    # -- Build student list --
    students: List[Dict[str, Any]] = []
    total_attempts = 0
    total_correct = 0
    active_students = 0
    total_practice_ms = 0

    for sid in student_ids:
        s = student_map.get(sid, {
            "student_id": sid, "attempts": 0, "correct": 0,
            "accuracy": 0.0, "hint_dependency": 0.0,
            "practice_minutes": 0.0, "last_attempt_at": None,
        })
        dist = mastery_dist.get(sid, {})
        needs_review = review_counts.get(sid, 0)
        mastered = dist.get("mastered", 0)
        developing = dist.get("developing", 0)
        approaching = dist.get("approaching_mastery", 0)
        unbuilt = dist.get("unbuilt", 0)
        total_concepts = mastered + developing + approaching + unbuilt + dist.get("review_needed", 0)

        risk = _risk_score(
            accuracy=s["accuracy"],
            hint_dependency=s["hint_dependency"],
            flagged_concepts=needs_review,
        )
        if s["attempts"] > 0:
            active_students += 1
        total_attempts += s["attempts"]
        total_correct += s["correct"]
        total_practice_ms += int(s["practice_minutes"] * 60000)

        students.append({
            **s,
            "mastery_distribution": dist,
            "mastered_concepts": mastered,
            "total_concepts": total_concepts,
            "needs_review": needs_review,
            "risk_score": risk,
            "recommended_action": "targeted_reteach" if risk >= 70 else "monitor" if risk >= 40 else "advance",
        })

    students.sort(key=lambda r: (-r["risk_score"], r["student_id"]))

    # -- Concept overview from la_student_concept_state --
    concept_rows = conn.execute(
        f"""
        SELECT
            concept_id,
            COUNT(*) AS student_count,
            SUM(CASE WHEN mastery_level = 'mastered' THEN 1 ELSE 0 END) AS mastered_count,
            SUM(CASE WHEN mastery_level = 'approaching_mastery' THEN 1 ELSE 0 END) AS approaching_count,
            SUM(CASE WHEN mastery_level = 'developing' THEN 1 ELSE 0 END) AS developing_count,
            SUM(CASE WHEN mastery_level = 'unbuilt' THEN 1 ELSE 0 END) AS unbuilt_count,
            SUM(CASE WHEN mastery_level = 'review_needed' THEN 1 ELSE 0 END) AS review_count
        FROM la_student_concept_state
        WHERE student_id IN ({placeholders})
        GROUP BY concept_id
        ORDER BY concept_id ASC
        """,
        student_ids,
    ).fetchall()

    # -- Weakness detection from la_attempt_events.error_type --
    weakness_rows = conn.execute(
        f"""
        SELECT
            COALESCE(NULLIF(error_type, ''), 'OTHER') AS error_type,
            COUNT(*) AS cnt
        FROM la_attempt_events
        WHERE student_id IN ({placeholders})
          AND ts >= ?
          AND COALESCE(is_correct, 0) != 1
          AND error_type IS NOT NULL
        GROUP BY COALESCE(NULLIF(error_type, ''), 'OTHER')
        ORDER BY cnt DESC
        LIMIT 5
        """,
        (*student_ids, since),
    ).fetchall()

    summary = {
        "student_count": len(student_ids),
        "active_students": active_students,
        "window_days": int(window_days),
        "total_attempts": total_attempts,
        "total_correct": total_correct,
        "average_accuracy": _safe_accuracy(total_correct, total_attempts),
        "total_practice_minutes": round(total_practice_ms / 60000.0, 2),
    }

    return {
        "class_name": class_name or "",
        "summary": summary,
        "students": students,
        "high_risk_students": [s for s in students if s["risk_score"] >= 40][:10],
        "concept_overview": [
            {
                "concept_id": row["concept_id"],
                "student_count": int(row["student_count"] or 0),
                "mastered_count": int(row["mastered_count"] or 0),
                "approaching_count": int(row["approaching_count"] or 0),
                "developing_count": int(row["developing_count"] or 0),
                "unbuilt_count": int(row["unbuilt_count"] or 0),
                "review_count": int(row["review_count"] or 0),
            }
            for row in concept_rows
        ],
        "weakness_top": [
            {
                "error_type": row["error_type"],
                "count": int(row["cnt"] or 0),
            }
            for row in weakness_rows
        ],
    }


def _empty_summary(window_days: int) -> Dict[str, Any]:
    return {
        "student_count": 0,
        "active_students": 0,
        "window_days": int(window_days),
        "total_attempts": 0,
        "total_correct": 0,
        "average_accuracy": 0.0,
        "total_practice_minutes": 0.0,
    }
