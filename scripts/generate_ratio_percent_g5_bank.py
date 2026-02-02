import json
import random
from decimal import Decimal, getcontext
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
OUT_JS = ROOT / "docs" / "ratio-percent-g5" / "bank.js"

random.seed(20260201)
getcontext().prec = 28


def _strip_trailing_zeros(s: str) -> str:
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def fmt_decimal(fr: Fraction) -> str:
    d = Decimal(fr.numerator) / Decimal(fr.denominator)
    return _strip_trailing_zeros(format(d, "f"))


def fmt_money(n: int) -> str:
    return f"{n:,}"


def q_base(
    *,
    qid: str,
    kind: str,
    difficulty: str,
    question: str,
    answer: str,
    answer_unit: str,
    hints: List[str],
    steps: List[str],
    explanation: str,
    unit: str | None = None,
) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "id": qid,
        "kind": kind,
        "topic": "國小五年級下｜比率與百分率",
        "difficulty": difficulty,
        "question": question,
        "answer": answer,
        "answer_unit": answer_unit,
        "hints": hints,
        "steps": steps,
        "explanation": explanation,
        "meta": {},
    }
    if unit:
        out["meta"]["unit"] = unit
    return out


def gen_ratio_part_total(i: int) -> Dict[str, Any]:
    total = random.choice([20, 25, 40, 50, 80, 100, 200])
    part = random.randint(1, total - 1)
    r = Fraction(part, total)
    ans = fmt_decimal(r)

    question = f"（比率）一共有 {total} 個物品，其中有 {part} 個是紅色。紅色占全體的比率是多少？（用小數表示）"

    hints = [
        "觀念：比率常用『部分 ÷ 全體』表示，結果是 0~1 的小數。",
        f"列式：{part} ÷ {total}。",
        "Level 3｜完整步驟\n"
        f"1) 比率 = 部分 ÷ 全體 = {part} ÷ {total}\n"
        f"2) 計算得到 {ans}\n"
        "3) 檢查：部分 < 全體，所以比率應該 < 1",
    ]

    steps = [
        "找出部分與全體",
        "用 部分÷全體",
        "寫成小數",
    ]

    return q_base(
        qid=f"rp5_ratio_pt_{i:03d}",
        kind="ratio_part_total",
        difficulty="easy",
        question=question,
        answer=ans,
        answer_unit="number",
        hints=hints,
        steps=steps,
        explanation=f"紅色比率= {part}/{total} = {ans}。",
    )


def gen_ratio_remaining(i: int) -> Dict[str, Any]:
    total = random.choice([20, 25, 40, 50, 80, 100, 200])
    used = random.randint(1, total - 1)
    left = total - used
    r = Fraction(left, total)
    ans = fmt_decimal(r)

    question = f"（比率）一共有 {total} 個物品，已經用掉 {used} 個，剩下的占全體的比率是多少？（用小數表示）"

    hints = [
        "觀念：剩下比率 = 剩下的數量 ÷ 全體；也可以用 1 − 已用比率。",
        f"先算剩下：{total} − {used} = {left}，再算 {left} ÷ {total}。",
        "Level 3｜完整步驟\n"
        f"1) 剩下 = {total} − {used} = {left}\n"
        f"2) 剩下比率 = {left} ÷ {total} = {ans}\n"
        "3) 檢查：剩下 < 全體，所以比率 < 1",
    ]

    steps = [
        "先算剩下數量",
        "用 剩下÷全體",
        "寫成小數",
    ]

    return q_base(
        qid=f"rp5_ratio_left_{i:03d}",
        kind="ratio_remaining",
        difficulty="easy",
        question=question,
        answer=ans,
        answer_unit="number",
        hints=hints,
        steps=steps,
        explanation=f"剩下比率= {left}/{total} = {ans}。",
    )


def gen_ratio_unit_rate(i: int) -> Dict[str, Any]:
    # Keep integer unit rate.
    hours = random.choice([2, 3, 4, 5])
    per_hour = random.choice([30, 40, 50, 60, 70, 80, 90])
    total = hours * per_hour

    question = f"（單位率）一輛車 {hours} 小時行駛 {total} 公里。平均每 1 小時行駛多少公里？"

    hints = [
        "觀念：單位率就是『每 1 單位』；把總量平均分到 1 個單位。",
        f"列式：{total} ÷ {hours}。",
        "Level 3｜完整步驟\n"
        f"1) 每 1 小時的公里數 = {total} ÷ {hours}\n"
        f"2) 計算得到 {per_hour}\n"
        "3) 單位：公里/小時",
    ]

    steps = [
        "用 總公里 ÷ 總小時",
        "得到每 1 小時",
        "寫上單位",
    ]

    return q_base(
        qid=f"rp5_unit_{i:03d}",
        kind="ratio_unit_rate",
        difficulty="easy",
        question=question,
        answer=str(per_hour),
        answer_unit="number",
        hints=hints,
        steps=steps,
        explanation=f"{total} ÷ {hours} = {per_hour}（公里/小時）。",
        unit="公里/小時",
    )


def gen_ratio_missing_to_1(i: int) -> Dict[str, Any]:
    # Two known ratios sum to < 1; find missing ratio.
    a = Fraction(random.choice([10, 15, 20, 25, 30, 35, 40]), 100)
    b = Fraction(random.choice([10, 15, 20, 25, 30, 35, 40]), 100)
    if a + b >= 1:
        # simple fallback
        a = Fraction(25, 100)
        b = Fraction(35, 100)
    missing = 1 - a - b

    a_s = fmt_decimal(a)
    b_s = fmt_decimal(b)
    m_s = fmt_decimal(missing)

    question = (
        "（比率）一個盒子裡有三種物品 A、B、C。已知 A 的比率是 "
        f"{a_s}，B 的比率是 {b_s}。C 的比率是多少？（用小數表示）"
    )

    hints = [
        "觀念：同一個群體裡，各部分的比率加起來 = 1。",
        f"列式：C = 1 − {a_s} − {b_s}。",
        "Level 3｜完整步驟\n"
        f"1) A+B+C=1\n"
        f"2) C = 1 − {a_s} − {b_s}\n"
        f"3) 計算得到 C = {m_s}",
    ]

    steps = [
        "利用 A+B+C=1",
        "把已知比率相加",
        "用 1 減去",
    ]

    return q_base(
        qid=f"rp5_ratio_miss_{i:03d}",
        kind="ratio_missing_to_1",
        difficulty="medium",
        question=question,
        answer=m_s,
        answer_unit="number",
        hints=hints,
        steps=steps,
        explanation=f"C = 1 − {a_s} − {b_s} = {m_s}。",
    )


def _pick_ratio_decimal() -> Fraction:
    # Prefer 2-decimal ratios for practicing decimal add/sub.
    return Fraction(random.choice([5, 8, 10, 12, 15, 18, 20, 22, 25, 28, 30, 32, 35, 38, 40, 45, 50, 55, 60, 65, 70, 75]), 100)


def gen_ratio_add_decimal(i: int) -> Dict[str, Any]:
    # Add two ratios expressed as decimals (sum <= 1).
    r1 = _pick_ratio_decimal()
    r2 = _pick_ratio_decimal()
    if r1 + r2 > Fraction(95, 100):
        r1, r2 = Fraction(28, 100), Fraction(35, 100)

    a_s = fmt_decimal(r1)
    b_s = fmt_decimal(r2)
    s_s = fmt_decimal(r1 + r2)

    ctx = random.choice([
        ("參加籃球社", "參加排球社", "兩個社團"),
        ("喜歡蘋果", "喜歡香蕉", "這兩種水果"),
        ("搭公車上學", "搭捷運上學", "這兩種方式"),
        ("選擇A方案", "選擇B方案", "A或B方案"),
    ])
    x1, x2, group = ctx

    question = (
        f"（比率｜小數加法）某班同學中，{x1} 的比率是 {a_s}，{x2} 的比率是 {b_s}。"
        f"{group}合計的比率是多少？（用小數表示）"
    )

    est = round(float(a_s), 1) + round(float(b_s), 1)

    hints = [
        "觀念：同一個群體裡，『合計比率』可以直接把各部分的比率相加。",
        f"列式：{a_s} + {b_s}。",
        "Level 3｜老師帶算（小數相加）\n"
        "1) 先估算檢查：把小數大約化成一位小數\n"
        f"   {a_s}≈{round(float(a_s), 1):.1f}，{b_s}≈{round(float(b_s), 1):.1f}，合計≈{est:.1f}\n"
        "2) 正式計算：小數點對齊後相加\n"
        f"   {a_s} + {b_s} = {s_s}\n"
        "3) 合理性檢查：合計比率應該在 0~1 之間（不會超過全體）",
    ]

    steps = [
        "找出要合計的兩個比率",
        "小數點對齊相加",
        "檢查結果是否在 0~1",
    ]

    return q_base(
        qid=f"rp5_ratio_addd_{i:03d}",
        kind="ratio_add_decimal",
        difficulty="easy",
        question=question,
        answer=s_s,
        answer_unit="number",
        hints=hints,
        steps=steps,
        explanation=f"合計比率 = {a_s} + {b_s} = {s_s}。",
    )


def gen_ratio_sub_decimal(i: int) -> Dict[str, Any]:
    # Subtract two ratios expressed as decimals (difference >= 0).
    r1 = _pick_ratio_decimal()
    r2 = _pick_ratio_decimal()
    if r1 <= r2:
        r1, r2 = Fraction(65, 100), Fraction(25, 100)

    a_s = fmt_decimal(r1)
    b_s = fmt_decimal(r2)
    d_s = fmt_decimal(r1 - r2)

    ctx = random.choice([
        ("使用手機", "使用平板", "手機"),
        ("喜歡科學", "喜歡社會", "喜歡科學"),
        ("搭機車", "搭腳踏車", "搭機車"),
        ("選擇A方案", "選擇B方案", "A方案"),
    ])
    x1, x2, focus = ctx

    question = (
        f"（比率｜小數減法）某群體中，{x1} 的比率是 {a_s}，{x2} 的比率是 {b_s}。"
        f"{focus} 的比率比{x2}多多少？（用小數表示）"
    )

    hints = [
        "觀念：『多多少比率』就是做差：大比率 − 小比率。",
        f"列式：{a_s} − {b_s}。",
        "Level 3｜老師帶算（小數相減）\n"
        "1) 先估算檢查：大約看一位小數\n"
        f"   {a_s}≈{round(float(a_s), 1):.1f}，{b_s}≈{round(float(b_s), 1):.1f}，差≈{round(float(a_s), 1)-round(float(b_s), 1):.1f}\n"
        "2) 正式計算：小數點對齊後相減\n"
        f"   {a_s} − {b_s} = {d_s}\n"
        "3) 合理性檢查：既然是『多多少』，答案應該 ≥ 0",
    ]

    steps = [
        "判斷哪個比率比較大",
        "用 大−小 來求差",
        "檢查答案是否為非負",
    ]

    return q_base(
        qid=f"rp5_ratio_subd_{i:03d}",
        kind="ratio_sub_decimal",
        difficulty="medium",
        question=question,
        answer=d_s,
        answer_unit="number",
        hints=hints,
        steps=steps,
        explanation=f"相差比率 = {a_s} − {b_s} = {d_s}。",
    )


def gen_percent_meaning(i: int) -> Dict[str, Any]:
    p = random.choice([5, 10, 12, 15, 20, 25, 30, 40, 50, 75])
    per_100 = p
    question = f"（百分率）{p}% 表示『每 100 份裡有幾份』？（請填整數）"

    hints = [
        "觀念：p% 就是 p/100，也就是『每 100 份裡有 p 份』。",
        f"把 {p}% 看成 {p}/100。",
        "Level 3｜完整步驟\n"
        f"1) {p}% = {p}/100\n"
        f"2) 所以每 100 份裡有 {p} 份",
    ]

    steps = [
        "把 % 理解成每 100",
        "寫出每 100 份有幾份",
    ]

    return q_base(
        qid=f"rp5_pct_mean_{i:03d}",
        kind="percent_meaning",
        difficulty="easy",
        question=question,
        answer=str(per_100),
        answer_unit="number",
        hints=hints,
        steps=steps,
        explanation=f"{p}% 表示每 100 份裡有 {p} 份。",
    )


def gen_percent_to_decimal(i: int) -> Dict[str, Any]:
    p = random.choice([5, 12.5, 20, 35, 40, 62.5, 75])
    fr = Fraction(int(p * 10), 10) if isinstance(p, float) and p % 1 != 0 else Fraction(int(p), 1)
    dec = fr / 100
    ans = fmt_decimal(dec)

    p_s = _strip_trailing_zeros(str(p))
    question = f"（換算）把 {p_s}% 化成小數是多少？"

    hints = [
        "觀念：p% = p/100，把小數點往左移 2 位。",
        f"列式：{p_s} ÷ 100。",
        "Level 3｜完整步驟\n"
        f"1) {p_s}% = {p_s}/100\n"
        f"2) {p_s} ÷ 100 = {ans}",
    ]

    steps = [
        "把 % 變成除以 100",
        "計算成小數",
    ]

    return q_base(
        qid=f"rp5_pct2dec_{i:03d}",
        kind="percent_to_decimal",
        difficulty="easy",
        question=question,
        answer=ans,
        answer_unit="number",
        hints=hints,
        steps=steps,
        explanation=f"{p_s}% = {p_s}/100 = {ans}。",
    )


def gen_decimal_to_percent(i: int) -> Dict[str, Any]:
    # Finite decimals.
    fr = random.choice([Fraction(1, 4), Fraction(3, 5), Fraction(7, 20), Fraction(9, 25), Fraction(11, 50)])
    dec = fmt_decimal(fr)
    pct = fr * 100
    pct_s = fmt_decimal(pct)

    question = f"（換算）把小數 {dec} 化成百分率是多少？（可填 35 或 35%）"

    hints = [
        "觀念：小數 → 百分率，就是乘以 100，再加上 %。",
        f"列式：{dec} × 100。",
        "Level 3｜完整步驟\n"
        f"1) {dec} × 100 = {pct_s}\n"
        f"2) 所以是 {pct_s}%",
    ]

    steps = [
        "把小數乘 100",
        "在後面加上 %",
    ]

    return q_base(
        qid=f"rp5_dec2pct_{i:03d}",
        kind="decimal_to_percent",
        difficulty="easy",
        question=question,
        answer=pct_s,
        answer_unit="percent",
        hints=hints,
        steps=steps,
        explanation=f"{dec}×100={pct_s}，所以是 {pct_s}%。",
        unit="%",
    )


def gen_fraction_to_percent(i: int) -> Dict[str, Any]:
    # Fractions with nice percents.
    fr = random.choice([Fraction(1, 2), Fraction(1, 4), Fraction(3, 4), Fraction(2, 5), Fraction(3, 5), Fraction(7, 10)])
    pct = fr * 100
    pct_s = fmt_decimal(pct)

    question = f"（換算）把分數 {fr.numerator}/{fr.denominator} 化成百分率是多少？（可填 75 或 75%）"

    hints = [
        "觀念：分數化成百分率：先算成小數（或直接 ×100），再加上 %。",
        f"列式：({fr.numerator}/{fr.denominator}) × 100。",
        "Level 3｜完整步驟\n"
        f"1) {fr.numerator}/{fr.denominator} × 100 = {pct_s}\n"
        f"2) 所以是 {pct_s}%",
    ]

    steps = [
        "分數 × 100",
        "加上 %",
    ]

    return q_base(
        qid=f"rp5_frac2pct_{i:03d}",
        kind="fraction_to_percent",
        difficulty="easy",
        question=question,
        answer=pct_s,
        answer_unit="percent",
        hints=hints,
        steps=steps,
        explanation=f"{fr.numerator}/{fr.denominator} = {fmt_decimal(fr)}，乘 100 得 {pct_s}% 。",
        unit="%",
    )


def gen_percent_find_percent(i: int) -> Dict[str, Any]:
    whole = random.choice([40, 50, 80, 100, 120, 200])
    pct = random.choice([10, 15, 20, 25, 30, 40, 50, 60, 75])
    part = whole * pct // 100

    question = f"（百分率應用）全體有 {whole} 人，其中有 {part} 人參加。參加的人占全體的百分率是多少？（可填 25 或 25%）"

    hints = [
        "觀念：百分率 = 部分 ÷ 全體，再乘 100%。",
        f"列式：{part} ÷ {whole} × 100。",
        "Level 3｜完整步驟\n"
        f"1) 百分率 = {part}/{whole}\n"
        f"2) {part} ÷ {whole} = {fmt_decimal(Fraction(part, whole))}\n"
        f"3) 乘 100 得 {pct}%",
    ]

    steps = [
        "用 部分÷全體",
        "再乘 100",
        "寫成 %",
    ]

    return q_base(
        qid=f"rp5_findpct_{i:03d}",
        kind="percent_find_percent",
        difficulty="easy",
        question=question,
        answer=str(pct),
        answer_unit="percent",
        hints=hints,
        steps=steps,
        explanation=f"{part}/{whole} = {pct}/100，所以是 {pct}%。",
        unit="%",
    )


def gen_percent_find_part(i: int) -> Dict[str, Any]:
    whole = random.choice([80, 100, 120, 200, 300, 500])
    pct = random.choice([5, 10, 12, 15, 20, 25, 30, 40])
    part = whole * pct // 100

    question = f"（百分率應用）全體是 {whole}，其中 {pct}% 是女生。女生有多少人？"

    hints = [
        "觀念：部分 = 全體 × 百分率（先把 % 變成 /100）。",
        f"列式：{whole} × {pct}/100。",
        "Level 3｜完整步驟\n"
        f"1) {pct}% = {pct}/100\n"
        f"2) 部分 = {whole} × {pct}/100 = {part}",
    ]

    steps = [
        "把 % 變成分數/小數",
        "用 全體×百分率",
    ]

    return q_base(
        qid=f"rp5_findpart_{i:03d}",
        kind="percent_find_part",
        difficulty="easy",
        question=question,
        answer=str(part),
        answer_unit="number",
        hints=hints,
        steps=steps,
        explanation=f"女生 = {whole}×{pct}% = {part}。",
    )


def gen_percent_find_whole(i: int) -> Dict[str, Any]:
    whole = random.choice([80, 100, 120, 200, 300, 500])
    pct = random.choice([10, 12.5, 20, 25, 40, 50])

    # Ensure part is integer.
    if pct == 12.5:
        part = whole // 8  # 12.5% = 1/8
        pct_fr = Fraction(125, 1000)
    else:
        part = int(whole * pct // 100)
        pct_fr = Fraction(int(pct), 100)

    pct_s = _strip_trailing_zeros(str(pct))

    question = f"（百分率應用）某班女生占 {pct_s}%，女生有 {part} 人。全班共有多少人？（請填整數）"

    hints = [
        "觀念：全體 = 部分 ÷ 百分率（先把 % 變成 /100）。",
        f"列式：全體 = {part} ÷ ({pct_s}/100)。",
        "Level 3｜完整步驟\n"
        f"1) {pct_s}% = {pct_s}/100\n"
        f"2) 全體 = {part} ÷ ({pct_s}/100)\n"
        f"3) 計算得到 全體 = {whole}",
    ]

    steps = [
        "把 % 變成分數/小數",
        "用 部分÷百分率",
        "檢查：部分應小於全體",
    ]

    return q_base(
        qid=f"rp5_findwhole_{i:03d}",
        kind="percent_find_whole",
        difficulty="medium",
        question=question,
        answer=str(whole),
        answer_unit="number",
        hints=hints,
        steps=steps,
        explanation=f"全體 = {part} ÷ {pct_fr} = {whole}。",
    )


def gen_percent_discount(i: int) -> Dict[str, Any]:
    price = random.choice([200, 240, 300, 360, 500, 800, 1200])
    off = random.choice([10, 20, 25, 30, 40])
    pay_pct = 100 - off
    final = price * pay_pct // 100

    question = f"（打折）原價 {fmt_money(price)} 元，打 {pay_pct}%（等於打 {pay_pct/10:g} 折）。折後價是多少元？"

    hints = [
        "觀念：打折後要付的比例 = 1 − 折扣百分率。折後價 = 原價 × 付款比例。",
        f"列式：{price} × {pay_pct}% = {price} × {pay_pct}/100。",
        "Level 3｜完整步驟\n"
        f"1) 付款比例 = {pay_pct}% = {pay_pct}/100\n"
        f"2) 折後價 = {price} × {pay_pct}/100 = {final}\n"
        f"3) 單位：元",
    ]

    steps = [
        "先找付款比例（不是折扣比例）",
        "原價×付款比例",
        "寫上單位元",
    ]

    return q_base(
        qid=f"rp5_disc_{i:03d}",
        kind="percent_discount",
        difficulty="easy",
        question=question,
        answer=str(final),
        answer_unit="number",
        hints=hints,
        steps=steps,
        explanation=f"折後價 = {price}×{pay_pct}% = {final}（元）。",
        unit="元",
    )


def gen_percent_increase_decrease(i: int) -> Dict[str, Any]:
    base = random.choice([200, 250, 300, 400, 500, 800, 1200])
    pct = random.choice([5, 10, 12, 15, 20, 25])
    up = random.choice([True, False])
    if up:
        new = base * (100 + pct) // 100
        word = "漲價"
        factor = 100 + pct
    else:
        new = base * (100 - pct) // 100
        word = "減少"
        factor = 100 - pct

    question = f"（漲跌）一個數原本是 {base}，{word} {pct}%。新的數是多少？"

    hints = [
        "觀念：新值 = 原值 × (1 ± 百分率)。",
        f"列式：{base} × {factor}% = {base} × {factor}/100。",
        "Level 3｜完整步驟\n"
        f"1) 變化後的比例 = {factor}%\n"
        f"2) 新值 = {base} × {factor}/100 = {new}",
    ]

    steps = [
        "先把『漲/減』變成乘法比例",
        "原值×比例",
    ]

    return q_base(
        qid=f"rp5_change_{i:03d}",
        kind="percent_increase_decrease",
        difficulty="medium",
        question=question,
        answer=str(new),
        answer_unit="number",
        hints=hints,
        steps=steps,
        explanation=f"新值 = {base}×{factor}% = {new}。",
    )


def gen_percent_tax_service(i: int) -> Dict[str, Any]:
    base = random.choice([200, 300, 450, 600, 800, 1200])
    rate = random.choice([5, 10])
    total = base * (100 + rate) // 100

    question = f"（稅金/服務費）餐點小計 {fmt_money(base)} 元，另加 {rate}% 服務費。總共要付多少元？"

    hints = [
        "觀念：含加成的總價 = 小計 × (1 + 百分率)。",
        f"列式：{base} × (100+{rate})% = {base} × {100+rate}/100。",
        "Level 3｜完整步驟\n"
        f"1) 總比例 = {100+rate}%\n"
        f"2) 總價 = {base} × {100+rate}/100 = {total}\n"
        f"3) 單位：元",
    ]

    steps = [
        "先找總比例（含加成）",
        "小計×總比例",
        "寫上單位元",
    ]

    return q_base(
        qid=f"rp5_tax_{i:03d}",
        kind="percent_tax_service",
        difficulty="easy",
        question=question,
        answer=str(total),
        answer_unit="number",
        hints=hints,
        steps=steps,
        explanation=f"總價 = {base}×{100+rate}% = {total}（元）。",
        unit="元",
    )


def gen_percent_interest(i: int) -> Dict[str, Any]:
    principal = random.choice([1000, 2000, 3000, 5000, 8000, 10000])
    rate = random.choice([2, 3, 4, 5])
    years = random.choice([1, 2, 3])
    interest = principal * rate * years // 100

    question = f"（利息｜單利）本金 {fmt_money(principal)} 元，年利率 {rate}%，存 {years} 年。利息是多少元？"

    hints = [
        "觀念：單利利息 = 本金 × 年利率 × 年數。",
        f"列式：{principal} × {rate}% × {years}。",
        "Level 3｜完整步驟\n"
        f"1) 年利率 {rate}% = {rate}/100\n"
        f"2) 利息 = {principal} × {rate}/100 × {years} = {interest}\n"
        f"3) 單位：元",
    ]

    steps = [
        "用 單利利息=本金×利率×年數",
        "把 % 變成 /100",
        "計算並寫上單位",
    ]

    return q_base(
        qid=f"rp5_int_{i:03d}",
        kind="percent_interest",
        difficulty="medium",
        question=question,
        answer=str(interest),
        answer_unit="number",
        hints=hints,
        steps=steps,
        explanation=f"利息 = {principal}×{rate}%×{years} = {interest}（元）。",
        unit="元",
    )


def generate_bank() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []

    out += [gen_ratio_part_total(i) for i in range(1, 19)]
    out += [gen_ratio_remaining(i) for i in range(1, 19)]
    out += [gen_ratio_unit_rate(i) for i in range(1, 15)]
    out += [gen_ratio_missing_to_1(i) for i in range(1, 15)]
    out += [gen_ratio_add_decimal(i) for i in range(1, 13)]
    out += [gen_ratio_sub_decimal(i) for i in range(1, 13)]

    out += [gen_percent_meaning(i) for i in range(1, 13)]
    out += [gen_percent_to_decimal(i) for i in range(1, 13)]
    out += [gen_decimal_to_percent(i) for i in range(1, 13)]
    out += [gen_fraction_to_percent(i) for i in range(1, 13)]

    out += [gen_percent_find_percent(i) for i in range(1, 17)]
    out += [gen_percent_find_part(i) for i in range(1, 17)]
    out += [gen_percent_find_whole(i) for i in range(1, 13)]

    out += [gen_percent_discount(i) for i in range(1, 13)]
    out += [gen_percent_increase_decrease(i) for i in range(1, 13)]
    out += [gen_percent_tax_service(i) for i in range(1, 13)]
    out += [gen_percent_interest(i) for i in range(1, 11)]

    random.shuffle(out)

    # Dedup by question text
    seen = set()
    uniq: List[Dict[str, Any]] = []
    for q in out:
        t = q.get("question")
        if t in seen:
            continue
        seen.add(t)
        uniq.append(q)

    return uniq


def main() -> None:
    bank = generate_bank()

    js = (
        "/* Auto-generated offline question bank. */\n"
        + "window.RATIO_PERCENT_G5_BANK = "
        + json.dumps(bank, ensure_ascii=False, indent=2)
        + ";\n"
    )

    OUT_JS.parent.mkdir(parents=True, exist_ok=True)
    OUT_JS.write_text(js, encoding="utf-8")
    print(f"Wrote: {OUT_JS} (n={len(bank)})")


if __name__ == "__main__":
    main()
