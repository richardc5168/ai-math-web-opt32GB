#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

MODULES: dict[str, tuple[str, str | None]] = {
    "fraction-g5": ("bank.js", "FRACTION_G5_BANK"),
    "fraction-word-g5": ("bank.js", "FRACTION_WORD_G5_BANK"),
    "decimal-unit4": ("bank.js", "DECIMAL_UNIT4_BANK"),
    "volume-g5": ("bank.js", "VOLUME_G5_BANK"),
    "ratio-percent-g5": ("bank.js", "RATIO_PERCENT_G5_BANK"),
    "life-applications-g5": ("bank.js", "LIFE_APPLICATIONS_G5_BANK"),
    "g5-grand-slam": ("bank.js", "G5_GRAND_SLAM_BANK"),
    "offline-math": ("bank.js", "OFFLINE_MATH_BANK"),
    "interactive-decimal-g5": ("bank.js", "INTERACTIVE_DECIMAL_G5_BANK"),
    "interactive-g5-empire": ("bank.js", "INTERACTIVE_G5_EMPIRE_BANK"),
    "interactive-g5-life-pack1-empire": ("bank.js", "G5_LIFE_PACK1_BANK"),
    "interactive-g5-life-pack1plus-empire": ("bank.js", "G5_LIFE_PACK1PLUS_BANK"),
    "interactive-g5-life-pack2-empire": ("bank.js", "G5_LIFE_PACK2_BANK"),
    "interactive-g5-life-pack2plus-empire": ("bank.js", "G5_LIFE_PACK2PLUS_BANK"),
    "interactive-g56-core-foundation": ("g56_core_foundation.json", None),
    "exam-sprint": ("bank.js", "EXAM_SPRINT_BANK"),
    "commercial-pack1-fraction-sprint": ("bank.js", "COMMERCIAL_PACK1_FRACTION_SPRINT_BANK"),
}

GARBLED_RE = re.compile(r"\ufffd|\?\?\?|")
FRAC_OVER_1_RE = re.compile(r"^\s*-?\d+\s*/\s*1\s*$")


def parse_js_array(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    for m in re.finditer(r"window\.\w+\s*=\s*\[", text):
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
        chunk = text[start:end]
        if len(chunk) < 10:
            continue
        try:
            arr = json.loads(chunk)
            if isinstance(arr, list):
                return arr
        except json.JSONDecodeError:
            continue
    # Fallback: use Node.js VM to evaluate IIFE-style bank files
    return _parse_js_via_node(path, text)


def _parse_js_via_node(path: Path, text: str) -> list[dict[str, Any]]:
    """Use Node.js to evaluate JS bank files that can't be statically parsed."""
    import subprocess
    import shutil

    node = shutil.which("node")
    if not node:
        return []
    # Find the window variable name
    var_match = re.search(r"window\.(\w+)\s*=", text)
    if not var_match:
        return []
    var_name = var_match.group(1)
    script = (
        f"const vm=require('vm'),fs=require('fs');"
        f"const code=fs.readFileSync({json.dumps(str(path))},'utf8');"
        f"const ctx={{window:{{}},console}};"
        f"vm.createContext(ctx);vm.runInContext(code,ctx);"
        f"process.stdout.write(JSON.stringify(ctx.window['{var_name}']||[]));"
    )
    try:
        result = subprocess.run(
            [node, "-e", script],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0 and result.stdout.strip():
            arr = json.loads(result.stdout)
            if isinstance(arr, list):
                return arr
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        pass
    return []


def load_module_questions(module: str, filename: str) -> list[dict[str, Any]]:
    path = DOCS / module / filename
    if not path.exists():
        return []
    if path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    return parse_js_array(path)


def pick_first(*vals: Any, default: str = "") -> str:
    for v in vals:
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return default


def normalize_hints(hints: Any) -> list[str]:
    if isinstance(hints, list):
        return [str(h).strip() for h in hints if str(h).strip()]
    if isinstance(hints, dict):
        out = []
        for k in ("level1", "level2", "level3"):
            v = str(hints.get(k, "")).strip()
            if v:
                out.append(v)
        return out
    return []


def hint_leak(ans: str, hints: list[str], strict: bool) -> bool:
    if not ans or len(ans) > 24:
        return False
    if not hints:
        return False
    target = hints[-1]
    if strict:
        return ans in target
    return bool(
        re.search(r"答案[：:是為]\s*" + re.escape(ans) + r"(\b|\s|。|$)", target)
        or re.search(r"=\s*" + re.escape(ans) + r"(\b|\s|。|$)", target)
    )


def validate_one(module: str, q: dict[str, Any], idx: int, strict_hint_leak: bool) -> list[tuple[str, str]]:
    issues: list[tuple[str, str]] = []

    qid = pick_first(q.get("id"), q.get("qid"), default=f"{module}#{idx}")
    question = pick_first(q.get("question"), q.get("stem"), q.get("prompt"))
    answer = pick_first(q.get("answer"), q.get("final_answer"))
    difficulty = pick_first(q.get("difficulty"), default="")
    topic = pick_first(q.get("topic"), q.get("block"), default="")
    kind = pick_first(q.get("kind"), q.get("subskill"), default="")
    hints = normalize_hints(q.get("hints"))
    steps = q.get("steps") or q.get("teacherSteps") or []
    explanation = pick_first(q.get("explanation"), q.get("analysis"), default="")

    if len(question) < 5:
        issues.append(("Q_TEXT", f"{qid}: missing/too-short question"))
    if not answer:
        issues.append(("Q_ANSWER", f"{qid}: missing answer"))
    if hints and len(hints) < 3:
        issues.append(("Q_HINT_COUNT", f"{qid}: hints < 3 (got {len(hints)})"))
    if hints and any(len(h) < 4 for h in hints[:3]):
        issues.append(("Q_HINT_SHORT", f"{qid}: hint too short"))
    if isinstance(steps, list) and len(steps) == 0 and module == "interactive-g56-core-foundation":
        issues.append(("Q_STEPS", f"{qid}: missing steps"))
    if module == "interactive-g56-core-foundation" and not explanation:
        issues.append(("Q_EXPLANATION", f"{qid}: missing explanation"))

    if difficulty:
        if difficulty.lower() not in {"easy", "medium", "hard", "1", "2", "3"}:
            issues.append(("Q_DIFFICULTY", f"{qid}: bad difficulty={difficulty}"))
    topic_or_unit = pick_first(q.get("topic"), q.get("block"), q.get("unit_id"), default="")
    if not topic_or_unit:
        issues.append(("Q_TOPIC", f"{qid}: missing topic/unit_id"))
    if not kind:
        issues.append(("Q_KIND", f"{qid}: missing kind"))

    whole = " ".join([question, answer, topic, kind, " ".join(hints), explanation])
    if "\ufffd" in whole or "???" in whole:
        issues.append(("Q_ENCODING", f"{qid}: possible garbled text"))

    if hints and hint_leak(answer, hints, strict_hint_leak):
        issues.append(("Q_HINT_LEAK", f"{qid}: hint reveals answer"))

    if FRAC_OVER_1_RE.match(answer):
        issues.append(("Q_FRAC_OVER_1", f"{qid}: answer {answer} could be integer"))

    return issues


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict-hint-leak", action="store_true", help="Flag any answer substring in last hint")
    ap.add_argument("--max-print", type=int, default=200, help="max detailed issue lines to print")
    args = ap.parse_args()

    issue_by_code = Counter()
    issue_by_module = Counter()
    module_counts = {}
    all_issues: list[tuple[str, str, str]] = []
    fail_ids = set()

    total = 0

    for module, (filename, _var) in MODULES.items():
        items = load_module_questions(module, filename)
        module_counts[module] = len(items)
        total += len(items)
        for i, q in enumerate(items, start=1):
            if not isinstance(q, dict):
                code = "Q_SCHEMA"
                msg = f"{module}#{i}: item is not object"
                issue_by_code[code] += 1
                issue_by_module[module] += 1
                all_issues.append((module, code, msg))
                fail_ids.add(f"{module}#{i}")
                continue

            qid = pick_first(q.get("id"), q.get("qid"), default=f"{module}#{i}")
            issues = validate_one(module, q, i, args.strict_hint_leak)
            if issues:
                fail_ids.add(qid)
            for code, msg in issues:
                issue_by_code[code] += 1
                issue_by_module[module] += 1
                all_issues.append((module, code, msg))

    print("=" * 72)
    print("ELEMENTARY BANK VALIDATION SUMMARY")
    print("=" * 72)
    print(f"Modules scanned : {len(MODULES)}")
    print(f"Total questions : {total}")
    print(f"PASS questions  : {total - len(fail_ids)}")
    print(f"FAIL questions  : {len(fail_ids)}")
    print(f"Total issues    : {len(all_issues)}")

    print("\n-- Questions per module --")
    for m, c in sorted(module_counts.items(), key=lambda kv: -kv[1]):
        print(f"  {m:45s} {c:4d}")

    print("\n-- Issues by code --")
    if not issue_by_code:
        print("  (none)")
    else:
        for code, c in issue_by_code.most_common():
            print(f"  {code:20s} {c:4d}")

    print("\n-- Issues by module --")
    if not issue_by_module:
        print("  (none)")
    else:
        for m, c in issue_by_module.most_common():
            print(f"  {m:45s} {c:4d}")

    if all_issues:
        print("\n-- Detailed issues --")
        for i, (m, code, msg) in enumerate(all_issues, start=1):
            if i > args.max_print:
                remain = len(all_issues) - args.max_print
                print(f"  ... ({remain} more not shown, increase --max-print)")
                break
            print(f"  [{code}] {m} :: {msg}")

    return 0 if len(all_issues) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
