#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
REPORT_PATH = ROOT / "data" / "elementary_fix_report.json"

MODULES: dict[str, tuple[str, str | None]] = {
    "fraction-g5": ("bank.js", None),
    "fraction-word-g5": ("bank.js", None),
    "decimal-unit4": ("bank.js", None),
    "volume-g5": ("bank.js", None),
    "ratio-percent-g5": ("bank.js", None),
    "life-applications-g5": ("bank.js", None),
    "g5-grand-slam": ("bank.js", None),
    "offline-math": ("bank.js", None),
    "interactive-decimal-g5": ("bank.js", None),
    "interactive-g5-empire": ("bank.js", None),
    "interactive-g5-life-pack1-empire": ("bank.js", None),
    "interactive-g5-life-pack1plus-empire": ("bank.js", None),
    "interactive-g5-life-pack2-empire": ("bank.js", None),
    "interactive-g5-life-pack2plus-empire": ("bank.js", None),
    "interactive-g56-core-foundation": ("g56_core_foundation.json", None),
    "exam-sprint": ("bank.js", None),
}

FRACTION_OVER_1_RE = re.compile(r"^\s*(-?\d+)\s*/\s*1\s*$")


def parse_js_bank(path: Path) -> tuple[str, list[dict[str, Any]]]:
    text = path.read_text(encoding="utf-8")
    for m in re.finditer(r"window\.(\w+)\s*=\s*\[", text):
        var_name = m.group(1)
        start = m.end() - 1
        depth = 0
        end = start
        for i in range(start, len(text)):
            c = text[i]
            if c == "[":
                depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        arr = text[start:end]
        if len(arr) < 10:
            continue
        try:
            parsed = json.loads(arr)
            if isinstance(parsed, list):
                return var_name, parsed
        except json.JSONDecodeError:
            continue
    raise RuntimeError(f"Could not parse JS array from {path}")


def write_js_bank(path: Path, var_name: str, items: list[dict[str, Any]]) -> None:
    body = json.dumps(items, ensure_ascii=False, indent=2)
    content = f"window.{var_name} = {body};\n"
    path.write_text(content, encoding="utf-8")


def normalize_hints(hints: Any) -> tuple[list[str], str]:
    if isinstance(hints, list):
        return [str(h).strip() for h in hints], "list"
    if isinstance(hints, dict):
        out: list[str] = []
        for k in ("level1", "level2", "level3"):
            v = str(hints.get(k, "")).strip()
            if v:
                out.append(v)
        return out, "dict"
    return [], "other"


def serialize_hints(hints: list[str], mode: str) -> Any:
    if mode == "dict":
        lv = hints[:3] + [""] * (3 - len(hints[:3]))
        return {"level1": lv[0], "level2": lv[1], "level3": lv[2]}
    return hints


def strip_hint_answer_leak(text: str, answer: str) -> str:
    s = str(text)
    ans = str(answer).strip()
    if not ans or len(ans) > 40:
        ans = ""

    # Strong rule: remove explicit answer segment after the keyword "答案"
    if "答案" in s:
        prefix = s.split("答案", 1)[0].rstrip("，,。；;：: ")
        if not prefix:
            prefix = "依照前面步驟計算"
        return f"{prefix}，最後請自行寫出答案。"

    esc = re.escape(ans) if ans else ""
    patterns = [
        r"[，,。；;\s]*答案[：:是為]\s*" + esc + r"[。\s]*$",
        r"[，,。；;\s]*(因此|所以)?\s*答案\s*[：:]?\s*" + esc + r"[。\s]*$",
        r"[，,。；;\s]*=\s*" + esc + r"[。\s]*$",
    ]
    out = s
    for p in patterns:
        out = re.sub(p, "。", out)

    # If the exact final answer token still appears in last hint, mask it.
    if ans:
        out = out.replace(ans, "（結果）")

    out = out.strip()
    if out.endswith("答案"):
        out += "請自行完成最後一步。"
    if not out:
        out = "依照前面步驟計算，最後請自行寫出答案。"
    return out


def ensure_steps_and_explanation(q: dict[str, Any], hints: list[str], report: Counter[str]) -> None:
    steps = q.get("steps") or q.get("teacherSteps") or []
    explanation = str(q.get("explanation") or "").strip()

    if not isinstance(steps, list) or len(steps) == 0:
        if hints:
            q["steps"] = [f"步驟{i+1}：{hints[i]}" for i in range(min(3, len(hints)))]
        else:
            q["steps"] = ["步驟1：先整理題目資訊。", "步驟2：選對運算式。", "步驟3：完成計算並檢查單位。"]
        report["add_steps"] += 1

    if not explanation:
        if hints:
            q["explanation"] = "；".join(hints[:3])
        else:
            q["explanation"] = "依照題目資訊列式後計算，並檢查答案合理性。"
        report["add_explanation"] += 1


def fix_question(module: str, q: dict[str, Any], report: Counter[str]) -> None:
    answer = str(q.get("answer") or "").strip()

    # Rule 1: fraction over 1 -> integer
    m = FRACTION_OVER_1_RE.match(answer)
    if m:
        q["answer"] = m.group(1)
        answer = q["answer"]
        report["fraction_over_1_to_int"] += 1

    # Rule 2: kind fallback
    if not str(q.get("kind") or "").strip():
        q["kind"] = "general"
        report["fill_kind"] += 1

    # Rule 3: hint leak cleanup
    hints_raw = q.get("hints")
    hints, mode = normalize_hints(hints_raw)
    if hints:
        # keep size, rewrite last hint as non-answer generic guidance
        new_hints: list[str] = []
        changed = False
        last_idx = len(hints) - 1
        for i, h in enumerate(hints):
            nh = h
            if i == last_idx:
                nh = "請依前面步驟完成計算，最後自行檢查單位並寫出答案。"
                if nh == h:
                    nh = strip_hint_answer_leak(h, answer)
            new_hints.append(nh)
            if nh != h:
                changed = True
        if changed:
            q["hints"] = serialize_hints(new_hints, mode)
            report["sanitize_hint_leak"] += 1

    # Rule 4: core-foundation needs steps/explanation
    if module == "interactive-g56-core-foundation":
        hints2, _ = normalize_hints(q.get("hints"))
        ensure_steps_and_explanation(q, hints2, report)


def main() -> int:
    overall = Counter()
    by_module: dict[str, Counter[str]] = defaultdict(Counter)

    for module, (filename, _unused) in MODULES.items():
        path = DOCS / module / filename
        if not path.exists():
            continue

        if filename.endswith(".json"):
            items = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(items, list):
                raise RuntimeError(f"JSON array expected: {path}")
            for q in items:
                if isinstance(q, dict):
                    fix_question(module, q, by_module[module])
            path.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        else:
            var_name, items = parse_js_bank(path)
            for q in items:
                if isinstance(q, dict):
                    fix_question(module, q, by_module[module])
            write_js_bank(path, var_name, items)

        overall.update(by_module[module])

    report = {
        "modules": sorted(MODULES.keys()),
        "overall": dict(overall),
        "by_module": {m: dict(c) for m, c in by_module.items()},
        "rules": {
            "fraction_over_1_to_int": "answer like n/1 is normalized to integer n",
            "fill_kind": "if kind missing/empty, set to 'general'",
            "sanitize_hint_leak": "remove explicit final-answer patterns from L3 hints",
            "add_steps": "for core-foundation, add default steps when missing",
            "add_explanation": "for core-foundation, add explanation when missing",
        },
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("Fixed modules:")
    for m in sorted(by_module):
        if by_module[m]:
            print(f"  {m}: {dict(by_module[m])}")
    print(f"\nOverall: {dict(overall)}")
    print(f"Report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
