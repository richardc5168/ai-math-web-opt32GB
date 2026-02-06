"""Generate the offline bank for the 'Interactive G5 Life Pack 1 Plus Empire' module.

Output:
    docs/interactive-g5-life-pack1plus-empire/bank.js
    dist_ai_math_web_pages/docs/interactive-g5-life-pack1plus-empire/bank.js

Exports:
    window.G5_LIFE_PACK1PLUS_BANK = [...]

Design goals:
- Exactly 10 units × 20 questions = 200 questions.
- Each question includes: hints (4), steps, explanation, common mistakes, tags, difficulty, core concepts.
- Stable generation (seeded RNG) for reproducible builds.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
DOCS_OUT = ROOT / "docs" / "interactive-g5-life-pack1plus-empire" / "bank.js"
DIST_OUT = ROOT / "dist_ai_math_web_pages" / "docs" / "interactive-g5-life-pack1plus-empire" / "bank.js"
DEFAULT_SEED = 20260209


UNITS: List[Tuple[str, str]] = [
    ("u1_avg_fraction", "Unit 1｜平均分配與分數意義"),
    ("u2_frac_addsub_life", "Unit 2｜分數加減（生活量）"),
    ("u3_frac_times_int", "Unit 3｜分數×整數（倍數）"),
    ("u4_money_decimal_addsub", "Unit 4｜小數與金錢（加減）"),
    ("u5_decimal_muldiv_price", "Unit 5｜小數乘除（單價/平均）"),
    ("u6_frac_dec_convert", "Unit 6｜分數↔小數（等值）"),
    ("u7_discount_percent", "Unit 7｜折扣與百分比（用小數比例）"),
    ("u8_ratio_recipe", "Unit 8｜比例與配方（份數法）"),
    ("u9_unit_convert_decimal", "Unit 9｜單位換算 + 小數"),
    ("u10_rate_time_distance", "Unit 10｜路程/時間/速率（每…）"),
]


def _rng(seed: int) -> random.Random:
    return random.Random(int(seed))


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


def _int_places_to_str_fixed(n: int, places: int) -> str:
    sign = "-" if n < 0 else ""
    a = abs(int(n))
    p = int(places)
    if p <= 0:
        return f"{sign}{a}"
    s = str(a).rjust(p + 1, "0")
    return f"{sign}{s[:-p]}.{s[-p:]}"


def _money2_from_cents(cents: int) -> str:
    # Return a string with up to 2 decimals (keep trailing zeros off to match UI parsing).
    s = _int_places_to_str_fixed(cents, 2)
    # Avoid scientific, keep as fixed but strip useless zeros.
    s2 = s.rstrip("0").rstrip(".")
    return s2 if s2 else "0"


def _pick(r: random.Random, items: List[str]) -> str:
    return items[r.randrange(len(items))]


def _difficulty_plan() -> List[str]:
    # 20 per unit (harder): 4 easy, 10 normal, 6 hard
    return ["easy"] * 4 + ["normal"] * 10 + ["hard"] * 6


# Extra (harder) questions for selected units to match the request "某幾單元加多題"
EXTRA_BY_UNIT: Dict[str, int] = {
    "u7_discount_percent": 10,
    "u8_ratio_recipe": 10,
    "u9_unit_convert_decimal": 10,
    "u10_rate_time_distance": 10,
}


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
    common_mistakes: List[str]
    tags: List[str]
    core: List[str]
    meta: Dict


def q_u1_avg_fraction(r: random.Random, qid: str, difficulty: str) -> Q:
    people = r.randint(2, 5) if difficulty == "easy" else r.randint(3, 8)
    total_num = 1
    total_den = 1

    # sometimes divide a whole, sometimes divide a fractional total
    if difficulty != "easy" and r.random() < 0.45:
        # total is a fraction like 3/2, 5/3...
        total_den = _pick(r, [2, 3, 4, 5])
        total_num = r.randint(total_den + 1, total_den * 2)

    n = total_num
    d = total_den * people
    ans = _frac_to_str(n, d)

    item = _pick(r, ["披薩", "蛋糕", "緞帶", "果汁", "巧克力"])
    total_s = "1" if (total_num, total_den) == (1, 1) else _frac_to_str(total_num, total_den)
    q = f"（生活應用｜平均分配）有 {total_s} 個{item}，平均分給 {people} 人，每人得到多少個？（用最簡分數 a/b 表示）"

    steps = [
        f"把『平均分給 {people} 人』寫成 ÷{people}",
        f"列式：{total_s} ÷ {people}",
        f"等於 {ans}（最簡分數）",
        "檢查：人數越多，每人分到應越少。",
    ]

    hints = [
        "觀念：平均分配就是『總量 ÷ 人數』。",
        "把除法改成乘法：除以 n 等於乘以 1/n。",
        f"列式：{total_s} × 1/{people}。先算分母：{total_den}×{people}。",
        "最後要記得把分數約分到最簡。",
    ]

    return Q(
        id=qid,
        kind="u1_avg_fraction",
        topic="小五生活應用題｜第一包｜加強版｜帝國",
        difficulty=difficulty,
        question=q,
        answer=ans,
        answer_mode="fraction",
        hints=hints,
        steps=steps,
        explanation=f"平均分配：{total_s} ÷ {people} = {ans}。",
        common_mistakes=[
            "把 ÷n 誤寫成 ×n（人越多反而變大）。",
            "忘記約分或分母算錯（沒有乘到人數）。",
        ],
        tags=["生活應用", "分數", "平均分配"],
        core=["分數意義", "平均分配=除法", "最簡分數"],
        meta={"people": people, "total": total_s},
    )


def q_u2_frac_addsub_life(r: random.Random, qid: str, difficulty: str) -> Q:
    den_choices = [2, 3, 4, 5, 6, 8, 10, 12]
    d1 = _pick(r, den_choices)
    d2 = d1 if (difficulty == "easy" or r.random() < 0.35) else _pick(r, den_choices)
    n1 = r.randint(1, d1 - 1)
    n2 = r.randint(1, d2 - 1)
    op = _pick(r, ["+", "-"]) if difficulty != "easy" else "+"

    # ensure non-negative result when subtraction
    if op == "-":
        # compare n1/d1 >= n2/d2
        if n1 * d2 < n2 * d1:
            n1, d1, n2, d2 = n2, d2, n1, d1

    # compute exact fraction
    l = abs(d1 * d2) // _gcd(d1, d2)
    a = n1 * (l // d1)
    b = n2 * (l // d2)
    res = a + b if op == "+" else a - b
    ans = _frac_to_str(res, l)

    thing = _pick(r, ["果汁", "水", "牛奶", "油", "湯"])
    unit = _pick(r, ["公升", "瓶", "杯"]) if difficulty != "hard" else _pick(r, ["公升", "升"])
    s1 = _frac_to_str(n1, d1)
    s2 = _frac_to_str(n2, d2)

    if op == "+":
        q = f"（生活應用｜分數加法）小明喝了 {s1} {unit}{thing}，又喝了 {s2} {unit}{thing}，一共喝了多少 {unit}{thing}？（最簡分數）"
        explain = f"通分後相加：{s1}+{s2}={ans}。"
        cm = ["只加分子不通分（分母不同時會錯）。", "通分後忘記約分。"]
    else:
        q = f"（生活應用｜分數減法）一瓶{thing}有 1 {unit}，小美先倒出 {s1} {unit}，又倒出 {s2} {unit}，剩下多少 {unit}？（最簡分數）"
        # remaining = 1 - (s1+s2)
        # But our ans is s1 - s2; not suitable. So craft subtraction context:
        q = f"（生活應用｜分數減法）原本有 {s1} {unit}{thing}，用掉 {s2} {unit}{thing}，還剩多少 {unit}{thing}？（最簡分數）"
        explain = f"通分後相減：{s1}-{s2}={ans}。"
        cm = ["把減法寫成加法（剩下反而變多）。", "通分時分母或分子乘錯。"]

    hints = [
        "觀念：分母不同要先通分，才能加/減分子。",
        f"先找最小公倍數：LCM({d1},{d2})。",
        f"把兩個分數都改成分母 {abs(d1*d2)//_gcd(d1,d2)}，再做 {op}。",
        "最後把答案約分成最簡。",
    ]

    steps = [
        "判斷分母是否相同，不同就通分。",
        "通分後做分子加/減。",
        "把結果約分成最簡分數。",
        "檢查：加法結果應比其中一個大；減法結果應變小且不為負。",
    ]

    return Q(
        id=qid,
        kind="u2_frac_addsub_life",
        topic="小五生活應用題｜第一包｜加強版｜帝國",
        difficulty=difficulty,
        question=q,
        answer=ans,
        answer_mode="fraction",
        hints=hints,
        steps=steps,
        explanation=explain,
        common_mistakes=cm,
        tags=["生活應用", "分數", "通分", "加減"],
        core=["通分", "最小公倍數", "最簡分數"],
        meta={"op": op, "a": s1, "b": s2, "d1": d1, "d2": d2},
    )


def q_u3_frac_times_int(r: random.Random, qid: str, difficulty: str) -> Q:
    den = _pick(r, [2, 3, 4, 5, 6, 8, 10, 12])
    num = r.randint(1, den - 1) if difficulty != "hard" else r.randint(den - 1, den * 2 - 1)
    k = r.randint(2, 5) if difficulty == "easy" else r.randint(3, 9)

    n = num * k
    d = den
    ans = _frac_to_str(n, d)

    item = _pick(r, ["披薩", "蛋糕", "水壺", "桶果汁", "鍋湯"])
    frac = _frac_to_str(num, den)
    q = f"（生活應用｜分數×整數）每份是 {frac} 個{item}，共有 {k} 份，一共有多少個{item}？（最簡分數）"

    hints = [
        "觀念：分數×整數 → 分子乘整數、分母不變。",
        f"列式：{frac}×{k}。",
        f"先算分子：{num}×{k}={num*k}，分母仍是 {den}。",
        "最後把結果約分成最簡。",
    ]

    steps = [
        "列出『每份』×『份數』。",
        "分子乘整數，分母不變。",
        "把結果約分成最簡分數。",
        "檢查：份數>1 時答案應比一份多。",
    ]

    return Q(
        id=qid,
        kind="u3_frac_times_int",
        topic="小五生活應用題｜第一包｜加強版｜帝國",
        difficulty=difficulty,
        question=q,
        answer=ans,
        answer_mode="fraction",
        hints=hints,
        steps=steps,
        explanation=f"{frac}×{k}={ans}。",
        common_mistakes=[
            "把分母也乘整數（分母不該變）。",
            "忘記約分或把整數乘錯。",
        ],
        tags=["生活應用", "分數", "乘法"],
        core=["分數乘整數", "最簡分數"],
        meta={"frac": frac, "k": k},
    )


def q_u4_money_decimal_addsub(r: random.Random, qid: str, difficulty: str) -> Q:
    # Work in cents
    if difficulty == "easy":
        prices = [r.randrange(100, 650, 50), r.randrange(80, 520, 40)]
    elif difficulty == "normal":
        prices = [r.randrange(120, 980, 20), r.randrange(90, 860, 10), r.randrange(70, 720, 10)]
    else:
        prices = [r.randrange(135, 1280, 5), r.randrange(95, 1100, 5), r.randrange(80, 900, 5)]

    scenario = _pick(r, ["合計", "找零"])
    items = _pick(r, [
        ["鉛筆", "橡皮擦", "尺"],
        ["果汁", "麵包", "餅乾"],
        ["貼紙", "筆記本", "原子筆"],
    ])

    if scenario == "合計":
        total = sum(prices)
        parts = "、".join(f"{items[i]} { _money2_from_cents(prices[i]) } 元" for i in range(len(prices)))
        q = f"（生活應用｜金錢小數加法）買了 {parts}，一共要付多少元？（可寫小數）"
        ans = _money2_from_cents(total)
        steps = [
            "把每個金額的小數點對齊。",
            "先算總分（元/角/分），再合併成總金額。",
            "答案用到小數點後兩位（或可省略尾端 0）。",
            "檢查：總價應大於任何單一商品價格。",
        ]
        hints = [
            "觀念：金額相加，小數點要對齊。",
            "可以先把金額都換成『分』再加總。",
            "加完後再把『分』換回『元』（除以 100）。",
            "最後檢查：合計是否合理（大約幾元）。",
        ]
        explain = f"合計：{ans} 元。"
        cm = ["小數點沒對齊就加，導致位值錯。", "把角、分進位忘記。"]
    else:
        pay = r.randrange(max(sum(prices) + 50, 500), max(sum(prices) + 1050, 2000), 50)
        total = sum(prices)
        change = pay - total
        parts = "、".join(f"{items[i]} { _money2_from_cents(prices[i]) } 元" for i in range(len(prices)))
        q = f"（生活應用｜金錢找零）買了 {parts}，共 { _money2_from_cents(total) } 元。付了 { _money2_from_cents(pay) } 元，要找回多少元？"
        ans = _money2_from_cents(change)
        steps = [
            "先算總價（把小數點對齊相加）。",
            "列式：付的金額 − 總價 = 找零。",
            "用『分』計算可避免小數誤差。",
            "檢查：付的金額應大於總價，找零應為正。",
        ]
        hints = [
            "先把所有價格加起來得到總價。",
            "找零 = 付的錢 − 總價。",
            "也可以先都換成『分』再做減法。",
            "最後檢查：找零加總價是否等於付的錢。",
        ]
        explain = f"找零：{ _money2_from_cents(pay) } − { _money2_from_cents(total) } = {ans}（元）。"
        cm = ["把減法順序弄反（總價−付的錢）。", "忘記先算總價就直接亂減。"]

    return Q(
        id=qid,
        kind="u4_money_decimal_addsub",
        topic="小五生活應用題｜第一包｜加強版｜帝國",
        difficulty=difficulty,
        question=q,
        answer=ans,
        answer_mode="money2",
        hints=hints,
        steps=steps,
        explanation=explain,
        common_mistakes=cm,
        tags=["生活應用", "小數", "金錢", "加減"],
        core=["小數位值", "金錢計算", "加減法"],
        meta={"prices_cents": prices, "scenario": scenario},
    )


def q_u5_decimal_muldiv_price(r: random.Random, qid: str, difficulty: str) -> Q:
    # Use cents; allow multiplication and division contexts
    mode = _pick(r, ["mul", "div"])
    if difficulty == "easy":
        unit_cents = r.randrange(50, 450, 50)
        qty = r.randint(2, 7)
    elif difficulty == "normal":
        unit_cents = r.randrange(35, 980, 5)
        qty = r.randint(2, 12)
    else:
        unit_cents = r.randrange(15, 1580, 5)
        qty = r.randint(3, 20)

    if mode == "mul":
        total = unit_cents * qty
        q = f"（生活應用｜單價×數量）一瓶飲料 { _money2_from_cents(unit_cents) } 元，買 {qty} 瓶，一共多少元？"
        ans = _money2_from_cents(total)
        steps = ["列式：單價×數量=總價。", "用『分』計算，再換回元。", "檢查：買多瓶總價應變大。"]
        hints = [
            "關鍵字：單價、買幾瓶。",
            "用乘法：單價×數量。",
            "先用『分』算：每瓶幾分×幾瓶。",
            "最後把『分』換回『元』（÷100）。",
        ]
        explain = f"{ _money2_from_cents(unit_cents) }×{qty}={ans}（元）。"
        cm = ["把乘法看成加法但漏加次數。", "小數點位置放錯（元/分混淆）。"]
    else:
        # Ensure divisible nicely: total is multiple of qty
        total = unit_cents * qty
        q = f"（生活應用｜平均/單價）{qty} 瓶飲料共 { _money2_from_cents(total) } 元，平均每瓶多少元？"
        ans = _money2_from_cents(unit_cents)
        steps = ["列式：總價÷瓶數=每瓶單價。", "用『分』計算避免小數誤差。", "檢查：平均單價應比總價小。"]
        hints = [
            "關鍵字：平均每瓶。",
            "用除法：總價÷瓶數。",
            "先把總價換成『分』，再除以瓶數。",
            "最後換回『元』（÷100）。",
        ]
        explain = f"{ _money2_from_cents(total) } ÷ {qty} = {ans}（元）。"
        cm = ["把除法寫成乘法（平均值反而變大）。", "沒有用總價而只拿其中一個數字計算。"]

    return Q(
        id=qid,
        kind="u5_decimal_muldiv_price",
        topic="小五生活應用題｜第一包｜加強版｜帝國",
        difficulty=difficulty,
        question=q,
        answer=ans,
        answer_mode="money2",
        hints=hints,
        steps=steps,
        explanation=explain,
        common_mistakes=cm,
        tags=["生活應用", "小數", "單價", "平均"],
        core=["乘除關係", "單位（元/分）", "平均概念"],
        meta={"unit_cents": unit_cents, "qty": qty, "mode": mode},
    )


def q_u6_frac_dec_convert(r: random.Random, qid: str, difficulty: str) -> Q:
    # Mix types: fraction->decimal or decimal->fraction
    kind = "f2d" if r.random() < 0.55 else "d2f"

    if kind == "f2d":
        den = _pick(r, [2, 4, 5, 8, 10, 20, 25, 50, 100]) if difficulty != "hard" else _pick(
            r, [2, 4, 5, 8, 10, 16, 20, 25, 40, 50, 80, 100]
        )
        num = r.randint(1, den - 1)
        f = _frac_to_str(num, den)
        # exact decimal using integer arithmetic
        places = 4 if den in (16, 40, 80) else 3
        # compute decimal with enough places then strip
        dec = num / den
        ans = f"{dec:.{places}f}".rstrip("0").rstrip(".")
        q = f"（生活應用｜等值）把分數 {f} 寫成小數。"
        mode = "number"
        steps = ["把分母變成 10、100、1000…（或用除法）。", "計算並寫成小數。", "檢查：小數應介於 0 和 1 之間。"]
        hints = [
            "可以用『分子÷分母』得到小數。",
            "若分母能變成 10/100/1000，就很好寫。",
            f"例如：{f} = {num}÷{den}。",
            "最後把小數寫乾淨（可省略尾端 0）。",
        ]
        explain = f"{f} = {num}÷{den} = {ans}。"
        cm = ["把分母直接當小數位數（錯誤規則）。", "除法算到一半就停（沒寫完整小數）。"]
        tags = ["分數", "小數", "等值"].copy()
        core = ["分數=除法", "小數位值"].copy()
        meta = {"from": f, "to": ans, "type": "fraction_to_decimal"}
    else:
        # decimal to fraction (terminating)
        places = 1 if difficulty == "easy" else (2 if difficulty == "normal" else 3)
        base = 10**places
        n = r.randint(1, base - 1)
        # avoid huge simplification to 1
        if n % base == 0:
            n += 1
        dec = _int_places_to_str_fixed(n, places).rstrip("0").rstrip(".")
        num, den = _simplify_fraction(n, base)
        ans = _frac_to_str(num, den)
        q = f"（生活應用｜等值）把小數 {dec} 寫成最簡分數 a/b。"
        mode = "fraction"
        steps = ["看小數點後有幾位 → 分母用 10/100/1000。", "把小數變成分數。", "約分到最簡。"]
        hints = [
            f"{dec} 小數點後有 {places} 位，所以分母用 {base}。",
            f"先寫成 {n}/{base}。",
            "再用最大公因數約分。",
            "檢查：把分數再轉回小數應該等於原小數。",
        ]
        explain = f"{dec} = {n}/{base} = {ans}。"
        cm = ["分母選錯（位數 2 卻用 10）。", "忘記約分到最簡。"]
        tags = ["分數", "小數", "等值"].copy()
        core = ["位值", "約分"].copy()
        meta = {"from": dec, "to": ans, "type": "decimal_to_fraction", "places": places}

    return Q(
        id=qid,
        kind="u6_frac_dec_convert",
        topic="小五生活應用題｜第一包｜加強版｜帝國",
        difficulty=difficulty,
        question=q,
        answer=ans,
        answer_mode=mode,
        hints=hints,
        steps=steps,
        explanation=explain,
        common_mistakes=cm,
        tags=tags,
        core=core,
        meta=meta,
    )


def q_u7_discount_percent(r: random.Random, qid: str, difficulty: str) -> Q:
    # Use discount as decimal ratio (x折)
    # e.g. 8折=0.8
    disc = _pick(r, [0.9, 0.85, 0.8, 0.75, 0.7]) if difficulty != "hard" else _pick(
        r, [0.95, 0.9, 0.88, 0.82, 0.78, 0.72, 0.66]
    )

    # price in cents
    price = r.randrange(500, 4500, 50) if difficulty == "easy" else r.randrange(380, 9800, 10)
    sale = int(round(price * disc))

    ask = _pick(r, ["sale", "save"]) if difficulty != "easy" else "sale"

    item = _pick(r, ["外套", "書包", "球鞋", "玩具", "文具組"])
    disc_text = f"{int(round(disc * 10))} 折" if abs(disc * 10 - round(disc * 10)) < 1e-9 else f"折扣 {disc}"

    if ask == "sale":
        q = f"（生活應用｜折扣）一件{item}原價 { _money2_from_cents(price) } 元，打 {disc_text}，折後價是多少元？"
        ans = _money2_from_cents(sale)
        steps = [
            "把『x折』換成小數倍率（例如 8 折=0.8）。",
            "列式：原價×倍率=折後價。",
            "用『分』計算再換回元。",
        ]
        hints = [
            "關鍵字：打折後要付多少。",
            "折後價 = 原價 × 折扣倍率。",
            f"{disc_text} 對應倍率約是 {disc}。",
            "最後檢查：打折後價格應比原價小。",
        ]
        explain = f"折後價：{ _money2_from_cents(price) }×{disc}={ans}（元）。"
        cm = ["把折扣當成要減的比例（直接減 disc）。", "把 8 折誤當 0.08。"]
    else:
        save = price - sale
        q = f"（生活應用｜折扣）一件{item}原價 { _money2_from_cents(price) } 元，打 {disc_text}，省下多少元？"
        ans = _money2_from_cents(save)
        steps = [
            "先算折後價：原價×倍率。",
            "省下 = 原價 − 折後價。",
            "用『分』計算避免小數誤差。",
        ]
        hints = [
            "先求折後價，再求省下多少。",
            "省下 = 原價 − 折後價。",
            "或用省下倍率：1−折扣倍率。",
            "檢查：省下 + 折後價 = 原價。",
        ]
        explain = f"折後價 { _money2_from_cents(sale) }，省下 { _money2_from_cents(price) } − { _money2_from_cents(sale) } = {ans}。"
        cm = ["把省下寫成折後價（問省下卻算要付）。", "忘記先乘折扣就直接相減。"]

    return Q(
        id=qid,
        kind="u7_discount_percent",
        topic="小五生活應用題｜第一包｜加強版｜帝國",
        difficulty=difficulty,
        question=q,
        answer=ans,
        answer_mode="money2",
        hints=hints,
        steps=steps,
        explanation=explain,
        common_mistakes=cm,
        tags=["生活應用", "折扣", "百分比", "小數"],
        core=["倍率概念", "乘法", "金錢"],
        meta={"price_cents": price, "disc": disc, "sale_cents": sale, "ask": ask},
    )


def q_u8_ratio_recipe(r: random.Random, qid: str, difficulty: str) -> Q:
    a = r.randint(1, 4) if difficulty == "easy" else r.randint(2, 7)
    b = r.randint(1, 5) if difficulty != "hard" else r.randint(3, 9)
    if _gcd(a, b) != 1 and difficulty == "easy":
        a, b = a // _gcd(a, b), b // _gcd(a, b)

    total = r.randint(300, 1200) if difficulty == "easy" else r.randint(450, 2400)
    # make total divisible by (a+b)
    parts = a + b
    total = (total // parts) * parts
    if total == 0:
        total = parts * 100

    each = total // parts
    x = a * each
    y = b * each

    ask = _pick(r, ["a", "b"]) if difficulty != "easy" else "a"
    drink = _pick(r, ["果汁", "奶茶", "檸檬水", "運動飲料"])

    if ask == "a":
        q = f"（生活應用｜比例）調配{drink}，果汁:水 = {a}:{b}，總共有 {total} mL，果汁有多少 mL？"
        ans = str(x)
        explain = f"總份數 {parts}，每份 {each} mL，所以果汁 {a} 份 = {x} mL。"
        cm = ["把 {a}:{b} 當成要相加/相減而不是份數。", "總份數算錯（忘記 a+b）。"]
    else:
        q = f"（生活應用｜比例）調配{drink}，果汁:水 = {a}:{b}，總共有 {total} mL，水有多少 mL？"
        ans = str(y)
        explain = f"總份數 {parts}，每份 {each} mL，所以水 {b} 份 = {y} mL。"
        cm = ["只算其中一邊，忘記用份數乘。", "每份=總量÷總份數這一步寫錯。"]

    hints = [
        "份數法：比例 a:b 表示 a 份對 b 份。",
        f"先算總份數：{a}+{b}={parts}。",
        f"每份 = 總量 ÷ 總份數 = {total}÷{parts}。",
        "最後用（需要的份數）×（每份）得到答案。",
    ]

    steps = [
        "算總份數 a+b。",
        "用總量÷總份數得到每份。",
        "用需要的份數×每份得到需要的量。",
        "檢查：兩部分相加應等於總量。",
    ]

    return Q(
        id=qid,
        kind="u8_ratio_recipe",
        topic="小五生活應用題｜第一包｜加強版｜帝國",
        difficulty=difficulty,
        question=q,
        answer=ans,
        answer_mode="number",
        hints=hints,
        steps=steps,
        explanation=explain,
        common_mistakes=cm,
        tags=["生活應用", "比例", "份數法"],
        core=["比例=份數", "平均", "乘除"],
        meta={"a": a, "b": b, "total": total, "ask": ask},
    )


def q_u9_unit_convert_decimal(r: random.Random, qid: str, difficulty: str) -> Q:
    conv = _pick(
        r,
        [
            ("m", "cm", 100),
            ("km", "m", 1000),
            ("kg", "g", 1000),
            ("L", "mL", 1000),
        ],
    )
    u_from, u_to, mul = conv

    # choose a value that yields simple decimal for reverse conversions
    if difficulty == "easy":
        x = r.randint(2, 35)
        places = 0
    elif difficulty == "normal":
        x = r.randint(15, 320)
        places = 1 if r.random() < 0.6 else 2
    else:
        x = r.randint(25, 880)
        places = 2 if r.random() < 0.55 else 3

    # value in from-unit as fixed decimal string
    a_int = x
    a_val = _int_places_to_str_fixed(a_int, places)

    # convert
    # If converting from larger to smaller: multiply by mul
    # If from smaller to larger: divide by mul (but here we always set from larger to smaller for simplicity)
    out_int = a_int * mul
    out_places = places
    ans = _int_places_to_str_fixed(out_int, out_places)
    ans = ans.rstrip("0").rstrip(".")

    q = f"（生活應用｜單位換算）{a_val} {u_from} = 多少 {u_to}？（可寫小數）"

    hints = [
        f"先記換算：1 {u_from} = {mul} {u_to}。",
        "由大單位換成小單位 → 用乘法。",
        f"列式：{a_val}×{mul}。",
        "檢查：換成更小單位，數字應變大。",
    ]

    steps = [
        "寫出 1 單位的換算關係。",
        "決定乘或除（大→小用乘）。",
        "計算並寫出答案。",
        "做合理性檢查。",
    ]

    return Q(
        id=qid,
        kind="u9_unit_convert_decimal",
        topic="小五生活應用題｜第一包｜加強版｜帝國",
        difficulty=difficulty,
        question=q,
        answer=ans,
        answer_mode="number",
        hints=hints,
        steps=steps,
        explanation=f"{a_val} {u_from} × {mul} = {ans} {u_to}。",
        common_mistakes=[
            "大→小卻用除法（方向弄反）。",
            "把換算倍率寫錯（例如 km→m 用 100）。",
        ],
        tags=["生活應用", "單位換算", "小數"],
        core=["乘除方向", "位值"],
        meta={"from": u_from, "to": u_to, "mul": mul, "a": a_val},
    )


def q_u10_rate_time_distance(r: random.Random, qid: str, difficulty: str) -> Q:
    # Use simple unit rates
    mode = _pick(r, ["d", "t"]) if difficulty != "easy" else "d"
    rate = r.randint(3, 9) if difficulty == "easy" else r.randint(4, 15)

    if mode == "d":
        t = r.randint(4, 20) if difficulty != "hard" else r.randint(6, 35)
        d = rate * t
        q = f"（生活應用｜速率）腳踏車每分鐘走 {rate} 公尺，走了 {t} 分鐘，一共走了多少公尺？"
        ans = str(d)
        steps = ["距離=速率×時間。", f"列式：{rate}×{t}。", "計算並寫出答案。", "檢查：時間越久距離越大。"]
        hints = [
            "關鍵字：每分鐘…（單位率）。",
            "距離 = 每分鐘走的距離 × 分鐘數。",
            f"列式：{rate}×{t}。",
            "最後檢查單位：公尺。",
        ]
        explain = f"距離 = {rate}×{t} = {d}（公尺）。"
        cm = ["把乘法寫成加法但只加一次。", "把『每分鐘』當成『總共』。"]
    else:
        d = r.randint(60, 240) if difficulty != "hard" else r.randint(120, 560)
        # make divisible
        d = (d // rate) * rate
        t = d // rate
        q = f"（生活應用｜速率）腳踏車每分鐘走 {rate} 公尺，要走 {d} 公尺，需要幾分鐘？"
        ans = str(t)
        steps = ["時間=距離÷速率。", f"列式：{d}÷{rate}。", "計算並寫出答案。", "檢查：速率越快時間越短。"]
        hints = [
            "關鍵字：需要幾分鐘（求時間）。",
            "時間 = 距離 ÷ 每分鐘走的距離。",
            f"列式：{d}÷{rate}。",
            "最後檢查：算出來應是整數分鐘。",
        ]
        explain = f"時間 = {d}÷{rate} = {t}（分鐘）。"
        cm = ["把除法寫成乘法，答案變得太大。", "單位搞混（公尺/分鐘）。"]

    return Q(
        id=qid,
        kind="u10_rate_time_distance",
        topic="小五生活應用題｜第一包｜加強版｜帝國",
        difficulty=difficulty,
        question=q,
        answer=ans,
        answer_mode="number",
        hints=hints,
        steps=steps,
        explanation=explain,
        common_mistakes=cm,
        tags=["生活應用", "速率", "單位率"],
        core=["單位率", "乘除"],
        meta={"rate": rate, "mode": mode},
    )


GEN_BY_UNIT = {
    "u1_avg_fraction": q_u1_avg_fraction,
    "u2_frac_addsub_life": q_u2_frac_addsub_life,
    "u3_frac_times_int": q_u3_frac_times_int,
    "u4_money_decimal_addsub": q_u4_money_decimal_addsub,
    "u5_decimal_muldiv_price": q_u5_decimal_muldiv_price,
    "u6_frac_dec_convert": q_u6_frac_dec_convert,
    "u7_discount_percent": q_u7_discount_percent,
    "u8_ratio_recipe": q_u8_ratio_recipe,
    "u9_unit_convert_decimal": q_u9_unit_convert_decimal,
    "u10_rate_time_distance": q_u10_rate_time_distance,
}


def generate(seed: int) -> List[Dict]:
    r = _rng(seed)
    bank: List[Dict] = []

    for unit_id, _title in UNITS:
        plan = _difficulty_plan()
        # shuffle difficulty order slightly but keep counts stable
        r.shuffle(plan)

        extra_n = int(EXTRA_BY_UNIT.get(unit_id, 0))
        extra_plan = ["hard"] * extra_n
        r.shuffle(extra_plan)

        full_plan = plan + extra_plan
        for i, diff in enumerate(full_plan, start=1):
            qid = f"g5lp1p_{unit_id}_{i:02d}"
            q = GEN_BY_UNIT[unit_id](r, qid=qid, difficulty=diff)
            bank.append(asdict(q))

    # global sanity
    ids = [q["id"] for q in bank]
    if len(ids) != len(set(ids)):
        raise RuntimeError("Duplicate question IDs found")
    expected = 200 + sum(EXTRA_BY_UNIT.values())
    if len(bank) != expected:
        raise RuntimeError(f"Bank size must be {expected}, got {len(bank)}")

    return bank


def write_bank_js(out_path: Path, bank: List[Dict]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    js = (
        "// Auto-generated by scripts/generate_g5_life_pack1plus_empire_bank.py\n"
        "// 小五生活應用題（分數/小數/比例）第一包｜加強版（更難 + 加題）\n"
        "// window.G5_LIFE_PACK1PLUS_BANK = [...]\n\n"
        + "window.G5_LIFE_PACK1PLUS_BANK = "
        + json.dumps(bank, ensure_ascii=False, indent=2)
        + ";\n"
    )
    out_path.write_text(js, encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--docs-out", type=str, default=str(DOCS_OUT))
    p.add_argument("--dist-out", type=str, default=str(DIST_OUT))
    args = p.parse_args()

    bank = generate(seed=int(args.seed))
    docs_out = Path(args.docs_out)
    dist_out = Path(args.dist_out)
    write_bank_js(docs_out, bank)
    write_bank_js(dist_out, bank)

    kinds = sorted(set(q["kind"] for q in bank))
    print(f"Wrote {docs_out} (n={len(bank)} kinds={len(kinds)}) seed={int(args.seed)}")
    print(f"Wrote {dist_out} (n={len(bank)} kinds={len(kinds)}) seed={int(args.seed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
