from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


TYPE_KEY = "fraction_decimal_application_web_v1"


def _die(msg: str) -> None:
    raise SystemExit(msg)


def _norm(s: str) -> str:
    return "".join(str(s or "").split()).lower()


def _is_fraction(value: str) -> bool:
    return bool(re.fullmatch(r"-?\d+\s*/\s*-?\d+", str(value or "").strip()))


def _hint_leaks(hints: dict[str, Any], answer: str) -> bool:
    ans = _norm(answer)
    if not ans:
        return False
    for key in ("level1", "level2", "level3"):
        if ans in _norm(hints.get(key) or ""):
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", default="data/fraction_decimal_application_web_v1_pack.json")
    args = parser.parse_args(argv)

    p = Path(args.pack)
    if not p.exists():
        _die(f"Missing pack: {p}")

    raw = json.loads(p.read_text(encoding="utf-8"))
    if raw.get("type_key") != TYPE_KEY:
        _die("pack.type_key mismatch")

    items = raw.get("items")
    if not isinstance(items, list) or not items:
        _die("pack.items must be non-empty list")

    seen_id: set[str] = set()
    seen_q: set[str] = set()
    category_seen: set[str] = set()

    for i, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            _die(f"item#{i} must be object")

        item_id = str(item.get("id") or "").strip()
        if not item_id:
            _die(f"item#{i} missing id")
        if item_id in seen_id:
            _die(f"duplicate id: {item_id}")
        seen_id.add(item_id)

        if str(item.get("type_key") or "") != TYPE_KEY:
            _die(f"item#{i} type_key mismatch")

        category = str(item.get("category") or "").strip()
        if category not in {"shopping_discount", "average_distribution", "unit_conversion", "distance_time"}:
            _die(f"item#{i} invalid category={category}")
        category_seen.add(category)

        question = str(item.get("question") or "").strip()
        if not question:
            _die(f"item#{i} missing question")
        if question in seen_q:
            _die(f"duplicate question: {question}")
        seen_q.add(question)

        answer = str(item.get("answer") or "").strip()
        if not answer:
            _die(f"item#{i} missing answer")

        hints = item.get("hints")
        if not isinstance(hints, dict):
            _die(f"item#{i} hints must be object")
        for level in ("level1", "level2", "level3"):
            if not str(hints.get(level) or "").strip():
                _die(f"item#{i} missing {level}")
        if _hint_leaks(hints, answer):
            _die(f"item#{i} hints leak answer")

        ladder = item.get("hint_ladder")
        if not isinstance(ladder, dict):
            _die(f"item#{i} hint_ladder must be object")
        for key in ("h1_strategy", "h2_equation", "h3_compute", "h4_check_reflect"):
            if not str(ladder.get(key) or "").strip():
                _die(f"item#{i} missing hint_ladder.{key}")

        diag = item.get("error_diagnostics")
        if not isinstance(diag, list) or len(diag) < 5:
            _die(f"item#{i} error_diagnostics must have >=5")

        validator = item.get("validator")
        if not isinstance(validator, dict):
            _die(f"item#{i} validator must be object")
        vtype = str(validator.get("type") or "")
        if vtype not in ("number", "fraction", "text"):
            _die(f"item#{i} invalid validator.type={vtype}")
        if vtype == "fraction" and not _is_fraction(answer):
            _die(f"item#{i} fraction answer parse error")
        if vtype == "number":
            try:
                float(answer)
            except Exception:
                _die(f"item#{i} number answer parse error")

        evidence = item.get("evidence")
        if not isinstance(evidence, dict) or not str(evidence.get("source_url") or "").strip():
            _die(f"item#{i} evidence.source_url required")

    required = {"shopping_discount", "average_distribution", "unit_conversion", "distance_time"}
    if not required.issubset(category_seen):
        _die("pack missing required categories")

    print(f"OK: items={len(items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
