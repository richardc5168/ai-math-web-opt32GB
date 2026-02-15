from __future__ import annotations

import argparse
from pathlib import Path

from scripts.question_review import compute_review_stats, iter_reviews_jsonl_lines


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Validate external LLM question review JSONL.")
    p.add_argument("--in_jsonl", default="artifacts/question_reviews.jsonl")
    args = p.parse_args(argv)

    path = Path(args.in_jsonl)
    if not path.exists():
        print(f"ERROR: not found: {path}")
        return 2

    text = path.read_text(encoding="utf-8")

    invalid = 0
    objs: list[dict] = []

    for line_no, obj, errors in iter_reviews_jsonl_lines(text):
        objs.append(obj)
        if errors:
            invalid += 1
            preview = (path.name, line_no)
            print(f"INVALID {preview}: {errors}")

    stats = compute_review_stats(objs, invalid)
    print("OK" if invalid == 0 else "HAS_ERRORS")
    print(
        f"summary: total={stats.total} invalid={stats.invalid} templates={stats.templates} file={path}"
    )

    return 0 if invalid == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
