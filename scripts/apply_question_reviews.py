from __future__ import annotations

import argparse
import difflib
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from scripts.question_review import iter_reviews_jsonl_lines


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)
    out: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if isinstance(obj, dict):
            out.append(obj)
    return out


def _best_review_item(items: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not items:
        return None

    def score_key(it: Dict[str, Any]) -> Tuple[int, int, int, int]:
        scores = it.get("scores") or {}
        issues = it.get("issues") or []
        issue_count = len(issues) if isinstance(issues, list) else 99
        hk = int(scores.get("hint_clarity_for_kids") or 0)
        sg = int(scores.get("stepwise_guidance") or 0)
        mr = int(scores.get("math_rigor") or 0)
        # Higher is better; fewer issues is better.
        return (hk + sg + mr, -issue_count, hk, sg)

    return max(items, key=score_key)


def build_hint_override_patch(
    *,
    hint_overrides_path: Path,
    new_entries: Dict[str, Dict[str, Any]],
) -> str:
    old_text = hint_overrides_path.read_text(encoding="utf-8") if hint_overrides_path.exists() else ""

    # Very small, safe insertion: we append new entries just before the final closing brace of HINT_OVERRIDES.
    marker = "HINT_OVERRIDES: Dict[str, Dict[str, Any]] = {"
    if marker not in old_text:
        raise RuntimeError(f"unexpected file format: {hint_overrides_path}")

    if not new_entries:
        return ""

    lines = old_text.splitlines()
    # Find the last line that is exactly '}' (end of dict). Use the last occurrence.
    close_idx = None
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip() == "}":
            close_idx = i
            break
    if close_idx is None:
        raise RuntimeError(f"cannot locate closing brace in: {hint_overrides_path}")

    insert: List[str] = []
    insert.append("    # --- candidates from external reviews (approved=False by default) ---")
    for template_id in sorted(new_entries.keys()):
        e = new_entries[template_id]
        l1 = json.dumps(str(e.get("level1") or ""), ensure_ascii=False)
        l2 = json.dumps(str(e.get("level2") or ""), ensure_ascii=False)
        l3 = json.dumps(str(e.get("level3") or ""), ensure_ascii=False)
        note = json.dumps(str(e.get("note") or ""), ensure_ascii=False)
        source = json.dumps(str(e.get("source") or "external_llm"), ensure_ascii=False)

        insert.extend(
            [
                f"    {json.dumps(template_id)}: {{",
                "        \"approved\": False,",
                f"        \"level1\": {l1},",
                f"        \"level2\": {l2},",
                f"        \"level3\": {l3},",
                f"        \"source\": {source},",
                f"        \"note\": {note},",
                "    },",
            ]
        )

    new_lines = lines[:close_idx] + insert + lines[close_idx:]
    new_text = "\n".join(new_lines) + "\n"

    diff = difflib.unified_diff(
        old_text.splitlines(keepends=True),
        new_text.splitlines(keepends=True),
        fromfile=str(hint_overrides_path).replace("\\", "/"),
        tofile=str(hint_overrides_path).replace("\\", "/"),
    )
    return "".join(diff)


def write_suggestions_md(
    *,
    out_path: Path,
    grouped: Dict[str, List[Dict[str, Any]]],
    dump_index: Dict[Tuple[str, int], Dict[str, Any]],
    max_examples: int,
) -> None:
    score_keys = [
        "question_quality",
        "answer_correctness",
        "hint_clarity_for_kids",
        "stepwise_guidance",
        "math_rigor",
    ]

    def avg(nums: List[int]) -> float:
        return (sum(nums) / len(nums)) if nums else 0.0

    lines: List[str] = []
    lines.append("# Apply Reviews (Suggestions)")
    lines.append(f"- templates: {len(grouped)}")

    for template_id in sorted(grouped.keys()):
        items = grouped[template_id]
        lines.append("")
        lines.append(f"## {template_id}")
        lines.append(f"- reviews: {len(items)}")

        score_buckets = {k: [] for k in score_keys}
        issue_types = Counter()

        for it in items:
            scores = it.get("scores") or {}
            for k in score_keys:
                v = scores.get(k)
                if isinstance(v, int):
                    score_buckets[k].append(v)
            for iss in (it.get("issues") or []):
                if isinstance(iss, dict) and isinstance(iss.get("type"), str):
                    issue_types[iss["type"]] += 1

        lines.append(
            "- avg_scores: "
            + json.dumps({k: round(avg(score_buckets[k]), 2) for k in score_keys}, ensure_ascii=False)
        )
        if issue_types:
            lines.append("- top_issues: " + json.dumps(issue_types.most_common(5), ensure_ascii=False))

        ex = 0
        for it in sorted(items, key=lambda x: int(x.get("seed") or 0)):
            rh = it.get("rewrite_hints")
            if not (isinstance(rh, list) and len(rh) == 3):
                continue
            seed = int(it.get("seed") or 0)
            dump_item = dump_index.get((template_id, seed))

            lines.append(f"- seed={seed}:")
            if dump_item:
                q = str(dump_item.get("question") or "").strip()
                a = str(dump_item.get("answer") or "").strip()
                if q:
                    lines.append(f"  - question: {q}")
                if a:
                    lines.append(f"  - answer: {a}")

            lines.append(f"  - rewrite_hint1: {rh[0]}")
            lines.append(f"  - rewrite_hint2: {rh[1]}")
            lines.append(f"  - rewrite_hint3: {rh[2]}")

            ex += 1
            if ex >= int(max_examples):
                break

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_dump_index(dump_items: List[Dict[str, Any]]) -> Dict[Tuple[str, int], Dict[str, Any]]:
    idx: Dict[Tuple[str, int], Dict[str, Any]] = {}
    for it in dump_items:
        try:
            template_id = str(it.get("template_id") or "").strip()
            seed = int(it.get("seed"))
        except Exception:
            continue
        if template_id and seed:
            idx[(template_id, seed)] = it
    return idx


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "Build a safe, human-reviewable patch from external LLM rewrite_hints. "
            "Does not modify engine automatically."
        )
    )
    p.add_argument("--in_reviews", default="artifacts/question_reviews.jsonl")
    p.add_argument("--in_dump", default="artifacts/questions_dump.jsonl")
    p.add_argument("--hint_overrides", default="hint_overrides.py")
    p.add_argument("--out_dir", default="artifacts/review_apply")
    p.add_argument("--max_examples", type=int, default=3)
    args = p.parse_args(argv)

    in_reviews = Path(args.in_reviews)
    in_dump = Path(args.in_dump)
    hint_overrides = Path(args.hint_overrides)
    out_dir = Path(args.out_dir)

    # Validate and load reviews
    text = in_reviews.read_text(encoding="utf-8")
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    invalid = 0

    for _, obj, errors in iter_reviews_jsonl_lines(text):
        if errors:
            invalid += 1
            continue
        tid = str(obj.get("template_id") or "").strip()
        if not tid:
            invalid += 1
            continue
        grouped[tid].append(obj)

    if invalid:
        print(f"ERROR: review file has invalid lines: {invalid}. Fix first via validate_question_reviews.py")
        return 2

    dump_items: List[Dict[str, Any]] = []
    if in_dump.exists():
        dump_items = _read_jsonl(in_dump)
    dump_index = build_dump_index(dump_items)

    # For each template, pick the best rewrite_hints and prepare override entries (approved=False)
    new_entries: Dict[str, Dict[str, Any]] = {}
    today = str(date.today())

    for tid in sorted(grouped.keys()):
        best = _best_review_item(grouped[tid])
        if not best:
            continue
        rh = best.get("rewrite_hints")
        if not (isinstance(rh, list) and len(rh) == 3):
            continue

        seed = int(best.get("seed") or 0)
        note_bits = [f"candidate {today}", f"seed={seed}"]
        new_entries[tid] = {
            "level1": str(rh[0]).strip(),
            "level2": str(rh[1]).strip(),
            "level3": str(rh[2]).strip(),
            "source": "external_llm",
            "note": "; ".join(note_bits),
        }

    out_dir.mkdir(parents=True, exist_ok=True)

    suggestions_md = out_dir / "suggestions_by_template.md"
    write_suggestions_md(
        out_path=suggestions_md,
        grouped=grouped,
        dump_index=dump_index,
        max_examples=int(args.max_examples),
    )

    patch_text = build_hint_override_patch(hint_overrides_path=hint_overrides, new_entries=new_entries)
    patch_path = out_dir / "hint_overrides_candidates.patch"
    patch_path.write_text(patch_text, encoding="utf-8")

    print("OK")
    print(f"- wrote: {suggestions_md}")
    print(f"- wrote: {patch_path}")
    print("Next: review patch, then apply with: git apply <patch>")
    print("Then manually set approved=True for the templates you accept.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
