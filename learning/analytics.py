from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .db import ensure_learning_schema, now_iso


@dataclass(frozen=True)
class SkillStats:
    skill_tag: str
    attempts: int
    correct: int
    accuracy: float
    correct_with_hints: int
    correct_without_hints: int
    hint_dependency: float
    top_mistake_code: Optional[str]
    top_mistake_count: int


def _since_iso(window_days: Optional[int]) -> Optional[str]:
    if window_days is None:
        return None
    dt = datetime.now() - timedelta(days=int(window_days))
    return dt.isoformat(timespec="seconds")


def _fetch_skill_stats(conn: sqlite3.Connection, *, student_id: str, since_iso: Optional[str]) -> List[SkillStats]:
    ensure_learning_schema(conn)

    where = ["e.student_id=?"]
    params: list[Any] = [student_id]
    if since_iso is not None:
        where.append("e.ts >= ?")
        params.append(since_iso)

    sql = f"""
    SELECT
      st.skill_tag AS skill_tag,
      COUNT(*) AS attempts,
      SUM(CASE WHEN e.is_correct=1 THEN 1 ELSE 0 END) AS correct,
      SUM(CASE WHEN e.is_correct=1 AND e.hints_viewed_count>0 THEN 1 ELSE 0 END) AS correct_with_hints,
      SUM(CASE WHEN e.is_correct=1 AND (e.hints_viewed_count IS NULL OR e.hints_viewed_count=0) THEN 1 ELSE 0 END) AS correct_without_hints
    FROM la_attempt_events e
    JOIN la_attempt_skill_tags st ON st.attempt_id = e.id
    WHERE {" AND ".join(where)}
    GROUP BY st.skill_tag
    ORDER BY st.skill_tag ASC
    """

    rows = conn.execute(sql, params).fetchall()

    # Mistake code histogram per skill (wrong only)
    mistakes_sql = f"""
    SELECT st.skill_tag AS skill_tag, e.mistake_code AS mistake_code, COUNT(*) AS cnt
    FROM la_attempt_events e
    JOIN la_attempt_skill_tags st ON st.attempt_id = e.id
    WHERE {" AND ".join(where)} AND e.is_correct=0 AND e.mistake_code IS NOT NULL AND e.mistake_code<>''
    GROUP BY st.skill_tag, e.mistake_code
    """
    mrows = conn.execute(mistakes_sql, params).fetchall()
    top: Dict[str, tuple[str, int]] = {}
    for r in mrows:
        sk = str(r["skill_tag"])
        mc = str(r["mistake_code"])
        cnt = int(r["cnt"] or 0)
        cur = top.get(sk)
        if cur is None or cnt > cur[1] or (cnt == cur[1] and mc < cur[0]):
            top[sk] = (mc, cnt)

    out: List[SkillStats] = []
    for r in rows:
        attempts = int(r["attempts"] or 0)
        correct = int(r["correct"] or 0)
        cwh = int(r["correct_with_hints"] or 0)
        cwo = int(r["correct_without_hints"] or 0)
        accuracy = (correct / attempts) if attempts else 0.0
        denom = max(1, cwh + cwo)
        hint_dependency = cwh / denom
        sk = str(r["skill_tag"])
        tm, tcnt = (top.get(sk) or (None, 0))
        out.append(
            SkillStats(
                skill_tag=sk,
                attempts=attempts,
                correct=correct,
                accuracy=accuracy,
                correct_with_hints=cwh,
                correct_without_hints=cwo,
                hint_dependency=hint_dependency,
                top_mistake_code=tm,
                top_mistake_count=int(tcnt),
            )
        )

    return out


def get_student_analytics(conn: sqlite3.Connection, *, student_id: str, window_days: Optional[int] = 14) -> Dict[str, Any]:
    """Return analytics dict (pure data, JSON-serializable)."""

    since = _since_iso(window_days)
    by_skill = _fetch_skill_stats(conn, student_id=student_id, since_iso=since)

    # Simple time trend windows
    def _acc_for_days(days: int) -> Dict[str, Any]:
        s = _since_iso(days)
        row = conn.execute(
            """
            SELECT COUNT(*) AS n, SUM(CASE WHEN is_correct=1 THEN 1 ELSE 0 END) AS c
            FROM la_attempt_events
            WHERE student_id=? AND (? IS NULL OR ts>=?)
            """,
            (student_id, s, s),
        ).fetchone()
        n = int(row["n"] or 0)
        c = int(row["c"] or 0)
        return {"days": days, "attempts": n, "accuracy": (c / n) if n else 0.0}

    trend = [_acc_for_days(1), _acc_for_days(3), _acc_for_days(7), _acc_for_days(14), _acc_for_days(30)]

    return {
        "student_id": student_id,
        "generated_at": now_iso(),
        "window_days": window_days,
        "by_skill": [s.__dict__ for s in by_skill],
        "trend": trend,
    }


def detect_weak_skills(
    analytics: Dict[str, Any],
    *,
    min_attempts: int = 5,
    low_accuracy: float = 0.70,
    high_hint_dependency: float = 0.60,
    repeated_mistake_count: int = 3,
) -> List[Dict[str, Any]]:
    items = analytics.get("by_skill") or []
    out: List[Dict[str, Any]] = []

    for it in items:
        attempts = int(it.get("attempts") or 0)
        if attempts < min_attempts:
            continue

        acc = float(it.get("accuracy") or 0.0)
        hd = float(it.get("hint_dependency") or 0.0)
        top_mistake = it.get("top_mistake_code")
        top_mistake_cnt = int(it.get("top_mistake_count") or 0)

        reasons: List[str] = []
        if acc < low_accuracy:
            reasons.append("low_accuracy")
        if hd > high_hint_dependency:
            reasons.append("high_hint_dependency")
        if top_mistake and top_mistake_cnt >= repeated_mistake_count:
            reasons.append("repeated_mistake_code")

        if reasons:
            out.append(
                {
                    "skill_tag": str(it.get("skill_tag") or "unknown"),
                    "score_inputs": {
                        "attempts": attempts,
                        "accuracy": acc,
                        "hint_dependency": hd,
                        "top_mistake_code": top_mistake,
                        "top_mistake_count": top_mistake_cnt,
                    },
                    "reasons": sorted(reasons),
                }
            )

    # deterministic order
    out.sort(key=lambda x: (x["skill_tag"]))
    return out


# ---------------------------------------------------------------------------
# Hint effectiveness analytics (Phase 2 / EXP-A1)
# ---------------------------------------------------------------------------


def get_hint_effectiveness_stats(
    conn: sqlite3.Connection,
    *,
    student_id: Optional[str] = None,
    window_days: Optional[int] = 30,
) -> Dict[str, Any]:
    """Compute hint effectiveness metrics from la_attempt_events.

    Measures:
    - hint_success_rate: % of hinted attempts where student answered correctly
    - stuck_after_hint_rate: % of hinted attempts where student still wrong
    - by_level: distribution and success rate per hint level count
    - by_concept: per-concept hint effectiveness breakdown

    Works for a single student (student_id given) or class-wide (None).
    """
    ensure_learning_schema(conn)
    since = _since_iso(window_days)

    where = ["e.hints_viewed_count > 0"]
    params: list[Any] = []
    if student_id is not None:
        where.append("e.student_id = ?")
        params.append(student_id)
    if since is not None:
        where.append("e.ts >= ?")
        params.append(since)

    sql = f"""
    SELECT
      e.hints_viewed_count,
      e.is_correct,
      e.concept_ids_json
    FROM la_attempt_events e
    WHERE {" AND ".join(where)}
    ORDER BY e.ts ASC
    """
    rows = conn.execute(sql, params).fetchall()

    total_hinted = 0
    correct_with_hint = 0
    level_counts: Dict[int, Dict[str, int]] = {}
    concept_counts: Dict[str, Dict[str, int]] = {}

    for r in rows:
        total_hinted += 1
        is_correct = bool(r["is_correct"])
        level = int(r["hints_viewed_count"])
        concepts = json.loads(r["concept_ids_json"] or "[]")

        if is_correct:
            correct_with_hint += 1

        # by level
        if level not in level_counts:
            level_counts[level] = {"total": 0, "correct": 0}
        level_counts[level]["total"] += 1
        if is_correct:
            level_counts[level]["correct"] += 1

        # by concept
        for cid in concepts:
            if cid not in concept_counts:
                concept_counts[cid] = {"total": 0, "correct": 0}
            concept_counts[cid]["total"] += 1
            if is_correct:
                concept_counts[cid]["correct"] += 1

    stuck = total_hinted - correct_with_hint

    def _rate(n: int, d: int) -> float:
        return n / d if d > 0 else 0.0

    return {
        "student_id": student_id,
        "window_days": window_days,
        "generated_at": now_iso(),
        "total_hinted_attempts": total_hinted,
        "correct_with_hint": correct_with_hint,
        "hint_success_rate": _rate(correct_with_hint, total_hinted),
        "stuck_after_hint": stuck,
        "stuck_after_hint_rate": _rate(stuck, total_hinted),
        "by_level": {
            str(lv): {
                "total": d["total"],
                "correct": d["correct"],
                "rate": _rate(d["correct"], d["total"]),
            }
            for lv, d in sorted(level_counts.items())
        },
        "by_concept": {
            cid: {
                "total": d["total"],
                "correct": d["correct"],
                "rate": _rate(d["correct"], d["total"]),
            }
            for cid, d in sorted(concept_counts.items())
        },
    }
