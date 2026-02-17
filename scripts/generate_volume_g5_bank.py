import json
import random
from decimal import Decimal, getcontext
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
OUT_JS = ROOT / "docs" / "volume-g5" / "bank.js"

random.seed(20260201)
getcontext().prec = 28


def fmt_int(n: int) -> str:
    return str(int(n))


def _strip_trailing_zeros(s: str) -> str:
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def fmt_decimal_from_fraction(fr: Fraction) -> str:
    d = Decimal(fr.numerator) / Decimal(fr.denominator)
    return _strip_trailing_zeros(format(d, "f"))


def fmt_num(x: int | Fraction) -> str:
    if isinstance(x, Fraction):
        if x.denominator == 1:
            return fmt_int(x.numerator)
        return fmt_decimal_from_fraction(x)
    return fmt_int(x)


def gen_cube_cm3(i: int) -> Dict[str, Any]:
    edge = random.randint(2, 15)
    v = edge**3
    unit = "立方公分（cm³）"

    question = f"（正方體體積）邊長 {edge} 公分的正方體，體積是多少立方公分？"

    hints = [
        "觀念：正方體的體積 = 邊長 × 邊長 × 邊長（邊長³）。",
        f"列式：{edge}×{edge}×{edge}。",
        "Level 3｜完整步驟\n"
        f"1) 先算 {edge}×{edge} = {edge*edge}\n"
        f"2) 再算 {edge*edge}×{edge} = {v}\n"
        f"3) 單位是 立方公分（cm³）",
    ]

    steps = [
        "使用公式 V=邊長³",
        f"計算 {edge}×{edge}×{edge}",
        f"寫上單位：{unit}",
    ]

    return {
        "id": f"vg5_cube_{i:03d}",
        "kind": "cube_cm3",
        "topic": "國小五年級｜體積（長方體/正方體）",
        "difficulty": "easy",
        "question": question,
        "answer": fmt_int(v),
        "hints": hints,
        "steps": steps,
        "meta": {"unit": unit},
        "explanation": f"正方體體積：{edge}×{edge}×{edge}={v}（立方公分）。",
    }


def gen_cube_find_edge_cm(i: int) -> Dict[str, Any]:
    edge = random.randint(2, 15)
    v = edge**3
    unit = "公分（cm）"

    question = f"（反求邊長）一個正方體的體積是 {v} 立方公分（cm³），它的邊長是多少公分？（請填整數）"

    # Teacher-style guided trial for cube root (integer edge length).
    anchor = 10
    anchor_cube = anchor**3
    direction = "大於" if v > anchor_cube else "小於" if v < anchor_cube else "等於"

    # Prepare a short cube table around the answer.
    table_min = max(2, edge - 2)
    table_max = min(15, edge + 2)
    cube_table = "、".join([f"{k}³={k**3}" for k in range(table_min, table_max + 1)])

    hints = [
        "觀念：正方體體積 V = 邊長³。反求邊長，就是找一個整數 n，使得 n³ = V。",
        f"方向：用「試算立方根」：先用常見立方數抓範圍，再逐一試算到剛好等於 {v}。",
        "Level 3｜老師帶算（立方根用試算）\n"
        "1) 先抓大概範圍：常用 10³=1000 當基準。\n"
        f"   因為 {v} {direction} 1000，所以邊長 {('>10' if v>1000 else '<10' if v<1000 else '=10')}。\n"
        "2) 在可能的範圍內「逐一試算」：算 n³ 就是 n×n×n。\n"
        f"   例如附近的立方數：{cube_table}\n"
        f"3) 找到剛好等於 {v} 的那個：{edge}³={edge}×{edge}×{edge}={v}\n"
        f"4) 所以邊長 = {edge} 公分",
    ]

    steps = [
        "使用 V=邊長³",
        "找整數的三次方",
        f"得到邊長 = {edge} cm",
    ]

    return {
        "id": f"vg5_cube_find_{i:03d}",
        "kind": "cube_find_edge",
        "topic": "國小五年級｜體積（長方體/正方體）",
        "difficulty": "medium",
        "question": question,
        "answer": fmt_int(edge),
        "hints": hints,
        "steps": steps,
        "meta": {"unit": unit},
        "explanation": f"因為 {edge}³={edge}×{edge}×{edge}={v}，所以邊長是 {edge} 公分。",
    }


def gen_composite3(i: int) -> Dict[str, Any]:
    # Three blocks (A,B,C) stacked side-by-side, same length & height; widths differ.
    l = random.randint(3, 18)
    h = random.randint(2, 14)
    w1 = random.randint(2, 9)
    w2 = random.randint(2, 9)
    w3 = random.randint(2, 9)

    v1 = l * w1 * h
    v2 = l * w2 * h
    v3 = l * w3 * h
    total = v1 + v2 + v3

    unit = "立方公分（cm³）"
    question = (
        "（複合形體進階｜三段相加）把形體分成三個長方體來算：\n"
        f"A：長 {l} 公分、寬 {w1} 公分、高 {h} 公分\n"
        f"B：長 {l} 公分、寬 {w2} 公分、高 {h} 公分\n"
        f"C：長 {l} 公分、寬 {w3} 公分、高 {h} 公分\n"
        "這個複合形體的總體積是多少立方公分？"
    )

    hints = [
        "觀念：複合形體先分解成幾個長方體，各自算體積後相加。",
        f"列式：V = ({l}×{w1}×{h}) + ({l}×{w2}×{h}) + ({l}×{w3}×{h})。",
        "Level 3｜完整步驟\n"
        f"1) A：{l}×{w1}×{h} = {v1}\n"
        f"2) B：{l}×{w2}×{h} = {v2}\n"
        f"3) C：{l}×{w3}×{h} = {v3}\n"
        f"4) 相加：{v1}+{v2}+{v3} = {total}\n"
        f"5) 單位：立方公分（cm³）",
    ]

    steps = [
        f"分解成 A({l}×{w1}×{h})、B({l}×{w2}×{h})、C({l}×{w3}×{h})",
        f"V_A={v1}, V_B={v2}, V_C={v3}",
        f"總體積 = {v1}+{v2}+{v3} = {total}",
    ]

    return {
        "id": f"vg5_comp3_{i:03d}",
        "kind": "composite3",
        "topic": "國小五年級｜體積（長方體/正方體）",
        "difficulty": "medium",
        "question": question,
        "answer": fmt_int(total),
        "hints": hints,
        "steps": steps,
        "meta": {"unit": unit},
        "explanation": f"總體積 = {v1}+{v2}+{v3}={total}（立方公分）。",
    }


def gen_rect_cm3(i: int) -> Dict[str, Any]:
    l = random.randint(3, 30)
    w = random.randint(2, 20)
    h = random.randint(2, 20)
    v = l * w * h
    unit = "立方公分（cm³）"

    question = f"（長方體體積）長 {l} 公分、寬 {w} 公分、高 {h} 公分的長方體，體積是多少立方公分？"

    hints = [
        "觀念：長方體的體積 V = 長 × 寬 × 高。",
        f"列式：{l}×{w}×{h}。",
        "Level 3｜完整步驟\n"
        f"1) 先算 {l}×{w} = {l*w}\n"
        f"2) 再算 {l*w}×{h} = {v}\n"
        f"3) 單位是 立方公分（cm³）",
    ]

    steps = [
        "使用公式 V=長×寬×高",
        "先算長×寬（底面積）",
        "再乘高",
        f"寫上單位：{unit}",
    ]

    return {
        "id": f"vg5_rect_{i:03d}",
        "kind": "rect_cm3",
        "topic": "國小五年級｜體積（長方體/正方體）",
        "difficulty": random.choice(["easy", "medium"]),
        "question": question,
        "answer": fmt_int(v),
        "hints": hints,
        "steps": steps,
        "meta": {"unit": unit},
        "explanation": f"長方體體積：{l}×{w}×{h}={v}（立方公分）。",
    }


def gen_rect_find_height_cm(i: int) -> Dict[str, Any]:
    l = random.randint(4, 30)
    w = random.randint(3, 20)
    h = random.randint(2, 18)
    v = l * w * h
    unit = "公分（cm）"
    base = l * w

    question = (
        "（反求高）一個長方體的長是 {l} 公分、寬是 {w} 公分，體積是 {v} 立方公分（cm³）。"
        "它的高是多少公分？（請填整數）"
    ).format(l=l, w=w, v=v)

    hints = [
        "觀念：長方體體積 V = 長×寬×高；要反求高，可以用 高 = 體積 ÷ (長×寬)。",
        f"列式：高 = {v} ÷ ({l}×{w})。",
        "Level 3｜完整步驟\n"
        f"1) 先算底面積：{l}×{w} = {base}\n"
        f"2) 高 = {v} ÷ {base} = {h}\n"
        f"3) 所以高 = {h} 公分",
    ]

    steps = [
        "先算長×寬（底面積）",
        "用 高 = 體積 ÷ 底面積",
        f"得到高 = {h} cm",
    ]

    return {
        "id": f"vg5_rect_find_h_{i:03d}",
        "kind": "rect_find_height",
        "topic": "國小五年級｜體積（長方體/正方體）",
        "difficulty": "medium",
        "question": question,
        "answer": fmt_int(h),
        "hints": hints,
        "steps": steps,
        "meta": {"unit": unit},
        "explanation": f"底面積={l}×{w}={base}，高={v}÷{base}={h}（公分）。",
    }


def gen_base_area_h(i: int) -> Dict[str, Any]:
    base_area = random.randint(20, 400)
    h = random.randint(2, 25)
    v = base_area * h
    unit = "立方公分（cm³）"

    question = f"（底面積×高）一個立體的底面積是 {base_area} 平方公分，高是 {h} 公分，體積是多少立方公分？"

    hints = [
        "觀念：體積 V = 底面積 × 高。",
        f"列式：{base_area}×{h}。",
        "Level 3｜完整步驟\n"
        f"1) V = 底面積×高 = {base_area}×{h}\n"
        f"2) {base_area}×{h} = {v}\n"
        f"3) 底面積(平方)×高(公分) → 立方公分（cm³）",
    ]

    steps = [
        f"V = 底面積×高",
        f"{base_area}×{h} = {v}",
        f"體積 = {v} cm³",
    ]

    return {
        "id": f"vg5_base_{i:03d}",
        "kind": "base_area_h",
        "topic": "國小五年級｜體積（長方體/正方體）",
        "difficulty": "easy",
        "question": question,
        "answer": fmt_int(v),
        "hints": hints,
        "steps": steps,
        "meta": {"unit": unit},
        "explanation": f"體積：{base_area}×{h}={v}（立方公分）。",
    }


def gen_m3_to_cm3(i: int) -> Dict[str, Any]:
    m3 = random.randint(1, 9)
    cm3 = m3 * 1_000_000
    unit = "立方公分（cm³）"

    question = f"（單位換算）{m3} 立方公尺（m³）等於多少立方公分（cm³）？"

    hints = [
        "觀念：1 m = 100 cm，所以 1 m³ = 100³ cm³。",
        "規則：1 m³ = 1,000,000 cm³。",
        "Level 3｜完整步驟\n"
        "1) 先記住：1 m³ = 1,000,000 cm³\n"
        f"2) {m3} m³ = {m3}×1,000,000 = {cm3} cm³",
    ]

    steps = [
        "用 1 m³ = 1,000,000 cm³",
        f"把 {m3} 乘上 1,000,000",
        "寫出結果（立方公分）",
    ]

    return {
        "id": f"vg5_m3_to_cm3_{i:03d}",
        "kind": "m3_to_cm3",
        "topic": "國小五年級｜體積（長方體/正方體）",
        "difficulty": "medium",
        "question": question,
        "answer": fmt_int(cm3),
        "hints": hints,
        "steps": steps,
        "meta": {"unit": unit},
        "explanation": f"1 m³ = 1,000,000 cm³，所以 {m3} m³ = {cm3} cm³。",
    }


def gen_cm3_to_m3(i: int) -> Dict[str, Any]:
    m3 = random.randint(1, 9)
    cm3 = m3 * 1_000_000
    unit = "立方公尺（m³）"

    question = f"（單位換算）{cm3:,} 立方公分（cm³）等於多少立方公尺（m³）？（請填整數）"

    hints = [
        "觀念：1 m³ = 1,000,000 cm³。",
        f"做法：把 {cm3:,} 除以 1,000,000。",
        "Level 3｜完整步驟\n"
        f"1) {cm3:,} cm³ ÷ 1,000,000 = {m3}\n"
        f"2) 所以是 {m3} m³",
    ]

    steps = [
        f"1 m³ = 1,000,000 cm³",
        f"{cm3:,} ÷ 1,000,000 = {m3}",
        f"= {m3} m³",
    ]

    return {
        "id": f"vg5_cm3_to_m3_{i:03d}",
        "kind": "cm3_to_m3",
        "topic": "國小五年級｜體積（長方體/正方體）",
        "difficulty": "medium",
        "question": question,
        "answer": fmt_int(m3),
        "hints": hints,
        "steps": steps,
        "meta": {"unit": unit},
        "explanation": f"{cm3:,} cm³ = {m3} m³（因為除以 1,000,000）。",
    }


def gen_composite(i: int) -> Dict[str, Any]:
    # Two blocks placed side-by-side sharing the same height.
    h = random.randint(2, 12)
    d = random.randint(2, 12)

    w1 = random.randint(2, 10)
    w2 = random.randint(2, 10)
    l = random.randint(3, 18)

    v1 = l * w1 * h
    v2 = l * w2 * h
    total = v1 + v2

    unit = "立方公分（cm³）"
    question = (
        "（複合形體）把形體分成兩個長方體來算：\n"
        f"A：長 {l} 公分、寬 {w1} 公分、高 {h} 公分\n"
        f"B：長 {l} 公分、寬 {w2} 公分、高 {h} 公分\n"
        "這個複合形體的總體積是多少立方公分？"
    )

    hints = [
        "觀念：複合形體先分解成幾個長方體/正方體，各自算體積再相加。",
        f"列式：V = ({l}×{w1}×{h}) + ({l}×{w2}×{h})。",
        "Level 3｜完整步驟\n"
        f"1) A 的體積：{l}×{w1}×{h} = {v1}\n"
        f"2) B 的體積：{l}×{w2}×{h} = {v2}\n"
        f"3) 相加：{v1}+{v2} = {total}\n"
        f"4) 單位：立方公分（cm³）",
    ]

    steps = [
        f"分成 A({l}×{w1}×{h}) 和 B({l}×{w2}×{h})",
        f"V_A={v1}, V_B={v2}",
        f"總體積 = {v1}+{v2} = {total}",
    ]

    return {
        "id": f"vg5_comp_{i:03d}",
        "kind": "composite",
        "topic": "國小五年級｜體積（長方體/正方體）",
        "difficulty": "medium",
        "question": question,
        "answer": fmt_int(total),
        "hints": hints,
        "steps": steps,
        "meta": {"unit": unit},
        "explanation": f"總體積 = {v1}+{v2}={total}（立方公分）。",
    }


def gen_rect_mixed_units_to_cm3(i: int) -> Dict[str, Any]:
    l_m = random.randint(1, 4)
    w_cm = random.choice([20, 25, 30, 35, 40, 45, 50, 60, 70, 80])
    h_cm = random.choice([10, 12, 15, 18, 20, 24, 25, 30, 36, 40])

    l_cm = l_m * 100
    v = l_cm * w_cm * h_cm
    unit = "立方公分（cm³）"

    question = (
        f"（單位混合）一個長方體的長是 {l_m} 公尺、寬是 {w_cm} 公分、高是 {h_cm} 公分。"
        "體積是多少立方公分（cm³）？"
    )

    hints = [
        "觀念：先把長、寬、高的單位統一（都換成 cm），再用 V=長×寬×高。",
        f"換算：{l_m} m = {l_cm} cm；列式：{l_cm}×{w_cm}×{h_cm}。",
        "Level 3｜完整步驟\n"
        f"1) 把公尺換成公分：{l_m} m = {l_cm} cm\n"
        f"2) V = {l_cm}×{w_cm}×{h_cm} = {v}\n"
        f"3) 單位：立方公分（cm³）",
    ]

    steps = [
        f"{l_m} m = {l_cm} cm",
        f"V = {l_cm}×{w_cm}×{h_cm} = {fmt_int(v)}",
        f"= {fmt_int(v)} cm³",
    ]

    return {
        "id": f"vg5_mixed_{i:03d}",
        "kind": "mixed_units",
        "topic": "國小五年級｜體積（長方體/正方體）",
        "difficulty": "medium",
        "question": question,
        "answer": fmt_int(v),
        "hints": hints,
        "steps": steps,
        "meta": {"unit": unit},
        "explanation": f"先換算 {l_m} m = {l_cm} cm，再算 {l_cm}×{w_cm}×{h_cm}={v}（cm³）。",
    }


def gen_rect_decimal_dims_m3(i: int) -> Dict[str, Any]:
    # Use tenths of meters to keep finite decimals.
    l = Fraction(random.randint(6, 28), 10)  # 0.6~2.8
    w = Fraction(random.randint(4, 20), 10)  # 0.4~2.0
    h = Fraction(random.randint(4, 20), 10)  # 0.4~2.0
    v = l * w * h

    l_s = fmt_decimal_from_fraction(l)
    w_s = fmt_decimal_from_fraction(w)
    h_s = fmt_decimal_from_fraction(h)
    v_s = fmt_decimal_from_fraction(v)

    unit = "立方公尺（m³）"
    question = (
        f"（帶小數尺寸）一個長方體的長 {l_s} 公尺、寬 {w_s} 公尺、高 {h_s} 公尺。"
        "體積是多少立方公尺（m³）？（可填小數）"
    )

    hints = [
        "觀念：單位都已經是公尺，直接用 V=長×寬×高 計算，答案單位是 m³。",
        f"列式：{l_s}×{w_s}×{h_s}。",
        "Level 3｜完整步驟\n"
        f"1) V = {l_s}×{w_s}×{h_s}\n"
        f"2) 計算得到 V = {v_s}\n"
        f"3) 單位：立方公尺（m³）",
    ]

    steps = [
        f"單位都是公尺",
        f"{l_s}×{w_s}×{h_s} = {v_s}",
        f"= {v_s} m³",
    ]

    return {
        "id": f"vg5_dec_{i:03d}",
        "kind": "decimal_dims",
        "topic": "國小五年級｜體積（長方體/正方體）",
        "difficulty": "medium",
        "question": question,
        "answer": v_s,
        "hints": hints,
        "steps": steps,
        "meta": {"unit": unit},
        "explanation": f"長方體體積：{l_s}×{w_s}×{h_s}={v_s}（m³）。",
    }


def generate_bank() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    out += [gen_cube_cm3(i) for i in range(1, 25)]
    out += [gen_cube_find_edge_cm(i) for i in range(1, 13)]
    out += [gen_rect_cm3(i) for i in range(1, 31)]
    out += [gen_rect_find_height_cm(i) for i in range(1, 13)]
    out += [gen_base_area_h(i) for i in range(1, 21)]
    out += [gen_m3_to_cm3(i) for i in range(1, 13)]
    out += [gen_cm3_to_m3(i) for i in range(1, 13)]
    out += [gen_rect_mixed_units_to_cm3(i) for i in range(1, 13)]
    out += [gen_rect_decimal_dims_m3(i) for i in range(1, 13)]
    out += [gen_composite(i) for i in range(1, 17)]
    out += [gen_composite3(i) for i in range(1, 13)]

    random.shuffle(out)

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

    js = "/* Auto-generated offline question bank. */\n" + "window.VOLUME_G5_BANK = " + json.dumps(
        bank, ensure_ascii=False, indent=2
    ) + ";\n"

    OUT_JS.parent.mkdir(parents=True, exist_ok=True)
    OUT_JS.write_text(js, encoding="utf-8")
    print(f"Wrote: {OUT_JS} (n={len(bank)})")


if __name__ == "__main__":
    main()
