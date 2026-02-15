from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List

from scripts.question_review import iter_reviews_jsonl_lines


def _avg(nums: List[int]) -> float:
    return (sum(nums) / len(nums)) if nums else 0.0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Summarize external LLM reviews to a Markdown report.")
    p.add_argument("--in_jsonl", default="artifacts/question_reviews.jsonl")
    p.add_argument("--out_md", default="artifacts/question_reviews_summary.md")
    p.add_argument("--max_examples", type=int, default=3)
    args = p.parse_args(argv)

    in_path = Path(args.in_jsonl)
    out_path = Path(args.out_md)

    if not in_path.exists():
        print(f"ERROR: not found: {in_path}")
        return 2

    text = in_path.read_text(encoding="utf-8")

    by_template: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    invalid_lines: List[int] = []

    for line_no, obj, errors in iter_reviews_jsonl_lines(text):
        if errors:
            invalid_lines.append(line_no)
            continue
        tid = str(obj.get("template_id") or "")
        by_template[tid].append(obj)

    lines: List[str] = []
    lines.append("# External LLM Review Summary")
    lines.append(f"- input: {in_path}")
    lines.append(f"- templates: {len(by_template)}")
    lines.append(f"- invalid_lines: {len(invalid_lines)}")
    if invalid_lines:
        lines.append(f"- invalid_line_numbers: {invalid_lines[:50]}")

    score_keys = [
        "question_quality",
        "answer_correctness",
        "hint_clarity_for_kids",
        "stepwise_guidance",
        "math_rigor",
    ]

    for tid in sorted(by_template.keys()):
        items = by_template[tid]
        if not items:
            continue

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

        lines.append("")
        lines.append(f"## {tid}")
        lines.append(f"- count: {len(items)}")
        lines.append(
            "- avg_scores: "
            + json.dumps({k: round(_avg(score_buckets[k]), 2) for k in score_keys}, ensure_ascii=False)
        )

        if issue_types:
            top = issue_types.most_common(5)
            lines.append("- top_issues: " + json.dumps(top, ensure_ascii=False))

        examples_added = 0
        for it in items:
            rh = it.get("rewrite_hints")
            if not (isinstance(rh, list) and len(rh) == 3):
                continue
            seed = it.get("seed")
            lines.append(f"- example seed={seed}:")
            lines.append(f"  - hint1: {rh[0]}")
            lines.append(f"  - hint2: {rh[1]}")
            lines.append(f"  - hint3: {rh[2]}")
            examples_added += 1
            if examples_added >= int(args.max_examples):
                break

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"OK: wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
