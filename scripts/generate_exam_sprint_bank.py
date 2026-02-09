from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DIST_DOCS = ROOT / "dist_ai_math_web_pages" / "docs"

OUT_JS = DOCS / "exam-sprint" / "bank.js"
OUT_JS_DIST = DIST_DOCS / "exam-sprint" / "bank.js"

WINDOW_VAR = "EXAM_SPRINT_BANK"


SOURCE_BANKS: List[Tuple[str, Path]] = [
    ("g5-grand-slam", DOCS / "g5-grand-slam" / "bank.js"),
    ("ratio-percent-g5", DOCS / "ratio-percent-g5" / "bank.js"),
    ("volume-g5", DOCS / "volume-g5" / "bank.js"),
    ("fraction-word-g5", DOCS / "fraction-word-g5" / "bank.js"),
    ("fraction-g5", DOCS / "fraction-g5" / "bank.js"),
    ("decimal-unit4", DOCS / "decimal-unit4" / "bank.js"),
    ("life-applications-g5", DOCS / "life-applications-g5" / "bank.js"),
    ("interactive-decimal-g5", DOCS / "interactive-decimal-g5" / "bank.js"),
    ("interactive-g5-empire", DOCS / "interactive-g5-empire" / "bank.js"),
    ("interactive-g5-life-pack1-empire", DOCS / "interactive-g5-life-pack1-empire" / "bank.js"),
    ("interactive-g5-life-pack1plus-empire", DOCS / "interactive-g5-life-pack1plus-empire" / "bank.js"),
    ("interactive-g5-life-pack2-empire", DOCS / "interactive-g5-life-pack2-empire" / "bank.js"),
    ("interactive-g5-life-pack2plus-empire", DOCS / "interactive-g5-life-pack2plus-empire" / "bank.js"),
]


ADV_KEYWORDS = (
    "至少",
    "最多",
    "剛好",
    "剩下",
    "其餘",
    "平均",
    "比較",
    "差",
    "比率",
    "百分率",
    "折",
    "打折",
    "原來",
    "如果",
    "需要",
    "共",
    "每",
    "分成",
    "三步",
)


def _len_score(text: str) -> int:
    s = str(text or "")
    s = re.sub(r"\s+", "", s)
    return len(s)


def _count_keywords(text: str) -> int:
    s = str(text or "")
    return sum(1 for k in ADV_KEYWORDS if k in s)


def _item_quality_score(q: Dict[str, Any], source_id: str) -> float:
    """Higher is better (more application-heavy, multi-step, longer stem)."""
    diff = str(q.get("difficulty") or "").lower().strip()
    base = float(_difficulty_rank(diff))

    qtext = str(q.get("question") or "")
    steps = q.get("steps") or []
    hints = q.get("hints") or []
    expl = str(q.get("explanation") or "")

    qlen = _len_score(qtext)
    elen = _len_score(expl)
    step_n = len(steps) if isinstance(steps, list) else 0
    hint_n = len(hints) if isinstance(hints, list) else 0
    kw = _count_keywords(qtext)

    source_boost = 0.0
    if source_id in (
        "fraction-word-g5",
        "life-applications-g5",
        "ratio-percent-g5",
        "volume-g5",
        "interactive-g5-life-pack1-empire",
        "interactive-g5-life-pack1plus-empire",
        "interactive-g5-life-pack2-empire",
        "interactive-g5-life-pack2plus-empire",
    ):
        source_boost = 0.4

    # Prefer long stems and multi-step structure.
    return (
        base * 10.0
        + min(60, qlen) * 0.06
        + min(120, elen) * 0.03
        + min(8, step_n) * 0.55
        + min(6, hint_n) * 0.18
        + kw * 0.35
        + source_boost
    )


def _extract_json_array_from_bank_js(text: str) -> List[Dict[str, Any]]:
    s = str(text)

    # Many banks include comments like: // window.X = [...]
    # So we must locate the real assignment and then extract the matching array.
    m = re.search(
        r"^[ \t]*(?!//)window\.[A-Za-z0-9_]+\s*=\s*\[",
        s,
        flags=re.MULTILINE,
    )
    if not m:
        raise ValueError("bank.js missing 'window.<VAR> = [' assignment")

    start = m.end() - 1  # points to '['
    depth = 0
    in_str: str | None = None
    esc = False

    for pos in range(start, len(s)):
        ch = s[pos]

        if in_str is not None:
            if esc:
                esc = False
                continue
            if ch == "\\":
                esc = True
                continue
            if ch == in_str:
                in_str = None
            continue

        if ch in ('"', "'", "`"):
            in_str = ch
            continue
        if ch == "[":
            depth += 1
            continue
        if ch == "]":
            depth -= 1
            if depth == 0:
                raw = s[start : pos + 1]
                return json.loads(raw)

    raise ValueError("bank.js missing matching closing ']' for array")


def _load_bank(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return _extract_json_array_from_bank_js(path.read_text(encoding="utf-8"))


def _difficulty_rank(diff: str) -> int:
    d = str(diff or "").lower().strip()
    if d == "hard":
        return 3
    if d == "advanced":
        return 3
    if d == "medium":
        return 2
    if d == "normal":
        return 2
    if d == "easy":
        return 1
    return 0


def _is_advanced_item(q: Dict[str, Any], source_id: str) -> bool:
    diff = str(q.get("difficulty") or "").lower().strip()
    if diff in ("hard", "advanced"):
        qtext = str(q.get("question") or "")
        qlen = _len_score(qtext)
        kw = _count_keywords(qtext)
        steps = q.get("steps") or []
        step_n = len(steps) if isinstance(steps, list) else 0

        # Keep hard items, but avoid pure short drills.
        if qlen < 16 and step_n < 3 and kw == 0:
            return False
        return True

    # We still allow a controlled amount of "medium" for sprint warm-up,
    # but only when it's clearly application-heavy / multi-step.
    if diff == "normal":
        diff = "medium"

    if diff != "medium":
        return False

    qtext = str(q.get("question") or "")
    qlen = _len_score(qtext)
    kw = _count_keywords(qtext)
    steps = q.get("steps") or []
    step_n = len(steps) if isinstance(steps, list) else 0

    # Hard filter: avoid short, drill-like stems.
    if qlen < 18 and kw == 0:
        return False

    # Multi-step or keyword-rich medium problems qualify.
    if step_n >= 4:
        return True
    if kw >= 2 and qlen >= 22:
        return True

    # Application-heavy sources get a slightly lower bar.
    if source_id in (
        "fraction-word-g5",
        "life-applications-g5",
        "ratio-percent-g5",
        "volume-g5",
        "interactive-g5-life-pack1-empire",
        "interactive-g5-life-pack1plus-empire",
        "interactive-g5-life-pack2-empire",
        "interactive-g5-life-pack2plus-empire",
    ):
        if qlen >= 26 and (kw >= 1 or step_n >= 3):
            return True

    return False


def _normalize_item(q: Dict[str, Any], source_id: str) -> Dict[str, Any]:
    # Keep schema compatible with existing offline pages.
    out: Dict[str, Any] = {}
    out["id"] = f"exam_{source_id}__{q.get('id') or q.get('qid') or ''}".strip('_')

    # Prefer existing topic/kind; fall back to source label.
    out["topic"] = q.get("topic") or source_id
    out["kind"] = q.get("kind") or "mixed"
    diff = q.get("difficulty") or "medium"
    if str(diff).lower().strip() == "normal":
        diff = "medium"
    out["difficulty"] = diff

    out["question"] = q.get("question") or ""
    out["answer"] = q.get("answer")

    # Preserve answer type fields if present.
    # Normalize answer type field across banks.
    if "answer_unit" in q and q.get("answer_unit"):
        out["answer_unit"] = q.get("answer_unit")
    elif "answer_mode" in q and q.get("answer_mode"):
        out["answer_unit"] = q.get("answer_mode")

    out["hints"] = q.get("hints") or []
    out["steps"] = q.get("steps") or []
    out["explanation"] = q.get("explanation") or ""

    meta = dict(q.get("meta") or {})
    meta["source_module"] = source_id
    meta["source_id"] = q.get("id") or q.get("qid")
    out["meta"] = meta

    return out


def _is_valid_item(q: Dict[str, Any]) -> bool:
    if not q.get("question"):
        return False
    if q.get("answer") is None:
        return False
    hints = q.get("hints")
    if not isinstance(hints, list) or len(hints) < 3:
        return False
    if not str(q.get("explanation") or "").strip():
        return False
    return True


def build_exam_sprint_bank(
    max_items: int = 240,
    seed: int = 20260209,
    target_hard: int = 220,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for source_id, path in SOURCE_BANKS:
        for q in _load_bank(path):
            if not isinstance(q, dict):
                continue
            if not _is_advanced_item(q, source_id):
                continue
            item = _normalize_item(q, source_id)
            if not _is_valid_item(item):
                continue
            rows.append(item)

    # De-dup by (topic, question)
    seen = set()
    uniq: List[Dict[str, Any]] = []
    for it in rows:
        key = (str(it.get("topic") or ""), str(it.get("question") or ""))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(it)

    # Score, then select with a hard/medium mix.
    scored: List[Tuple[float, Dict[str, Any]]] = []
    for it in uniq:
        scored.append((_item_quality_score(it, str(it.get("meta", {}).get("source_module") or "")), it))

    # Deterministic jitter so ties don't always cluster.
    rng = random.Random(int(seed))
    scored.sort(key=lambda x: (x[0], rng.random()), reverse=True)

    hard_items: List[Dict[str, Any]] = []
    med_items: List[Dict[str, Any]] = []
    for _, it in scored:
        r = _difficulty_rank(str(it.get("difficulty")))
        if r >= 3:
            hard_items.append(it)
        elif r == 2:
            med_items.append(it)

    hard_take = min(int(target_hard), int(max_items), len(hard_items))
    med_take = min(int(max_items) - hard_take, len(med_items))

    def step_count(it: Dict[str, Any]) -> int:
        steps = it.get("steps") or []
        return len(steps) if isinstance(steps, list) else 0

    # User goal: hard questions should be more multi-step.
    # Enforce a higher step bar for hard items, but keep generation robust by falling back
    # to slightly lower step counts if strict filtering cannot satisfy target_hard.
    min_hard_steps_primary = 4
    min_hard_steps_fallback = 3

    hard_primary = [it for it in hard_items if step_count(it) >= min_hard_steps_primary]
    hard_fallback = [it for it in hard_items if min_hard_steps_fallback <= step_count(it) < min_hard_steps_primary]

    hard_ranked: List[Dict[str, Any]] = []
    hard_ranked.extend(hard_primary)
    if len(hard_ranked) < hard_take:
        hard_ranked.extend(hard_fallback)

    # If still not enough (rare), use the remaining hard items as last resort.
    if len(hard_ranked) < hard_take:
        hard_ids = {str(it.get("id")) for it in hard_ranked}
        hard_ranked.extend([it for it in hard_items if str(it.get("id")) not in hard_ids])

    # Prefer medium that still looks multi-step.
    def is_elite_medium(it: Dict[str, Any]) -> bool:
        qtext = str(it.get("question") or "")
        qlen = _len_score(qtext)
        kw = _count_keywords(qtext)
        steps = it.get("steps") or []
        step_n = len(steps) if isinstance(steps, list) else 0
        return (step_n >= 4) or (qlen >= 30 and kw >= 2 and step_n >= 3)

    elite_medium = [it for it in med_items if is_elite_medium(it)]
    rest_medium = [it for it in med_items if not is_elite_medium(it)]

    picked = hard_ranked[:hard_take] + elite_medium[:med_take]
    if len(picked) < int(max_items):
        need = int(max_items) - len(picked)
        picked.extend(rest_medium[:need])

    rng.shuffle(picked)
    return picked[: int(max_items)]


def write_bank_js(items: List[Dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(items, ensure_ascii=False, indent=2)
    out_path.write_text(
        f"/* Auto-generated offline question bank. */\nwindow.{WINDOW_VAR} = {payload};\n",
        encoding="utf-8",
    )


def main() -> int:
    items = build_exam_sprint_bank()
    write_bank_js(items, OUT_JS)
    write_bank_js(items, OUT_JS_DIST)

    hard = sum(1 for x in items if str(x.get("difficulty")).lower() in ("hard", "advanced"))
    medium = sum(1 for x in items if str(x.get("difficulty")).lower() == "medium")
    print(f"Wrote {len(items)} items: hard={hard} medium={medium}")
    print(f"- {OUT_JS}")
    print(f"- {OUT_JS_DIST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
