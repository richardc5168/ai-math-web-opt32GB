from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, Optional

from . import analytics as analytics_mod
from .concept_state import get_all_states, get_concept_state, upsert_concept_state
from .concept_taxonomy import resolve_concept_ids
from .gamification import check_unlocks, compute_badges
from .db import connect, ensure_learning_schema, now_iso
from .datasets import load_dataset
from .error_classifier import classify_error
from .mastery_engine import update_mastery, AnswerEvent
from .remediation import generate_remediation_plan
from .validator import validate_attempt_event


def recordAttempt(event: Dict[str, Any], *, db_path: Optional[str] = None, dev_mode: bool = True) -> Dict[str, Any]:
    """Persist one attempt event into SQLite (normalized learning tables).

    Returns a small ack dict including the inserted attempt_id.
    """

    v = validate_attempt_event(event, dev_mode=dev_mode)

    conn = connect(db_path)
    try:
        ensure_learning_schema(conn)

        conn.execute(
            "INSERT OR IGNORE INTO la_students(student_id, created_at, meta_json) VALUES (?,?,?)",
            (v.student_id, now_iso(), "{}"),
        )
        conn.execute(
            "INSERT OR IGNORE INTO la_questions(question_id, created_at, meta_json) VALUES (?,?,?)",
            (v.question_id, now_iso(), "{}"),
        )

        # skill tags registry
        for tag in sorted(set(v.skill_tags)):
            conn.execute(
                "INSERT OR IGNORE INTO la_skill_tags(skill_tag, created_at, description) VALUES (?,?,?)",
                (tag, now_iso(), None),
            )

        cur = conn.execute(
            """
            INSERT INTO la_attempt_events(
              student_id, question_id, ts, is_correct, answer_raw,
              duration_ms, hints_viewed_count, hint_steps_viewed_json,
              mistake_code, unit, topic, question_type,
              session_id, device_json, extra_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                v.student_id,
                v.question_id,
                v.timestamp_iso,
                1 if v.is_correct else 0,
                v.answer_raw,
                v.duration_ms,
                int(v.hints_viewed_count),
                json.dumps(v.hint_steps_viewed, ensure_ascii=False),
                v.mistake_code,
                v.unit,
                v.topic,
                v.question_type,
                v.session_id,
                json.dumps(v.device or {}, ensure_ascii=False),
                json.dumps(v.extra or {}, ensure_ascii=False),
            ),
        )
        attempt_id = int(cur.lastrowid)

        for tag in sorted(set(v.skill_tags)):
            conn.execute(
                "INSERT OR IGNORE INTO la_attempt_skill_tags(attempt_id, skill_tag) VALUES (?,?)",
                (attempt_id, tag),
            )

        for step in v.hint_steps_viewed:
            conn.execute(
                "INSERT INTO la_hint_usage(attempt_id, step_index) VALUES (?,?)",
                (attempt_id, int(step)),
            )

        # --- Concept enrichment (EXP-01) ---
        topic_tags = list(set(v.skill_tags))
        if v.topic:
            topic_tags.append(v.topic)
        concept_points = v.extra.get("concept_points") if v.extra else None
        concept_ids = resolve_concept_ids(topic_tags, concept_points)
        if concept_ids:
            conn.execute(
                "UPDATE la_attempt_events SET concept_ids_json = ? WHERE rowid = ?",
                (json.dumps(concept_ids, ensure_ascii=False), attempt_id),
            )

        # --- Error classification (EXP-03) ---
        error_type = None
        if not v.is_correct:
            correct_answer = (v.extra or {}).get("correct_answer")
            duration_sec = v.duration_ms / 1000.0 if v.duration_ms else 0.0
            et = classify_error(
                is_correct=False,
                user_answer=v.answer_raw,
                correct_answer=correct_answer,
                response_time_sec=duration_sec,
                used_hints=v.hints_viewed_count > 0,
                hint_levels_shown=v.hints_viewed_count,
                changed_answer=bool((v.extra or {}).get("changed_answer")),
                meta=v.extra,
            )
            if et is not None:
                error_type = et.value
                conn.execute(
                    "UPDATE la_attempt_events SET error_type = ? WHERE rowid = ?",
                    (error_type, attempt_id),
                )

        # --- Mastery update (EXP-02) ---
        mastery_updates = []
        if concept_ids:
            answer_event = AnswerEvent(
                is_correct=v.is_correct,
                used_hint=v.hints_viewed_count > 0,
                hint_levels_shown=v.hints_viewed_count,
                response_time_sec=v.duration_ms / 1000.0 if v.duration_ms else 0.0,
                changed_answer=bool((v.extra or {}).get("changed_answer")),
                error_type=error_type,
            )
            for cid in concept_ids:
                state = get_concept_state(v.student_id, cid, conn=conn)
                state, actions = update_mastery(state, answer_event)
                upsert_concept_state(state, conn=conn)
                mastery_updates.append({
                    "concept_id": cid,
                    "level": state.mastery_level.value,
                    "score": round(state.mastery_score, 4),
                    "remediation_needed": actions.remediation_needed,
                    "calm_mode": actions.calm_mode_entered,
                })

        # --- Remediation signals (EXP-05) ---
        remediation_concepts = [m["concept_id"] for m in mastery_updates if m.get("remediation_needed")]

        # --- Gamification (EXP-07) ---
        unlocks = []
        badges = []
        if concept_ids:
            all_states = get_all_states(v.student_id, conn=conn)
            state_list = list(all_states.values())
            unlocks = [
                {"concept_id": u.concept_id, "zone_unlocked": u.zone_unlocked,
                 "boss_unlocked": u.boss_unlocked, "unlock_reason": u.unlock_reason}
                for u in check_unlocks(state_list)
            ]
            badges = [
                {"badge_type": b.badge_type.value, "display_name_zh": b.display_name_zh,
                 "icon": b.icon}
                for b in compute_badges(state_list)
            ]

        conn.commit()
        return {
            "ok": True, "attempt_id": attempt_id, "concept_ids": concept_ids,
            "error_type": error_type, "mastery": mastery_updates,
            "remediation_concepts": remediation_concepts,
            "unlocks": unlocks, "badges": badges,
        }
    finally:
        conn.close()


def getStudentAnalytics(
    studentId: str,
    windowDays: int = 14,
    *,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    conn = connect(db_path)
    try:
        return analytics_mod.get_student_analytics(conn, student_id=str(studentId), window_days=int(windowDays))
    finally:
        conn.close()


def getRemediationPlan(
    studentId: str,
    datasetName: Optional[str] = None,
    windowDays: int = 14,
    *,
    db_path: Optional[str] = None,
    persist: bool = True,
) -> Dict[str, Any]:
    conn = connect(db_path)
    try:
        ensure_learning_schema(conn)

        analytics = analytics_mod.get_student_analytics(conn, student_id=str(studentId), window_days=int(windowDays))
        blueprint = load_dataset(datasetName) if datasetName else None
        plan = generate_remediation_plan(analytics, blueprint=blueprint)

        if persist:
            conn.execute(
                "INSERT OR IGNORE INTO la_students(student_id, created_at, meta_json) VALUES (?,?,?)",
                (str(studentId), now_iso(), "{}"),
            )
            conn.execute(
                """
                INSERT INTO la_remediation_plans(
                  student_id, generated_at, window_days, dataset_name, plan_json, evidence_json
                ) VALUES (?,?,?,?,?,?)
                """,
                (
                    str(studentId),
                    now_iso(),
                    int(windowDays),
                    datasetName,
                    json.dumps(plan, ensure_ascii=False, sort_keys=True),
                    json.dumps({"analytics": analytics}, ensure_ascii=False, sort_keys=True),
                ),
            )
            conn.commit()

        return plan
    finally:
        conn.close()
