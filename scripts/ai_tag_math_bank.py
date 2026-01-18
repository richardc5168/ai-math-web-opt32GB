from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.openai_chat import chat_json
from ai.prompt_templates import build_tagging_prompt
from ai.schemas import TaggingResult


DEFAULT_KNOWLEDGE_POINTS = [
    "A1.分配律",
    "A2.十字交乘",
    "A3.完全平方",
    "A4.公式解",
    "F1.分數通分",
    "F2.分數加減",
    "F3.分數乘除",
]


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="AI automated tagging for math_bank JSON")
    ap.add_argument("--input", required=True, help="Input JSON file (list of items)")
    ap.add_argument("--output", required=True, help="Output JSON file")
    ap.add_argument(
        "--knowledge",
        default="",
        help="Optional JSON file containing a list of knowledge points",
    )
    ap.add_argument("--limit", type=int, default=0, help="Only tag first N items")
    ap.add_argument("--model", default="", help="Override OpenAI model")
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--dry-run", action="store_true", help="Print prompt only (no API call)")
    args = ap.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)

    items = _load_json(in_path)
    if not isinstance(items, list):
        raise SystemExit("Input JSON must be a list")

    if args.knowledge:
        kp = _load_json(Path(args.knowledge))
        if not isinstance(kp, list) or not all(isinstance(x, str) for x in kp):
            raise SystemExit("--knowledge must be a JSON list of strings")
        knowledge_points = kp
    else:
        knowledge_points = DEFAULT_KNOWLEDGE_POINTS

    limit = args.limit if args.limit and args.limit > 0 else len(items)

    tagged = []
    for idx, item in enumerate(items[:limit], start=1):
        q = str(item.get("question", "")).strip()
        if not q:
            tagged.append(item)
            continue

        prompt = build_tagging_prompt(knowledge_points=knowledge_points, question=q)
        if args.dry_run:
            print(prompt)
            return 0

        raw = chat_json(prompt=prompt, model=(args.model or None), temperature=args.temperature)
        result = TaggingResult.model_validate(raw)

        merged = dict(item)
        merged["tags"] = result.model_dump()
        tagged.append(merged)
        print(f"[{idx}/{limit}] tagged: {result.core_concept} (diff={result.difficulty})")

    # Keep non-tagged tail if limit was used
    if limit < len(items):
        tagged.extend(items[limit:])

    out_path.write_text(json.dumps(tagged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
