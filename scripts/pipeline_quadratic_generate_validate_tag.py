from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import re

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.openai_chat import chat_json
from ai.prompt_templates import build_misconception_mcq_prompt, build_tagging_prompt
from ai.schemas import GeneratedMCQSet, TaggingResult


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_list(vals: list[str]) -> list[str]:
    return sorted([str(v).strip() for v in vals if str(v).strip()])


def _difficulty_limits(difficulty: int, *, roots_mode: str) -> dict[str, int]:
    """Coefficient magnitude limits.

    Notes:
    - For rational/mixed roots, integer-coefficient quadratics often require a larger |a|
      (e.g., roots with denominators 2 commonly lead to a multiple of 4).
    - We keep |b|,|c| bounded to preserve "textbook" feel.
    """

    base = {
        1: {"a": 1, "b": 10, "c": 25},
        2: {"a": 2, "b": 20, "c": 50},
        3: {"a": 3, "b": 30, "c": 80},
        4: {"a": 4, "b": 50, "c": 120},
        5: {"a": 6, "b": 80, "c": 200},
    }
    lim = dict(base[int(difficulty)])

    if roots_mode in ("rational", "mixed"):
        # Allow larger a to support denominators while staying hand-calculable.
        lim["a"] = max(lim["a"], 8 if difficulty <= 3 else 12)
    return lim


@dataclass
class VerifyReport:
    ok: bool
    reason: str
    solutions: list[str]


def verify_mcq_item(item: dict[str, Any], *, roots_mode: str, difficulty: int) -> VerifyReport:
    try:
        import sympy as sp
    except Exception as e:
        return VerifyReport(False, f"sympy not installed: {e}", [])

    ver = item.get("verification") or {}
    symbol = str(ver.get("symbol") or "x")
    expr_str = str(ver.get("expr") or "").strip()
    expected = _normalize_list(ver.get("solution_set") or [])

    if not expr_str:
        return VerifyReport(False, "missing verification.expr", [])

    x = sp.symbols(symbol)
    try:
        expr = sp.sympify(expr_str)
    except Exception as e:
        return VerifyReport(False, f"sympify failed: {e}", [])

    # Enforce quadratic integer-coefficient polynomial and size limits.
    try:
        poly = sp.Poly(expr, x)
    except Exception:
        return VerifyReport(False, "verification.expr is not a polynomial in symbol", [])
    if poly.degree() != 2:
        return VerifyReport(False, f"expected quadratic degree=2 got={poly.degree()}", [])
    coeffs = poly.all_coeffs()  # [a,b,c]
    if len(coeffs) != 3:
        return VerifyReport(False, "unexpected polynomial coeff shape", [])
    a, b, c = coeffs
    if not all(getattr(v, "is_integer", False) is True for v in (a, b, c)):
        return VerifyReport(False, "coefficients must be integers", [])
    a_i, b_i, c_i = int(a), int(b), int(c)
    lim = _difficulty_limits(int(difficulty), roots_mode=roots_mode)
    if abs(a_i) > lim["a"] or abs(b_i) > lim["b"] or abs(c_i) > lim["c"]:
        return VerifyReport(
            False,
            f"coeff out of range for difficulty={difficulty}: (a,b,c)=({a_i},{b_i},{c_i}) limits={lim}",
            [],
        )

    try:
        sols = sp.solve(expr, x)
    except Exception as e:
        return VerifyReport(False, f"solve failed: {e}", [])

    # Keep real solutions only; stringify for stable output.
    real_sols = []
    for s in sols:
        try:
            if s.is_real is False:
                continue
        except Exception:
            pass
        real_sols.append(s)

    sol_strs = _normalize_list([str(s) for s in real_sols])

    # Enforce root type mode.
    def _is_int_root(v) -> bool:
        try:
            return bool(sp.Integer(v) == v)
        except Exception:
            return False

    def _is_rational_root(v) -> bool:
        try:
            return getattr(v, "is_rational", False) is True
        except Exception:
            return False

    if roots_mode not in ("integer", "rational", "mixed"):
        return VerifyReport(False, f"invalid roots_mode={roots_mode}", sol_strs)

    if not real_sols:
        return VerifyReport(False, "no real solutions", [])

    all_rational = all(_is_rational_root(s) for s in real_sols)
    any_int = any(_is_int_root(s) for s in real_sols)
    any_non_int = any(_is_rational_root(s) and (not _is_int_root(s)) for s in real_sols)

    if roots_mode == "integer" and not (all_rational and all(_is_int_root(s) for s in real_sols)):
        return VerifyReport(False, "roots are not all integers", sol_strs)
    if roots_mode == "rational" and not (all_rational and any_non_int):
        return VerifyReport(False, "roots must be rational and include a non-integer", sol_strs)
    if roots_mode == "mixed" and not (all_rational and any_int and any_non_int):
        return VerifyReport(False, "roots must be rational with at least one integer and one non-integer", sol_strs)

    # If expected provided, enforce it.
    if expected and expected != sol_strs:
        return VerifyReport(False, f"solution_set mismatch expected={expected} got={sol_strs}", sol_strs)

    correct_key = item.get("correct")
    options = item.get("options") or []
    opt_map = {o.get("key"): o for o in options if isinstance(o, dict)}

    if correct_key not in opt_map:
        return VerifyReport(False, "correct key not found in options", sol_strs)

    correct_vals = _normalize_list((opt_map[correct_key].get("values") or []))
    if correct_vals != sol_strs:
        return VerifyReport(False, f"correct option values mismatch got={correct_vals} sols={sol_strs}", sol_strs)

    # Ensure wrong options aren't accidentally correct.
    for k, opt in opt_map.items():
        if k == correct_key:
            continue
        v = _normalize_list((opt.get("values") or []))
        if v == sol_strs:
            return VerifyReport(False, f"wrong option {k} equals true solution set", sol_strs)

    # Enforce textbook-style hint structure and prevent leaking answers.
    # Prefer 4 layers: 整理→因式分解→零乘積→公式驗算; allow legacy 3 layers for backward compatibility.
    hints = item.get("hints") or {}
    if not isinstance(hints, dict):
        return VerifyReport(False, "missing hints", sol_strs)

    has_level4 = bool(str(hints.get("level4") or "").strip())
    required = ("level1", "level2", "level3", "level4") if has_level4 else ("level1", "level2", "level3")
    if not all(k in hints for k in required):
        return VerifyReport(False, f"missing hints.{ '/'.join(required) }", sol_strs)

    h1 = str(hints.get("level1") or "")
    h2 = str(hints.get("level2") or "")
    h3 = str(hints.get("level3") or "")
    h4 = str(hints.get("level4") or "")
    joined = (h1 + "\n" + h2 + "\n" + h3 + ("\n" + h4 if has_level4 else "")).lower()

    # Must include the intended teaching steps.
    if ("ax^2" not in joined) or ("bx" not in joined) or ("c=0" not in joined.replace(" ", "")):
        return VerifyReport(False, "hints must mention整理成 ax^2+bx+c=0", sol_strs)

    if has_level4:
        if "因式" not in h2:
            return VerifyReport(False, "level2 must mention因式分解", sol_strs)
        if "零乘積" not in h3:
            return VerifyReport(False, "level3 must mention零乘積性質", sol_strs)
        if ("Δ" not in h4) and ("delta" not in h4.lower()):
            return VerifyReport(False, "level4 should mention判別式Δ", sol_strs)
        if "2a" not in h4.lower().replace(" ", ""):
            return VerifyReport(False, "level4 should mention/(2a)", sol_strs)
    else:
        # Legacy: allow combining steps across level2/level3.
        if "因式" not in (h2 + h3):
            return VerifyReport(False, "hints must mention因式分解", sol_strs)
        if "零乘積" not in (h2 + h3):
            return VerifyReport(False, "hints must mention零乘積性質", sol_strs)
        if ("Δ" not in h3) and ("delta" not in h3.lower()):
            return VerifyReport(False, "level3 should mention判別式Δ", sol_strs)
        if "2a" not in h3.lower().replace(" ", ""):
            return VerifyReport(False, "level3 should mention/(2a)", sol_strs)

    # Hard forbid: writing explicit numeric answers (but allow the general formula x=[...]/(2a)).
    if re.search(r"\bx\s*=\s*[-+]?\d", joined):
        return VerifyReport(False, "hints must not contain explicit numeric x=...", sol_strs)

    # Avoid false positives from formula text (e.g., b^2, 2a).
    # Only treat a solution as leaked if hints explicitly *state* it (e.g., "解是 2", "答案：1/2").
    hint_texts = [h1, h2, h3] + ([h4] if has_level4 else [])
    for s in sol_strs:
        if not s:
            continue
        pat1 = re.compile(r"(解|根|答案).{0,10}(為|是|=|：|:)\s*" + re.escape(s))
        pat2 = re.compile(re.escape(s) + r"\s*(為|是|=|：|:).{0,6}(解|根|答案)")
        if any(pat1.search(t) for t in hint_texts) or any(pat2.search(t) for t in hint_texts):
            return VerifyReport(False, "hints must not leak solution values", sol_strs)

    return VerifyReport(True, "ok", sol_strs)


def offline_stub_set(concept: str) -> dict[str, Any]:
    # Reuse the generator script stub by importing its local function would be messy;
    # keep one deterministic stub here.
    return {
        "items": [
            {
                "concept_tag": concept,
                "stem": "解方程式：x^2 - 5x + 6 = 0。下列哪一組是正確解？",
                "verification": {"symbol": "x", "expr": "x**2 - 5*x + 6", "solution_set": ["2", "3"]},
                "options": [
                    {"key": "A", "text": "x = 2 或 x = 6", "values": ["2", "6"], "misconception_tag": "常數項誤算"},
                    {"key": "B", "text": "x = -2 或 x = -3", "values": ["-2", "-3"], "misconception_tag": "符號帶錯"},
                    {"key": "C", "text": "x = 2 或 x = -3", "values": ["2", "-3"], "misconception_tag": "只找到一個根"},
                    {"key": "D", "text": "x = 2 或 x = 3", "values": ["2", "3"], "misconception_tag": None},
                ],
                "correct": "D",
                "solution": "(x-2)(x-3)=0，所以 x=2 或 x=3。",
                "diagnostics": {
                    "A": "常數項處理錯/乘積看錯",
                    "B": "符號概念混淆",
                    "C": "只取到一個根或另一根符號錯",
                    "D": "可正確因式分解並解方程",
                },
                "hints": {
                    "level1": "先把方程式整理成 ax^2+bx+c=0（移項、合併同類項）。",
                    "level2": "嘗試因式分解成 (px+q)(rx+s)=0（先找兩數相乘 6、相加 -5）。",
                    "level3": "利用零乘積性質：令 px+q=0 或 rx+s=0，得到兩個一次方程。",
                    "level4": "用公式解驗算：Δ=b^2-4ac，x=[-b±sqrt(Δ)]/(2a)（只用來檢核，不要直接寫出最後根）。",
                },
            }
        ]
    }


def offline_stub_set_controlled(*, concept: str, roots_mode: str, difficulty: int) -> dict[str, Any]:
    # Deterministic stubs that satisfy roots constraints and stay within difficulty limits.
    # NOTE: For offline we keep stems simple; online mode is where we get richer narratives.
    if roots_mode == "integer":
        # x^2 - 5x + 6 = 0, roots 2 and 3
        expr = "x**2 - 5*x + 6"
        sol = ["2", "3"]
        optA, optB, optC = (["2", "6"], ["-2", "-3"], ["2", "-3"])
    elif roots_mode == "rational":
        # (2x-1)(2x+3)=0 => 4x^2+4x-3=0, roots 1/2 and -3/2
        expr = "4*x**2 + 4*x - 3"
        sol = ["1/2", "-3/2"]
        optA, optB, optC = (["1/2", "3/2"], ["-1/2", "-3/2"], ["1/2", "-3"])
    else:  # mixed
        # (x-2)(3x-1)=0 => 3x^2-7x+2=0, roots 2 and 1/3
        expr = "3*x**2 - 7*x + 2"
        sol = ["2", "1/3"]
        optA, optB, optC = (["2", "3"], ["-2", "1/3"], ["2", "-1/3"])

    return {
        "items": [
            {
                "concept_tag": concept,
                "stem": "解一元二次方程式，並選出正確的解集合。",
                "verification": {"symbol": "x", "expr": expr, "solution_set": sol},
                "options": [
                    {"key": "A", "text": "A 選項", "values": optA, "misconception_tag": "因式配對錯"},
                    {"key": "B", "text": "B 選項", "values": optB, "misconception_tag": "符號/移項錯"},
                    {"key": "C", "text": "C 選項", "values": optC, "misconception_tag": "只取到一個根"},
                    {"key": "D", "text": "D 選項", "values": sol, "misconception_tag": None},
                ],
                "correct": "D",
                "solution": "先因式分解求根，再用公式解驗算。",
                "diagnostics": {
                    "A": "因式分解配對/乘積檢核錯",
                    "B": "符號/移項概念混淆",
                    "C": "零乘積性質或漏根",
                    "D": "解題流程正確",
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
    ap = argparse.ArgumentParser(description="Quadratic pipeline: generate -> sympy validate -> tag")
    ap.add_argument("--count", type=int, default=10, help="How many validated items to output")
    ap.add_argument("--concept", default="一元二次方程式-公式解", help="Concept tag")
    ap.add_argument(
        "--roots",
        default="integer",
        choices=["integer", "rational", "mixed"],
        help="Control root types for generated questions",
    )
    ap.add_argument(
        "--difficulty",
        type=int,
        default=3,
        choices=[1, 2, 3, 4, 5],
        help="Control coefficient size/steps (1-5)",
    )
    ap.add_argument(
        "--style",
        default="factoring_then_formula",
        choices=["standard", "factoring_then_formula"],
        help="Generation style for the MCQ",
    )
    ap.add_argument("--knowledge", default=str(ROOT / "knowledge_points_quadratic.json"))
    ap.add_argument("--output", default=str(ROOT / "data" / "quadratic.validated.jsonl"))
    ap.add_argument("--model", default="", help="Override OpenAI model")
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--max-attempts", type=int, default=50, help="Max LLM generations to try")
    ap.add_argument("--offline", action="store_true", help="Force offline mode (no API calls)")
    ap.add_argument("--debug", action="store_true", help="Print why attempts were rejected")
    args = ap.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    knowledge_points = _load_json(Path(args.knowledge))
    if not isinstance(knowledge_points, list):
        raise SystemExit("knowledge points file must be a JSON list")

    concept = str(args.concept).strip()

    written = 0
    attempts = 0

    with out_path.open("w", encoding="utf-8") as f:
        while written < args.count and attempts < args.max_attempts:
            attempts += 1

            if args.offline or not os.getenv("OPENAI_API_KEY", "").strip():
                raw = offline_stub_set_controlled(concept=concept, roots_mode=args.roots, difficulty=args.difficulty)
            else:
                prompt = build_misconception_mcq_prompt(
                    concept=concept,
                    style=args.style,
                    roots=args.roots,
                    difficulty=args.difficulty,
                )
                raw = chat_json(
                    prompt=prompt,
                    model=(args.model or None),
                    temperature=args.temperature,
                )

            mcq_set = GeneratedMCQSet.model_validate(raw)
            if not mcq_set.items:
                continue

            item = mcq_set.items[0].model_dump()
            rep = verify_mcq_item(item, roots_mode=args.roots, difficulty=args.difficulty)
            if not rep.ok:
                if args.debug:
                    print(f"[skip] attempt {attempts}: {rep.reason}")
                continue

            # Tagging step (AI). If no key, fallback to deterministic tags.
            if os.getenv("OPENAI_API_KEY", "").strip() and not args.offline:
                tag_prompt = build_tagging_prompt(knowledge_points=knowledge_points, question=item["stem"])
                tag_raw = chat_json(
                    prompt=tag_prompt,
                    model=(args.model or None),
                    temperature=0.2,
                )
                tags = TaggingResult.model_validate(tag_raw).model_dump()
            else:
                tags = {
                    "core_concept": "Q4.公式解",
                    "prerequisites": ["ALG1.代數式運算", "ALG2.移項與等式性質"],
                    "difficulty": 3,
                    "estimated_time_sec": 120,
                    "rationale": "offline default",
                }

            record = {
                "concept": concept,
                "tags": tags,
                "mcq": item,
                "verification": {"ok": True, "solutions": rep.solutions},
            }

            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1
            print(f"[{written}/{args.count}] ok (attempt {attempts}) expr={item['verification']['expr']}")

    print(f"Wrote: {out_path}")
    return 0 if written == args.count else 2


if __name__ == "__main__":
    raise SystemExit(main())
