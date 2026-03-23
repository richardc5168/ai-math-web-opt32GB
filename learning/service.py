from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, Optional

from . import analytics as analytics_mod
from . import before_after_analytics as ba_analytics
from .concept_state import get_all_states, get_concept_state, upsert_concept_state, MasteryLevel
from .concept_taxonomy import resolve_concept_ids, get_concept as _get_concept
from .gamification import check_unlocks, compute_badges, detect_new_badges, compute_zone_progress
from .db import connect, ensure_learning_schema, now_iso
from .datasets import load_dataset
from .error_classifier import classify_error
from .mastery_engine import update_mastery, check_review_needed, AnswerEvent
from .remediation import generate_remediation_plan
from .remediation_flow import get_next_hint as _rf_get_next_hint, evaluate_remediation_need, should_flag_teacher, HintSession, HintLevel
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
        recovered_concepts: set = set()
        _extra = v.extra or {}
        if concept_ids:
            for cid in concept_ids:
                state = get_concept_state(v.student_id, cid, conn=conn)

                # --- EXP-P3-06: Detect delayed review ---
                if state.mastery_level == MasteryLevel.MASTERED:
                    state, _review_fired = check_review_needed(state)
                    if _review_fired:
                        upsert_concept_state(state, conn=conn)
                is_delayed = state.mastery_level == MasteryLevel.REVIEW_NEEDED

                # --- EXP-P3-06: Detect transfer item ---
                is_transfer = bool(_extra.get("is_transfer_item"))
                if not is_transfer:
                    cinfo = _get_concept(cid)
                    if cinfo and cinfo.get("domain") == "application":
                        is_transfer = True

                answer_event = AnswerEvent(
                    is_correct=v.is_correct,
                    used_hint=v.hints_viewed_count > 0,
                    hint_levels_shown=v.hints_viewed_count,
                    response_time_sec=v.duration_ms / 1000.0 if v.duration_ms else 0.0,
                    changed_answer=bool(_extra.get("changed_answer")),
                    error_type=error_type,
                    is_transfer_item=is_transfer,
                    is_delayed_review=is_delayed,
                )
                old_level = state.mastery_level
                state, actions = update_mastery(state, answer_event)
                upsert_concept_state(state, conn=conn)
                mastery_updates.append({
                    "concept_id": cid,
                    "level": state.mastery_level.value,
                    "score": round(state.mastery_score, 4),
                    "remediation_needed": actions.remediation_needed,
                    "calm_mode": actions.calm_mode_entered,
                })
                # Track comeback: REVIEW_NEEDED → MASTERED
                if old_level == MasteryLevel.REVIEW_NEEDED and state.mastery_level == MasteryLevel.MASTERED:
                    recovered_concepts.add(cid)

        # Track consecutive no-hint correct for badge (EXP-S3-03)
        consecutive_no_hint_correct = 0
        if v.is_correct and v.hints_viewed_count == 0:
            consecutive_no_hint_correct = int((v.extra or {}).get("consecutive_no_hint_correct", 1))

        # --- Remediation signals (EXP-05) ---
        remediation_concepts = [m["concept_id"] for m in mastery_updates if m.get("remediation_needed")]

        # --- Gamification (EXP-07 + EXP-S3-03) ---
        unlocks = []
        badges = []
        new_badges = []
        zone_progress = []
        if concept_ids:
            all_states = get_all_states(v.student_id, conn=conn)
            state_list = list(all_states.values())
            unlocks = [
                {"concept_id": u.concept_id, "zone_unlocked": u.zone_unlocked,
                 "boss_unlocked": u.boss_unlocked, "unlock_reason": u.unlock_reason}
                for u in check_unlocks(state_list)
            ]
            # Compute previous badge set (without this attempt's extras)
            prev_badge_types = {
                b.badge_type.value
                for b in compute_badges(state_list)
            }
            # Full badge computation with all inputs
            all_badges = compute_badges(
                state_list,
                consecutive_no_hint_correct=consecutive_no_hint_correct,
                recovered_concepts=recovered_concepts,
            )
            new_badges = [
                {"badge_type": b.badge_type.value, "display_name_zh": b.display_name_zh,
                 "icon": b.icon, "is_new": True}
                for b in detect_new_badges(all_badges, prev_badge_types)
            ]
            badges = [
                {"badge_type": b.badge_type.value, "display_name_zh": b.display_name_zh,
                 "icon": b.icon}
                for b in all_badges
            ]
            zone_progress = [
                {"zone_id": z.zone_id, "display_name_zh": z.display_name_zh,
                 "total_concepts": z.total_concepts, "mastered_count": z.mastered_count,
                 "progress_pct": z.progress_pct, "is_complete": z.is_complete}
                for z in compute_zone_progress(state_list)
            ]

        conn.commit()
        return {
            "ok": True, "attempt_id": attempt_id, "concept_ids": concept_ids,
            "error_type": error_type, "mastery": mastery_updates,
            "remediation_concepts": remediation_concepts,
            "unlocks": unlocks, "badges": badges, "new_badges": new_badges,
            "zone_progress": zone_progress,
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


def getBeforeAfterComparison(
    student_id: str,
    *,
    pre_window_days: int = 14,
    post_window_days: int = 14,
    intervention_date: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Compare student accuracy before vs after an intervention date.

    Uses la_attempt_events split by intervention_date. If no date given,
    uses the midpoint of available data.
    """
    conn = connect(db_path)
    try:
        ensure_learning_schema(conn)

        # Determine intervention date
        if not intervention_date:
            row = conn.execute(
                "SELECT MIN(ts), MAX(ts) FROM la_attempt_events WHERE student_id = ?",
                (student_id,),
            ).fetchone()
            if not row or not row[0]:
                return {"label": "insufficient_evidence", "compared_group_count": 0,
                        "groups": [], "uncertainty": ["No attempt data found."]}
            from datetime import date as _date
            first = _date.fromisoformat(row[0][:10])
            last = _date.fromisoformat(row[1][:10])
            mid = first + (last - first) / 2
            intervention_date = mid.isoformat()

        # Fetch pre and post records
        pre_rows = conn.execute(
            """SELECT question_id, is_correct as correctness, concept_ids_json
               FROM la_attempt_events
               WHERE student_id = ? AND ts < ?
               ORDER BY ts""",
            (student_id, intervention_date),
        ).fetchall()

        post_rows = conn.execute(
            """SELECT question_id, is_correct as correctness, concept_ids_json
               FROM la_attempt_events
               WHERE student_id = ? AND ts >= ?
               ORDER BY ts""",
            (student_id, intervention_date),
        ).fetchall()

        # Build question metadata from concept_ids_json
        question_metadata = []
        seen_qids: set = set()
        for row in list(pre_rows) + list(post_rows):
            qid = row[0]
            if qid in seen_qids:
                continue
            seen_qids.add(qid)
            concept_json = row[2]
            if concept_json:
                concepts = json.loads(concept_json)
                skill = concepts[0] if concepts else "unknown"
            else:
                skill = "unknown"
            question_metadata.append({
                "question_id": qid,
                "equivalent_group_id": skill,
                "skill_tag": skill,
                "knowledge_point": skill,
            })

        pre_records = [{"question_id": r[0], "correctness": bool(r[1])} for r in pre_rows]
        post_records = [{"question_id": r[0], "correctness": bool(r[1])} for r in post_rows]

        result = ba_analytics.compare_pre_post(
            question_metadata=question_metadata,
            pre_records=pre_records,
            post_records=post_records,
        )
        result["student_id"] = student_id
        result["intervention_date"] = intervention_date
        return result
    finally:
        conn.close()


def getNextHint(
    student_id: str,
    question_id: str,
    concept_id: str = "",
    *,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Return the next adaptive hint for a student on a question.

    Builds a HintSession from DB state (previous hints shown, wrong count),
    calls remediation_flow.get_next_hint(), and returns the action.
    """
    conn = connect(db_path)
    try:
        ensure_learning_schema(conn)

        # Count hints already shown for this student+question
        row = conn.execute(
            "SELECT hints_viewed_count FROM la_attempt_events "
            "WHERE student_id = ? AND question_id = ? "
            "ORDER BY rowid DESC LIMIT 1",
            (str(student_id), str(question_id)),
        ).fetchone()
        hints_already = int(row[0]) if row else 0

        # Count wrong attempts on this concept
        total_wrong = 0
        if concept_id:
            wr = conn.execute(
                "SELECT COUNT(*) FROM la_attempt_events "
                "WHERE student_id = ? AND is_correct = 0 AND concept_ids_json LIKE ?",
                (str(student_id), f'%"{concept_id}"%'),
            ).fetchone()
            total_wrong = int(wr[0]) if wr else 0

        # Build session
        current_level = HintLevel(min(hints_already, HintLevel.SOLUTION))
        session = HintSession(
            question_id=str(question_id),
            concept_id=concept_id or "unknown",
            current_level=current_level,
            hints_shown=[HintLevel(i) for i in range(1, hints_already + 1) if i <= HintLevel.SOLUTION],
            total_wrong_this_concept=total_wrong,
        )

        action = _rf_get_next_hint(session)
        flag_teacher = should_flag_teacher(session)

        return {
            "action_type": action.action_type,
            "hint_level": int(action.hint_level) if action.hint_level is not None else None,
            "target_concept_id": action.target_concept_id,
            "reason": action.reason,
            "details": action.details,
            "flag_teacher": flag_teacher,
            "session_state": {
                "current_level": int(session.current_level),
                "hints_shown": [int(h) for h in session.hints_shown],
                "total_wrong_this_concept": session.total_wrong_this_concept,
            },
        }
    finally:
        conn.close()
