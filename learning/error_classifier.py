"""Error Type Classification — Rule-based error taxonomy.

Classifies student errors into actionable categories that inform
hint delivery, remediation strategy, and teacher/parent reports.

Categories:
- concept_misunderstanding: Wrong method or approach
- careless: Small slip, close to correct
- calculation_error: Steps OK but arithmetic wrong
- unit_error: Wrong units or unit conversion
- reading_comprehension_issue: Misread or misunderstood the problem
- guess_pattern: Random or very fast answers
- stuck_after_hint: Wrong even after receiving hints

Usage:
    from learning.error_classifier import ErrorType, classify_error
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional


class ErrorType(str, Enum):
    CONCEPT_MISUNDERSTANDING = "concept_misunderstanding"
    CARELESS = "careless"
    CALCULATION_ERROR = "calculation_error"
    UNIT_ERROR = "unit_error"
    READING_COMPREHENSION = "reading_comprehension_issue"
    GUESS_PATTERN = "guess_pattern"
    STUCK_AFTER_HINT = "stuck_after_hint"


# Human-readable descriptions for reports
ERROR_DESCRIPTIONS: Dict[ErrorType, Dict[str, str]] = {
    ErrorType.CONCEPT_MISUNDERSTANDING: {
        "zh": "觀念理解錯誤",
        "description_zh": "使用了錯誤的方法或觀念來解題",
        "teacher_action_zh": "建議重新教導此概念，檢查學生是否有迷思概念",
        "parent_action_zh": "孩子對這個觀念還不熟，需要更多解釋和練習",
    },
    ErrorType.CARELESS: {
        "zh": "粗心錯誤",
        "description_zh": "答案接近正確，可能是抄寫或小計算失誤",
        "teacher_action_zh": "提醒學生檢查答案，養成驗算習慣",
        "parent_action_zh": "孩子其實會做，只是不小心算錯了，鼓勵他多檢查",
    },
    ErrorType.CALCULATION_ERROR: {
        "zh": "計算錯誤",
        "description_zh": "解題步驟正確但最後計算有誤",
        "teacher_action_zh": "加強基本運算練習，特別是多位數或分數運算",
        "parent_action_zh": "孩子理解觀念但計算需要加強",
    },
    ErrorType.UNIT_ERROR: {
        "zh": "單位錯誤",
        "description_zh": "單位換算錯誤或忘記標示單位",
        "teacher_action_zh": "強調單位換算步驟，建立單位對照表",
        "parent_action_zh": "孩子需要多練習單位的轉換",
    },
    ErrorType.READING_COMPREHENSION: {
        "zh": "閱讀理解問題",
        "description_zh": "可能未正確理解題目要求，花費較長時間",
        "teacher_action_zh": "使用題目圈劃法，協助學生找出關鍵資訊",
        "parent_action_zh": "孩子可能看不太懂題目，可以先幫他讀一遍題目",
    },
    ErrorType.GUESS_PATTERN: {
        "zh": "猜測作答",
        "description_zh": "回答速度過快，可能未經思考",
        "teacher_action_zh": "了解學生是否理解題目，是否需要更基礎的題目",
        "parent_action_zh": "孩子可能在亂猜，需要先確認他理解題目",
    },
    ErrorType.STUCK_AFTER_HINT: {
        "zh": "提示後仍卡住",
        "description_zh": "看了提示後仍然答錯，可能需要更基礎的協助",
        "teacher_action_zh": "建議面對面指導，此概念需要更詳細的教學",
        "parent_action_zh": "孩子可能需要老師個別指導這個部分",
    },
}


def classify_error(
    *,
    is_correct: bool,
    user_answer: Optional[str],
    correct_answer: Optional[str],
    response_time_sec: float = 0.0,
    avg_response_time_sec: Optional[float] = None,
    used_hints: bool = False,
    hint_levels_shown: int = 0,
    changed_answer: bool = False,
    meta: Optional[Dict[str, Any]] = None,
) -> Optional[ErrorType]:
    """Classify an incorrect answer into an error type.

    Returns None if the answer is correct.
    Uses rule-based heuristics — no ML.
    """
    if is_correct:
        return None

    meta = meta or {}

    # --- Priority 1: Explicit signals from engine ---
    if meta.get("method_wrong") is True:
        return ErrorType.CONCEPT_MISUNDERSTANDING

    if meta.get("steps_ok_final_wrong") is True:
        return ErrorType.CALCULATION_ERROR

    if meta.get("unit_mismatch") is True:
        return ErrorType.UNIT_ERROR

    # --- Priority 2: Stuck after hint ---
    if used_hints and hint_levels_shown >= 2:
        return ErrorType.STUCK_AFTER_HINT

    # --- Priority 3: Guess pattern (very fast wrong) ---
    if response_time_sec > 0 and response_time_sec <= 2:
        return ErrorType.GUESS_PATTERN

    # --- Priority 4: Reading comprehension (very slow) ---
    if avg_response_time_sec and avg_response_time_sec > 0 and response_time_sec > 0:
        threshold = max(30, avg_response_time_sec * 2.5)
        if response_time_sec >= threshold:
            return ErrorType.READING_COMPREHENSION

    # --- Priority 5: Careless (close to correct) ---
    if _is_numerically_close(user_answer, correct_answer):
        return ErrorType.CARELESS

    # --- Priority 6: Unit error ---
    if _has_unit_mismatch(user_answer, correct_answer):
        return ErrorType.UNIT_ERROR

    # --- Priority 7: Small delta or changed answer ---
    if changed_answer and meta.get("small_delta") is True:
        return ErrorType.CARELESS

    # --- Default: concept misunderstanding ---
    return ErrorType.CONCEPT_MISUNDERSTANDING


def get_error_description(error_type: ErrorType, lang: str = "zh") -> str:
    """Get human-readable description of an error type."""
    info = ERROR_DESCRIPTIONS.get(error_type, {})
    return info.get(f"description_{lang}", str(error_type.value))


def get_teacher_action(error_type: ErrorType) -> str:
    """Get suggested teacher action for an error type."""
    info = ERROR_DESCRIPTIONS.get(error_type, {})
    return info.get("teacher_action_zh", "")


def get_parent_action(error_type: ErrorType) -> str:
    """Get suggested parent action for an error type."""
    info = ERROR_DESCRIPTIONS.get(error_type, {})
    return info.get("parent_action_zh", "")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_numerically_close(
    user_answer: Optional[str],
    correct_answer: Optional[str],
    relative_tolerance: float = 0.05,
) -> bool:
    """Check if user answer is numerically close to correct answer."""
    if not user_answer or not correct_answer:
        return False
    try:
        # Strip common Chinese units
        u = _strip_units(str(user_answer).strip())
        c = _strip_units(str(correct_answer).strip())
        uf = float(u)
        cf = float(c)
        if abs(cf) < 1e-9:
            return abs(uf) < 1e-9
        return abs(uf - cf) / max(abs(cf), 1e-9) <= relative_tolerance
    except (ValueError, TypeError):
        return False


def _has_unit_mismatch(
    user_answer: Optional[str],
    correct_answer: Optional[str],
) -> bool:
    """Check if the numerical part matches but units differ."""
    if not user_answer or not correct_answer:
        return False

    u_num = _strip_units(str(user_answer).strip())
    c_num = _strip_units(str(correct_answer).strip())
    u_unit = str(user_answer).strip().replace(u_num, "").strip()
    c_unit = str(correct_answer).strip().replace(c_num, "").strip()

    if not c_unit:
        return False

    try:
        if abs(float(u_num) - float(c_num)) < 1e-9 and u_unit != c_unit:
            return True
    except (ValueError, TypeError):
        pass

    return False


_UNIT_CHARS = set("公分公尺公里公升毫升公斤克元角塊顆個隻本張秒分小時天日週月年度℃%")


def _strip_units(s: str) -> str:
    """Remove common Chinese math units from a string."""
    result = []
    for ch in s:
        if ch not in _UNIT_CHARS:
            result.append(ch)
    stripped = "".join(result).strip()
    return stripped if stripped else s
