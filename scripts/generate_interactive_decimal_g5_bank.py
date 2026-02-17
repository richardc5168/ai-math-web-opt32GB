import json
import random
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP, getcontext
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
OUT_JS = ROOT / "docs" / "interactive-decimal-g5" / "bank.js"

random.seed(20260204)
getcontext().prec = 28


def _strip_trailing_zeros(s: str) -> str:
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def to_str(d: Decimal) -> str:
    return _strip_trailing_zeros(format(d, "f"))


def decimal_places(x: Decimal) -> int:
    return max(0, -x.as_tuple().exponent)


def qround(x: Decimal, ndigits: int) -> Decimal:
    q = Decimal("1").scaleb(-ndigits)
    return x.quantize(q, rounding=ROUND_HALF_UP)


def int_form(x: Decimal) -> tuple[int, int]:
    """Return (x_int, places) where x = x_int / 10^places."""
    places = decimal_places(x)
    x_int = int((x * (Decimal(10) ** places)).to_integral_value(rounding=ROUND_HALF_UP))
    return x_int, places


@dataclass(frozen=True)
class Q:
    id: str
    kind: str
    difficulty: str
    question: str
    answer: str
    answer_mode: str
    hints: List[str]
    steps: List[str]
    meta: Dict[str, Any]
    explanation: str


TOPIC = "五下｜互動小數計算"


def _mk_mul_meta(a: Decimal, b: Decimal) -> Dict[str, Any]:
    a_int, pa = int_form(a)
    b_int, pb = int_form(b)
    return {
        "a": to_str(a),
        "b": to_str(b),
        "a_int": a_int,
        "b_int": b_int,
        "a_places": pa,
        "b_places": pb,
        "raw_int_product": a_int * b_int,
        "total_places": pa + pb,
    }


def q_d_mul_int(i: int) -> Q:
    unit = random.choice(["公升", "公斤", "公尺"])
    item = random.choice(["果汁", "白米", "緞帶", "繩子"])
    per = Decimal(random.randint(15, 320)) / Decimal(100)  # 0.15~3.20
    count = random.randint(2, 12)
    raw = per * Decimal(count)

    question = f"（互動）{item}每份 {to_str(per)} {unit}，買 {count} 份，一共多少 {unit}？（可寫小數）"
    answer = to_str(raw)

    meta = _mk_mul_meta(per, Decimal(count))
    meta.update({"unit": unit, "context": "d_mul_int"})

    hints = [
        "觀念：小數×整數 → 先當整數算，再把小數點放回去。",
        f"列式：{to_str(per)}×{count}。估算：{to_str(qround(per,1))}×{count} 大約 {to_str(qround(qround(per,1)*Decimal(count),1))}。",
        "Level 3｜互動提示：先把小數點拿掉算整數乘法，再把小數位數放回去。",
    ]

    steps = [
        f"列式：{to_str(per)} × {count}",
        "去掉小數點做整數乘法",
        f"放回小數點 → {answer}",
        "估算檢查 ✓",
    ]

    explanation = (
        f"{to_str(per)}×{count}：先算整數後再放回小數點，得到 {answer}（{unit}）。"
    )

    return Q(
        id=f"idg5_d_mul_int_{i:03d}",
        kind="d_mul_int",
        difficulty="easy",
        question=question,
        answer=answer,
        answer_mode="number",
        hints=hints,
        steps=steps,
        meta=meta,
        explanation=explanation,
    )


def q_int_mul_d(i: int) -> Q:
    base = Decimal(random.randrange(40, 501, 5))
    rate = Decimal(random.choice(["0.2", "0.25", "0.3", "0.4", "0.5", "0.6", "0.75", "0.8", "0.9"]))
    item = random.choice(["書包", "球鞋", "外套", "玩具"])
    raw = base * rate

    question = f"（互動）{item}原價 {to_str(base)} 元，打 {to_str(rate)} 倍（= 付 {int(rate*100)}%），要付多少元？"
    answer = to_str(raw)

    meta = _mk_mul_meta(base, rate)
    meta.update({"unit": "元", "context": "int_mul_d"})

    hints = [
        "觀念：整數×小數（小於 1）→ 答案會變小。",
        f"列式：{to_str(base)}×{to_str(rate)}。先估算：{to_str(base)} 的 {int(rate*100)}% 應該小於 {to_str(base)}。",
        "Level 3｜互動提示：把小數點拿掉先算整數乘法，再依小數位數把小數點放回去。",
    ]

    steps = [
        f"乘 {to_str(rate)} 會變小",
        "先去掉小數點做整數乘",
        f"{to_str(base)} × {to_str(rate)} = {answer}",
        f"答案 {answer} 元",
    ]

    explanation = f"付 {int(rate*100)}%：{to_str(base)}×{to_str(rate)}={answer}（元）。"

    return Q(
        id=f"idg5_int_mul_d_{i:03d}",
        kind="int_mul_d",
        difficulty="easy",
        question=question,
        answer=answer,
        answer_mode="number",
        hints=hints,
        steps=steps,
        meta=meta,
        explanation=explanation,
    )


def q_d_mul_d(i: int) -> Q:
    a = Decimal(random.randint(12, 480)) / Decimal(10)  # 1.2~48.0
    b = Decimal(random.randint(12, 350)) / Decimal(10)  # 1.2~35.0
    mode = random.choice(["area", "price_weight"])

    if mode == "area":
        raw = a * b
        question = f"（互動）長方形長 {to_str(a)} 公尺、寬 {to_str(b)} 公尺，面積是多少平方公尺？"
        unit = "平方公尺"
    else:
        price = Decimal(random.randint(15, 120)) / Decimal(10)  # 1.5~12.0
        weight = Decimal(random.randint(5, 45)) / Decimal(10)  # 0.5~4.5
        a = price
        b = weight
        raw = a * b
        question = f"（互動）水果每公斤 {to_str(price)} 元，買了 {to_str(weight)} 公斤，總價多少元？"
        unit = "元"

    answer = to_str(raw)
    meta = _mk_mul_meta(a, b)
    meta.update({"unit": unit, "context": "d_mul_d"})

    pa = meta["a_places"]
    pb = meta["b_places"]

    hints = [
        "觀念：小數×小數 → 先整數乘，再把『小數位數加起來』放回去。",
        f"規則：{to_str(a)} 有 {pa} 位小數、{to_str(b)} 有 {pb} 位小數，共 {pa+pb} 位。",
        "Level 3｜互動提示：先做整數乘法得到 raw，再從右邊數回小數位數點上小數點。",
    ]

    steps = [
        f"估算 {to_str(a)}×{to_str(b)}",
        "去掉小數點做整數乘",
        f"小數位數 {pa}+{pb} = {pa+pb} 位",
        f"放回小數點 → {answer} {unit}",
    ]

    explanation = f"先當整數乘，再放回 {pa+pb} 位小數，得到 {answer}（{unit}）。"

    return Q(
        id=f"idg5_d_mul_d_{i:03d}",
        kind="d_mul_d",
        difficulty="medium",
        question=question,
        answer=answer,
        answer_mode="number",
        hints=hints,
        steps=steps,
        meta=meta,
        explanation=explanation,
    )


def q_d_div_int(i: int) -> Q:
    divisor = random.randint(2, 9)
    # choose a clean quotient with <=3 dp
    dp = random.choice([1, 2, 3])
    base = Decimal(random.randint(12, 980)) / (Decimal(10) ** dp)
    dividend = base * Decimal(divisor)

    unit = random.choice(["公升", "公斤", "公尺", "元"])
    thing = random.choice(["果汁", "糖果", "緞帶", "零用錢"])

    question = f"（互動）把 {to_str(dividend)} {unit} 的{thing}平均分給 {divisor} 人，每人多少 {unit}？"
    answer = to_str(base)

    hints = [
        "觀念：小數÷整數＝平均分配；不夠除就『補 0』繼續除。",
        f"列式：{to_str(dividend)} ÷ {divisor}。先估算：答案應該比 {to_str(dividend)} 小。",
        "Level 3｜互動提示：做到小數點時要在商那一行點上小數點；不夠除就補 0。",
    ]

    steps = [
        f"列式：{to_str(dividend)} ÷ {divisor}",
        "做到小數點就往上點到商",
        "不夠除就補 0 繼續",
        f"商 = {answer} {unit}",
    ]

    meta = {
        "dividend": to_str(dividend),
        "divisor": divisor,
        "unit": unit,
        "context": "d_div_int",
    }

    explanation = f"平均分：{to_str(dividend)}÷{divisor}={answer}（{unit}）。"

    return Q(
        id=f"idg5_d_div_int_{i:03d}",
        kind="d_div_int",
        difficulty="medium",
        question=question,
        answer=answer,
        answer_mode="number",
        hints=hints,
        steps=steps,
        meta=meta,
        explanation=explanation,
    )


def q_int_div_int_to_decimal(i: int) -> Q:
    divisor = random.choice([2, 4, 5, 8, 10, 20, 25, 40])
    dp = random.choice([1, 2, 3])
    q = Decimal(random.randint(10, 999)) / (Decimal(10) ** dp)
    dividend = (q * Decimal(divisor)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    # ensure exact
    q2 = Decimal(dividend) / Decimal(divisor)

    question = f"（互動）計算：{int(dividend)} ÷ {divisor} = ?（商是小數）"
    answer = to_str(q2)

    hints = [
        "觀念：整數÷整數，如果不夠除，可以在被除數後面『補 0』變小數再除。",
        f"列式：{int(dividend)} ÷ {divisor}。做到不夠除就補 0。",
        "Level 3｜互動提示：補 0 不會改變數的大小（只是換成十分位/百分位繼續除）。",
    ]

    steps = [
        f"{int(dividend)} ÷ {divisor}",
        "不夠除就補 0 繼續",
        f"商 = {answer}",
        f"驗算：{answer}×{divisor} = {int(dividend)}",
    ]

    meta = {
        "dividend": int(dividend),
        "divisor": divisor,
        "unit": "",
        "context": "int_div_int_to_decimal",
    }

    explanation = f"因為不夠除就補 0 繼續除，得到 {answer}。"

    return Q(
        id=f"idg5_int_div_dec_{i:03d}",
        kind="int_div_int_to_decimal",
        difficulty="easy",
        question=question,
        answer=answer,
        answer_mode="number",
        hints=hints,
        steps=steps,
        meta=meta,
        explanation=explanation,
    )


def q_x10_shift(i: int) -> Q:
    x = Decimal(random.randint(12, 9999)) / Decimal(100)  # 0.12~99.99
    shift = random.choice([-3, -2, -1, 1, 2, 3])

    if shift > 0:
        mul = Decimal(10) ** shift
        expr = f"×{int(mul)}"
    else:
        mul = Decimal(10) ** shift
        expr = f"×{to_str(mul)}"

    raw = x * mul

    question = f"（互動）小數點移動：{to_str(x)} {expr} = ?"
    answer = to_str(raw)

    hints = [
        "觀念：只有乘以 10/100/1000 或 0.1/0.01/0.001，才是小數點左右移動。",
        f"規則：這題小數點要{'往右' if shift>0 else '往左'}移 {abs(shift)} 格；不夠就補 0。",
        "Level 3｜互動提示：移動後用大小感檢查（乘 >1 變大；乘 <1 變小）。",
    ]

    steps = [
        f"{to_str(x)} {expr}",
        f"小數點{'往右' if shift>0 else '往左'}移 {abs(shift)} 格",
        f"= {answer}",
        f"{'變大' if shift>0 else '變小'} ✓",
    ]

    meta = {"x": to_str(x), "shift": shift, "unit": "", "context": "x10_shift"}
    explanation = f"依規則移動小數點，得到 {answer}。"

    return Q(
        id=f"idg5_shift_{i:03d}",
        kind="x10_shift",
        difficulty="easy",
        question=question,
        answer=answer,
        answer_mode="exact",
        hints=hints,
        steps=steps,
        meta=meta,
        explanation=explanation,
    )


def build_bank(target_total: int = 240) -> List[Dict[str, Any]]:
    generators = {
        "d_mul_int": q_d_mul_int,
        "int_mul_d": q_int_mul_d,
        "d_mul_d": q_d_mul_d,
        "d_div_int": q_d_div_int,
        "int_div_int_to_decimal": q_int_div_int_to_decimal,
        "x10_shift": q_x10_shift,
    }

    quotas = {
        "d_mul_int": 55,
        "int_mul_d": 45,
        "d_mul_d": 40,
        "d_div_int": 40,
        "int_div_int_to_decimal": 30,
        "x10_shift": 30,
    }

    seen: set[str] = set()
    out: List[Dict[str, Any]] = []
    idx = 1

    def emit(q: Q) -> None:
        out.append(
            {
                "id": q.id,
                "kind": q.kind,
                "topic": TOPIC,
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

    for kind, target in quotas.items():
        made = 0
        attempts = 0
        gen = generators[kind]
        while made < target:
            attempts += 1
            if attempts > target * 800:
                raise RuntimeError(f"Unable to fill quota kind={kind} target={target} made={made}")

            q = gen(idx)
            if q.question in seen:
                continue
            seen.add(q.question)
            emit(q)
            idx += 1
            made += 1

    if len(out) < target_total:
        kinds = list(generators.keys())
        attempts = 0
        while len(out) < target_total:
            attempts += 1
            if attempts > (target_total - len(out)) * 1200:
                raise RuntimeError(f"Unable to reach target_total={target_total} got={len(out)}")
            kind = random.choice(kinds)
            q = generators[kind](idx)
            if q.question in seen:
                continue
            seen.add(q.question)
            emit(q)
            idx += 1

    return out


def main() -> None:
    bank = build_bank(target_total=240)
    OUT_JS.parent.mkdir(parents=True, exist_ok=True)

    payload = json.dumps(bank, ensure_ascii=False, indent=2)
    header = "/* Auto-generated offline question bank. */\nwindow.INTERACTIVE_DECIMAL_G5_BANK = "
    OUT_JS.write_text(header + payload + ";\n", encoding="utf-8")

    kinds = sorted({x["kind"] for x in bank})
    print(f"Wrote {OUT_JS} (n={len(bank)} kinds={len(kinds)}: {', '.join(kinds)})")


if __name__ == "__main__":
    main()
