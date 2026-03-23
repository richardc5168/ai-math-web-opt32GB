"""Learning / Analytics endpoints extracted from server.py (R40/EXP-P4-06).

Covers:
  /v1/learning/weekly_report
  /v1/learning/practice_next
  /v1/learning/remediation_plan
  /v1/student/concept-state
  /v1/student/hint-effectiveness
  /v1/student/concept-progress
  /v1/student/before-after
  /v1/practice/concept-next
  /v1/adaptive/state
  /v1/adaptive/dashboard

All shared helpers (db, auth, learning_* imports) are accessed via lazy
``import server as _srv`` inside each handler body to avoid circular imports.
"""
from __future__ import annotations

import json
import random
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
learning_router = APIRouter(tags=["learning"])


# ---------------------------------------------------------------------------
# Pydantic request models (moved from server.py)
# ---------------------------------------------------------------------------

class WeeklyReportRequest(BaseModel):
    student_id: int = Field(..., ge=1)
    window_days: int = Field(default=7, ge=1, le=60)
    top_k: int = Field(default=3, ge=1, le=5)
    questions_per_skill: int = Field(default=3, ge=1, le=8)


class PracticeNextRequest(BaseModel):
    student_id: int = Field(..., ge=1)
    skill_tag: str = Field(..., min_length=1)
    window_days: int = Field(default=14, ge=1, le=60)
    topic_key: Optional[str] = Field(default=None, description="Optional override for engine generator key")
    seed: Optional[int] = Field(default=None, description="Optional deterministic seed for question generation")


class RemediationPlanRequest(BaseModel):
    student_id: int = Field(..., ge=1)
    dataset_name: Optional[str] = Field(default=None)
    window_days: int = Field(default=14, ge=1, le=60)


class BeforeAfterRequest(BaseModel):
    student_id: int = Field(..., ge=1)
    intervention_date: Optional[str] = Field(default=None, description="ISO date (YYYY-MM-DD). If omitted, midpoint of available data is used.")
    pre_window_days: int = Field(default=14, ge=1, le=90)
    post_window_days: int = Field(default=14, ge=1, le=90)


class ConceptNextRequest(BaseModel):
    student_id: int = Field(..., ge=1)
    domain: Optional[str] = Field(default=None, description="Filter by domain: fraction, decimal, percent, etc.")
    recent_item_ids: Optional[List[str]] = Field(default=None, description="Recently shown item IDs to avoid repetition")


# ---------------------------------------------------------------------------
# Helper functions (moved from server.py — only used within this module)
# ---------------------------------------------------------------------------

def _skill_snapshot_from_analytics(analytics: Dict[str, Any], *, skill_tag: str) -> Dict[str, Any]:
    for it in (analytics.get("by_skill") or []):
        if not isinstance(it, dict):
            continue
        if str(it.get("skill_tag") or "") == str(skill_tag):
            return {
                "attempts": int(it.get("attempts") or 0),
                "correct": int(it.get("correct") or 0),
                "accuracy": float(it.get("accuracy") or 0.0),
                "hint_dependency": float(it.get("hint_dependency") or 0.0),
                "top_mistake_code": it.get("top_mistake_code"),
                "top_mistake_count": int(it.get("top_mistake_count") or 0),
            }
    return {
        "attempts": 0,
        "correct": 0,
        "accuracy": 0.0,
        "hint_dependency": 0.0,
        "top_mistake_code": None,
        "top_mistake_count": 0,
    }


def _build_concept_question_pool(domain=None):
    """Build virtual QuestionItem pool from concept taxonomy for adaptive selection."""
    import server as _srv
    items = []
    if _srv.learning_concept_taxonomy is None or _srv.LearningQuestionItem is None:
        return items
    for cid, info in _srv.learning_concept_taxonomy.items():
        if domain and info.get("domain") != domain:
            continue
        for diff in ("easy", "normal", "hard"):
            items.append(_srv.LearningQuestionItem(
                item_id=f"{cid}_{diff}",
                concept_ids=[cid],
                difficulty=diff,
                prerequisite_concepts=info.get("prerequisites", []),
                topic_tags=[info.get("domain", "")],
                is_application=(diff == "hard"),
            ))
    return items


class _SeedContext:
    """Context manager for deterministic random seed."""
    def __init__(self, seed: Optional[int]):
        self._seed = seed

    def __enter__(self):
        self._state = random.getstate()
        if self._seed is not None:
            random.seed(int(self._seed))

    def __exit__(self, exc_type, exc, tb):
        random.setstate(self._state)
        return False


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

@learning_router.post("/v1/learning/weekly_report", summary="Parent weekly report (weak skills + practice + teaching guide)")
def learning_weekly_report(req: WeeklyReportRequest, x_api_key: str = Header(..., alias="X-API-Key")):
    import server as _srv
    acc = _srv.get_account_by_api_key(x_api_key)
    _srv.ensure_subscription_active(acc["id"])

    if _srv.learning_connect is None or _srv.ensure_learning_schema is None or _srv.generate_parent_weekly_report is None:
        raise HTTPException(status_code=500, detail="Learning module not available")

    conn = _srv.db()
    st = conn.execute("SELECT * FROM students WHERE id=? AND account_id=?", (int(req.student_id), acc["id"])).fetchone()
    conn.close()
    if not st:
        raise HTTPException(status_code=404, detail="Student not found")

    lconn = _srv.learning_connect(_srv.DB_PATH)
    try:
        _srv.ensure_learning_schema(lconn)
        report = _srv.generate_parent_weekly_report(
            lconn,
            student_id=str(req.student_id),
            window_days=int(req.window_days),
            top_k=int(req.top_k),
            questions_per_skill=int(req.questions_per_skill),
        )
        return {
            "ok": True,
            "student": {"id": int(st["id"]), "display_name": st["display_name"], "grade": st["grade"]},
            "window_days": int(req.window_days),
            "report": report,
        }
    finally:
        try:
            lconn.close()
        except Exception:
            pass


@learning_router.post("/v1/learning/practice_next", summary="Targeted practice: next question + mastery status")
def learning_practice_next(req: PracticeNextRequest, x_api_key: str = Header(..., alias="X-API-Key")):
    import server as _srv
    acc = _srv.get_account_by_api_key(x_api_key)
    _srv.ensure_subscription_active(acc["id"])

    if (
        _srv.learning_connect is None
        or _srv.ensure_learning_schema is None
        or _srv.learning_get_student_analytics is None
        or _srv.compute_skill_status is None
        or _srv.get_practice_items_for_skill is None
        or _srv.get_teaching_guide is None
        or _srv.suggested_engine_topic_key is None
    ):
        raise HTTPException(status_code=500, detail="Learning module not available")

    if _srv.engine is None:
        raise HTTPException(status_code=500, detail="engine.py not found")

    conn = _srv.db()
    st = conn.execute("SELECT * FROM students WHERE id=? AND account_id=?", (int(req.student_id), acc["id"])).fetchone()
    conn.close()
    if not st:
        raise HTTPException(status_code=404, detail="Student not found")

    lconn = _srv.learning_connect(_srv.DB_PATH)
    try:
        _srv.ensure_learning_schema(lconn)
        analytics = _srv.learning_get_student_analytics(lconn, student_id=str(req.student_id), window_days=int(req.window_days))
        snapshot = _skill_snapshot_from_analytics(analytics, skill_tag=str(req.skill_tag))
        status = _srv.compute_skill_status(
            attempts=int(snapshot.get("attempts") or 0),
            accuracy=float(snapshot.get("accuracy") or 0.0),
            hint_dependency=float(snapshot.get("hint_dependency") or 0.0),
            skill_tag=str(req.skill_tag),
        )
    finally:
        try:
            lconn.close()
        except Exception:
            pass

    guide = _srv.get_teaching_guide(str(req.skill_tag))
    practice_items = _srv.get_practice_items_for_skill(str(req.skill_tag))

    topic_key = str(req.topic_key) if req.topic_key not in (None, "") else (_srv.suggested_engine_topic_key(str(req.skill_tag)) or None)
    if topic_key is None:
        topic_key = "11"

    with _SeedContext(req.seed):
        q = _srv.engine.next_question(topic_key)
    hints = _srv._build_hints(q)

    conn = _srv.db()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO question_cache(topic,difficulty,question,correct_answer,explanation,created_at)
                   VALUES (?,?,?,?,?,?)""",
        (q.get("topic"), q.get("difficulty"), q.get("question"), q.get("answer"), q.get("explanation"), _srv.now_iso()),
    )
    qid = int(cur.lastrowid)
    try:
        cur.execute("UPDATE question_cache SET hints_json=? WHERE id=?", (json.dumps(hints, ensure_ascii=False), qid))
    except Exception:
        pass
    conn.commit()
    conn.close()

    return {
        "ok": True,
        "student": {"id": int(st["id"]), "display_name": st["display_name"], "grade": st["grade"]},
        "skill_tag": str(req.skill_tag),
        "window_days": int(req.window_days),
        "topic_key": topic_key,
        "mastery": {"snapshot": snapshot, "status": status},
        "recommendations": {
            "practice_items": practice_items,
            "teaching_guide": guide.__dict__,
        },
        "question": {
            "question_id": qid,
            "topic": q.get("topic"),
            "difficulty": q.get("difficulty"),
            "question": q.get("question"),
            "hints": hints,
            "policy": {"reveal_answer_after_submit": True, "max_hint_level": 3},
            "explanation_preview": "（交卷後顯示）",
        },
    }


@learning_router.post("/v1/learning/remediation_plan", summary="Generate remediation plan for a student")
def learning_remediation_plan(req: RemediationPlanRequest, x_api_key: str = Header(..., alias="X-API-Key")):
    import server as _srv
    acc = _srv.get_account_by_api_key(x_api_key)
    _srv.ensure_subscription_active(acc["id"])

    if _srv.learning_connect is None or _srv.ensure_learning_schema is None or _srv.learning_get_remediation_plan is None:
        raise HTTPException(status_code=500, detail="Learning module not available")

    conn = _srv.db()
    st = conn.execute("SELECT * FROM students WHERE id=? AND account_id=?", (int(req.student_id), acc["id"])).fetchone()
    conn.close()
    if not st:
        raise HTTPException(status_code=404, detail="Student not found")

    plan = _srv.learning_get_remediation_plan(
        studentId=str(req.student_id),
        datasetName=req.dataset_name,
        windowDays=int(req.window_days),
        db_path=_srv.DB_PATH,
    )

    return {
        "ok": True,
        "student": {"id": int(st["id"]), "display_name": st["display_name"], "grade": st["grade"]},
        "window_days": int(req.window_days),
        "plan": plan,
    }


@learning_router.get("/v1/student/concept-state", summary="Get concept mastery states (EXP-06)")
def student_concept_state(student_id: int, x_api_key: str = Header(..., alias="X-API-Key")):
    """Return all concept mastery states for a student from la_student_concept_state."""
    import server as _srv
    acc = _srv.get_account_by_api_key(x_api_key)
    _srv.ensure_subscription_active(acc["id"])

    if _srv.learning_get_all_concept_states is None or _srv.learning_connect is None:
        raise HTTPException(status_code=500, detail="Learning module not available")

    conn = _srv.db()
    st = conn.execute("SELECT * FROM students WHERE id=? AND account_id=?", (int(student_id), acc["id"])).fetchone()
    conn.close()
    if not st:
        raise HTTPException(status_code=404, detail="Student not found")

    lconn = _srv.learning_connect(_srv.DB_PATH)
    try:
        _srv.ensure_learning_schema(lconn)
        states = _srv.learning_get_all_concept_states(str(student_id), conn=lconn)
    finally:
        try:
            lconn.close()
        except Exception:
            pass

    return {
        "ok": True,
        "student_id": int(student_id),
        "concepts": {
            cid: {
                "mastery_level": s.mastery_level.value,
                "mastery_score": round(s.mastery_score, 4),
                "attempts_total": s.attempts_total,
                "correct_total": s.correct_total,
                "recent_accuracy": round(s.recent_accuracy, 4) if s.recent_accuracy is not None else None,
                "hint_dependency": round(s.hint_dependency, 4),
                "consecutive_correct": s.consecutive_correct,
                "consecutive_wrong": s.consecutive_wrong,
                "needs_review": s.needs_review,
                "last_seen_at": s.last_seen_at,
            }
            for cid, s in states.items()
        },
    }


@learning_router.get("/v1/student/hint-effectiveness", summary="Hint effectiveness analytics (EXP-A2)")
def student_hint_effectiveness(
    student_id: Optional[int] = None,
    window_days: int = 30,
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    """Return hint effectiveness metrics for a student or class-wide."""
    import server as _srv
    acc = _srv.get_account_by_api_key(x_api_key)
    _srv.ensure_subscription_active(acc["id"])

    if _srv.learning_get_hint_effectiveness_stats is None or _srv.learning_connect is None:
        raise HTTPException(status_code=500, detail="Learning module not available")

    if student_id is not None:
        conn = _srv.db()
        st = conn.execute(
            "SELECT * FROM students WHERE id=? AND account_id=?",
            (int(student_id), acc["id"]),
        ).fetchone()
        conn.close()
        if not st:
            raise HTTPException(status_code=404, detail="Student not found")

    lconn = _srv.learning_connect(_srv.DB_PATH)
    try:
        _srv.ensure_learning_schema(lconn)
        stats = _srv.learning_get_hint_effectiveness_stats(
            lconn,
            student_id=str(student_id) if student_id is not None else None,
            window_days=window_days,
        )
    finally:
        try:
            lconn.close()
        except Exception:
            pass

    return {"ok": True, **stats}


@learning_router.get("/v1/student/concept-progress", summary="Parent concept progress report (EXP-09)")
def student_concept_progress(student_id: int, x_api_key: str = Header(..., alias="X-API-Key")):
    """Return concept-level mastery progress formatted for parent consumption."""
    import server as _srv
    acc = _srv.get_account_by_api_key(x_api_key)
    _srv.ensure_subscription_active(acc["id"])

    if _srv.learning_parent_concept_progress is None or _srv.learning_get_all_concept_states is None:
        raise HTTPException(status_code=503, detail="Parent concept progress module unavailable")

    conn = _srv.db()
    st = conn.execute("SELECT * FROM students WHERE id=? AND account_id=?", (int(student_id), acc["id"])).fetchone()
    conn.close()
    if not st:
        raise HTTPException(status_code=404, detail="Student not found")

    lconn = _srv.learning_connect(_srv.DB_PATH)
    try:
        _srv.ensure_learning_schema(lconn)
        states = _srv.learning_get_all_concept_states(str(student_id), conn=lconn)
    finally:
        try:
            lconn.close()
        except Exception:
            pass

    report = _srv.learning_parent_concept_progress(
        student_id=str(student_id),
        states=list(states.values()),
    )
    return _srv.learning_parent_progress_to_dict(report)


@learning_router.post("/v1/student/before-after", summary="Before-after comparison (EXP-P4-04)")
def student_before_after(req: BeforeAfterRequest, x_api_key: str = Header(..., alias="X-API-Key")):
    """Compare student accuracy before vs after an intervention date."""
    import server as _srv
    acc = _srv.get_account_by_api_key(x_api_key)
    _srv.ensure_subscription_active(acc["id"])

    if _srv.learning_get_before_after is None:
        raise HTTPException(status_code=503, detail="Before-after analytics module unavailable")

    conn = _srv.db()
    st = conn.execute("SELECT * FROM students WHERE id=? AND account_id=?", (int(req.student_id), acc["id"])).fetchone()
    conn.close()
    if not st:
        raise HTTPException(status_code=404, detail="Student not found")

    result = _srv.learning_get_before_after(
        student_id=str(req.student_id),
        pre_window_days=req.pre_window_days,
        post_window_days=req.post_window_days,
        intervention_date=req.intervention_date,
        db_path=_srv.DB_PATH,
    )

    return {
        "ok": True,
        "student": {"id": int(st["id"]), "display_name": st["display_name"], "grade": st["grade"]},
        "comparison": result,
    }


@learning_router.post("/v1/practice/concept-next", summary="Adaptive next-concept recommendation (EXP-04)")
def practice_concept_next(req: ConceptNextRequest, x_api_key: str = Header(..., alias="X-API-Key")):
    """Select the next concept and difficulty for adaptive practice based on student mastery state."""
    import server as _srv
    acc = _srv.get_account_by_api_key(x_api_key)
    _srv.ensure_subscription_active(acc["id"])

    if _srv.learning_select_next_item is None or _srv.learning_get_all_concept_states is None or _srv.learning_connect is None:
        raise HTTPException(status_code=503, detail="Next-item selector module unavailable")

    conn = _srv.db()
    st = conn.execute("SELECT * FROM students WHERE id=? AND account_id=?", (int(req.student_id), acc["id"])).fetchone()
    conn.close()
    if not st:
        raise HTTPException(status_code=404, detail="Student not found")

    lconn = _srv.learning_connect(_srv.DB_PATH)
    try:
        _srv.ensure_learning_schema(lconn)
        states = _srv.learning_get_all_concept_states(str(req.student_id), conn=lconn)
    finally:
        try:
            lconn.close()
        except Exception:
            pass

    pool = _build_concept_question_pool(domain=req.domain)
    result = _srv.learning_select_next_item(
        student_id=str(req.student_id),
        concept_states=states,
        available_items=pool,
        recent_item_ids=req.recent_item_ids,
    )

    if result is None:
        return {"ok": True, "recommendation": None, "reason": "No items available for the given filters"}

    return {
        "ok": True,
        "recommendation": {
            "item_id": result.item.item_id,
            "target_concept": result.target_concept,
            "concept_ids": result.item.concept_ids,
            "difficulty": result.item.difficulty,
            "strategy": result.strategy,
            "reason": result.reason,
            "domain": (result.item.topic_tags or [None])[0],
        },
    }


@learning_router.get("/v1/adaptive/state", summary="Get adaptive mastery state for a student")
def adaptive_state(student_id: int, x_api_key: str = Header(..., alias="X-API-Key")):
    import server as _srv
    acc = _srv.get_account_by_api_key(x_api_key)
    _srv.ensure_subscription_active(acc["id"])

    conn = _srv.db()
    st = conn.execute(
        "SELECT * FROM students WHERE id=? AND account_id=?",
        (int(student_id), acc["id"]),
    ).fetchone()
    if not st:
        conn.close()
        raise HTTPException(status_code=404, detail="Student not found")

    current = str(st["current_concept_id"] or "").strip() or None
    if not current:
        seq = _srv._concept_sequence()
        current = seq[0] if seq else None

    out_state = None
    if current:
        cs = _srv._get_or_create_student_concept(conn, student_id=int(student_id), concept_id=current)
        out_state = {
            "concept_id": cs.concept_id,
            "stage": cs.stage.value,
            "answered": cs.answered,
            "correct": cs.correct,
            "mastery": round(cs.mastery(), 4),
            "in_hint_mode": bool(cs.in_hint_mode),
            "in_micro_step": bool(cs.in_micro_step),
            "micro_count": int(cs.micro_count),
            "consecutive_wrong": int(cs.consecutive_wrong),
            "calm_mode": bool(cs.calm_mode),
            "flag_teacher": bool(cs.flag_teacher),
            "completed": bool(cs.completed),
            "error_stats": cs.error_stats,
        }

        if not st["current_concept_id"]:
            conn.execute(
                "UPDATE students SET current_concept_id=?, updated_at=? WHERE id=?",
                (current, _srv.now_iso(), int(student_id)),
            )
            conn.commit()

    conn.close()
    return {
        "student_id": int(student_id),
        "current_concept_id": current,
        "sequence": _srv._concept_sequence(),
        "current_state": out_state,
    }


@learning_router.get("/v1/adaptive/dashboard", summary="Dashboard (JSON) for parent/teacher")
def adaptive_dashboard(student_id: int, x_api_key: str = Header(..., alias="X-API-Key")):
    import server as _srv
    acc = _srv.get_account_by_api_key(x_api_key)
    _srv.ensure_subscription_active(acc["id"])

    conn = _srv.db()
    st = conn.execute(
        "SELECT * FROM students WHERE id=? AND account_id=?",
        (int(student_id), acc["id"]),
    ).fetchone()
    if not st:
        conn.close()
        raise HTTPException(status_code=404, detail="Student not found")

    rows = conn.execute(
        "SELECT * FROM student_concepts WHERE student_id=? ORDER BY concept_id ASC",
        (int(student_id),),
    ).fetchall()

    seq = _srv._concept_sequence()
    cur_id = str(st["current_concept_id"] or "").strip() or (seq[0] if seq else None)

    concepts: List[Dict[str, Any]] = []
    for r in rows:
        answered = int(r["answered"] or 0)
        correct = int(r["correct"] or 0)
        mastery = (correct / answered) if answered > 0 else 0.0
        stuck_flag = bool(answered >= 6 and mastery < 0.6)

        color = "yellow"
        if bool(r["completed"]):
            color = "green"
        elif bool(r["flag_teacher"]) or stuck_flag:
            color = "red"

        concepts.append(
            {
                "concept_id": r["concept_id"],
                "stage": r["stage"],
                "answered": answered,
                "correct": correct,
                "mastery": round(mastery, 4),
                "in_hint_mode": bool(r["in_hint_mode"]),
                "in_micro_step": bool(r["in_micro_step"]),
                "micro_count": int(r["micro_count"] or 0),
                "consecutive_wrong": int(r["consecutive_wrong"] or 0),
                "calm_mode": bool(r["calm_mode"]),
                "stuck_flag": bool(stuck_flag),
                "flag_teacher": bool(r["flag_teacher"]),
                "last_activity": r["last_activity"],
                "color": color,
                "error_stats": _srv.error_stats_from_json(r["error_stats_json"]),
            }
        )

    conn.close()
    return {
        "student": {
            "id": st["id"],
            "display_name": st["display_name"],
            "grade": st["grade"],
        },
        "current_concept_id": cur_id,
        "concepts": concepts,
    }
