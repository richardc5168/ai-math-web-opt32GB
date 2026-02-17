import json
import random
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP, getcontext
from fractions import Fraction
from math import gcd
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
OUT_JS = ROOT / "docs" / "g5-grand-slam" / "bank.js"

# Deterministic bank generation
random.seed(20260202)
getcontext().prec = 28


def _strip_trailing_zeros(s: str) -> str:
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def fmt_decimal(x: Decimal) -> str:
    return _strip_trailing_zeros(format(x, "f"))


def fmt_int(n: int) -> str:
    return f"{n:,}"


def fmt_frac(f: Fraction) -> str:
    f = Fraction(f.numerator, f.denominator)
    if f.denominator == 1:
        return str(f.numerator)
    return f"{f.numerator}/{f.denominator}"


def fmt_mixed(f: Fraction) -> str:
    f = Fraction(f.numerator, f.denominator)
    if f.denominator == 1:
        return str(f.numerator)

    n = f.numerator
    d = f.denominator
    sign = -1 if n < 0 else 1
    n = abs(n)

    whole = n // d
    rem = n % d
    if whole == 0:
        return fmt_frac(Fraction(sign * n, d))
    if rem == 0:
        return str(sign * whole)

    part = Fraction(rem, d)
    return f"{sign * whole} {part.numerator}/{part.denominator}"


def lcm(a: int, b: int) -> int:
    return a // gcd(a, b) * b


def q_base(
    *,
    qid: str,
    topic: str,
    kind: str,
    kind_title: str,
    difficulty: str,
    question: str,
    answer: str,
    answer_unit: str,
    hints: List[str],
    steps: List[str],
    explanation: str,
    unit: Optional[str] = None,
    text_type: Optional[str] = None,
    accept: Optional[List[str]] = None,
) -> Dict[str, Any]:
    meta: Dict[str, Any] = {"kind_title": kind_title}
    if unit:
        meta["unit"] = unit
    if text_type:
        meta["text_type"] = text_type
    if accept:
        meta["accept"] = accept

    return {
        "id": qid,
        "topic": topic,
        "kind": kind,
        "difficulty": difficulty,
        "question": question,
        "answer": answer,
        "answer_unit": answer_unit,
        "hints": hints,
        "steps": steps,
        "explanation": explanation,
        "meta": meta,
    }


def _hints(h1: str, h2: str, h3: str) -> List[str]:
    # Strict 3-stage child-guided hint format.
    return [
        "Hint 1｜觀念\n" + h1.strip(),
        "Hint 2｜列式/判斷\n" + h2.strip(),
        "Hint 3｜計算/解答\n" + h3.strip(),
    ]


# ------------------------------
# 1) 大數與位值
# ------------------------------

def gen_place_value(i: int) -> Dict[str, Any]:
    topic = "大數與位值"
    if i % 3 == 1:
        # truncate (floor) to a given place
        n = random.randint(12_345_678, 987_654_321)
        place_name, place = random.choice([
            ("萬位", 10_000),
            ("十萬位", 100_000),
            ("百萬位", 1_000_000),
            ("千萬位", 10_000_000),
        ])
        ans = (n // place) * place
        question = f"（概數｜無條件捨去）把 {fmt_int(n)} 無條件捨去到{place_name}，得到多少？（填整數）"
        hints = _hints(
            "無條件捨去＝直接把後面的位數全部變成 0（不進位）。",
            f"做法：先找 {place_name} 是 {place:,}，算 (原數 ÷ {place:,}) 取整數，再乘回 {place:,}。",
            f"1) {fmt_int(n)} ÷ {place:,} 取整數 = {n // place}\n2) {n // place} × {place:,} = {fmt_int(ans)}",
        )
        steps = [f"找到{place_name}，位值 = {place:,}", f"{fmt_int(n)} ÷ {place:,} 取整數 = {n // place}", f"{n // place} × {place:,} = {fmt_int(ans)}"]
        return q_base(
            qid=f"g5gs_pv_trunc_{i:03d}",
            topic=topic,
            kind="place_value_truncate",
            kind_title="概數：無條件捨去到指定位",
            difficulty="easy",
            question=question,
            answer=str(ans),
            answer_unit="number",
            hints=hints,
            steps=steps,
            explanation=f"無條件捨去到{place_name}：{fmt_int(ans)}。",
        )

    if i % 3 == 2:
        n = random.randint(100_000_000, 999_999_999)
        place_name, place = random.choice([
            ("千萬位", 10_000_000),
            ("百萬位", 1_000_000),
            ("十萬位", 100_000),
            ("萬位", 10_000),
            ("千位", 1_000),
        ])
        digit = (n // place) % 10
        question = f"（位值）在 {fmt_int(n)} 裡，{place_name}的數字是多少？（填 0~9）"
        hints = _hints(
            "每一位都有固定的位值（萬、十萬、百萬…），看那一位上的『數字』。",
            f"做法：先用整除把前面的位移掉，再用 %10 取出那一位。",
            f"1) {fmt_int(n)} ÷ {place:,} 取整數 = {n // place}\n2) 取個位：{n // place} % 10 = {digit}",
        )
        steps = [f"{place_name}對應位值 {place:,}", f"{fmt_int(n)} ÷ {place:,} = {n // place}", f"{n // place} % 10 = {digit}"]
        return q_base(
            qid=f"g5gs_pv_digit_{i:03d}",
            topic=topic,
            kind="place_value_digit",
            kind_title="位值：指定位置的數字",
            difficulty="easy",
            question=question,
            answer=str(digit),
            answer_unit="number",
            hints=hints,
            steps=steps,
            explanation=f"{place_name}的數字是 {digit}。",
        )

    # 億萬表示法 → 數字
    yi = random.randint(1, 9)
    wan = random.randint(0, 9999)
    rest = random.randint(0, 9999)
    n = yi * 100_000_000 + wan * 10_000 + rest
    question = f"（億萬表示）{yi} 億 {wan} 萬 {rest} 表示多少？（填整數）"
    hints = _hints(
        "1 億 = 100,000,000；1 萬 = 10,000。",
        f"列式：{yi}×100,000,000 + {wan}×10,000 + {rest}。",
        f"1) {yi}×100,000,000 = {fmt_int(yi*100_000_000)}\n2) {wan}×10,000 = {fmt_int(wan*10_000)}\n3) 相加得到 {fmt_int(n)}",
    )
    steps = [f"1億 = 100,000,000；1萬 = 10,000", f"{yi}×1億 = {fmt_int(yi*100_000_000)}，{wan}×1萬 = {fmt_int(wan*10_000)}", f"合計 {fmt_int(n)}"]
    return q_base(
        qid=f"g5gs_pv_yiwan_{i:03d}",
        topic=topic,
        kind="place_value_yi_wan",
        kind_title="億萬表示：換成整數",
        difficulty="medium",
        question=question,
        answer=str(n),
        answer_unit="number",
        hints=hints,
        steps=steps,
        explanation=f"{yi}億{wan}萬{rest} = {fmt_int(n)}。",
    )


# ------------------------------
# 2) 因數與倍數
# ------------------------------

def gen_factors(i: int) -> Dict[str, Any]:
    topic = "因數與倍數"

    if i % 3 == 1:
        # prime/composite
        n = random.choice([
            11, 13, 17, 19, 23, 29, 31, 37,
            21, 25, 27, 33, 35, 39, 49, 51,
        ])
        is_prime = n > 1 and all(n % d for d in range(2, int(n**0.5) + 1))
        ans = "質數" if is_prime else "合數"
        question = f"（質數/合數）{n} 是質數還是合數？（填：質數 或 合數）"
        test_divs = [2, 3, 5, 7]
        hints = _hints(
            "質數：只有 1 和自己兩個因數；合數：因數超過兩個。",
            "做法：試除 2、3、5、7…，只要能整除（且不是 1 和自己）就是合數。",
            "\n".join([
                f"1) 試除：{', '.join(map(str, test_divs))}",
                f"2) {'找不到可整除的數，所以是質數。' if is_prime else '找到可以整除的數，所以是合數。'}",
                f"3) 答案：{ans}",
            ]),
        )
        steps = [f"質數只有 1 和自己兩個因數", f"試除 2,3,5,7：{n} {'都不能被整除' if is_prime else '可被整除'}", f"結論：{n} 是{ans}"]
        return q_base(
            qid=f"g5gs_fac_prime_{i:03d}",
            topic=topic,
            kind="prime_or_composite",
            kind_title="質數與合數判斷",
            difficulty="easy",
            question=question,
            answer=ans,
            answer_unit="text",
            hints=hints,
            steps=steps,
            explanation=f"{n} 的判斷結果：{ans}。",
        )

    if i % 3 == 2:
        # gcd word problem
        a = random.choice([24, 30, 36, 42, 48, 54, 60, 72, 84, 90, 96])
        b = random.choice([18, 24, 28, 36, 40, 42, 56, 60, 63, 70, 84])
        g = gcd(a, b)
        question = f"（GCD 應用）有兩條緞帶長 {a} 公分和 {b} 公分，要剪成一樣長且不能有剩，最長可以剪成每段多少公分？"
        hints = _hints(
            "要剪成一樣長且不能有剩 → 找『最大公因數』。",
            f"列式：gcd({a},{b})。可以先列因數或用短除法。",
            f"1) 找 {a} 和 {b} 的共同因數\n2) 最大的那個就是答案\n3) gcd({a},{b}) = {g}（公分）",
        )
        steps = [f"最長且不剩 → 求 gcd({a},{b})", f"找 {a} 和 {b} 的共同因數", f"最大公因數 = {g} 公分"]
        return q_base(
            qid=f"g5gs_fac_gcd_{i:03d}",
            topic=topic,
            kind="gcd_word",
            kind_title="GCD：剪緞帶/分段最長",
            difficulty="medium",
            question=question,
            answer=str(g),
            answer_unit="number",
            hints=hints,
            steps=steps,
            explanation=f"最大公因數是 {g}。",
            unit="公分",
        )

    # lcm word problem
    a = random.choice([3, 4, 5, 6, 8, 9, 10, 12])
    b = random.choice([4, 5, 6, 7, 8, 9, 10, 12])
    while a == b:
        b = random.choice([4, 5, 6, 7, 8, 9, 10, 12])
    L = lcm(a, b)
    question = f"（LCM 應用）甲車每 {a} 分鐘來一次，乙車每 {b} 分鐘來一次。兩車同時來了以後，最少再過幾分鐘會再同時來？"
    hints = _hints(
        "同時再次發生 → 找『最小公倍數』。",
        f"列式：lcm({a},{b})。可用倍數列表或質因數分解。",
        f"1) 列出 {a} 的倍數與 {b} 的倍數\n2) 第一個相同的倍數就是最小公倍數\n3) lcm({a},{b}) = {L}（分鐘）",
    )
    steps = [f"再同時出現 → 求 lcm({a},{b})", f"列出 {a} 和 {b} 的倍數", f"最小公倍數 = {L} 分鐘"]
    return q_base(
        qid=f"g5gs_fac_lcm_{i:03d}",
        topic=topic,
        kind="lcm_word",
        kind_title="LCM：同時出現問題",
        difficulty="medium",
        question=question,
        answer=str(L),
        answer_unit="number",
        hints=hints,
        steps=steps,
        explanation=f"最少 {L} 分鐘後再同時來。",
        unit="分鐘",
    )


# ------------------------------
# 3) 分數加減
# ------------------------------

def _pick_den() -> int:
    return random.choice([4, 5, 6, 8, 10, 12])


def gen_frac_addsub(i: int) -> Dict[str, Any]:
    topic = "分數加減"
    if i % 2 == 1:
        d1 = _pick_den()
        d2 = _pick_den()
        while d2 == d1:
            d2 = _pick_den()
        a1 = random.randint(1, d1 - 1)
        a2 = random.randint(1, d2 - 1)
        f1 = Fraction(a1, d1)
        f2 = Fraction(a2, d2)
        s = f1 + f2
        ans = fmt_mixed(s)
        question = f"（異分母加法）計算：{a1}/{d1} + {a2}/{d2} = ？（可填最簡分數或帶分數）"
        L = lcm(d1, d2)
        n1 = a1 * (L // d1)
        n2 = a2 * (L // d2)
        hints = _hints(
            "異分母相加：先通分成同分母，再把分子相加。",
            f"先找最小公倍數：lcm({d1},{d2}) = {L}，把兩個分數通分到 {L}。",
            f"1) {a1}/{d1} = {n1}/{L}\n2) {a2}/{d2} = {n2}/{L}\n3) 相加：({n1}+{n2})/{L} = {fmt_frac(s)}\n4) 如需要可寫成帶分數：{ans}",
        )
        steps = [f"lcm({d1},{d2}) = {L}", f"通分：{a1}/{d1} = {n1}/{L}，{a2}/{d2} = {n2}/{L}", f"相加：({n1}+{n2})/{L} = {fmt_frac(s)}", f"化簡 → {ans}"]
        return q_base(
            qid=f"g5gs_fas_add_{i:03d}",
            topic=topic,
            kind="fraction_add_unlike",
            kind_title="分數加法：異分母通分",
            difficulty="medium",
            question=question,
            answer=ans,
            answer_unit="fraction",
            hints=hints,
            steps=steps,
            explanation=f"答案是 {ans}。",
        )

    # mixed subtraction
    w1 = random.randint(1, 4)
    w2 = random.randint(0, w1)
    d = _pick_den()
    a = random.randint(1, d - 1)
    b = random.randint(1, d - 1)
    f1 = Fraction(w1 * d + a, d)
    f2 = Fraction(w2 * d + b, d)
    if f2 > f1:
        f1, f2 = f2, f1
    diff = f1 - f2
    ans = fmt_mixed(diff)
    question = f"（帶分數減法）計算：{fmt_mixed(f1)} − {fmt_mixed(f2)} = ？（可填最簡分數或帶分數）"
    hints = _hints(
        "帶分數減法：可以先化成假分數，再通分/相減，最後化回帶分數。",
        "做法：帶分數 → 假分數（整數×分母+分子）。",
        "\n".join([
            f"1) 化成假分數：{fmt_mixed(f1)} = {fmt_frac(f1)}；{fmt_mixed(f2)} = {fmt_frac(f2)}",
            f"2) 同分母可直接相減：{fmt_frac(f1)} − {fmt_frac(f2)} = {fmt_frac(diff)}",
            f"3) 化回帶分數：{ans}",
        ]),
    )
    steps = [f"化假分數：{fmt_mixed(f1)} = {fmt_frac(f1)}，{fmt_mixed(f2)} = {fmt_frac(f2)}", f"相減：{fmt_frac(f1)} − {fmt_frac(f2)} = {fmt_frac(diff)}", f"化回帶分數 → {ans}"]
    return q_base(
        qid=f"g5gs_fas_sub_{i:03d}",
        topic=topic,
        kind="fraction_sub_mixed",
        kind_title="分數減法：帶分數/假分數",
        difficulty="medium",
        question=question,
        answer=ans,
        answer_unit="fraction",
        hints=hints,
        steps=steps,
        explanation=f"答案是 {ans}。",
    )


# ------------------------------
# 4) 平面圖形（面積）
# ------------------------------

def gen_plane_area(i: int) -> Dict[str, Any]:
    topic = "平面圖形"

    t = i % 4
    if t == 1:
        b = random.choice([8, 10, 12, 14, 16])
        h = random.choice([5, 6, 7, 8, 9])
        area = b * h // 2
        question = f"（三角形面積）底 {b} 公分，高 {h} 公分。面積是多少平方公分？"
        hints = _hints(
            "三角形面積 = 底×高÷2。",
            f"列式：{b}×{h}÷2。",
            f"1) {b}×{h} = {b*h}\n2) {b*h}÷2 = {area}\n3) 單位：平方公分",
        )
        steps = [f"三角形面積 = 底×高÷2", f"{b}×{h} = {b*h}，÷2 = {area}", f"面積 = {area} 平方公分"]
        return q_base(
            qid=f"g5gs_geo_tri_{i:03d}",
            topic=topic,
            kind="area_triangle",
            kind_title="面積：三角形",
            difficulty="easy",
            question=question,
            answer=str(area),
            answer_unit="number",
            hints=hints,
            steps=steps,
            explanation=f"面積 = {area} 平方公分。",
            unit="平方公分",
        )

    if t == 2:
        b = random.choice([9, 12, 15, 18])
        h = random.choice([4, 5, 6, 7, 8])
        area = b * h
        question = f"（平行四邊形面積）底 {b} 公分，高 {h} 公分。面積是多少平方公分？"
        hints = _hints(
            "平行四邊形面積 = 底×高。",
            f"列式：{b}×{h}。",
            f"1) {b}×{h} = {area}\n2) 單位：平方公分",
        )
        steps = [f"平行四邊形面積 = 底×高", f"{b}×{h} = {area}", f"面積 = {area} 平方公分"]
        return q_base(
            qid=f"g5gs_geo_para_{i:03d}",
            topic=topic,
            kind="area_parallelogram",
            kind_title="面積：平行四邊形",
            difficulty="easy",
            question=question,
            answer=str(area),
            answer_unit="number",
            hints=hints,
            steps=steps,
            explanation=f"面積 = {area} 平方公分。",
            unit="平方公分",
        )

    if t == 3:
        a = random.choice([6, 8, 10, 12])
        b = random.choice([10, 12, 14, 16, 18])
        h = random.choice([4, 5, 6, 7])
        area = (a + b) * h // 2
        question = f"（梯形面積）上底 {a} 公分，下底 {b} 公分，高 {h} 公分。面積是多少平方公分？"
        hints = _hints(
            "梯形面積 = (上底+下底)×高÷2。",
            f"列式：({a}+{b})×{h}÷2。",
            f"1) 上底+下底 = {a+b}\n2) {a+b}×{h} = {(a+b)*h}\n3) ÷2 得 {area}",
        )
        steps = [f"上底+下底 = {a}+{b} = {a+b}", f"{a+b}×{h} = {(a+b)*h}", f"÷2 = {area} 平方公分"]
        return q_base(
            qid=f"g5gs_geo_trap_{i:03d}",
            topic=topic,
            kind="area_trapezoid",
            kind_title="面積：梯形",
            difficulty="medium",
            question=question,
            answer=str(area),
            answer_unit="number",
            hints=hints,
            steps=steps,
            explanation=f"面積 = {area} 平方公分。",
            unit="平方公分",
        )

    # congruent split
    b = random.choice([10, 12, 14, 16])
    h = random.choice([5, 6, 7, 8])
    para = b * h
    tri = para // 2
    question = f"（全等拼貼）兩個全等三角形拼成一個平行四邊形，底 {b} 公分，高 {h} 公分。求其中一個三角形面積（平方公分）。"
    hints = _hints(
        "兩個全等三角形拼成平行四邊形 → 平行四邊形面積的一半就是一個三角形面積。",
        f"先算平行四邊形面積：{b}×{h}，再 ÷2。",
        f"1) 平行四邊形面積 = {b}×{h} = {para}\n2) 一個三角形 = {para}÷2 = {tri}",
    )
    steps = [f"平行四邊形面積 = {b}×{h} = {para}", f"一個三角形 = {para}÷2 = {tri}", f"面積 = {tri} 平方公分"]
    return q_base(
        qid=f"g5gs_geo_tile_{i:03d}",
        topic=topic,
        kind="area_congruent_tile",
        kind_title="面積：全等拼貼（對半）",
        difficulty="medium",
        question=question,
        answer=str(tri),
        answer_unit="number",
        hints=hints,
        steps=steps,
        explanation=f"一個三角形面積 = {tri} 平方公分。",
        unit="平方公分",
    )


# ------------------------------
# 5) 整數乘分數
# ------------------------------

def gen_int_times_frac(i: int) -> Dict[str, Any]:
    topic = "整數乘分數"
    if i % 2 == 1:
        n = random.choice([3, 4, 5, 6, 7, 8, 9, 10, 12])
        a = random.randint(1, 5)
        b = random.choice([6, 8, 10, 12])
        f = Fraction(a, b)
        prod = Fraction(n) * f
        ans = fmt_mixed(prod)
        question = f"（整數×分數）計算：{n} × {a}/{b} = ？（可填最簡分數或帶分數）"
        hints = _hints(
            "整數可以看成分母是 1 的分數：n = n/1，分數乘法分子乘分子、分母乘分母。",
            f"列式：{n}/1 × {a}/{b}，可以先約分再相乘。",
            f"1) {n}×{a} / (1×{b}) = {fmt_frac(prod)}\n2) 若是假分數可寫帶分數：{ans}",
        )
        steps = [f"整數寫成 {n}/1", f"{n}×{a} / (1×{b}) = {fmt_frac(prod)}", f"化簡 → {ans}"]
        return q_base(
            qid=f"g5gs_itf_mul_{i:03d}",
            topic=topic,
            kind="int_times_fraction",
            kind_title="整數×分數（可先約分）",
            difficulty="easy",
            question=question,
            answer=ans,
            answer_unit="fraction",
            hints=hints,
            steps=steps,
            explanation=f"答案是 {ans}。",
        )

    total = random.choice([600, 750, 900, 1200])
    a = random.choice([1, 2, 3])
    b = random.choice([4, 5, 6, 8, 10])
    used = Fraction(a, b)
    left = 1 - used
    left_amt = int(Fraction(total) * left)
    question = f"（剩餘量）一瓶有 {total} mL，喝掉 {a}/{b}，剩下多少 mL？（填整數）"
    hints = _hints(
        "先找『剩下的分數』：1 − 已喝的分數，再乘上總量。",
        f"列式：剩下 = {total}×(1 − {a}/{b})。",
        f"1) 剩下分數 = 1 − {a}/{b} = {fmt_frac(left)}\n2) 剩下量 = {total}×{fmt_frac(left)} = {left_amt}（mL）",
    )
    steps = [f"1 − {a}/{b} = {fmt_frac(left)}", f"{total}×{fmt_frac(left)} = {left_amt}", f"剩下 {left_amt} mL"]
    return q_base(
        qid=f"g5gs_itf_left_{i:03d}",
        topic=topic,
        kind="remaining_by_fraction",
        kind_title="剩餘量（1−分數）×總量",
        difficulty="medium",
        question=question,
        answer=str(left_amt),
        answer_unit="number",
        hints=hints,
        steps=steps,
        explanation=f"剩下 {left_amt} mL。",
        unit="mL",
    )


# ------------------------------
# 6) 扇形與圓心角 / 時鐘角
# ------------------------------

def gen_angles(i: int) -> Dict[str, Any]:
    topic = "扇形與圓心角"
    if i % 2 == 1:
        num = random.choice([1, 2, 3, 4, 5, 6, 7, 8, 9])
        den = random.choice([10, 12, 15, 20])
        frac = Fraction(num, den)
        deg = float(frac) * 360
        # Keep answers at .0 or .5
        deg = round(deg * 2) / 2
        deg_s = _strip_trailing_zeros(f"{deg:.1f}")
        question = f"（圓心角）一個扇形占整個圓的 {num}/{den}。圓心角是多少度？（可填小數）"
        hints = _hints(
            "整個圓是 360°；扇形占幾分之幾，就乘上 360°。",
            f"列式：360×{num}/{den}。",
            f"1) 360×{num} = {360*num}\n2) {360*num}÷{den} = {deg_s}\n3) 答案：{deg_s}°",
        )
        steps = [f"整圓 360°，扇形占 {num}/{den}", f"360×{num}÷{den} = {deg_s}", f"圓心角 = {deg_s}°"]
        return q_base(
            qid=f"g5gs_ang_sector_{i:03d}",
            topic=topic,
            kind="sector_central_angle",
            kind_title="扇形：圓心角計算",
            difficulty="easy",
            question=question,
            answer=deg_s,
            answer_unit="number",
            hints=hints,
            steps=steps,
            explanation=f"圓心角 = 360×{num}/{den} = {deg_s}°。",
            unit="°",
        )

    # clock angle (smaller)
    # Use quarter/half hours for friendliness
    hour = random.choice([1, 2, 3, 4, 5, 7, 8, 9, 10, 11])
    minute = random.choice([0, 15, 30, 45])
    # angles from 12 o'clock
    minute_angle = minute * 6
    hour_angle = (hour % 12) * 30 + minute * 0.5
    diff = abs(hour_angle - minute_angle)
    diff = min(diff, 360 - diff)
    diff_s = _strip_trailing_zeros(f"{diff:.1f}")
    question = f"（時鐘夾角）在 {hour}:{minute:02d}，時針和分針的『較小夾角』是多少度？（可填小數）"
    hints = _hints(
        "分針每分鐘走 6°；時針每分鐘走 0.5°。先算兩者角度，再取差的較小值。",
        "列式：分針角度=分鐘×6；時針角度=小時×30+分鐘×0.5；夾角=|差|，再取較小。",
        "\n".join([
            f"1) 分針角度 = {minute}×6 = {minute_angle}°",
            f"2) 時針角度 = {hour}×30 + {minute}×0.5 = {hour_angle}°",
            f"3) 差 = |{hour_angle} − {minute_angle}| = {abs(hour_angle-minute_angle)}°，較小夾角 = {diff_s}°",
        ]),
    )
    steps = [f"分針角度 = {minute}×6 = {minute_angle}°", f"時針角度 = {hour}×30+{minute}×0.5 = {hour_angle}°", f"較小夾角 = {diff_s}°"]
    return q_base(
        qid=f"g5gs_ang_clock_{i:03d}",
        topic=topic,
        kind="clock_angle",
        kind_title="時鐘：時針分針夾角",
        difficulty="hard",
        question=question,
        answer=diff_s,
        answer_unit="number",
        hints=hints,
        steps=steps,
        explanation=f"較小夾角 = {diff_s}°。",
        unit="°",
    )


# ------------------------------
# 7) 小數乘法
# ------------------------------

def gen_decimal_mul(i: int) -> Dict[str, Any]:
    topic = "小數乘法"
    if i % 2 == 1:
        a = Decimal(random.choice(["1.2", "2.5", "3.6", "4.08", "0.75", "12.5"]))
        b = Decimal(random.choice(["3", "4", "5", "6", "8"]))
        ans = (a * b).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        ans_s = fmt_decimal(ans)
        question = f"（小數×整數）計算：{fmt_decimal(a)} × {fmt_decimal(b)} = ？"
        hints = _hints(
            "小數乘法：先當作整數相乘，最後再把小數點放回（小數位數相加）。",
            f"判斷小數位：{fmt_decimal(a)} 有 {max(0, -a.as_tuple().exponent)} 位小數。",
            f"1) 先算乘法：{fmt_decimal(a)}×{fmt_decimal(b)} = {ans_s}\n2) 檢查：乘以 {fmt_decimal(b)}，答案應該比 {fmt_decimal(a)} 大（當 {fmt_decimal(b)} > 1）",
        )
        steps = [f"小數乘法：{fmt_decimal(a)}×{fmt_decimal(b)}", f"計算得 {ans_s}", f"檢查小數位數是否正確"]
        return q_base(
            qid=f"g5gs_dec_mul1_{i:03d}",
            topic=topic,
            kind="decimal_times_integer",
            kind_title="小數×整數（位數移動）",
            difficulty="easy",
            question=question,
            answer=ans_s,
            answer_unit="number",
            hints=hints,
            steps=steps,
            explanation=f"答案是 {ans_s}。",
        )

    a = Decimal(random.choice(["0.3", "0.6", "1.25", "2.4", "3.15", "4.08"]))
    b = Decimal(random.choice(["0.4", "0.5", "0.75", "1.2", "1.5"]))
    ans = (a * b).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    ans_s = fmt_decimal(ans)
    question = f"（小數×小數）計算：{fmt_decimal(a)} × {fmt_decimal(b)} = ？"
    hints = _hints(
        "小數×小數：先把小數點拿掉當整數乘，最後小數位數＝兩數小數位數相加。",
        "做法：計算前先估算：0.3×0.4 約等於 0.12（小於 1）。",
        f"1) 直接計算得到 {ans_s}\n2) 檢查：若兩個因數都 <1，答案也應該 <1（或至少變小）",
    )
    steps = [f"估算 {fmt_decimal(a)}×{fmt_decimal(b)} 的範圍", f"計算得 {ans_s}", f"確認小數點位置"]
    return q_base(
        qid=f"g5gs_dec_mul2_{i:03d}",
        topic=topic,
        kind="decimal_times_decimal",
        kind_title="小數×小數（小數位數相加）",
        difficulty="medium",
        question=question,
        answer=ans_s,
        answer_unit="number",
        hints=hints,
        steps=steps,
        explanation=f"答案是 {ans_s}。",
    )


# ------------------------------
# 8) 分數乘分數
# ------------------------------

def gen_frac_mul(i: int) -> Dict[str, Any]:
    topic = "分數乘分數"
    if i % 3 == 1:
        a1, b1 = random.randint(1, 7), random.choice([8, 9, 10, 12])
        a2, b2 = random.randint(1, 7), random.choice([8, 9, 10, 12])
        f1 = Fraction(a1, b1)
        f2 = Fraction(a2, b2)
        prod = f1 * f2
        ans = fmt_frac(prod)
        question = f"（分數乘法）計算：{a1}/{b1} × {a2}/{b2} = ？（填最簡分數）"
        hints = _hints(
            "分數乘法：分子乘分子、分母乘分母；可以先交叉約分讓計算更簡單。",
            "做法：先看能不能把一個分子的因數跟另一個分母約掉。",
            f"1) 相乘：({a1}×{a2})/({b1}×{b2})\n2) 約分後得到 {ans}",
        )
        steps = [f"先交叉約分", f"({a1}×{a2})/({b1}×{b2}) 約分得 {ans}", f"確認最簡"]
        return q_base(
            qid=f"g5gs_fm_mul_{i:03d}",
            topic=topic,
            kind="fraction_times_fraction",
            kind_title="分數×分數（交叉約分）",
            difficulty="medium",
            question=question,
            answer=ans,
            answer_unit="fraction",
            hints=hints,
            steps=steps,
            explanation=f"答案是 {ans}。",
        )

    if i % 3 == 2:
        a, b = random.randint(2, 9), random.randint(2, 9)
        while gcd(a, b) != 1:
            a, b = random.randint(2, 9), random.randint(2, 9)
        question = f"（倒數）{a}/{b} 的倒數是多少？（填最簡分數）"
        ans = f"{b}/{a}"
        hints = _hints(
            "倒數：把分子和分母交換，乘起來會等於 1。",
            f"列式：{a}/{b} × ( ? ) = 1，所以 ? = {b}/{a}。",
            f"1) 交換分子分母：{a}/{b} → {b}/{a}\n2) 檢查：{a}/{b}×{b}/{a}=1",
        )
        steps = [f"分子分母交換：{a}/{b} → {b}/{a}", f"檢查：{a}/{b}×{b}/{a} = 1"]
        return q_base(
            qid=f"g5gs_fm_rec_{i:03d}",
            topic=topic,
            kind="reciprocal",
            kind_title="倒數（分子分母交換）",
            difficulty="easy",
            question=question,
            answer=ans,
            answer_unit="fraction",
            hints=hints,
            steps=steps,
            explanation=f"倒數是 {ans}。",
        )

    # fraction of a fraction (application)
    den1 = random.choice([4, 5, 6, 8, 10, 12])
    den2 = random.choice([4, 5, 6, 8, 10, 12])
    num1 = random.randint(1, min(3, den1 - 1))
    num2 = random.randint(1, min(3, den2 - 1))
    f1 = Fraction(num1, den1)
    f2 = Fraction(num2, den2)
    # Guarantee integer: total is multiple of den1*den2.
    total = den1 * den2 * random.choice([2, 3, 4])
    part = Fraction(total) * f1 * f2
    if part.denominator != 1:
        raise RuntimeError("Expected integer result in fraction-of-fraction generator")
    ans_n = part.numerator
    question = f"（分數的分數）有 {total} 個，先取其中的 {fmt_frac(f1)}，再取取到的 {fmt_frac(f2)}。最後有多少個？（填整數）"
    hints = _hints(
        "『幾分之幾的幾分之幾』→ 用乘法。",
        f"列式：{total}×{fmt_frac(f1)}×{fmt_frac(f2)}。",
        f"1) 先算：{total}×{fmt_frac(f1)} = {int(Fraction(total) * f1)}\n2) 再乘 {fmt_frac(f2)} 得 {ans_n}",
    )
    steps = [f"『的』代表乘法", f"{total}×{fmt_frac(f1)}×{fmt_frac(f2)}", f"= {ans_n}"]
    return q_base(
        qid=f"g5gs_fm_of_{i:03d}",
        topic=topic,
        kind="fraction_of_fraction",
        kind_title="分數的分數（連乘）",
        difficulty="hard",
        question=question,
        answer=str(ans_n),
        answer_unit="number",
        hints=hints,
        steps=steps,
        explanation=f"最後有 {ans_n} 個。",
    )


# ------------------------------
# 9) 體積與容積
# ------------------------------

def gen_volume_capacity(i: int) -> Dict[str, Any]:
    topic = "體積與容積"
    if i % 3 == 1:
        # displacement in mL
        start = random.choice([120, 150, 180, 200, 250])
        diff = random.choice([30, 40, 50, 60, 75])
        end = start + diff
        question = f"（排水法）量筒裡原本有 {start} mL 的水，把石頭放入後變成 {end} mL。石頭的體積是多少？（填整數）"
        hints = _hints(
            "排水法：物體體積 = 水面上升的體積（差）。",
            f"列式：{end} − {start}。",
            f"1) 上升量 = {end} − {start} = {diff}\n2) 1 mL = 1 cm³，所以體積是 {diff} cm³",
        )
        steps = [f"{end} − {start} = {diff}", f"1 mL = 1 cm³，體積 = {diff} cm³"]
        return q_base(
            qid=f"g5gs_vol_disp_{i:03d}",
            topic=topic,
            kind="displacement",
            kind_title="排水法：終點−起點",
            difficulty="easy",
            question=question,
            answer=str(diff),
            answer_unit="number",
            hints=hints,
            steps=steps,
            explanation=f"體積 = {diff} cm³。",
            unit="cm³",
        )

    if i % 3 == 2:
        n = random.choice([150, 250, 400, 600, 1200])
        question = f"（單位換算）{n} cm³ 等於多少 mL？（填整數）"
        hints = _hints(
            "1 cm³ = 1 mL。",
            "所以數值不變，直接填同一個數。",
            f"{n} cm³ = {n} mL",
        )
        steps = [f"1 cm³ = 1 mL", f"{n} cm³ = {n} mL"]
        return q_base(
            qid=f"g5gs_vol_cm3ml_{i:03d}",
            topic=topic,
            kind="cm3_to_ml",
            kind_title="換算：cm³ ↔ mL",
            difficulty="easy",
            question=question,
            answer=str(n),
            answer_unit="number",
            hints=hints,
            steps=steps,
            explanation=f"{n} cm³ = {n} mL。",
            unit="mL",
        )

    # liter to ml
    liters = Decimal(random.choice(["0.8", "1.2", "1.5", "2.3", "3.6"]))
    ml = int((liters * 1000).to_integral_value(rounding=ROUND_HALF_UP))
    question = f"（單位換算）{fmt_decimal(liters)} L 等於多少 mL？（填整數）"
    hints = _hints(
        "1 L = 1000 mL。",
        f"列式：{fmt_decimal(liters)}×1000。",
        f"{fmt_decimal(liters)}×1000 = {ml}",
    )
    steps = [f"1 L = 1000 mL", f"{fmt_decimal(liters)}×1000 = {ml} mL"]
    return q_base(
        qid=f"g5gs_vol_lml_{i:03d}",
        topic=topic,
        kind="liter_to_ml",
        kind_title="換算：L → mL",
        difficulty="easy",
        question=question,
        answer=str(ml),
        answer_unit="number",
        hints=hints,
        steps=steps,
        explanation=f"{fmt_decimal(liters)} L = {ml} mL。",
        unit="mL",
    )


# ------------------------------
# 10) 時間計算
# ------------------------------

def _add_minutes(h: int, m: int, add: int) -> Tuple[int, int]:
    total = (h * 60 + m + add) % (24 * 60)
    return total // 60, total % 60


def gen_time(i: int) -> Dict[str, Any]:
    topic = "時間計算"

    if i % 3 == 1:
        h = random.choice([21, 22, 23])
        m = random.choice([0, 10, 15, 30, 45])
        add_h = random.choice([1, 2, 3, 4])
        add_m = random.choice([0, 15, 30, 45])
        add = add_h * 60 + add_m
        nh, nm = _add_minutes(h, m, add)
        ans = f"{nh:02d}:{nm:02d}"
        question = f"（跨日加法）現在是 {h:02d}:{m:02d}，再過 {add_h} 小時 {add_m} 分，會是幾點幾分？（用 HH:MM）"
        hints = _hints(
            "先把時間都換成『分鐘』來算，算完再換回 HH:MM。跨過 24 小時要回到 0。",
            f"列式：把 {h:02d}:{m:02d} 變成分鐘，再加上 {add} 分鐘。",
            f"1) 起始分鐘 = {h}×60+{m} = {h*60+m}\n2) 加上 {add} 得 {(h*60+m)+add}\n3) 換回 HH:MM（跨日取 24 小時內）→ {ans}",
        )
        steps = [f"{h:02d}:{m:02d} → {h*60+m} 分鐘", f"加 {add} 得 {(h*60+m)+add} 分鐘", f"換回 HH:MM → {ans}"]
        return q_base(
            qid=f"g5gs_time_add_{i:03d}",
            topic=topic,
            kind="time_add_cross_day",
            kind_title="跨日：時間加法",
            difficulty="medium",
            question=question,
            answer=ans,
            answer_unit="text",
            hints=hints,
            steps=steps,
            explanation=f"答案是 {ans}。",
            text_type="time_hhmm",
        )

    if i % 3 == 2:
        # subtraction
        h = random.choice([0, 1, 5, 6])
        m = random.choice([0, 10, 20, 30, 45])
        sub = random.choice([35, 45, 70, 95])
        nh, nm = _add_minutes(h, m, -sub)
        ans = f"{nh:02d}:{nm:02d}"
        question = f"（跨日減法）現在是 {h:02d}:{m:02d}，往前推 {sub} 分鐘，會是幾點幾分？（用 HH:MM）"
        hints = _hints(
            "時間減法也可以用『加上負的分鐘』來算。跨到前一天要回到 23:xx。",
            f"列式：把 {h:02d}:{m:02d} 變成分鐘，減去 {sub}。",
            f"1) 起始分鐘 = {h}×60+{m} = {h*60+m}\n2) 減去 {sub} 得 {(h*60+m)-sub}\n3) 換回 HH:MM（跨日前一天）→ {ans}",
        )
        steps = [f"{h:02d}:{m:02d} → {h*60+m} 分鐘", f"減 {sub} 得 {(h*60+m)-sub} 分鐘", f"換回 HH:MM → {ans}"]
        return q_base(
            qid=f"g5gs_time_sub_{i:03d}",
            topic=topic,
            kind="time_sub_cross_day",
            kind_title="跨日：時間減法",
            difficulty="medium",
            question=question,
            answer=ans,
            answer_unit="text",
            hints=hints,
            steps=steps,
            explanation=f"答案是 {ans}。",
            text_type="time_hhmm",
        )

    # time multiplication/div
    seg = random.choice([10, 12, 15, 20, 25])
    n = random.choice([4, 5, 6, 7, 8])
    total = seg * n
    question = f"（時間×整數）每段 {seg} 分鐘，做 {n} 段。總共幾分鐘？（填整數）"
    hints = _hints(
        "同樣長度的段數 × 每段時間 = 總時間。",
        f"列式：{seg}×{n}。",
        f"{seg}×{n} = {total}（分鐘）",
    )
    steps = [f"每段 {seg} 分鐘 × {n} 段", f"{seg}×{n} = {total} 分鐘"]
    return q_base(
        qid=f"g5gs_time_mul_{i:03d}",
        topic=topic,
        kind="time_multiply",
        kind_title="時間：每段×段數",
        difficulty="easy",
        question=question,
        answer=str(total),
        answer_unit="number",
        hints=hints,
        steps=steps,
        explanation=f"總共 {total} 分鐘。",
        unit="分鐘",
    )


# ------------------------------
# 11) 大單位換算
# ------------------------------

def gen_big_units(i: int) -> Dict[str, Any]:
    topic = "大單位換算"
    t = i % 3
    if t == 1:
        km2 = Decimal(random.choice(["0.8", "1.2", "2.5", "3.6"]))
        ha = int((km2 * 100).to_integral_value(rounding=ROUND_HALF_UP))
        question = f"（面積換算）{fmt_decimal(km2)} 平方公里 = 多少公頃？（填整數）"
        hints = _hints(
            "1 平方公里 = 100 公頃。",
            f"列式：{fmt_decimal(km2)}×100。",
            f"{fmt_decimal(km2)}×100 = {ha}（公頃）",
        )
        steps = [f"1 km² = 100 公頃", f"{fmt_decimal(km2)}×100 = {ha}", f"答案 {ha} 公頃"]
        return q_base(
            qid=f"g5gs_unit_km2ha_{i:03d}",
            topic=topic,
            kind="km2_to_ha",
            kind_title="平方公里 → 公頃",
            difficulty="easy",
            question=question,
            answer=str(ha),
            answer_unit="number",
            hints=hints,
            steps=steps,
            explanation=f"{fmt_decimal(km2)} km² = {ha} 公頃。",
            unit="公頃",
        )

    if t == 2:
        ha = random.choice([3, 5, 12, 18, 25, 40])
        m2 = ha * 10_000
        question = f"（面積換算）{ha} 公頃 = 多少平方公尺？（填整數）"
        hints = _hints(
            "1 公頃 = 10,000 平方公尺。",
            f"列式：{ha}×10,000。",
            f"{ha}×10,000 = {fmt_int(m2)}（平方公尺）",
        )
        steps = [f"1 公頃 = 10,000 m²", f"{ha}×10,000 = {fmt_int(m2)}", f"答案 {fmt_int(m2)} 平方公尺"]
        return q_base(
            qid=f"g5gs_unit_ha2m2_{i:03d}",
            topic=topic,
            kind="ha_to_m2",
            kind_title="公頃 → 平方公尺",
            difficulty="easy",
            question=question,
            answer=str(m2),
            answer_unit="number",
            hints=hints,
            steps=steps,
            explanation=f"{ha} 公頃 = {fmt_int(m2)} 平方公尺。",
            unit="平方公尺",
        )

    a = random.choice([15, 28, 60, 75, 120])
    m2 = a * 100
    question = f"（面積換算）{a} 公畝 = 多少平方公尺？（填整數）"
    hints = _hints(
        "1 公畝 = 100 平方公尺。",
        f"列式：{a}×100。",
        f"{a}×100 = {fmt_int(m2)}（平方公尺）",
    )
    steps = [f"1 公畝 = 100 m²", f"{a}×100 = {fmt_int(m2)} 平方公尺"]
    return q_base(
        qid=f"g5gs_unit_a2m2_{i:03d}",
        topic=topic,
        kind="are_to_m2",
        kind_title="公畝 → 平方公尺",
        difficulty="easy",
        question=question,
        answer=str(m2),
        answer_unit="number",
        hints=hints,
        steps=steps,
        explanation=f"{a} 公畝 = {fmt_int(m2)} 平方公尺。",
        unit="平方公尺",
    )


# ------------------------------
# 12) 比率與百分率（含 PPM）
# ------------------------------

def gen_ratio_percent(i: int) -> Dict[str, Any]:
    topic = "比率與百分率"

    if i % 4 == 1:
        price = random.choice([200, 300, 450, 600, 800, 1200])
        off = random.choice([10, 20, 25, 30, 40])
        pay = 100 - off
        final = price * pay // 100
        question = f"（打折）原價 {fmt_int(price)} 元，打 {pay}%（等於打 {pay/10:g} 折）。折後價是多少元？"
        hints = _hints(
            "打折後要付的比例叫『付款比例』，不是折扣比例。",
            f"列式：折後價 = 原價×{pay}% = {price}×{pay}/100。",
            f"1) 付款比例 = {pay}% = {pay}/100\n2) 折後價 = {price}×{pay}/100 = {final}（元）",
        )
        steps = [f"付款比例 = {pay}%", f"{price}×{pay}/100 = {final}", f"折後價 {final} 元"]
        return q_base(
            qid=f"g5gs_rp_disc_{i:03d}",
            topic=topic,
            kind="percent_discount",
            kind_title="百分率應用：打折",
            difficulty="easy",
            question=question,
            answer=str(final),
            answer_unit="number",
            hints=hints,
            steps=steps,
            explanation=f"折後價是 {final} 元。",
            unit="元",
        )

    if i % 4 == 2:
        base = random.choice([200, 250, 400, 500, 800])
        add = random.choice([1, 2, 3, 4])
        # 加三成 = +30%
        pct = add * 10
        new = base * (100 + pct) // 100
        question = f"（成數）原價 {base} 元，加{add}成（=加{pct}%）。新價格是多少元？"
        hints = _hints(
            "加幾成 = 加幾個 10%。例如加三成=加30%。",
            f"列式：新價 = 原價×(100+{pct})% = {base}×{100+pct}/100。",
            f"{base}×{100+pct}/100 = {new}（元）",
        )
        steps = [f"加{add}成 = 加{pct}%", f"{base}×{100+pct}/100 = {new}", f"新價 {new} 元"]
        return q_base(
            qid=f"g5gs_rp_cheng_{i:03d}",
            topic=topic,
            kind="cheng_increase",
            kind_title="成數：加幾成",
            difficulty="medium",
            question=question,
            answer=str(new),
            answer_unit="number",
            hints=hints,
            steps=steps,
            explanation=f"新價格是 {new} 元。",
            unit="元",
        )

    if i % 4 == 3:
        # ppm extension
        pct = random.choice([0.1, 0.2, 0.35, 0.5])  # percent
        ppm = int(pct * 10_000)
        pct_s = _strip_trailing_zeros(str(pct))
        question = f"（延伸｜PPM）把 {pct_s}% 換算成 ppm（百萬分點）是多少？（填整數）"
        hints = _hints(
            "1% = 10,000 ppm（因為 1% = 1/100，而 ppm = 1/1,000,000）。",
            f"列式：{pct_s}×10,000。",
            f"{pct_s}×10,000 = {ppm} ppm",
        )
        steps = [f"1% = 10,000 ppm", f"{pct_s}×10,000 = {ppm} ppm"]
        return q_base(
            qid=f"g5gs_rp_ppm_{i:03d}",
            topic=topic,
            kind="percent_to_ppm",
            kind_title="延伸：% → ppm",
            difficulty="hard",
            question=question,
            answer=str(ppm),
            answer_unit="number",
            hints=hints,
            steps=steps,
            explanation=f"{pct_s}% = {ppm} ppm。",
            unit="ppm",
        )

    # find percent
    whole = random.choice([40, 50, 80, 100, 120, 200])
    pct = random.choice([10, 15, 20, 25, 30, 40, 50, 60, 75])
    part = whole * pct // 100
    question = f"（百分率）全體 {whole} 人，其中 {part} 人參加。參加的人占全體的百分率是多少？（可填 25 或 25% 或 0.25）"
    hints = _hints(
        "百分率 = 部分 ÷ 全體，再乘 100%。",
        f"列式：{part}÷{whole}×100。",
        f"1) {part}/{whole} = {pct}/100\n2) 所以百分率 = {pct}%",
    )
    steps = [f"{part}÷{whole} = {pct}/100", f"百分率 = {pct}%"]
    return q_base(
        qid=f"g5gs_rp_findpct_{i:03d}",
        topic=topic,
        kind="find_percent",
        kind_title="百分率：已知部分/全體",
        difficulty="easy",
        question=question,
        answer=str(pct),
        answer_unit="percent",
        hints=hints,
        steps=steps,
        explanation=f"答案是 {pct}%。",
        unit="%",
    )


# ------------------------------
# 13) 表面積
# ------------------------------

def gen_surface_area(i: int) -> Dict[str, Any]:
    topic = "表面積"
    t = i % 3
    if t == 1:
        a = random.choice([3, 4, 5, 6, 7, 8])
        sa = 6 * a * a
        question = f"（正方體表面積）正方體邊長 {a} 公分，表面積是多少平方公分？"
        hints = _hints(
            "正方體有 6 個一樣的正方形面。",
            f"列式：表面積 = 6×a² = 6×{a}×{a}。",
            f"6×{a}×{a} = {sa}（平方公分）",
        )
        steps = [f"一個面 = {a}×{a} = {a*a}", f"6×{a*a} = {sa}", f"表面積 = {sa} 平方公分"]
        return q_base(
            qid=f"g5gs_sa_cube_{i:03d}",
            topic=topic,
            kind="surface_area_cube",
            kind_title="表面積：正方體 6a²",
            difficulty="easy",
            question=question,
            answer=str(sa),
            answer_unit="number",
            hints=hints,
            steps=steps,
            explanation=f"表面積是 {sa} 平方公分。",
            unit="平方公分",
        )

    if t == 2:
        l_ = random.choice([6, 8, 10, 12])
        w_ = random.choice([4, 5, 6, 7])
        h_ = random.choice([3, 4, 5, 6])
        sa = 2 * (l_ * w_ + l_ * h_ + w_ * h_)
        question = f"（長方體表面積）長 {l_}、寬 {w_}、高 {h_}（公分）。表面積是多少平方公分？"
        hints = _hints(
            "長方體有 3 對相同的面：lw、lh、wh。",
            f"列式：2×(lw+lh+wh) = 2×({l_}×{w_}+{l_}×{h_}+{w_}×{h_})。",
            f"1) lw={l_*w_}，lh={l_*h_}，wh={w_*h_}\n2) 相加={l_*w_ + l_*h_ + w_*h_}\n3) 乘 2 得 {sa}",
        )
        steps = [f"lw={l_*w_}，lh={l_*h_}，wh={w_*h_}", f"相加 = {l_*w_+l_*h_+w_*h_}", f"×2 = {sa} 平方公分"]
        return q_base(
            qid=f"g5gs_sa_rect_{i:03d}",
            topic=topic,
            kind="surface_area_rect_prism",
            kind_title="表面積：長方體 2(lw+lh+wh)",
            difficulty="medium",
            question=question,
            answer=str(sa),
            answer_unit="number",
            hints=hints,
            steps=steps,
            explanation=f"表面積是 {sa} 平方公分。",
            unit="平方公分",
        )

    # contact faces removed: 2 cubes glued
    a = random.choice([3, 4, 5, 6])
    sa_two = 2 * 6 * a * a
    contact = 2 * a * a
    sa = sa_two - contact
    question = f"（接觸面扣除）兩個邊長 {a} 公分的正方體黏在一起（接觸一個面）。黏好後的外表面積是多少平方公分？"
    hints = _hints(
        "兩個正方體原本各有 6 面，但黏在一起的那一面會變成內部，看不到，要扣掉兩個接觸面。",
        f"列式：外表面積 = 2×(6a²) − 2×(接觸面積 a²)。",
        f"1) 兩個正方體表面積 = {sa_two}\n2) 需扣掉接觸的 2 面：2×{a}×{a} = {contact}\n3) {sa_two} − {contact} = {sa}",
    )
    steps = [f"兩個正方體表面積 = {sa_two}", f"扣除 2 個接觸面 = {contact}", f"外表面積 = {sa_two}−{contact} = {sa}"]
    return q_base(
        qid=f"g5gs_sa_contact_{i:03d}",
        topic=topic,
        kind="surface_area_contact_removed",
        kind_title="表面積：接觸面扣除",
        difficulty="hard",
        question=question,
        answer=str(sa),
        answer_unit="number",
        hints=hints,
        steps=steps,
        explanation=f"外表面積是 {sa} 平方公分。",
        unit="平方公分",
    )


# ------------------------------
# 14) 線對稱
# ------------------------------

def gen_symmetry(i: int) -> Dict[str, Any]:
    topic = "線對稱"
    t = i % 3

    if t == 1:
        shape, axes = random.choice([
            ("正方形", 4),
            ("長方形（非正方形）", 2),
            ("等邊三角形", 3),
            ("等腰三角形（非等邊）", 1),
            ("圓形", 999),
        ])
        if axes == 999:
            question = "（對稱軸）圓形有幾條對稱軸？（填：無限多）"
            hints = _hints(
                "圓形任意一條通過圓心的直線都是對稱軸。",
                "所以對稱軸的條數沒有上限。",
                "答案：無限多",
            )
            steps = ["圓形的對稱軸是無限多", f"任意通過圓心的直線都是對稱軸"]
            return q_base(
                qid=f"g5gs_sym_axes_{i:03d}",
                topic=topic,
                kind="symmetry_axes",
                kind_title="對稱軸數量",
                difficulty="easy",
                question=question,
                answer="無限多",
                answer_unit="text",
                hints=hints,
                steps=steps,
                explanation="圓形的對稱軸是無限多。",
                accept=["無限多", "無限"],
            )

        question = f"（對稱軸）{shape} 有幾條對稱軸？（填整數）"
        hints = _hints(
            "對稱軸是把圖形對折後兩邊完全重合的直線。",
            "想像『對折』：能對折成功的方向就是對稱軸。",
            f"{shape} 的對稱軸共有 {axes} 條",
        )
        steps = [f"想像{shape}對折方向", f"能完全重合的直線有 {axes} 條"]
        return q_base(
            qid=f"g5gs_sym_axes_{i:03d}",
            topic=topic,
            kind="symmetry_axes",
            kind_title="對稱軸數量",
            difficulty="easy",
            question=question,
            answer=str(axes),
            answer_unit="number",
            hints=hints,
            steps=steps,
            explanation=f"{shape} 的對稱軸是 {axes} 條。",
        )

    letters = ["A", "B", "C", "D", "E", "F"]
    a, b = random.sample(letters, 2)
    p = random.choice(["P", "Q", "R"])

    if t == 2:
        question = f"（垂直平分線）判斷：線段 {a}{b} 的垂直平分線上任意一點 {p}，與 {a}、{b} 的距離關係是？（填：{p}{a}={p}{b}）"
        hints = _hints(
            "垂直平分線的性質：線上的點到兩端點距離相等。",
            f"所以 {p} 到 {a} 的距離 = {p} 到 {b} 的距離。",
            f"答案：{p}{a}={p}{b}",
        )
        steps = [f"垂直平分線上的點到兩端距離相等", f"{p}{a} = {p}{b}"]
        return q_base(
            qid=f"g5gs_sym_bis_{i:03d}",
            topic=topic,
            kind="perp_bisector_property",
            kind_title="垂直平分線性質：距離相等",
            difficulty="medium",
            question=question,
            answer=f"{p}{a}={p}{b}",
            answer_unit="text",
            hints=hints,
            steps=steps,
            explanation=f"垂直平分線上任意點到兩端點距離相等：{p}{a}={p}{b}。",
            accept=[f"{p}{a}={p}{b}", f"{p}{a} = {p}{b}"],
        )

    question = f"（垂直平分線）判斷：如果一點 {p} 到 {a}、{b} 的距離相等（{p}{a}={p}{b}），那麼 {p} 一定在 {a}{b} 的垂直平分線上嗎？（填：是 或 否）"
    hints = _hints(
        "反過來也成立：到兩端點距離相等的點，會落在垂直平分線上。",
        f"看到 {p}{a}={p}{b}，就想到『垂直平分線』。",
        "答案：是",
    )
    steps = [f"看到 {p}{a}={p}{b}，距離相等", f"聯想到垂直平分線", "答案：是"]
    return q_base(
        qid=f"g5gs_sym_bis2_{i:03d}",
        topic=topic,
        kind="perp_bisector_converse",
        kind_title="垂直平分線：距離相等的反推",
        difficulty="hard",
        question=question,
        answer="是",
        answer_unit="text",
        hints=hints,
        steps=steps,
        explanation=f"因為到 {a}、{b} 距離相等的點都在 {a}{b} 的垂直平分線上，所以答案是『是』。",
        accept=["是", "對"],
    )


# ------------------------------
# 15) 代數前導
# ------------------------------

def gen_algebra(i: int) -> Dict[str, Any]:
    topic = "代數前導"
    t = i % 3
    if t == 1:
        x = random.randint(8, 40)
        a = random.choice([5, 7, 9, 12, 15])
        b = x + a
        question = f"（等量公理）解方程：x + {a} = {b}，x = ？"
        hints = _hints(
            "等量公理：等式兩邊做同樣的事，等式仍成立。",
            f"把 +{a} 移到右邊：兩邊都減 {a}。",
            f"1) x + {a} = {b}\n2) 兩邊都 −{a}：x = {b} − {a} = {x}",
        )
        steps = [f"兩邊同減 {a}", f"x = {b} − {a}", f"x = {x}"]
        return q_base(
            qid=f"g5gs_alg_add_{i:03d}",
            topic=topic,
            kind="solve_x_plus_a",
            kind_title="解方程：x + a = b",
            difficulty="easy",
            question=question,
            answer=str(x),
            answer_unit="number",
            hints=hints,
            steps=steps,
            explanation=f"x = {x}。",
        )

    if t == 2:
        x = random.randint(4, 18)
        a = random.choice([2, 3, 4, 5, 6])
        b = a * x
        question = f"（等量公理）解方程：{a}x = {b}，x = ？"
        hints = _hints(
            "把 x 單獨留下：等式兩邊同除以係數。",
            f"兩邊都 ÷{a}。",
            f"{a}x = {b} ⇒ x = {b}÷{a} = {x}",
        )
        steps = [f"係數是 {a}", f"兩邊同除以 {a}", f"x = {b}÷{a} = {x}"]
        return q_base(
            qid=f"g5gs_alg_mul_{i:03d}",
            topic=topic,
            kind="solve_ax",
            kind_title="解方程：ax = b",
            difficulty="medium",
            question=question,
            answer=str(x),
            answer_unit="number",
            hints=hints,
            steps=steps,
            explanation=f"x = {x}。",
        )

    x = random.randint(3, 20)
    d = random.choice([2, 3, 4, 5])
    b = x
    a = x * d
    question = f"（等量公理）解方程：x ÷ {d} = {b}，x = ？"
    hints = _hints(
        "除法可以用乘法反做：要消掉 ÷d，就兩邊都 ×d。",
        f"兩邊都 ×{d}。",
        f"x ÷ {d} = {b} ⇒ x = {b}×{d} = {a}",
    )
    steps = [f"消掉 ÷{d}，兩邊同乘 {d}", f"x = {b}×{d}", f"x = {a}"]
    return q_base(
        qid=f"g5gs_alg_div_{i:03d}",
        topic=topic,
        kind="solve_x_div_d",
        kind_title="解方程：x ÷ d = b",
        difficulty="medium",
        question=question,
        answer=str(a),
        answer_unit="number",
        hints=hints,
        steps=steps,
        explanation=f"x = {a}。",
    )


# ------------------------------
# 16) 折線圖（用表格表示）
# ------------------------------

def gen_line_graph(i: int) -> Dict[str, Any]:
    topic = "折線圖"

    months = ["1月", "2月", "3月", "4月", "5月", "6月"]
    base = random.randint(12, 30)
    vals = [base]
    for _ in range(5):
        vals.append(vals[-1] + random.choice([-3, -2, -1, 1, 2, 3]))

    # pick question type
    t = i % 3
    if t == 1:
        a = random.randint(0, 4)
        m1, m2 = months[a], months[a + 1]
        v1, v2 = vals[a], vals[a + 1]
        ans = "上升" if v2 > v1 else "下降" if v2 < v1 else "不變"
        question = (
            "（折線圖判讀）以下是某地溫度（°C）的折線圖資料（用表格表示）：\n"
            + "\n".join([f"{months[j]}：{vals[j]}" for j in range(6)])
            + f"\n請判斷：從 {m1} 到 {m2} 的趨勢是？（填：上升/下降/不變）"
        )
        hints = _hints(
            "折線圖看『趨勢』：比較兩個時間點的數值大小。",
            f"比較 {m1} 的 {v1} 和 {m2} 的 {v2}。",
            f"{v2} {'>' if v2>v1 else '<' if v2<v1 else '='} {v1}，所以是「{ans}」。",
        )
        steps = [f"{m1} = {v1}，{m2} = {v2}", f"{v2} {'>' if v2>v1 else '<' if v2<v1 else '='} {v1}", f"趨勢：{ans}"]
        accept = [ans]
        if ans == "上升":
            accept = ["上升", "上漲", "變高"]
        elif ans == "下降":
            accept = ["下降", "下跌", "變低"]
        elif ans == "不變":
            accept = ["不變", "一樣"]
        return q_base(
            qid=f"g5gs_line_trend_{i:03d}",
            topic=topic,
            kind="line_trend",
            kind_title="折線圖：趨勢判斷",
            difficulty="easy",
            question=question,
            answer=ans,
            answer_unit="text",
            hints=hints,
            steps=steps,
            explanation=f"{m1}→{m2} 是 {ans}。",
            accept=accept,
        )

    if t == 2:
        mx = max(vals)
        idx = vals.index(mx)
        ans = months[idx]
        question = (
            "（折線圖判讀）以下是某店每月銷量（箱）的資料：\n"
            + "\n".join([f"{months[j]}：{vals[j]}" for j in range(6)])
            + "\n請問：哪一個月份的銷量最高？（填：例如 3月）"
        )
        hints = _hints(
            "找最高值：把 6 個月份的數字比一比，最大的就是最高。",
            "可以先圈出看起來最大的那個數，再確認其他都比它小。",
            f"最大值是 {mx}，出現在 {ans}，所以答案是 {ans}。",
        )
        steps = [f"找最大值 {mx}", f"出現在 {ans}", f"答案：{ans}"]
        return q_base(
            qid=f"g5gs_line_max_{i:03d}",
            topic=topic,
            kind="line_max_month",
            kind_title="折線圖：最高點月份",
            difficulty="medium",
            question=question,
            answer=ans,
            answer_unit="text",
            hints=hints,
            steps=steps,
            explanation=f"最高的是 {ans}（{mx}）。",
        )

    # omit symbol / skipped month value (simple)
    # Provide a sequence and ask missing if trend is arithmetic
    m = random.choice(["3月", "4月", "5月"])
    idx = months.index(m)
    d = random.choice([2, 3])
    seq = [10, 10 + d, 10 + 2 * d, 10 + 3 * d]
    missing = seq[2]
    question = (
        "（折線圖省略符號）折線圖有時會用省略符號表示數字規律。\n"
        f"如果某項數值依序是：{seq[0]}、{seq[1]}、□、{seq[3]}（每次都增加同樣的數），請問 □ 是多少？"
    )
    hints = _hints(
        "等差規律：每次增加同樣的數。",
        f"先算公差：{seq[1]} − {seq[0]} = {d}。",
        f"下一個就再加 {d}：{seq[1]} + {d} = {missing}",
    )
    steps = [f"公差 = {seq[1]}−{seq[0]} = {d}", f"{seq[1]}+{d} = {missing}"]
    return q_base(
        qid=f"g5gs_line_omit_{i:03d}",
        topic=topic,
        kind="line_omit_rule",
        kind_title="折線圖：省略符號/規律補值",
        difficulty="hard",
        question=question,
        answer=str(missing),
        answer_unit="number",
        hints=hints,
        steps=steps,
        explanation=f"每次 +{d}，所以 □ = {missing}。",
    )


@dataclass
class TopicSpec:
    key: str
    title: str
    target: int
    gen: Callable[[int], Dict[str, Any]]


TOPICS: List[TopicSpec] = [
    TopicSpec("pv", "大數與位值", 12, gen_place_value),
    TopicSpec("fac", "因數與倍數", 12, gen_factors),
    TopicSpec("fas", "分數加減", 12, gen_frac_addsub),
    TopicSpec("geo", "平面圖形", 12, gen_plane_area),
    TopicSpec("itf", "整數乘分數", 12, gen_int_times_frac),
    TopicSpec("ang", "扇形與圓心角", 11, gen_angles),
    TopicSpec("dec", "小數乘法", 12, gen_decimal_mul),
    TopicSpec("fm", "分數乘分數", 12, gen_frac_mul),
    TopicSpec("vol", "體積與容積", 12, gen_volume_capacity),
    TopicSpec("time", "時間計算", 12, gen_time),
    TopicSpec("unit", "大單位換算", 12, gen_big_units),
    TopicSpec("rp", "比率與百分率", 12, gen_ratio_percent),
    TopicSpec("sa", "表面積", 11, gen_surface_area),
    TopicSpec("sym", "線對稱", 12, gen_symmetry),
    TopicSpec("alg", "代數前導", 11, gen_algebra),
    TopicSpec("line", "折線圖", 11, gen_line_graph),
]


def _build_topic(spec: TopicSpec) -> List[Dict[str, Any]]:
    uniq: List[Dict[str, Any]] = []
    seen = set()
    i = 1
    guard = 0
    while len(uniq) < spec.target:
        q = spec.gen(i)
        i += 1
        guard += 1
        if guard > spec.target * 80:
            raise RuntimeError(f"Unable to reach target for {spec.title}")
        t = q.get("question")
        if t in seen:
            continue
        seen.add(t)
        uniq.append(q)
    return uniq


def generate_bank() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for spec in TOPICS:
        out.extend(_build_topic(spec))

    # Final sanity: exact 188
    if len(out) != 188:
        raise RuntimeError(f"Expected 188 questions, got {len(out)}")

    random.shuffle(out)
    return out


def main() -> None:
    bank = generate_bank()

    js = (
        "/* Auto-generated offline question bank. */\n"
        + "window.G5_GRAND_SLAM_BANK = "
        + json.dumps(bank, ensure_ascii=False, indent=2)
        + ";\n"
    )

    OUT_JS.parent.mkdir(parents=True, exist_ok=True)
    OUT_JS.write_text(js, encoding="utf-8")
    print(f"Wrote: {OUT_JS} (n={len(bank)})")


if __name__ == "__main__":
    main()
