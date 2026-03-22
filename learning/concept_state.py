"""Student per-concept mastery state — CRUD operations.

Each student has a mastery state for each concept they've interacted with.
States: unbuilt → developing → approaching_mastery → mastered → review_needed

Usage:
    from learning.concept_state import (
        get_concept_state, upsert_concept_state, get_all_states,
        MasteryLevel, StudentConceptState
    )
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from .db import connect, ensure_learning_schema, now_iso


# ---------------------------------------------------------------------------
# Mastery Level Enum
# ---------------------------------------------------------------------------

class MasteryLevel(str, Enum):
    UNBUILT = "unbuilt"
    DEVELOPING = "developing"
    APPROACHING_MASTERY = "approaching_mastery"
    MASTERED = "mastered"
    REVIEW_NEEDED = "review_needed"


# ---------------------------------------------------------------------------
# Data Class
# ---------------------------------------------------------------------------

@dataclass
class StudentConceptState:
    student_id: str
    concept_id: str
    mastery_level: MasteryLevel = MasteryLevel.UNBUILT
    mastery_score: float = 0.0
    recent_accuracy: Optional[float] = None
    hint_dependency: float = 0.0
    avg_response_time_sec: Optional[float] = None
    attempts_total: int = 0
    correct_total: int = 0
    correct_no_hint: int = 0
    correct_with_hint: int = 0
    consecutive_correct: int = 0
    consecutive_wrong: int = 0
    transfer_success_count: int = 0
    delayed_review_status: str = "none"
    needs_review: bool = False
    last_seen_at: Optional[str] = None
    last_mastered_at: Optional[str] = None
    updated_at: Optional[str] = None

    def accuracy(self) -> float:
        if self.attempts_total <= 0:
            return 0.0
        return self.correct_total / self.attempts_total

    def to_dict(self) -> dict:
        d = asdict(self)
        d["mastery_level"] = self.mastery_level.value
        d["needs_review"] = int(self.needs_review)
        return d


# ---------------------------------------------------------------------------
# Database Operations
# ---------------------------------------------------------------------------

def get_concept_state(
    student_id: str,
    concept_id: str,
    *,
    conn: Optional[sqlite3.Connection] = None,
    db_path: Optional[str] = None,
) -> StudentConceptState:
    """Get student's concept state. Returns default unbuilt state if not found."""
    own_conn = conn is None
    if own_conn:
        conn = connect(db_path)
        ensure_learning_schema(conn)
    try:
        row = conn.execute(
            "SELECT * FROM la_student_concept_state WHERE student_id=? AND concept_id=?",
            (student_id, concept_id),
        ).fetchone()
        if row is None:
            return StudentConceptState(student_id=student_id, concept_id=concept_id)
        return _row_to_state(row)
    finally:
        if own_conn:
            conn.close()


def get_all_states(
    student_id: str,
    *,
    conn: Optional[sqlite3.Connection] = None,
    db_path: Optional[str] = None,
) -> Dict[str, StudentConceptState]:
    """Get all concept states for a student."""
    own_conn = conn is None
    if own_conn:
        conn = connect(db_path)
        ensure_learning_schema(conn)
    try:
        rows = conn.execute(
            "SELECT * FROM la_student_concept_state WHERE student_id=? ORDER BY concept_id",
            (student_id,),
        ).fetchall()
        return {row["concept_id"]: _row_to_state(row) for row in rows}
    finally:
        if own_conn:
            conn.close()


def get_class_states(
    student_ids: List[str],
    *,
    conn: Optional[sqlite3.Connection] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Dict[str, StudentConceptState]]:
    """Get concept states for multiple students. Returns {student_id: {concept_id: state}}."""
    own_conn = conn is None
    if own_conn:
        conn = connect(db_path)
        ensure_learning_schema(conn)
    try:
        placeholders = ",".join("?" for _ in student_ids)
        rows = conn.execute(
            f"SELECT * FROM la_student_concept_state WHERE student_id IN ({placeholders}) ORDER BY student_id, concept_id",
            student_ids,
        ).fetchall()
        result: Dict[str, Dict[str, StudentConceptState]] = {}
        for row in rows:
            sid = row["student_id"]
            if sid not in result:
                result[sid] = {}
            result[sid][row["concept_id"]] = _row_to_state(row)
        return result
    finally:
        if own_conn:
            conn.close()


def upsert_concept_state(
    state: StudentConceptState,
    *,
    conn: Optional[sqlite3.Connection] = None,
    db_path: Optional[str] = None,
) -> None:
    """Insert or update a student concept state."""
    own_conn = conn is None
    if own_conn:
        conn = connect(db_path)
        ensure_learning_schema(conn)
    try:
        now = now_iso()
        conn.execute(
            """
            INSERT INTO la_student_concept_state (
                student_id, concept_id, mastery_level, mastery_score,
                recent_accuracy, hint_dependency, avg_response_time_sec,
                attempts_total, correct_total, correct_no_hint, correct_with_hint,
                consecutive_correct, consecutive_wrong, transfer_success_count,
                delayed_review_status, needs_review,
                last_seen_at, last_mastered_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(student_id, concept_id) DO UPDATE SET
                mastery_level=excluded.mastery_level,
                mastery_score=excluded.mastery_score,
                recent_accuracy=excluded.recent_accuracy,
                hint_dependency=excluded.hint_dependency,
                avg_response_time_sec=excluded.avg_response_time_sec,
                attempts_total=excluded.attempts_total,
                correct_total=excluded.correct_total,
                correct_no_hint=excluded.correct_no_hint,
                correct_with_hint=excluded.correct_with_hint,
                consecutive_correct=excluded.consecutive_correct,
                consecutive_wrong=excluded.consecutive_wrong,
                transfer_success_count=excluded.transfer_success_count,
                delayed_review_status=excluded.delayed_review_status,
                needs_review=excluded.needs_review,
                last_seen_at=excluded.last_seen_at,
                last_mastered_at=excluded.last_mastered_at,
                updated_at=excluded.updated_at
            """,
            (
                state.student_id, state.concept_id, state.mastery_level.value,
                state.mastery_score, state.recent_accuracy, state.hint_dependency,
                state.avg_response_time_sec, state.attempts_total, state.correct_total,
                state.correct_no_hint, state.correct_with_hint,
                state.consecutive_correct, state.consecutive_wrong,
                state.transfer_success_count, state.delayed_review_status,
                int(state.needs_review), state.last_seen_at, state.last_mastered_at,
                now,
            ),
        )
        if own_conn:
            conn.commit()
    finally:
        if own_conn:
            conn.close()


def get_students_needing_review(
    *,
    conn: Optional[sqlite3.Connection] = None,
    db_path: Optional[str] = None,
) -> List[StudentConceptState]:
    """Get all student-concept pairs that need review."""
    own_conn = conn is None
    if own_conn:
        conn = connect(db_path)
        ensure_learning_schema(conn)
    try:
        rows = conn.execute(
            "SELECT * FROM la_student_concept_state WHERE needs_review=1 ORDER BY student_id, concept_id",
        ).fetchall()
        return [_row_to_state(row) for row in rows]
    finally:
        if own_conn:
            conn.close()


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _row_to_state(row: sqlite3.Row) -> StudentConceptState:
    return StudentConceptState(
        student_id=row["student_id"],
        concept_id=row["concept_id"],
        mastery_level=MasteryLevel(row["mastery_level"]),
        mastery_score=float(row["mastery_score"]),
        recent_accuracy=float(row["recent_accuracy"]) if row["recent_accuracy"] is not None else None,
        hint_dependency=float(row["hint_dependency"] or 0),
        avg_response_time_sec=float(row["avg_response_time_sec"]) if row["avg_response_time_sec"] is not None else None,
        attempts_total=int(row["attempts_total"] or 0),
        correct_total=int(row["correct_total"] or 0),
        correct_no_hint=int(row["correct_no_hint"] or 0),
        correct_with_hint=int(row["correct_with_hint"] or 0),
        consecutive_correct=int(row["consecutive_correct"] or 0),
        consecutive_wrong=int(row["consecutive_wrong"] or 0),
        transfer_success_count=int(row["transfer_success_count"] or 0),
        delayed_review_status=str(row["delayed_review_status"] or "none"),
        needs_review=bool(row["needs_review"]),
        last_seen_at=row["last_seen_at"],
        last_mastered_at=row["last_mastered_at"],
        updated_at=row["updated_at"],
    )
