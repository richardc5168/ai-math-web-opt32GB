import json
import random
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
OUT_JS = ROOT / "docs" / "decimal-unit4" / "bank.js"

random.seed(20260201)


def qround(x: Decimal, ndigits: int) -> Decimal:
    q = Decimal("1").scaleb(-ndigits)
    return x.quantize(q, rounding=ROUND_HALF_UP)


def to_str(d: Decimal) -> str:
    s = format(d, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def decimal_places(x: Decimal) -> int:
    # Decimal('0.9').as_tuple().exponent == -1
    # Decimal('2').as_tuple().exponent == 0
    return max(0, -x.as_tuple().exponent)


def fmt_vertical_mul(a: int, b: int) -> str:
    # Simple vertical multiplication visualization (text-only)
    # Example:
    #    99
    # ×   9
    # -----
    #   891
    a_s = str(a)
    b_s = str(b)
    w = max(len(a_s), len(b_s) + 2, len(str(a * b)))
    top = a_s.rjust(w)
    mid = ("× " + b_s).rjust(w)
    line = "-" * w
    bottom = str(a * b).rjust(w)
    return "\n".join([top, mid, line, bottom])


def mul_single_digit_explain(a: int, digit: int) -> List[str]:
    """Return teacher-style step lines for a × digit, where digit is 0..9."""
    if digit < 0 or digit > 9:
        raise ValueError("digit must be 0..9")

    a_s = str(abs(a))
    ones_digit = int(a_s[-1])
    steps: List[str] = []

    steps.append(f"個位對個位（{digit} 對 {ones_digit}）")

    carry = 0
    digits = list(reversed([int(ch) for ch in a_s]))
    for idx, d in enumerate(digits):
        base_prod = d * digit
        total = base_prod + carry
        write = total % 10
        new_carry = total // 10

        if idx == 0:
            if new_carry:
                steps.append(f"先算 {digit}×{d}={base_prod}，寫 {write} 進 {new_carry}")
            else:
                steps.append(f"先算 {digit}×{d}={base_prod}，寫 {write}")
        elif idx == len(digits) - 1:
            if carry:
                steps.append(f"再算 {digit}×{d}={base_prod}，加進位 {carry} 變 {total}，寫 {total} → 得 {abs(a) * digit}")
            else:
                steps.append(f"再算 {digit}×{d}={base_prod}，寫 {total} → 得 {abs(a) * digit}")
        else:
            if carry:
                steps.append(f"再算 {digit}×{d}={base_prod}，加進位 {carry} 變 {total}，寫 {write} 進 {new_carry}")
            else:
                steps.append(f"再算 {digit}×{d}={base_prod}，寫 {write} 進 {new_carry}")

        carry = new_carry

    return steps


def build_level3_hint_int_mul_decimal(*, base: int, rate: Decimal, unit: str, answer: Decimal, answer_mode: str) -> str:
    rate_pct = int((rate * Decimal(100)).to_integral_value(rounding=ROUND_HALF_UP))
    places = decimal_places(rate)
    rate_int = int((rate * (Decimal(10) ** places)).to_integral_value(rounding=ROUND_HALF_UP))
    raw = Decimal(base) * rate
    approx = qround(raw, 1)

    too_big = base * 10
    too_small = Decimal(base) / Decimal(10)
    direction_check = (
        f"{to_str(rate)} = {rate_pct}%（不到 1）\n"
        f"{base} {unit} 取 {rate_pct}% 會「變小」，答案應該比 {base} 小，而且接近 {to_str(approx)}\n"
        f"所以最後若算到 {too_big} 多或 {to_str(too_small)} 都不合理"
    )

    equation = f"{base}\n×\n{to_str(rate)}\n{base}×{to_str(rate)}"

    method_a = [
        "計算方法 A（最清楚：把小數變整數再乘）",
        f"因為 {to_str(rate)} 有 {places} 位小數，我們先當作\n{rate_int}\n來算（等一下再把小數點放回去）",
        f"直式乘法（先算 {base} × {rate_int}）：",
    ]
    if rate_int < 10:
        method_a.append(fmt_vertical_mul(base, rate_int))
        method_a.append("對齊提醒：")
        for s in mul_single_digit_explain(base, rate_int):
            method_a.append(s)
    else:
        method_a.append(f"先算 {base} × {rate_int}（可以用直式或分配律），得到 {base * rate_int}。")
        method_a.append("對齊提醒：")
        method_a.append("- 直式乘法要『個位對個位』，每一列乘完再相加")

    put_back = [
        "把小數點放回去（關鍵提醒）",
        f"原本是乘\n{to_str(rate)}\n{to_str(rate)}，有「{places} 位小數」",
        "所以乘完之後，要從右邊往左數小數位數，點上小數點：",
        f"{base * rate_int}\n→\n{to_str(raw)}\n{base * rate_int}→{to_str(raw)}",
    ]

    rounding_note = ""
    if answer_mode in ("money2", "round2"):
        rounding_note = f"最後依題目要求四捨五入到小數點後 2 位：{to_str(answer)}"

    reminder = f"（給孩子的小提醒一句話）\n乘 {to_str(rate)} 就像「取 {rate_pct}%」，所以答案一定比 {base} 小，{to_str(answer)} 很合理。"

    lines = [
        "Level 3｜計算步驟（含直式對齊提醒）",
        "",
        "先估算（檢查方向對不對）",
        direction_check,
        "",
        "列式",
        equation,
        "",
        *method_a,
        "",
        *put_back,
    ]
    if rounding_note:
        lines += ["", rounding_note]
    lines += [
        "",
        "寫上單位",
        f"{to_str(answer)} {unit}",
        "",
        "結論",
        f"{base}×{to_str(rate)}={to_str(answer)} {unit}",
        "",
        reminder,
    ]
    return "\n".join(lines)


def build_level3_hint_decimal_mul_int(*, per: Decimal, count: int, unit: str, answer: Decimal, answer_mode: str) -> str:
    places = decimal_places(per)
    per_int = int((per * (Decimal(10) ** places)).to_integral_value(rounding=ROUND_HALF_UP))
    raw = per * Decimal(count)
    approx = qround(raw, 1)

    rounding_note = ""
    if answer_mode in ("money2", "round2"):
        rounding_note = f"最後依題目要求四捨五入到小數點後 2 位：{to_str(answer)}"

    lines = [
        "Level 3｜計算步驟（含直式對齊提醒）",
        "",
        "先估算（檢查方向對不對）",
        f"份數是 {count}（大於 1），所以答案一定比每份 {to_str(per)} 大，並且接近 {to_str(approx)}。",
        "",
        "列式",
        f"{to_str(per)}\n×\n{count}\n{to_str(per)}×{count}",
        "",
        "計算方法 A（最清楚：把小數變整數再乘）",
        f"因為 {to_str(per)} 有 {places} 位小數，我們先當作\n{per_int}\n來算（等一下再把小數點放回去）",
        f"直式乘法（先算 {per_int} × {count}）：",
    ]

    if count < 10:
        lines.append(fmt_vertical_mul(per_int, count))
        lines.append("對齊提醒：")
        for s in mul_single_digit_explain(per_int, count):
            lines.append(s)
    else:
        lines.append(f"先算 {per_int} × {count} = {per_int * count}。")

    lines += [
        "",
        "把小數點放回去（關鍵提醒）",
        f"原本是乘 {to_str(per)}，有「{places} 位小數」",
        f"所以乘完 {per_int * count} 之後，要從右邊往左數 {places} 位，點上小數點：\n{per_int * count} → {to_str(raw)}",
    ]
    if rounding_note:
        lines += [rounding_note]
    lines += [
        "",
        f"寫上單位\n{to_str(answer)} {unit}",
        "",
        "小提醒：先估算，再點小數點，錯誤率會大幅下降。",
    ]
    return "\n".join(lines)


def build_level3_hint_decimal_mul_decimal(*, a: Decimal, b: Decimal, unit: str, answer: Decimal, answer_mode: str) -> str:
    pa = decimal_places(a)
    pb = decimal_places(b)
    a_int = int((a * (Decimal(10) ** pa)).to_integral_value(rounding=ROUND_HALF_UP))
    b_int = int((b * (Decimal(10) ** pb)).to_integral_value(rounding=ROUND_HALF_UP))
    raw = a * b
    approx = qround(raw, 1)

    rounding_note = ""
    if answer_mode in ("money2", "round2"):
        rounding_note = f"最後依題目要求四捨五入到小數點後 2 位：{to_str(answer)}"

    lines = [
        "Level 3｜計算步驟（含直式對齊提醒）",
        "",
        "先估算（檢查大小）",
        f"把 {to_str(a)} 約成 {to_str(qround(a,1))}，{to_str(b)} 約成 {to_str(qround(b,1))}，大約是 {to_str(approx)}。",
        "",
        "列式",
        f"{to_str(a)} × {to_str(b)}",
        "",
        "計算方法 A：先整數乘，再放回小數點",
        f"先把小數點去掉：{to_str(a)} → {a_int}（{pa} 位小數），{to_str(b)} → {b_int}（{pb} 位小數）",
        f"先算整數：{a_int} × {b_int} = {a_int * b_int}",
        f"小數位數要『加起來』：{pa}+{pb} = {pa+pb} 位，所以答案要從右邊往左數 {pa+pb} 位點小數點。",
        f"得到：{to_str(raw)}",
    ]
    if rounding_note:
        lines += [rounding_note]
    lines += ["", f"寫上單位\n{to_str(answer)} {unit}"]
    return "\n".join(lines)


def make_decimal_int(scale_choices: List[int], min_int: int, max_int: int) -> Decimal:
    scale = random.choice(scale_choices)
    n = random.randint(min_int, max_int)
    return Decimal(n) / (Decimal(10) ** scale)


def money(d: Decimal) -> Decimal:
    return qround(d, 2)


def gen_d_mul_int(i: int) -> Dict[str, Any]:
    # price per item * count, liters per bottle * count
    unit = random.choice(["元", "公升", "公斤", "公尺"])
    count = random.randint(2, 9)

    if unit == "元":
        a = make_decimal_int([1, 2], 10, 500)  # 1~2 decimal digits
        ans = money(a * Decimal(count))
        question = f"（買多份）一個物品 {to_str(a)} 元，買 {count} 個，一共多少元？"
        answer_mode = "money2"
    else:
        a = make_decimal_int([1, 2, 3], 5, 500)
        ans = qround(a * Decimal(count), 3)
        question = f"（買多份）每份 {to_str(a)} {unit}，有 {count} 份，一共多少 {unit}？"
        answer_mode = "exact"

    hints = [
        "觀念：同一份量有很多份 → 用乘法。",
        "列式：每份 × 份數。先估算會變大（因為乘的是整數份數）。",
        build_level3_hint_decimal_mul_int(per=a, count=count, unit=unit, answer=ans, answer_mode=answer_mode),
    ]

    steps = [
        f"估算 {to_str(a)}×{count}",
        f"列式：{to_str(a)} × {count}",
        "先忽略小數點做整數乘法",
        f"放回小數點 → {to_str(ans)} {unit}",
        "檢查大小合理 ✓",
    ]

    return {
        "id": f"d4_d_mul_int_{i:03d}",
        "kind": "d_mul_int",
        "topic": "五下第4單元｜小數",
        "difficulty": random.choice(["easy", "medium"]),
        "question": question,
        "answer": to_str(ans),
        "answer_mode": answer_mode,
        "hints": hints,
        "steps": steps,
        "meta": {"unit": unit},
        "explanation": f"用乘法：{to_str(a)} × {count} = {to_str(a*Decimal(count))}，依題目需求取位數 → {to_str(ans)} {unit}。",
    }


def gen_int_mul_d(i: int) -> Dict[str, Any]:
    # discount, fraction of quantity
    base = random.randint(20, 500)
    rate = random.choice([Decimal("0.1"), Decimal("0.2"), Decimal("0.25"), Decimal("0.3"), Decimal("0.4"), Decimal("0.5"), Decimal("0.75"), Decimal("0.8"), Decimal("0.9")])

    scenario = random.choice(["折扣", "比例"])
    if scenario == "折扣":
        ans = money(Decimal(base) * rate)
        question = f"（打折）原價 {base} 元，打 {to_str(rate)} 倍（= {int(rate*100)}%），要付多少元？"
        unit = "元"
        answer_mode = "money2"
    else:
        unit = random.choice(["公尺", "公里", "公斤", "公升"])
        ans = qround(Decimal(base) * rate, 2)
        question = f"（比例）共有 {base} {unit}，取其中的 {to_str(rate)}（= {int(rate*100)}%），是多少 {unit}？"
        answer_mode = "round2"

    hints = [
        "觀念：乘上小於 1 的小數，結果會變小。",
        "列式：原本 × 倍數（或比例）。先估算答案大約在哪。",
        build_level3_hint_int_mul_decimal(base=base, rate=rate, unit=unit, answer=ans, answer_mode=answer_mode),
    ]

    steps = [
        f"乘 {to_str(rate)}（<1）→ 答案 < {base}",
        f"列式：{base} × {to_str(rate)}",
        "先做整數乘法",
        f"放回小數點 → {to_str(ans)} {unit}",
        f"答案 {to_str(ans)} < {base} ✓",
    ]

    return {
        "id": f"d4_int_mul_d_{i:03d}",
        "kind": "int_mul_d",
        "topic": "五下第4單元｜小數",
        "difficulty": random.choice(["easy", "medium"]),
        "question": question,
        "answer": to_str(ans),
        "answer_mode": answer_mode,
        "hints": hints,
        "steps": steps,
        "meta": {"unit": unit},
        "explanation": f"列式：{base} × {to_str(rate)}。計算後得到 {to_str(ans)} {unit}。",
    }


def gen_d_mul_d(i: int) -> Dict[str, Any]:
    # area / price per kg * kg
    kind = random.choice(["面積", "單價"])
    if kind == "面積":
        a = make_decimal_int([1, 2], 10, 90)
        b = make_decimal_int([1, 2], 10, 90)
        ans = qround(a * b, 3)
        question = f"（面積）長方形長 {to_str(a)} 公尺、寬 {to_str(b)} 公尺，面積是多少平方公尺？"
        unit = "平方公尺"
        answer_mode = "exact"
    else:
        price = make_decimal_int([1, 2], 50, 900)  # 元/公斤
        weight = make_decimal_int([1, 2], 5, 80)   # 公斤
        ans = money(price * weight)
        question = f"（單價×重量）每公斤 {to_str(price)} 元，買了 {to_str(weight)} 公斤，一共多少元？"
        unit = "元"
        answer_mode = "money2"

    ref_a = a if kind == "面積" else price
    ref_b = b if kind == "面積" else weight
    hints = [
        "觀念：小數×小數常見在面積（長×寬）或單價×數量。",
        "列式：小數 × 小數。先估算，再用『小數位數加起來』放回小數點。",
        build_level3_hint_decimal_mul_decimal(a=ref_a, b=ref_b, unit=unit, answer=ans, answer_mode=answer_mode),
    ]

    steps = [
        f"估算 {to_str(ref_a)}×{to_str(ref_b)}",
        "去掉小數點做整數乘",
        "小數位數加起來放回",
        f"= {to_str(ans)} {unit}",
        "大小合理 ✓",
    ]

    return {
        "id": f"d4_d_mul_d_{i:03d}",
        "kind": "d_mul_d",
        "topic": "五下第4單元｜小數",
        "difficulty": random.choice(["easy", "medium"]),
        "question": question,
        "answer": to_str(ans),
        "answer_mode": answer_mode,
        "hints": hints,
        "steps": steps,
        "meta": {"unit": unit},
        "explanation": f"依題意用乘法，先整數乘，再把小數位數加起來放回，得到 {to_str(ans)} {unit}。",
    }


def gen_d_div_int(i: int) -> Dict[str, Any]:
    unit = random.choice(["公升", "公斤", "公尺", "元"])
    n_people = random.randint(2, 9)

    if unit == "元":
        total = make_decimal_int([1, 2], 50, 900)
        # ensure divisibility to 2 decimals by constructing as multiple
        each = money(total / Decimal(n_people))
        total = money(each * Decimal(n_people))
        ans = each
        question = f"（平均分）一共 {to_str(total)} 元，平均分給 {n_people} 人，每人多少元？"
        answer_mode = "money2"
    else:
        each = make_decimal_int([1, 2], 5, 120)
        total = qround(each * Decimal(n_people), 2)
        ans = qround(total / Decimal(n_people), 2)
        question = f"（平均分）一共 {to_str(total)} {unit}，平均分給 {n_people} 份，每份多少 {unit}？"
        answer_mode = "round2"

    hints = [
        "觀念：平均分配 → 用除法（總量 ÷ 份數）。",
        "列式：總量 ÷ 份數。直式除法不夠除就補 0。",
        "步驟：做到小數點時，把小數點點到商那一行；最後用『商×除數=被除數』檢查。",
    ]

    steps = [
        f"列式：{to_str(total)} ÷ {n_people}",
        "直式除法計算",
        "不夠除就補 0",
        f"商 = {to_str(ans)} {unit}",
        f"驗算：{to_str(ans)}×{n_people} ≈ {to_str(total)} ✓",
    ]

    return {
        "id": f"d4_d_div_int_{i:03d}",
        "kind": "d_div_int",
        "topic": "五下第4單元｜小數",
        "difficulty": random.choice(["easy", "medium"]),
        "question": question,
        "answer": to_str(ans),
        "answer_mode": answer_mode,
        "hints": hints,
        "steps": steps,
        "meta": {"unit": unit},
        "explanation": f"平均分：{to_str(total)} ÷ {n_people} = {to_str(ans)} {unit}。",
    }


def gen_int_div_int_to_decimal(i: int) -> Dict[str, Any]:
    # construct to produce terminating decimal (divide by 2,4,5,8,10,20,25)
    divisor = random.choice([2, 4, 5, 8, 10, 20, 25])
    # build quotient with 1-2 decimals
    q = make_decimal_int([1, 2], 10, 500)
    dividend = qround(q * Decimal(divisor), 2)
    ans = qround(dividend / Decimal(divisor), 2)

    question = f"（商是小數）計算：{to_str(dividend)} ÷ {divisor} = ?"

    hints = [
        "觀念：整數÷整數也可能得到小數；不夠除就補 0。",
        "列式：被除數 ÷ 除數。做到被除數的小數點時，商也要點小數點。",
        "步驟：用直式除法，補 0 繼續，最後檢查：商×除數=被除數。",
    ]

    steps = [
        f"{to_str(dividend)} ÷ {divisor}",
        "不夠除就補 0 繼續",
        f"商 = {to_str(ans)}",
        f"驗算：{to_str(ans)}×{divisor} = {to_str(dividend)}",
    ]

    return {
        "id": f"d4_int_div_int_{i:03d}",
        "kind": "int_div_int_to_decimal",
        "topic": "五下第4單元｜小數",
        "difficulty": random.choice(["easy", "medium"]),
        "question": question,
        "answer": to_str(ans),
        "answer_mode": "round2",
        "hints": hints,
        "steps": steps,
        "meta": {"unit": ""},
        "explanation": f"直式計算或心算：{to_str(dividend)} ÷ {divisor} = {to_str(ans)}。",
    }


def gen_x10_shift(i: int) -> Dict[str, Any]:
    base = make_decimal_int([1, 2, 3], 1, 9999)
    op = random.choice(["×10", "×100", "×1000", "×0.1", "×0.01", "×0.001"])

    if op.startswith("×0"):
        k = int(op.split("×0.")[1].count("0") + 1)  # 0.1 ->1, 0.01 ->2, 0.001 ->3
        ans = base / (Decimal(10) ** k)
        direction = "左"
    else:
        multiplier = int(op.replace("×", ""))
        shift = {10: 1, 100: 2, 1000: 3}[multiplier]
        ans = base * (Decimal(10) ** shift)
        direction = "右"

    question = f"（小數點移動）計算：{to_str(base)} {op} = ?"

    hints = [
        "觀念：只有乘以 10/100/1000（或 0.1/0.01/0.001）才是『小數點移動』。",
        f"規則：這題要把小數點往{direction}移 {1 if '10' in op and '100' not in op else (2 if '100' in op and '1000' not in op else 3)} 格；不夠就補 0。",
        "步驟：先找小數點位置 → 移動 → 必要時補 0 → 再檢查大小有沒有變對方向。",
    ]

    steps = [
        f"確認 {op}",
        f"小數點往{direction}移",
        f"= {to_str(qround(ans, 6))}",
        f"{'變大' if direction=='右' else '變小'} ✓",
    ]

    return {
        "id": f"d4_x10_shift_{i:03d}",
        "kind": "x10_shift",
        "topic": "五下第4單元｜小數",
        "difficulty": "easy",
        "question": question,
        "answer": to_str(qround(ans, 6)),
        "answer_mode": "exact",
        "hints": hints,
        "steps": steps,
        "meta": {"unit": ""},
        "explanation": f"依規則移動小數點，得到 {to_str(ans)}。",
    }


def generate_bank(target_counts: Dict[str, int]) -> List[Dict[str, Any]]:
    makers = {
        "d_mul_int": gen_d_mul_int,
        "int_mul_d": gen_int_mul_d,
        "d_mul_d": gen_d_mul_d,
        "d_div_int": gen_d_div_int,
        "int_div_int_to_decimal": gen_int_div_int_to_decimal,
        "x10_shift": gen_x10_shift,
    }

    out: List[Dict[str, Any]] = []
    for kind, cnt in target_counts.items():
        gen = makers[kind]
        for i in range(1, cnt + 1):
            out.append(gen(i))

    # shuffle for variety
    random.shuffle(out)

    # de-dup by question text
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
    bank = generate_bank(
        {
            "d_mul_int": 20,
            "int_mul_d": 16,
            "d_mul_d": 18,
            "d_div_int": 16,
            "int_div_int_to_decimal": 12,
            "x10_shift": 12,
        }
    )

    js = "/* Auto-generated offline question bank. */\n" + "window.DECIMAL_UNIT4_BANK = " + json.dumps(
        bank, ensure_ascii=False, indent=2
    ) + ";\n"

    OUT_JS.write_text(js, encoding="utf-8")
    print(f"Wrote: {OUT_JS} (n={len(bank)})")


if __name__ == "__main__":
    main()
