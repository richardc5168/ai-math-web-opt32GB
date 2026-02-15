from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List


NEW_S2 = "判斷題型：『先用掉一些 → 剩下一些 → 再用掉剩下的一部分』，分兩段。"
NEW_S3 = "列式：第一次剩下 = 1 − 第一次用掉分數；第二次用掉 = 第一次剩下 × 第二次用掉分數；最後剩下 = 第一次剩下 − 第二次用掉（或 第一次剩下 × (1 − 第二次用掉分數)）。"


def _extract_json_array_from_bank_js(text: str) -> List[Dict[str, Any]]:
    s = str(text)

    m = re.search(
        r"^[ \t]*(?!//)window\.[A-Za-z0-9_]+\s*=\s*\[",
        s,
        flags=re.MULTILINE,
    )
    if not m:
        raise ValueError("bank.js missing 'window.<VAR> = [' assignment")

    start = m.end() - 1
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


def _rewrite_bank(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    items = _extract_json_array_from_bank_js(text)

    changed = 0
    for it in items:
        if not isinstance(it, dict):
            continue
        if str(it.get("kind") or "") != "remain_then_fraction":
            continue

        steps = list(it.get("steps") or [])
        if len(steps) < 3:
            continue

        if steps[1] != NEW_S2 or steps[2] != NEW_S3:
            steps[1] = NEW_S2
            steps[2] = NEW_S3
            it["steps"] = steps
            it["explanation"] = "\n".join([f"步驟 {i + 1}：{s}" for i, s in enumerate(steps)])
            changed += 1

    payload = json.dumps(items, ensure_ascii=False, indent=2)
    out = "/* Auto-generated offline question bank. */\n" + f"window.FRACTION_WORD_G5_BANK = {payload};\n"
    path.write_text(out, encoding="utf-8")

    return changed


def main() -> int:
    paths = [
        Path("docs/fraction-word-g5/bank.js"),
        Path("dist_ai_math_web_pages/docs/fraction-word-g5/bank.js"),
    ]

    total = 0
    for p in paths:
        n = _rewrite_bank(p)
        total += n
        print(f"OK: {p} updated remain_then_fraction items: {n}")

    if total == 0:
        print("OK: no changes needed")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
