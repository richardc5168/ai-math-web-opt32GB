import json
import random
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
OUT_JS = ROOT / "docs" / "fraction-g5" / "bank.js"

random.seed(20260201)


def fmt_frac(f: Fraction) -> str:
    if f.denominator == 1:
        return str(f.numerator)
    return f"{f.numerator}/{f.denominator}"


def fmt_mixed(f: Fraction) -> str:
    # Always return simplest (Fraction already reduced)
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


def make_reducible_fraction(max_den: int = 24) -> Tuple[Fraction, Tuple[int, int]]:
    """Return a fraction that is reducible, plus (n,d) original."""
    d0 = random.choice([6, 8, 9, 10, 12, 14, 15, 16, 18, 20, 21, 24])
    k = random.choice([2, 3, 4])
    d = d0
    n = random.randint(2, d - 1)

    g = random.choice([2, 3, 4, 5, 6])
    # Ensure reducible by multiplying
    n2 = n * g
    d2 = d * g
    # Keep size reasonable
    if d2 > max_den * 6:
        g = 2
        n2 = n * g
        d2 = d * g

    return Fraction(n2, d2), (n2, d2)


def lcm(a: int, b: int) -> int:
    from math import gcd

    return a // gcd(a, b) * b


def gen_simplify(i: int) -> Dict[str, Any]:
    f, (n0, d0) = make_reducible_fraction()
    ans = f
    question = f"（約分）把分數化成最簡分數：{n0}/{d0}"

    hints = [
        "觀念：分子分母同除以『最大公因數』，分數大小不變。",
        "做法：先找分子分母的公因數（先試 2、3、5…），能一直除就一直除到不能再除。",
        "Level 3｜完整步驟\n1) 找最大公因數 g\n2) 分子÷g、分母÷g\n3) 檢查：新的分子分母沒有公因數（最簡分數）",
    ]

    steps = [f"gcd({n0},{d0}) = {n0 // f.numerator}", f"分子分母同除以 {n0 // f.numerator}", f"= {fmt_frac(ans)}"]

    return {
        "id": f"fg5_simplify_{i:03d}",
        "kind": "simplify",
        "topic": "國小五年級｜分數（計算）",
        "difficulty": "easy",
        "question": question,
        "answer": fmt_frac(ans),
        "hints": hints,
        "steps": steps,
        "explanation": f"{n0}/{d0} 的最簡分數是 {fmt_frac(ans)}。",
    }


def gen_equivalent(i: int) -> Dict[str, Any]:
    base = Fraction(random.randint(1, 4), random.randint(2, 9))
    base = base.limit_denominator(12)
    k = random.choice([2, 3, 4, 5])

    if random.random() < 0.5:
        # missing numerator
        den = base.denominator * k
        num = base.numerator * k
        question = f"（等值分數）填空：□/{den} = {base.numerator}/{base.denominator}"
        ans = Fraction(num, den)
        answer = str(num)
        explain = f"同乘 {k}：{base.numerator}/{base.denominator} = {num}/{den}，所以 □ = {num}。"
    else:
        # missing denominator
        den = base.denominator * k
        num = base.numerator * k
        question = f"（等值分數）填空：{num}/□ = {base.numerator}/{base.denominator}"
        answer = str(den)
        explain = f"同乘 {k}：{base.numerator}/{base.denominator} = {num}/{den}，所以 □ = {den}。"

    hints = [
        "觀念：等值分數＝分子分母同乘（或同除）同一個數。",
        "列式：把右邊分數的分子分母都乘上同一個 k，去對齊左邊已知的那一邊。",
        "Level 3｜完整步驟\n1) 先看分母（或分子）放大了幾倍\n2) 分子（或分母）也要放大同樣倍數\n3) 填入空格",
    ]

    steps = [f"放大倍數 k = {k}", f"分子分母同乘 {k}", f"□ = {answer}"]

    return {
        "id": f"fg5_equiv_{i:03d}",
        "kind": "equivalent",
        "topic": "國小五年級｜分數（計算）",
        "difficulty": "easy",
        "question": question,
        "answer": answer,
        "hints": hints,
        "steps": steps,
        "explanation": explain,
    }


def gen_add_like(i: int) -> Dict[str, Any]:
    d = random.choice([4, 5, 6, 8, 9, 10, 12])
    a_num = random.randint(1, d - 1)
    b_num = random.randint(1, d - 1)
    ans = Fraction(a_num, d) + Fraction(b_num, d)
    question = f"（同分母加法）計算：{a_num}/{d} + {b_num}/{d} = ?"

    hints = [
        "觀念：同分母加法，分母不變，分子相加。",
        f"列式：({a_num}+{b_num})/{d}，最後記得約分。",
        "Level 3｜完整步驟\n1) 分母一樣 → 分母不變\n2) 分子相加\n3) 約分成最簡分數",
    ]

    steps = [f"分母 {d} 不變", f"分子 {a_num}+{b_num} = {a_num+b_num}", f"約分 → {fmt_frac(ans)}"]

    return {
        "id": f"fg5_add_like_{i:03d}",
        "kind": "add_like",
        "topic": "國小五年級｜分數（計算）",
        "difficulty": "easy",
        "question": question,
        "answer": fmt_frac(ans),
        "hints": hints,
        "steps": steps,
        "explanation": f"同分母：{a_num}/{d} + {b_num}/{d} = {(a_num + b_num)}/{d}，約分後 = {fmt_frac(ans)}。",
    }


def gen_sub_like(i: int) -> Dict[str, Any]:
    d = random.choice([4, 5, 6, 8, 9, 10, 12])
    a_num = random.randint(2, d - 1)
    b_num = random.randint(1, a_num - 1)
    ans = Fraction(a_num, d) - Fraction(b_num, d)
    question = f"（同分母減法）計算：{a_num}/{d} - {b_num}/{d} = ?"

    hints = [
        "觀念：同分母減法，分母不變，分子相減。",
        f"列式：({a_num}-{b_num})/{d}，最後記得約分。",
        "Level 3｜完整步驟\n1) 分母一樣 → 分母不變\n2) 分子相減\n3) 約分成最簡分數",
    ]

    steps = [f"分母 {d} 不變", f"分子 {a_num}−{b_num} = {a_num-b_num}", f"約分 → {fmt_frac(ans)}"]

    return {
        "id": f"fg5_sub_like_{i:03d}",
        "kind": "sub_like",
        "topic": "國小五年級｜分數（計算）",
        "difficulty": "easy",
        "question": question,
        "answer": fmt_frac(ans),
        "hints": hints,
        "steps": steps,
        "explanation": f"同分母：{a_num}/{d} - {b_num}/{d} = {(a_num - b_num)}/{d}，約分後 = {fmt_frac(ans)}。",
    }


def gen_add_unlike(i: int) -> Dict[str, Any]:
    d1 = random.choice([2, 3, 4, 5, 6, 8, 9, 10, 12])
    d2 = random.choice([2, 3, 4, 5, 6, 8, 9, 10, 12])
    while d2 == d1:
        d2 = random.choice([2, 3, 4, 5, 6, 8, 9, 10, 12])

    a = Fraction(random.randint(1, d1 - 1), d1)
    b = Fraction(random.randint(1, d2 - 1), d2)

    L = lcm(d1, d2)
    a2 = Fraction(a.numerator * (L // d1), L)
    b2 = Fraction(b.numerator * (L // d2), L)
    ans = a + b

    question = f"（異分母加法）計算：{fmt_frac(a)} + {fmt_frac(b)} = ?"

    hints = [
        "觀念：異分母加法要先通分（同分母）才能加。",
        f"列式：先找分母 {d1} 和 {d2} 的最小公倍數 L，改寫成 /L 再相加。",
        "Level 3｜完整步驟\n1) 找最小公倍數 L\n2) 兩個分數都通分成 /L\n3) 同分母加法：分子相加\n4) 最後約分",
    ]

    steps = [f"lcm({d1},{d2}) = {L}", f"通分：{fmt_frac(a)} = {fmt_frac(a2)}，{fmt_frac(b)} = {fmt_frac(b2)}", f"分子相加：{a2.numerator}+{b2.numerator} = {a2.numerator+b2.numerator}", f"約分 → {fmt_frac(ans)}"]

    return {
        "id": f"fg5_add_unlike_{i:03d}",
        "kind": "add_unlike",
        "topic": "國小五年級｜分數（計算）",
        "difficulty": "medium",
        "question": question,
        "answer": fmt_frac(ans),
        "hints": hints,
        "steps": steps,
        "explanation": f"通分：{fmt_frac(a)} = {fmt_frac(a2)}，{fmt_frac(b)} = {fmt_frac(b2)}；相加 = {fmt_frac(a2)}+{fmt_frac(b2)} = {fmt_frac(a2+b2)}，約分後 = {fmt_frac(ans)}。",
    }


def gen_sub_unlike(i: int) -> Dict[str, Any]:
    d1 = random.choice([2, 3, 4, 5, 6, 8, 9, 10, 12])
    d2 = random.choice([2, 3, 4, 5, 6, 8, 9, 10, 12])
    while d2 == d1:
        d2 = random.choice([2, 3, 4, 5, 6, 8, 9, 10, 12])

    a = Fraction(random.randint(1, d1 - 1), d1)
    b = Fraction(random.randint(1, d2 - 1), d2)
    if a < b:
        a, b = b, a
        d1, d2 = a.denominator, b.denominator

    L = lcm(a.denominator, b.denominator)
    a2 = Fraction(a.numerator * (L // a.denominator), L)
    b2 = Fraction(b.numerator * (L // b.denominator), L)
    ans = a - b

    question = f"（異分母減法）計算：{fmt_frac(a)} - {fmt_frac(b)} = ?"

    hints = [
        "觀念：異分母減法要先通分（同分母）才能減。",
        "列式：先找分母的最小公倍數 L，改寫成同分母後分子相減。",
        "Level 3｜完整步驟\n1) 找最小公倍數 L\n2) 通分成 /L\n3) 分子相減\n4) 約分",
    ]

    steps = [f"lcm({a.denominator},{b.denominator}) = {L}", f"通分：{fmt_frac(a)} = {fmt_frac(a2)}，{fmt_frac(b)} = {fmt_frac(b2)}", f"分子相減：{a2.numerator}−{b2.numerator} = {a2.numerator-b2.numerator}", f"約分 → {fmt_frac(ans)}"]

    return {
        "id": f"fg5_sub_unlike_{i:03d}",
        "kind": "sub_unlike",
        "topic": "國小五年級｜分數（計算）",
        "difficulty": "medium",
        "question": question,
        "answer": fmt_frac(ans),
        "hints": hints,
        "steps": steps,
        "explanation": f"通分：{fmt_frac(a)} = {fmt_frac(a2)}，{fmt_frac(b)} = {fmt_frac(b2)}；相減 = {fmt_frac(a2)}-{fmt_frac(b2)} = {fmt_frac(a2-b2)}，約分後 = {fmt_frac(ans)}。",
    }


def gen_mul(i: int) -> Dict[str, Any]:
    d1 = random.choice([2, 3, 4, 5, 6, 8, 9, 10, 12])
    d2 = random.choice([2, 3, 4, 5, 6, 8, 9, 10, 12])
    a = Fraction(random.randint(1, d1 - 1), d1)
    b = Fraction(random.randint(1, d2 - 1), d2)
    ans = a * b

    question = f"（分數乘法）計算：{fmt_frac(a)} × {fmt_frac(b)} = ?"

    hints = [
        "觀念：分數乘分數＝分子乘分子、分母乘分母。",
        "技巧：能先交叉約分就先約分，算起來更快更不容易錯。",
        "Level 3｜完整步驟\n1) 先看能不能交叉約分\n2) 分子×分子、分母×分母\n3) 約分成最簡分數",
    ]

    steps = [f"先交叉約分", f"{a.numerator}×{b.numerator} / {a.denominator}×{b.denominator}", f"= {fmt_frac(ans)}"]

    return {
        "id": f"fg5_mul_{i:03d}",
        "kind": "mul",
        "topic": "國小五年級｜分數（計算）",
        "difficulty": "medium",
        "question": question,
        "answer": fmt_frac(ans),
        "hints": hints,
        "steps": steps,
        "explanation": f"{fmt_frac(a)}×{fmt_frac(b)} = {a.numerator}×{b.numerator}/{a.denominator}×{b.denominator} = {fmt_frac(ans)}（已最簡）。",
    }


def gen_mul_int(i: int) -> Dict[str, Any]:
    d = random.choice([2, 3, 4, 5, 6, 8, 9, 10, 12])
    a = Fraction(random.randint(1, d - 1), d)
    k = random.randint(2, 9)
    ans = a * k

    question = f"（分數×整數）計算：{fmt_frac(a)} × {k} = ?"

    hints = [
        "觀念：分數×整數＝分數×(整數/1)。",
        "做法：把整數當作 /1，再分子分母相乘；能先約分更快。",
        "Level 3｜完整步驟\n1) 把整數寫成 k/1\n2) 能交叉約分就先約分\n3) 分子相乘、分母相乘\n4) 約分",
    ]

    steps = [f"{k} = {k}/1", f"{fmt_frac(a)} × {k}/1 = {a.numerator*k}/{a.denominator}", f"約分 → {fmt_frac(ans)}"]

    return {
        "id": f"fg5_mul_int_{i:03d}",
        "kind": "mul_int",
        "topic": "國小五年級｜分數（計算）",
        "difficulty": "easy",
        "question": question,
        "answer": fmt_frac(ans),
        "hints": hints,
        "steps": steps,
        "explanation": f"把 {k} 看成 {k}/1：{fmt_frac(a)}×{k}/1 = {fmt_frac(ans)}。",
    }


def gen_mixed_convert(i: int) -> Dict[str, Any]:
    # two subtypes: mixed->improper or improper->mixed
    if random.random() < 0.5:
        whole = random.randint(1, 5)
        d = random.choice([2, 3, 4, 5, 6, 8, 10, 12])
        n = random.randint(1, d - 1)
        f = Fraction(whole * d + n, d)
        question = f"（互換）把帶分數改成假分數：{whole} {n}/{d} = ?"
        answer = fmt_frac(f)
        explanation = f"帶分數→假分數：({whole}×{d}+{n})/{d} = {answer}。"
        steps = [f"帶分數→假分數", f"({whole}×{d}+{n})/{d} = {f.numerator}/{d}", f"= {answer}"]
    else:
        d = random.choice([2, 3, 4, 5, 6, 8, 10, 12])
        whole = random.randint(1, 6)
        n = random.randint(1, d - 1)
        f = Fraction(whole * d + n, d)
        question = f"（互換）把假分數改成帶分數：{fmt_frac(f)} = ?"
        answer = fmt_mixed(f)
        explanation = f"假分數→帶分數：{f.numerator}÷{d} = {whole} 餘 {n}，所以是 {whole} {n}/{d}。"
        steps = [f"假分數→帶分數", f"{f.numerator}÷{d} = {whole} 餘 {n}", f"= {whole} {n}/{d}"]

    hints = [
        "觀念：帶分數＝整數部分 + 分數部分。",
        "規則：a b/c = (a×c+b)/c；假分數→帶分數用整除，餘數當分子。",
        "Level 3｜完整步驟\n1) 帶分數→假分數：a×c+b\n2) 假分數→帶分數：n÷d 取商、餘數\n3) 保持分數部分是最簡分數",
    ]

    return {
        "id": f"fg5_mixed_{i:03d}",
        "kind": "mixed_convert",
        "topic": "國小五年級｜分數（計算）",
        "difficulty": "easy",
        "question": question,
        "answer": answer,
        "hints": hints,
        "steps": steps,
        "explanation": explanation,
    }


def generate_bank() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    out += [gen_simplify(i) for i in range(1, 21)]
    out += [gen_equivalent(i) for i in range(1, 17)]
    out += [gen_add_like(i) for i in range(1, 15)]
    out += [gen_sub_like(i) for i in range(1, 15)]
    out += [gen_add_unlike(i) for i in range(1, 13)]
    out += [gen_sub_unlike(i) for i in range(1, 13)]
    out += [gen_mul(i) for i in range(1, 13)]
    out += [gen_mul_int(i) for i in range(1, 13)]
    out += [gen_mixed_convert(i) for i in range(1, 17)]

    random.shuffle(out)

    seen = set()
    uniq = []
    for q in out:
        t = q.get("question")
        if t in seen:
            continue
        seen.add(t)
        uniq.append(q)

    return uniq


def main() -> None:
    bank = generate_bank()

    js = "/* Auto-generated offline question bank. */\n" + "window.FRACTION_G5_BANK = " + json.dumps(
        bank, ensure_ascii=False, indent=2
    ) + ";\n"

    OUT_JS.parent.mkdir(parents=True, exist_ok=True)
    OUT_JS.write_text(js, encoding="utf-8")
    print(f"Wrote: {OUT_JS} (n={len(bank)})")


if __name__ == "__main__":
    main()
