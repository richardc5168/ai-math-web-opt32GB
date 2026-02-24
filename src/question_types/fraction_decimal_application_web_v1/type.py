from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any


TYPE_KEY = "fraction_decimal_application_web_v1"
DEFAULT_PACK_PATH = Path("data/fraction_decimal_application_web_v1_pack.json")


@dataclass(frozen=True)
class PackItem:
    id: str
    type_key: str
    category: str
    difficulty: str
    question: str
    answer: str
    hints: dict[str, str]
    hint_ladder: dict[str, str]
    steps: list[str]
    error_diagnostics: list[dict[str, str]]
    validator: dict[str, Any]
    evidence: dict[str, Any]
    topic_tags: list[str]
    concept_points: list[str]


_PACK_CACHE: list[PackItem] | None = None


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def load_pack(path: Path = DEFAULT_PACK_PATH) -> list[PackItem]:
    global _PACK_CACHE
    if _PACK_CACHE is not None:
        return _PACK_CACHE

    raw = json.loads(path.read_text(encoding="utf-8"))
    items = raw.get("items")
    if not isinstance(items, list):
        raise ValueError("pack.items must be list")

    out: list[PackItem] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if _safe_text(item.get("type_key")) != TYPE_KEY:
            continue
        out.append(
            PackItem(
                id=_safe_text(item.get("id")),
                type_key=TYPE_KEY,
                category=_safe_text(item.get("category")),
                difficulty=_safe_text(item.get("difficulty") or "medium"),
                question=_safe_text(item.get("question")),
                answer=_safe_text(item.get("answer")),
                hints=dict(item.get("hints") or {}),
                hint_ladder=dict(item.get("hint_ladder") or {}),
                steps=[_safe_text(x) for x in (item.get("steps") or [])],
                error_diagnostics=[
                    {
                        "code": _safe_text(x.get("code")) if isinstance(x, dict) else "",
                        "message": _safe_text(x.get("message")) if isinstance(x, dict) else "",
                        "remedy": _safe_text(x.get("remedy")) if isinstance(x, dict) else "",
                    }
                    for x in (item.get("error_diagnostics") or [])
                ],
                validator=dict(item.get("validator") or {}),
                evidence=dict(item.get("evidence") or {}),
                topic_tags=[_safe_text(x) for x in (item.get("topic_tags") or [])],
                concept_points=[_safe_text(x) for x in (item.get("concept_points") or [])],
            )
        )

    if not out:
        raise ValueError("No items loaded for TYPE_KEY")

    _PACK_CACHE = out
    return out


def _parse_fraction(value: str) -> Fraction | None:
    normalized = (value or "").strip().replace(" ", "")
    if not normalized or "/" not in normalized:
        return None
    if not re.fullmatch(r"-?\d+\s*/\s*-?\d+", normalized):
        return None
    try:
        return Fraction(normalized)
    except Exception:
        return None


def _parse_number(value: str) -> float | None:
    normalized = (value or "").strip().replace(",", "")
    if not normalized:
        return None
    try:
        return float(normalized)
    except Exception:
        return None


def make_engine_question(item: PackItem) -> dict[str, Any]:
    correct_payload = {
        "type_key": TYPE_KEY,
        "answer": item.answer,
        "validator": item.validator,
    }
    explanation = "\n".join(
        [
            "（完整步驟）",
            *[f"- {line}" for line in item.steps],
            "",
            f"（Evidence）{item.evidence.get('title', '')} | {item.evidence.get('source_url', '')}",
        ]
    ).strip()

    hints = {
        "level1": _safe_text(item.hints.get("level1") or item.hint_ladder.get("h1_strategy")),
        "level2": _safe_text(item.hints.get("level2") or item.hint_ladder.get("h2_equation")),
        "level3": _safe_text(item.hints.get("level3") or item.hint_ladder.get("h3_compute")),
    }

    return {
        "type_key": TYPE_KEY,
        "topic": TYPE_KEY,
        "difficulty": item.difficulty,
        "question": item.question,
        "answer": json.dumps(correct_payload, ensure_ascii=False),
        "explanation": explanation,
        "steps": item.steps,
        "hints": hints,
    }


def next_question() -> dict[str, Any]:
    import random

    items = load_pack()
    chosen = random.choice(items)
    return make_engine_question(chosen)


def check_answer(user_answer: str, payload: dict[str, Any]) -> int | None:
    validator = payload.get("validator") if isinstance(payload.get("validator"), dict) else {}
    vtype = _safe_text(validator.get("type"))
    correct_answer = _safe_text(payload.get("answer"))
    user = _safe_text(user_answer)

    if vtype == "fraction":
        user_fraction = _parse_fraction(user)
        correct_fraction = _parse_fraction(correct_answer)
        if user_fraction is None or correct_fraction is None:
            return None
        return 1 if user_fraction == correct_fraction else 0

    if vtype == "number":
        user_number = _parse_number(user)
        correct_number = _parse_number(correct_answer)
        if user_number is None or correct_number is None:
            return None
        tolerance = float(validator.get("tolerance") or 0)
        return 1 if math.isclose(user_number, correct_number, rel_tol=0.0, abs_tol=tolerance) else 0

    user_clean = "".join(user.split()).lower()
    correct_clean = "".join(correct_answer.split()).lower()
    if not user_clean or not correct_clean:
        return None
    return 1 if user_clean == correct_clean else 0
