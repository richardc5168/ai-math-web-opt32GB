from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.openai_chat import chat_json
from ai.prompt_templates import build_misconception_mcq_prompt
from ai.schemas import GeneratedMCQSet


def _offline_stub(concept: str, *, roots_mode: str) -> dict:
    if roots_mode == "integer":
        expr = "x**2 - 5*x + 6"
        sol = ["2", "3"]
        wrongs = [
            ("A", "x = 2 或 x = 6", ["2", "6"], "因式配對錯"),
            ("B", "x = -2 或 x = -3", ["-2", "-3"], "符號帶錯"),
            ("C", "x = 2 或 x = -3", ["2", "-3"], "漏根/零乘積性質混淆"),
        ]
    elif roots_mode == "rational":
        # roots: 1/2 and -3/2
        expr = "4*x**2 + 4*x - 3"
        sol = ["1/2", "-3/2"]
        wrongs = [
            ("A", "x = 1/2 或 x = 3/2", ["1/2", "3/2"], "正負號帶錯"),
            ("B", "x = -1/2 或 x = -3/2", ["-1/2", "-3/2"], "移項/符號錯"),
            ("C", "x = 1/2 或 x = -3", ["1/2", "-3"], "只解出一個因式"),
        ]
    else:  # mixed
        # roots: 2 and 1/3
        expr = "3*x**2 - 7*x + 2"
        sol = ["2", "1/3"]
        wrongs = [
            ("A", "x = 2 或 x = 3", ["2", "3"], "把 1/3 看成 3"),
            ("B", "x = -2 或 x = 1/3", ["-2", "1/3"], "符號帶錯"),
            ("C", "x = 2 或 x = -1/3", ["2", "-1/3"], "根的正負號錯"),
        ]

    options = [
        {"key": k, "text": t, "values": v, "misconception_tag": tag}
        for (k, t, v, tag) in wrongs
    ] + [{"key": "D", "text": f"x = {sol[0]} 或 x = {sol[1]}", "values": sol, "misconception_tag": None}]

    return {
        "items": [
            {
                "concept_tag": concept,
                "stem": "解一元二次方程式，選出正確的解集合。",
                "verification": {"symbol": "x", "expr": expr, "solution_set": sol},
                "options": options,
                "correct": "D",
                "solution": "先因式分解求根，再用公式解驗算。",
                "diagnostics": {
                    "A": "常見計算/概念錯誤（依選項而定）",
                    "B": "常見計算/概念錯誤（依選項而定）",
                    "C": "常見計算/概念錯誤（依選項而定）",
                    "D": "流程正確：整理→因分→零乘積→公式解驗算",
                },
                "hints": {
                    "level1": "先把方程式整理成 ax^2+bx+c=0（移項、合併同類項）。",
                    "level2": "嘗試因式分解成 (px+q)(rx+s)=0（必要時可先提出公因數）。",
                    "level3": "利用零乘積性質：令 px+q=0 或 rx+s=0，得到兩個一次方程。",
                    "level4": "用公式解驗算：Δ=b^2-4ac，x=[-b±sqrt(Δ)]/(2a)（只用來檢核，不要直接在這步寫出最後根）。",
                },
            }
        ]
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate misconception-aware MCQ via LLM")
    ap.add_argument("--concept", required=True, help="Concept tag, e.g. 一元二次方程式-公式解")
    ap.add_argument("--output", required=True, help="Output JSON file")
    ap.add_argument("--model", default="", help="Override OpenAI model")
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument(
        "--style",
        default="factoring_then_formula",
        choices=["standard", "factoring_then_formula"],
        help="Generation style",
    )
    ap.add_argument(
        "--roots",
        default="integer",
        choices=["integer", "rational", "mixed"],
        help="Control root types",
    )
    ap.add_argument(
        "--difficulty",
        type=int,
        default=3,
        choices=[1, 2, 3, 4, 5],
        help="Control coefficient size/steps (1-5)",
    )
    ap.add_argument("--offline", action="store_true", help="Force offline stub (no API call)")
    args = ap.parse_args()

    concept = args.concept.strip()
    out_path = Path(args.output)

    if args.offline:
        raw = _offline_stub(concept, roots_mode=args.roots)
    else:
        prompt = build_misconception_mcq_prompt(
            concept=concept,
            style=args.style,
            roots=args.roots,
            difficulty=args.difficulty,
        )
        try:
            raw = chat_json(prompt=prompt, model=(args.model or None), temperature=args.temperature)
        except RuntimeError:
            raw = _offline_stub(concept, roots_mode=args.roots)

    mcq_set = GeneratedMCQSet.model_validate(raw)
    out_path.write_text(json.dumps(mcq_set.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
