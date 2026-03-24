from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


_ALLOWED_MISTAKE_CODES = {
    "concept",
    "calculation",
    "unit",
    "reading",
    "careless",
}


@dataclass(frozen=True)
class ValidatedAttemptEvent:
    student_id: str
    question_id: str
    timestamp_iso: str
    is_correct: bool
    answer_raw: str

    duration_ms: Optional[int]
    hints_viewed_count: int
    hint_steps_viewed: List[int]
    mistake_code: Optional[str]

    unit: Optional[str]
    topic: Optional[str]
    question_type: Optional[str]

    session_id: Optional[str]
    device: Dict[str, Any]
    extra: Dict[str, Any]
    skill_tags: List[str]

    # R44: mastery evidence fields
    started_at: Optional[str] = None
    first_answer: Optional[str] = None
    attempts_count: int = 1
    changed_answer: bool = False
    selection_reason: Optional[str] = None


def _as_str(x: Any) -> str:
    return str(x) if x is not None else ""


def _parse_timestamp_to_iso(ts: Any) -> str:
    if ts is None or ts == "":
        raise ValueError("timestamp is required")

    if isinstance(ts, (int, float)):
        # Heuristic: treat >= 10^12 as ms, else seconds.
        v = float(ts)
        if v >= 1e12:
            dt = datetime.fromtimestamp(v / 1000.0, tz=timezone.utc)
        else:
            dt = datetime.fromtimestamp(v, tz=timezone.utc)
        return dt.isoformat(timespec="seconds")

    if isinstance(ts, str):
        s = ts.strip()
        if not s:
            raise ValueError("timestamp is required")
        try:
            # Accept ISO 8601; if no timezone, keep as-is.
            datetime.fromisoformat(s.replace("Z", "+00:00"))
            return s
        except Exception as e:
            raise ValueError(f"timestamp must be ISO 8601: {s!r}") from e

    raise ValueError("timestamp must be number or ISO string")


def validate_attempt_event(event: Dict[str, Any], *, dev_mode: bool = True) -> ValidatedAttemptEvent:
    if not isinstance(event, dict):
        raise ValueError("event must be a dict")

    def g(*keys: str, default: Any = None) -> Any:
        for k in keys:
            if k in event:
                return event.get(k)
        return default

    student_id = _as_str(g("student_id", "studentId"))
    question_id = _as_str(g("question_id", "questionId"))
    if not student_id:
        raise ValueError("student_id is required")
    if not question_id:
        raise ValueError("question_id is required")

    timestamp_iso = _parse_timestamp_to_iso(g("timestamp", "ts", "time"))

    is_correct_raw = g("is_correct", "isCorrect")
    if not isinstance(is_correct_raw, bool):
        # Allow 0/1 for compatibility.
        if is_correct_raw in (0, 1):
            is_correct = bool(is_correct_raw)
        else:
            raise ValueError("is_correct must be boolean")
    else:
        is_correct = is_correct_raw

    answer_raw = _as_str(g("answer_raw", "answerRaw", "answer", "user_answer"))

    duration_ms = g("duration_ms", "durationMs")
    if duration_ms is not None:
        try:
            duration_ms = int(duration_ms)
        except Exception as e:
            raise ValueError("duration_ms must be int") from e
        if duration_ms < 0:
            raise ValueError("duration_ms must be >= 0")

    hints_viewed_count = g("hints_viewed_count", "hintsViewedCount", default=0)
    try:
        hints_viewed_count = int(hints_viewed_count)
    except Exception as e:
        raise ValueError("hints_viewed_count must be int") from e
    if hints_viewed_count < 0:
        raise ValueError("hints_viewed_count must be >= 0")

    hint_steps_viewed_raw = g("hint_steps_viewed", "hintStepsViewed", default=[])
    if hint_steps_viewed_raw is None:
        hint_steps_viewed_raw = []
    if not isinstance(hint_steps_viewed_raw, list):
        raise ValueError("hint_steps_viewed must be a list")

    hint_steps_viewed: List[int] = []
    for it in hint_steps_viewed_raw:
        try:
            hint_steps_viewed.append(int(it))
        except Exception as e:
            raise ValueError("hint_steps_viewed items must be integers") from e
    if hints_viewed_count == 0 and hint_steps_viewed:
        hints_viewed_count = len(hint_steps_viewed)

    mistake_code = g("mistake_code", "mistakeCode")
    if mistake_code is not None:
        mistake_code = str(mistake_code).strip().lower()
        if mistake_code == "":
            mistake_code = None
        if mistake_code is not None and mistake_code not in _ALLOWED_MISTAKE_CODES:
            raise ValueError(f"mistake_code must be one of: {sorted(_ALLOWED_MISTAKE_CODES)}")

    unit = g("unit", "unit_id", "unitId")
    unit = str(unit).strip() if unit not in (None, "") else None

    topic = g("topic")
    topic = str(topic).strip() if topic not in (None, "") else None

    question_type = g("question_type", "questionType", "kind")
    question_type = str(question_type).strip() if question_type not in (None, "") else None

    session_id = g("session_id", "sessionId")
    session_id = str(session_id).strip() if session_id not in (None, "") else None

    device = g("device", default={})
    if device is None:
        device = {}
    if not isinstance(device, dict):
        raise ValueError("device must be a dict")

    extra = g("extra", "meta", default={})
    if extra is None:
        extra = {}
    if not isinstance(extra, dict):
        raise ValueError("extra/meta must be a dict")

    skill_tags_raw = g("skill_tags", "skillTags", default=[])
    if skill_tags_raw is None:
        skill_tags_raw = []
    if not isinstance(skill_tags_raw, list):
        raise ValueError("skill_tags must be a list")

    skill_tags = [str(x).strip() for x in skill_tags_raw if str(x).strip()]
    if not skill_tags and dev_mode:
        # Provide a stable fallback to keep downstream analytics deterministic.
        skill_tags = ["unknown"]

    # R44: mastery evidence fields
    started_at = g("started_at", "startedAt")
    if started_at is not None:
        started_at = str(started_at).strip() or None
    first_answer = g("first_answer", "firstAnswer")
    if first_answer is not None:
        first_answer = str(first_answer).strip()
    attempts_count_raw = g("attempts_count", "attemptsCount", default=1)
    try:
        attempts_count = max(1, int(attempts_count_raw))
    except Exception:
        attempts_count = 1
    changed_answer_raw = g("changed_answer", "changedAnswer", default=False)
    changed_answer = bool(changed_answer_raw)
    selection_reason = g("selection_reason", "selectionReason")
    if selection_reason is not None:
        selection_reason = str(selection_reason).strip() or None

    return ValidatedAttemptEvent(
        student_id=student_id,
        question_id=question_id,
        timestamp_iso=timestamp_iso,
        is_correct=is_correct,
        answer_raw=answer_raw,
        duration_ms=duration_ms,
        hints_viewed_count=hints_viewed_count,
        hint_steps_viewed=hint_steps_viewed,
        mistake_code=mistake_code,
        unit=unit,
        topic=topic,
        question_type=question_type,
        session_id=session_id,
        device=device,
        extra=extra,
        skill_tags=skill_tags,
        started_at=started_at,
        first_answer=first_answer,
        attempts_count=attempts_count,
        changed_answer=changed_answer,
        selection_reason=selection_reason,
    )
