from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple


ALLOWED_ISSUE_TYPES = {
    "math_error",
    "ambiguity",
    "wording",
    "hint_gap",
    "too_hard",
    "answer_format",
    "unit_mismatch",
    "other",
}


@dataclass(frozen=True)
class ReviewStats:
    total: int
    invalid: int
    templates: int


def _is_int_in_range(v: Any, lo: int, hi: int) -> bool:
    return isinstance(v, int) and lo <= v <= hi


def validate_review_item(obj: Dict[str, Any]) -> List[str]:
    errors: List[str] = []

    if not isinstance(obj.get("template_id"), str) or not obj.get("template_id"):
        errors.append("template_id missing/invalid")

    if not isinstance(obj.get("seed"), int):
        errors.append("seed missing/invalid")

    scores = obj.get("scores")
    if not isinstance(scores, dict):
        errors.append("scores missing/invalid")
    else:
        required_scores = [
            "question_quality",
            "answer_correctness",
            "hint_clarity_for_kids",
            "stepwise_guidance",
            "math_rigor",
        ]
        for k in required_scores:
            if not _is_int_in_range(scores.get(k), 0, 5):
                errors.append(f"scores.{k} missing/invalid")

    issues = obj.get("issues")
    if not isinstance(issues, list):
        errors.append("issues missing/invalid")
    else:
        for it in issues:
            if not isinstance(it, dict):
                errors.append("issues item not object")
                continue
            t = it.get("type")
            d = it.get("detail")
            if t not in ALLOWED_ISSUE_TYPES:
                errors.append(f"issues.type invalid: {t}")
            if not isinstance(d, str):
                errors.append("issues.detail missing/invalid")

    rh = obj.get("rewrite_hints")
    if not (isinstance(rh, list) and len(rh) == 3 and all(isinstance(x, str) and x.strip() for x in rh)):
        errors.append("rewrite_hints missing/invalid (must be 3 non-empty strings)")

    # Optional: rewrite_solution_steps
    rss = obj.get("rewrite_solution_steps")
    if rss is not None:
        if not (isinstance(rss, list) and all(isinstance(x, str) for x in rss)):
            errors.append("rewrite_solution_steps invalid")

    return errors


def iter_reviews_jsonl_lines(text: str) -> Iterable[Tuple[int, Dict[str, Any], List[str]]]:
    for idx, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            yield idx, {}, ["invalid json"]
            continue
        if not isinstance(obj, dict):
            yield idx, {}, ["line is not a JSON object"]
            continue
        yield idx, obj, validate_review_item(obj)


def compute_review_stats(objs: List[Dict[str, Any]], invalid: int) -> ReviewStats:
    templates = len({str(o.get("template_id")) for o in objs if isinstance(o, dict) and o.get("template_id")})
    return ReviewStats(total=len(objs), invalid=int(invalid), templates=int(templates))
