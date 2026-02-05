"""Generate an offline bank for the 'Interactive G5 Empire' module.

Output:
  docs/interactive-g5-empire/bank.js
  window.INTERACTIVE_G5_EMPIRE_BANK = [...]

This bank is intentionally self-contained and uses simple, school-grade-5 friendly contexts.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "docs" / "interactive-g5-empire" / "bank.js"
DEFAULT_SEED = 20260204


def _rng(seed: int = DEFAULT_SEED) -> random.Random:
    # Stable default seed; overridden by CLI for stability checks.
    return random.Random(int(seed))


def _to_str(x: float) -> str:
    # Avoid scientific notation and trailing zeros.
    s = f"{x:.10f}".rstrip("0").rstrip(".")
    return s if s else "0"


def _int_places_to_str_fixed(n: int, places: int) -> str:
        """Convert integer `n` into a fixed-decimal string with exactly `places` digits.

        Examples:
            n=123, places=1 -> '12.3'
            n=5, places=2 -> '0.05'
            n=120, places=2 -> '1.20'
        """

        sign = "-" if n < 0 else ""
        a = abs(int(n))
        p = int(places)
        if p <= 0:
                return f"{sign}{a}"
        s = str(a).rjust(p + 1, "0")
        return f"{sign}{s[:-p]}.{s[-p:]}"


def _gcd(a: int, b: int) -> int:
    return math.gcd(a, b)


def _simplify_fraction(n: int, d: int) -> Tuple[int, int]:
    if d == 0:
        raise ValueError("denominator=0")
    if d < 0:
        n, d = -n, -d
    g = _gcd(abs(n), abs(d))
    return n // g, d // g


def _frac_to_str(n: int, d: int) -> str:
    n, d = _simplify_fraction(n, d)
    return f"{n}/{d}"


def _hhmm(minutes: int) -> str:
    minutes %= 24 * 60
    hh = minutes // 60
    mm = minutes % 60
    return f"{hh:02d}:{mm:02d}"


def _pick(r: random.Random, items: List[str]) -> str:
    return items[r.randrange(len(items))]


def _unit_context_mul(unit: str) -> str:
    if unit == "公尺":
        return "每段繩子長"
    if unit == "公斤":
        return "每袋米重"
    if unit == "元":
        return "每張票"
    if unit == "公升":
        return "每瓶果汁有"
    return "每份"


def _unit_context_div(unit: str) -> str:
    if unit == "公尺":
        return "把繩子平均剪成"
    if unit == "公斤":
        return "把米平均分成"
    if unit == "元":
        return "把錢平均分成"
    if unit == "公升":
        return "把果汁平均分成"
    return "平均分成"


@dataclass
class Q:
    id: str
    kind: str
    topic: str
    difficulty: str
    question: str
    answer: str
    answer_mode: str
    hints: List[str]
    steps: List[str]
    explanation: str
    meta: Dict


def q_decimal_mul(r: random.Random, idx: int) -> Q:
    # a (1-2 decimals) * int, generated exactly with integers to avoid float rounding
    a_places = 1 if r.random() < 0.6 else 2
    a_int = r.randint(12, 399)
    b = r.randint(2, 9)
    raw = a_int * b
    a_s = _int_places_to_str_fixed(a_int, a_places)
    ans_s = _int_places_to_str_fixed(raw, a_places)
    unit = _pick(r, ["公尺", "公斤", "元", "公升"])
    ctx = _unit_context_mul(unit)
    if unit == "元":
        q = f"（帝國｜小數乘法）{ctx} {a_s} 元，買 {b} 張，一共多少元？（可寫小數）"
    else:
        q = f"（帝國｜小數乘法）{ctx} {a_s} {unit}，有 {b} 份，一共多少 {unit}？（可寫小數）"

    return Q(
        id=f"g5e_decimal_mul_{idx:03d}",
        kind="decimal_mul",
        topic="五年級｜帝國互動闖關",
        difficulty="easy" if a_places == 1 else "medium",
        question=q,
        answer=ans_s,
        answer_mode="number",
        hints=[
            "觀念：小數×整數 → 先把小數當整數算，最後再把小數點放回。",
            f"列式：{a_s}×{b}。數小數位：{a_s} 有 {a_places} 位小數，所以答案也要有 {a_places} 位小數。",
            "Level 3｜互動：到「小數點放回工坊」→ Step 1 填整數乘法結果 → Step 2 把小數點放回（放回指定位數）。",
        ],
        steps=[
            "列式：小數 × 整數",
            "把小數點暫時拿掉，先做整數乘法",
            "依小數位數把小數點放回去",
            "估算檢查：乘數>1 時答案應變大",
        ],
        explanation=f"{a_s}×{b}={ans_s}。",
        meta={
            "a": a_s,
            "b": str(b),
            "a_int": a_int,
            "b_int": b,
            "a_places": a_places,
            "raw_int_product": raw,
            "total_places": a_places,
            "unit": unit,
        },
    )


def q_decimal_div(r: random.Random, idx: int) -> Q:
    # decimal / int, guaranteed terminating with <=2 decimal places
    b = r.randint(2, 9)
    a_places = 0 if r.random() < 0.25 else (1 if r.random() < 0.7 else 2)
    # Work in integers: let a_int = b * k, where a = a_int / 10^a_places, ans = k / 10^a_places
    k_min = max(1, math.ceil(10 / b))
    k_max = max(k_min, 600 // b)
    k = r.randint(k_min, k_max)
    a_int = b * k
    a_s = _int_places_to_str_fixed(a_int, a_places)
    ans_s = _int_places_to_str_fixed(k, a_places)
    unit = _pick(r, ["公尺", "公斤", "元", "公升"])
    ctx = _unit_context_div(unit)
    if unit == "公尺":
        q = f"（帝國｜小數除法）有一條 {a_s} 公尺的繩子，{ctx} {b} 段，每段長多少公尺？（可寫小數）"
    elif unit == "公斤":
        q = f"（帝國｜小數除法）有 {a_s} 公斤的米，{ctx} {b} 袋，每袋重多少公斤？（可寫小數）"
    elif unit == "元":
        q = f"（帝國｜小數除法）有 {a_s} 元，{ctx} {b} 份，每份多少元？（可寫小數）"
    else:
        q = f"（帝國｜小數除法）有 {a_s} 公升的果汁，{ctx} {b} 杯，每杯多少公升？（可寫小數）"

    return Q(
        id=f"g5e_decimal_div_{idx:03d}",
        kind="decimal_div",
        topic="五年級｜帝國互動闖關",
        difficulty="easy" if a_places <= 1 else "medium",
        question=q,
        answer=ans_s,
        answer_mode="number",
        hints=[
            "觀念：平均分配 → 用除法。",
            f"列式：{a_s}÷{b}。做直式時：不夠除就補 0；商的小數點要和被除數的小數點對齊。",
            "Level 3｜互動：到「小數除法對齊工坊」→ Step 1 先把被除數右移變整數 a_int → Step 2 算整數商 ans_int → Step 3 放回小數點得到答案。",
        ],
        steps=[
            "列式：小數 ÷ 整數",
            "做直式除法（不夠除就補 0）",
            "商的小數點對齊被除數的小數點",
            "用乘回去檢查：商×除數=被除數",
        ],
        explanation=f"{a_s}÷{b}={ans_s}。",
        meta={
            "a": a_s,
            "b": str(b),
            "a_int": a_int,
            "a_places": a_places,
            "ans_int": k,
            "ans_places": a_places,
            "unit": unit,
        },
    )


def q_fraction_addsub(r: random.Random, idx: int) -> Q:
    # n1/d + n2/d or with lcm
    d1 = _pick(r, [4, 5, 6, 8, 10, 12])
    d2 = _pick(r, [4, 5, 6, 8, 10, 12])
    n1 = r.randint(1, d1 - 1)
    n2 = r.randint(1, d2 - 1)
    op = "+" if r.random() < 0.6 else "-"

    a_n, a_d = n1, d1
    b_n, b_d = n2, d2
    l = a_d * b_d // _gcd(a_d, b_d)
    a2 = a_n * (l // a_d)
    b2 = b_n * (l // b_d)
    res_n = a2 + b2 if op == "+" else a2 - b2
    # keep result positive
    if res_n <= 0:
        op = "+"
        res_n = a2 + b2

    ans = _frac_to_str(res_n, l)
    q = f"（帝國｜分數加減）{a_n}/{a_d} {op} {b_n}/{b_d} = ？（答案寫最簡分數）"

    return Q(
        id=f"g5e_fraction_addsub_{idx:03d}",
        kind="fraction_addsub",
        topic="五年級｜帝國互動闖關",
        difficulty="easy" if a_d == b_d else "medium",
        question=q,
        answer=ans,
        answer_mode="fraction",
        hints=[
            "觀念：分數加減要先通分（變成同分母），才能相加相減。",
            f"做法：先找公分母（常用最小公倍數）。{a_d} 和 {b_d} 通分後，分子也要乘同樣的倍數。",
            "Level 3｜互動：到「通分工坊」→ 先填公分母 → 再填兩個新分子 → 分子相加減 → 最後約分到最簡分數。",
        ],
        steps=[
            "找公分母（通分）",
            "改寫成同分母的兩個分數",
            "分子相加/相減",
            "把結果約分到最簡",
        ],
        explanation=f"通分到 {l} 後計算，得到 {ans}。",
        meta={"a": f"{a_n}/{a_d}", "b": f"{b_n}/{b_d}", "lcm": l, "op": op},
    )


def q_fraction_mul(r: random.Random, idx: int) -> Q:
    d1 = _pick(r, [4, 5, 6, 8, 9, 10, 12])
    d2 = _pick(r, [4, 5, 6, 8, 9, 10, 12])
    n1 = r.randint(1, d1 - 1)
    n2 = r.randint(1, d2 - 1)
    res_n, res_d = _simplify_fraction(n1 * n2, d1 * d2)
    ans = f"{res_n}/{res_d}"
    q = f"（帝國｜分數乘法）{n1}/{d1} × {n2}/{d2} = ？（答案寫最簡分數）"

    return Q(
        id=f"g5e_fraction_mul_{idx:03d}",
        kind="fraction_mul",
        topic="五年級｜帝國互動闖關",
        difficulty="easy" if _gcd(n1, d2) > 1 or _gcd(n2, d1) > 1 else "medium",
        question=q,
        answer=ans,
        answer_mode="fraction",
        hints=[
            "觀念：分數乘法 → 分子×分子，分母×分母。",
            "技巧：先交叉約分（左分子和右分母、右分子和左分母），可以讓數字變小更好算。",
            "Level 3｜互動：到「交叉約分工坊」→ 先做約分 → 再相乘 → 最後確認答案是最簡分數。",
        ],
        steps=[
            "先交叉約分（能約就先約）",
            "分子相乘",
            "分母相乘",
            "再約分一次，寫成最簡分數",
        ],
        explanation=f"{n1}/{d1}×{n2}/{d2}={ans}。",
        meta={"a": f"{n1}/{d1}", "b": f"{n2}/{d2}"},
    )


def q_percent_of(r: random.Random, idx: int) -> Q:
    base = r.randint(20, 600)
    p = _pick(r, [10, 20, 25, 30, 40, 50, 60, 75])
    ans = base * p / 100
    q = f"（帝國｜百分率）{p}% 的 {base} 是多少？（可寫整數或小數）"

    return Q(
        id=f"g5e_percent_of_{idx:03d}",
        kind="percent_of",
        topic="五年級｜帝國互動闖關",
        difficulty="easy" if p in (10, 20, 25, 50, 75) else "medium",
        question=q,
        answer=_to_str(ans),
        answer_mode="number",
        hints=[
            "觀念：p% 表示「每 100 份拿 p 份」→ 等於 p/100。",
            f"列式：{base}×{p}/100。也可以用快算：10%=÷10，20%=÷5，25%=÷4，50%=÷2，75%=3/4。",
            "Level 3｜互動：到「百分率拼圖」→ 先拆成好算的百分率（例如 40%=20%+20%）→ 分別算出來再相加。",
        ],
        steps=[
            "把 p% 轉成分數 p/100",
            "用乘法求「部分」：全體×p/100",
            "用快算簡化（例如 25%=1/4、50%=1/2）",
            "合理檢查：p<100 時答案應小於全體",
        ],
        explanation=f"{p}%={p}/100，所以 {base}×{p}/100={_to_str(ans)}。",
        meta={"base": base, "p": p},
    )


def q_volume_rect_prism(r: random.Random, idx: int) -> Q:
    l = r.randint(2, 18)
    w = r.randint(2, 16)
    h = r.randint(2, 14)
    vol = l * w * h
    q = f"（帝國｜體積）長方體長 {l} cm、寬 {w} cm、高 {h} cm，體積是多少 cm³？"

    return Q(
        id=f"g5e_volume_{idx:03d}",
        kind="volume_rect_prism",
        topic="五年級｜帝國互動闖關",
        difficulty="easy" if l*w < 200 else "medium",
        question=q,
        answer=str(vol),
        answer_mode="number",
        hints=[
            "觀念：長方體體積 = 長×寬×高。",
            "做法：先算底面積（長×寬），再乘高（有幾層就乘幾次）。",
            "Level 3｜互動：到「積木層層數」→ Step 1 先算一層有多少顆（底面積）→ Step 2 乘上層數（高）得到體積。",
        ],
        steps=[
            "算底面積：長×寬",
            "底面積×高（層數）",
            "答案要寫單位：cm³",
            "合理檢查：長/寬/高越大，體積越大",
        ],
        explanation=f"{l}×{w}×{h}={vol}（cm³）。",
        meta={"l": l, "w": w, "h": h, "unit": "cm³"},
    )


def q_time_add(r: random.Random, idx: int) -> Q:
    start_h = r.randint(6, 20)
    start_m = _pick(r, [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55])
    add_m = r.randint(10, 140)
    start = start_h * 60 + start_m
    end = start + add_m
    q = f"（帝國｜時間加法）從 {_hhmm(start)} 開始，過了 {add_m} 分鐘，時間是幾點幾分？（用 HH:MM）"

    return Q(
        id=f"g5e_time_add_{idx:03d}",
        kind="time_add",
        topic="五年級｜帝國互動闖關",
        difficulty="easy" if add_m < 60 else "medium",
        question=q,
        answer=_hhmm(end),
        answer_mode="hhmm",
        hints=[
            "觀念：時間加法先加分鐘；每滿 60 分鐘就進位 1 小時。",
            "做法：先算總分鐘 = 起始分鐘 + 加的分鐘；再把『整包 60』進位到小時，剩下的是分鐘。",
            "Level 3｜互動：到「時間進位工具」→ Step 1 填總分鐘 → Step 2 填進位後的小時 → Step 3 填剩下分鐘，組成 HH:MM。",
        ],
        steps=[
            "把起始時間寫成 小時:分鐘",
            "先加分鐘，滿 60 就進位到小時",
            "再把小時加上進位",
            "格式寫成 HH:MM（分鐘要兩位）",
        ],
        explanation=f"{_hhmm(start)} + {add_m} 分 = {_hhmm(end)}。",
        meta={"start": _hhmm(start), "add_m": add_m, "end": _hhmm(end)},
    )


def q_unit_convert(r: random.Random, idx: int) -> Q:
    kind = _pick(r, ["m_cm", "kg_g", "l_ml"])
    if kind == "m_cm":
        m = r.randint(1, 25)
        cm = r.randint(0, 99)
        total_cm = m * 100 + cm
        q = f"（帝國｜單位換算）{m} 公尺 {cm} 公分 = 多少公分？"
        ans = str(total_cm)
        meta = {"m": m, "cm": cm}
    elif kind == "kg_g":
        kg = r.randint(1, 20)
        g = r.randint(0, 999)
        total_g = kg * 1000 + g
        q = f"（帝國｜單位換算）{kg} 公斤 {g} 公克 = 多少公克？"
        ans = str(total_g)
        meta = {"kg": kg, "g": g}
    else:
        l = r.randint(1, 15)
        ml = r.randint(0, 999)
        total_ml = l * 1000 + ml
        q = f"（帝國｜單位換算）{l} 公升 {ml} 毫升 = 多少毫升？"
        ans = str(total_ml)
        meta = {"l": l, "ml": ml}

    return Q(
        id=f"g5e_unit_convert_{idx:03d}",
        kind="unit_convert",
        topic="五年級｜帝國互動闖關",
        difficulty="easy",
        question=q,
        answer=ans,
        answer_mode="number",
        hints=[
            "觀念：同一種量換單位，就是用乘法把『整包』換成小單位。",
            "關係：1 公尺=100 公分；1 公斤=1000 公克；1 公升=1000 毫升。",
            "Level 3｜互動：到「滑桿換算」→ 先算整包（例如 公尺×100）→ 再加上剩下的部分，得到總數。",
        ],
        steps=[
            "寫出換算關係",
            "先算整包（例如 ×100 或 ×1000）",
            "再加上剩下的部分",
            "檢查單位是否正確",
        ],
        explanation=f"依換算關係計算，答案是 {ans}。",
        meta=meta | {"convert_kind": kind},
    )


GENERATORS: List[Tuple[str, Callable[[random.Random, int], Q]]] = [
    ("decimal_mul", q_decimal_mul),
    ("decimal_div", q_decimal_div),
    ("fraction_addsub", q_fraction_addsub),
    ("fraction_mul", q_fraction_mul),
    ("percent_of", q_percent_of),
    ("volume_rect_prism", q_volume_rect_prism),
    ("time_add", q_time_add),
    ("unit_convert", q_unit_convert),
]


def build_bank(target_total: int = 320, seed: int = DEFAULT_SEED) -> List[Dict]:
    r = _rng(seed)

    per_kind = target_total // len(GENERATORS)
    quotas: Dict[str, int] = {k: per_kind for k, _ in GENERATORS}
    # distribute remainder
    rem = target_total - per_kind * len(GENERATORS)
    for i in range(rem):
        quotas[GENERATORS[i][0]] += 1

    bank: List[Dict] = []
    seen = set()
    counters: Dict[str, int] = {k: 0 for k, _ in GENERATORS}

    for kind, gen in GENERATORS:
        want = quotas[kind]
        tries = 0
        while counters[kind] < want:
            tries += 1
            if tries > want * 200:
                raise RuntimeError(f"quota fill failed for {kind}: got {counters[kind]}/{want}")

            q = gen(r, counters[kind] + 1)
            key = (q.kind, q.question, q.answer)
            if key in seen:
                continue
            seen.add(key)

            bank.append(
                {
                    "id": q.id,
                    "kind": q.kind,
                    "topic": q.topic,
                    "difficulty": q.difficulty,
                    "question": q.question,
                    "answer": q.answer,
                    "answer_mode": q.answer_mode,
                    "hints": q.hints,
                    "steps": q.steps,
                    "meta": q.meta,
                    "explanation": q.explanation,
                }
            )
            counters[kind] += 1

    r.shuffle(bank)
    return bank


def write_bank_js(out_path: Path, bank: List[Dict]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(bank, ensure_ascii=False, indent=2)
    out_path.write_text(
        "/* Auto-generated offline question bank. */\n"
        "window.INTERACTIVE_G5_EMPIRE_BANK = "
        + payload
        + ";\n",
        encoding="utf-8",
    )


def main(argv: List[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Generate interactive-g5-empire offline bank.js")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED, help="RNG seed (default: stable)")
    p.add_argument("--total", type=int, default=320, help="Total questions (default: 320)")
    p.add_argument("--out", type=str, default=str(OUT_PATH), help="Output path to bank.js")
    args = p.parse_args(argv)

    out_path = Path(args.out)
    bank = build_bank(target_total=int(args.total), seed=int(args.seed))
    write_bank_js(out_path, bank)

    kinds = sorted({q["kind"] for q in bank})
    print(f"Wrote {out_path} (n={len(bank)} kinds={len(kinds)}: {', '.join(kinds)}) seed={int(args.seed)}")


if __name__ == "__main__":
    main()
