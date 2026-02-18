# -*- coding: utf-8 -*-
"""Grade 5 fraction application word problems (offline)."""
from __future__ import annotations

import random
import math
import re
from fractions import Fraction
from typing import Dict, Any, List, Callable


def _fmt_fraction(f: Fraction) -> str:
    if f.denominator == 1:
        return str(f.numerator)
    return f"{f.numerator}/{f.denominator}"


def _fmt_mixed(f: Fraction) -> str:
    if f.denominator == 1:
        return str(f.numerator)
    whole = f.numerator // f.denominator
    rem = abs(f.numerator) % f.denominator
    if whole == 0:
        return _fmt_fraction(f)
    return f"{whole} {rem}/{f.denominator}"


def _choose_total_divisible(den: int, min_total: int = 12, max_total: int = 72) -> int:
    candidates = [t for t in range(min_total, max_total + 1) if t % den == 0]
    return random.choice(candidates)


def _steps(*items: str) -> List[str]:
    return [s.strip() for s in items if s and s.strip()]


def _is_ambiguous_wording(qtext: str) -> bool:
    text = str(qtext or "")
    patterns = [
        r"剩下的又看了\s*1(?:\s*/\s*1)?(?=[\s，。；！？])",
        r"剩下的又用掉\s*1(?:\s*/\s*1)?(?=[\s，。；！？])",
        r"剩下的又用了\s*1(?:\s*/\s*1)?(?=[\s，。；！？])",
    ]
    return any(re.search(p, text) for p in patterns)


def _template_fraction_of_quantity() -> Dict[str, Any]:
    den = random.choice([2, 3, 4, 5, 6, 8, 10, 12])
    num = random.randint(1, den - 1)
    total = _choose_total_divisible(den)
    amount = Fraction(total) * Fraction(num, den)
    q = f"一桶水有 {total} 公升，倒出其中的 {num}/{den}，倒出多少公升？"
    steps = _steps(
        "找出題目中的分數與總量。",
        f"計算 {num}/{den} × {total}。",
        f"{num}/{den} × {total} = {num * total}/{den} = {_fmt_fraction(amount)} 公升。",
    )
    return {"question": q, "answer": _fmt_fraction(amount), "steps": steps}


def _template_remaining_after_fraction() -> Dict[str, Any]:
    den = random.choice([3, 4, 5, 6, 8, 10, 12])
    num = random.randint(1, den - 1)
    total = _choose_total_divisible(den)
    remain_frac = Fraction(1, 1) - Fraction(num, den)
    remain_amt = Fraction(total) * remain_frac
    q = f"一條繩子長 {total} 公尺，用了 {num}/{den}，剩下多少公尺？"
    steps = _steps(
        f"剩下的比例是 1 - {num}/{den} = {_fmt_fraction(remain_frac)}。",
        f"再算剩下長度：{total} × {_fmt_fraction(remain_frac)}。",
        f"{total} × {_fmt_fraction(remain_frac)} = {_fmt_fraction(remain_amt)} 公尺。",
    )
    return {"question": q, "answer": _fmt_fraction(remain_amt), "steps": steps}


def _template_two_fractions_used() -> Dict[str, Any]:
    f1 = Fraction(random.randint(1, 3), random.choice([4, 5, 6, 8]))
    f2 = Fraction(random.randint(1, 3), random.choice([4, 5, 6, 8]))
    if f1 + f2 >= 1:
        f2 = Fraction(1, 4)
    remain = Fraction(1, 1) - (f1 + f2)
    q = f"一塊蛋糕先吃了 {_fmt_fraction(f1)}，又吃了 {_fmt_fraction(f2)}，還剩幾分之幾？"
    steps = _steps(
        f"先把吃掉的加起來：{_fmt_fraction(f1)} + {_fmt_fraction(f2)}。",
        f"吃掉的總和 = {_fmt_fraction(f1 + f2)}。",
        f"剩下 = 1 - {_fmt_fraction(f1 + f2)} = {_fmt_fraction(remain)}。",
    )
    return {"question": q, "answer": _fmt_fraction(remain), "steps": steps}


def _template_fraction_of_fraction() -> Dict[str, Any]:
    base = Fraction(random.randint(1, 3), random.choice([4, 5, 6, 8]))
    use = Fraction(random.randint(1, 3), random.choice([3, 4, 5, 6]))
    amount = base * use
    q = f"一瓶果汁有 {_fmt_fraction(base)} 公升，喝了其中的 {_fmt_fraction(use)}，喝了多少公升？"
    steps = _steps(
        "這是『分數的分數』問題，用乘法。",
        f"{_fmt_fraction(base)} × {_fmt_fraction(use)} = {_fmt_fraction(amount)} 公升。",
        "結果化為最簡分數。",
    )
    return {"question": q, "answer": _fmt_fraction(amount), "steps": steps}


def _template_read_pages() -> Dict[str, Any]:
    f1 = Fraction(random.randint(1, 3), random.choice([4, 5, 6, 8]))
    f2 = Fraction(random.randint(1, 3), random.choice([3, 4, 5, 6]))
    total = _choose_total_divisible(f1.denominator * f2.denominator, 60, 180)
    after_first = Fraction(total) * (1 - f1)
    read_second = after_first * f2
    remain = after_first - read_second
    q = f"一本書有 {total} 頁，先看了 {_fmt_fraction(f1)}，剩下的又看了 {_fmt_fraction(f2)}，還剩多少頁？"
    steps = _steps(
        f"第一次先看了 {_fmt_fraction(f1)}，所以第一次剩下頁數：{total} × (1 - {_fmt_fraction(f1)}) = {_fmt_fraction(after_first)}。",
        f"第二次是『在剩下裡』看了 {_fmt_fraction(f2)}，第二次看掉：{_fmt_fraction(after_first)} × {_fmt_fraction(f2)} = {_fmt_fraction(read_second)}。",
        f"最後剩下：第一次剩下 - 第二次看掉 = {_fmt_fraction(after_first)} - {_fmt_fraction(read_second)} = {_fmt_fraction(remain)} 頁。",
    )
    return {"question": q, "answer": _fmt_fraction(remain), "steps": steps}


def _template_mixed_number_remaining() -> Dict[str, Any]:
    whole = random.randint(2, 6)
    frac = Fraction(random.randint(1, 3), random.choice([4, 5, 6, 8]))
    total = Fraction(whole, 1) + frac
    use = Fraction(random.randint(1, 3), random.choice([4, 5, 6]))
    remain = total * (1 - use)
    q = f"一桶油有 {_fmt_mixed(total)} 公升，用了 {_fmt_fraction(use)}，剩下多少公升？"
    steps = _steps(
        f"把帶分數改成假分數：{_fmt_mixed(total)} = {_fmt_fraction(total)}。",
        f"剩下比例是 1 - {_fmt_fraction(use)} = {_fmt_fraction(1 - use)}。",
        f"{_fmt_fraction(total)} × {_fmt_fraction(1 - use)} = {_fmt_fraction(remain)} 公升。",
    )
    return {"question": q, "answer": _fmt_fraction(remain), "steps": steps}


def _template_class_boys() -> Dict[str, Any]:
    den = random.choice([4, 5, 6, 8, 10, 12])
    num = random.randint(1, den - 1)
    total = _choose_total_divisible(den, 24, 60)
    boys = Fraction(total) * Fraction(num, den)
    q = f"某班有 {total} 人，男生占 {_fmt_fraction(Fraction(num, den))}，男生有多少人？"
    steps = _steps(
        "用總人數乘以男生所占分數。",
        f"{total} × {_fmt_fraction(Fraction(num, den))} = {_fmt_fraction(boys)}。",
        "答案是人數(整數)。",
    )
    return {"question": q, "answer": _fmt_fraction(boys), "steps": steps}


def _template_money_original() -> Dict[str, Any]:
    spend = Fraction(random.randint(1, 3), random.choice([4, 5, 6]))
    remain_frac = Fraction(1, 1) - spend
    total = _choose_total_divisible(remain_frac.denominator, 30, 120)
    remain_amt = Fraction(total) * remain_frac
    q = f"小明花掉零用錢的 {_fmt_fraction(spend)}，還剩 {int(remain_amt)} 元，原來有多少元？"
    steps = _steps(
        f"剩下的比例是 1 - {_fmt_fraction(spend)} = {_fmt_fraction(remain_frac)}。",
        f"原來的錢 = 剩下的錢 ÷ 剩下比例 = {int(remain_amt)} ÷ {_fmt_fraction(remain_frac)}。",
        f"{int(remain_amt)} ÷ {_fmt_fraction(remain_frac)} = {total} 元。",
    )
    return {"question": q, "answer": str(total), "steps": steps}


def _template_orchard() -> Dict[str, Any]:
    den = random.choice([4, 5, 6, 8])
    num = random.randint(1, den - 1)
    total = _choose_total_divisible(den, 32, 96)
    apples = Fraction(total) * Fraction(num, den)
    pears = Fraction(total) - apples
    q = f"果園有 {total} 棵果樹，其中 {_fmt_fraction(Fraction(num, den))} 是蘋果樹，其餘是梨樹。梨樹有多少棵？"
    steps = _steps(
        f"先算蘋果樹：{total} × {_fmt_fraction(Fraction(num, den))} = {_fmt_fraction(apples)}。",
        f"梨樹 = 總數 - 蘋果樹 = {total} - {_fmt_fraction(apples)} = {_fmt_fraction(pears)}。",
        "答案是棵數(整數)。",
    )
    return {"question": q, "answer": _fmt_fraction(pears), "steps": steps}


def _template_tank_pour_out() -> Dict[str, Any]:
    den = random.choice([3, 4, 5, 6])
    num = random.randint(1, den - 1)
    capacity = _choose_total_divisible(den, 40, 80)
    current = Fraction(capacity) * Fraction(num, den)
    pour = Fraction(random.randint(1, 3), random.choice([2, 3, 4]))
    poured_amt = current * pour
    remain = current - poured_amt
    q = f"水箱容量 {capacity} 公升，現在有 {_fmt_fraction(Fraction(num, den))}。倒出現有水的 {_fmt_fraction(pour)}，還剩多少公升？"
    steps = _steps(
        f"先算現有水量：{capacity} × {_fmt_fraction(Fraction(num, den))} = {_fmt_fraction(current)}。",
        f"倒出現有的 {_fmt_fraction(pour)}：{_fmt_fraction(current)} × {_fmt_fraction(pour)} = {_fmt_fraction(poured_amt)}。",
        f"剩下：{_fmt_fraction(current)} - {_fmt_fraction(poured_amt)} = {_fmt_fraction(remain)} 公升。",
    )
    return {"question": q, "answer": _fmt_fraction(remain), "steps": steps}


def _template_area_fraction() -> Dict[str, Any]:
    f1 = Fraction(random.randint(1, 3), random.choice([3, 4, 5, 6]))
    f2 = Fraction(random.randint(1, 3), random.choice([3, 4, 5, 6]))
    result = f1 * f2
    q = f"一塊地的 {_fmt_fraction(f1)} 用來種菜，其中的 {_fmt_fraction(f2)} 種高麗菜。高麗菜占全地幾分之幾？"
    steps = _steps(
        "先找『分數的分數』，用乘法。",
        f"{_fmt_fraction(f1)} × {_fmt_fraction(f2)} = {_fmt_fraction(result)}。",
        "答案是占全地的比例。",
    )
    return {"question": q, "answer": _fmt_fraction(result), "steps": steps}


def _template_distance_total() -> Dict[str, Any]:
    f = Fraction(random.randint(2, 5), random.choice([6, 8, 10, 12]))
    remain_frac = 1 - f
    total = _choose_total_divisible(remain_frac.denominator, 12, 48)
    remain_dist = Fraction(total) * remain_frac
    q = f"小華走了全程的 {_fmt_fraction(f)}，還剩 {int(remain_dist)} 公里。全程長多少公里？"
    steps = _steps(
        f"剩下的比例是 1 - {_fmt_fraction(f)} = {_fmt_fraction(remain_frac)}。",
        f"全程 = 剩下距離 ÷ 剩下比例 = {int(remain_dist)} ÷ {_fmt_fraction(remain_frac)}。",
        f"計算得到全程 = {total} 公里。",
    )
    return {"question": q, "answer": str(total), "steps": steps}


def _template_oil_remaining() -> Dict[str, Any]:
    den = random.choice([3, 4, 5, 6, 8])
    num = random.randint(1, den - 1)
    total = _choose_total_divisible(den, 18, 60)
    remain = Fraction(total) * (1 - Fraction(num, den))
    q = f"一桶油重 {total} 公斤，用掉 {_fmt_fraction(Fraction(num, den))}，剩多少公斤？"
    steps = _steps(
        f"剩下的比例是 1 - {_fmt_fraction(Fraction(num, den))}。",
        f"剩下重量 = {total} × (1 - {_fmt_fraction(Fraction(num, den))}) = {_fmt_fraction(remain)}。",
        "答案是公斤數。",
    )
    return {"question": q, "answer": _fmt_fraction(remain), "steps": steps}


def _template_used_then_used_remaining() -> Dict[str, Any]:
    f1 = Fraction(random.randint(1, 3), random.choice([4, 5, 6]))
    f2 = Fraction(random.randint(1, 3), random.choice([3, 4, 5]))
    remain_frac = (1 - f1) * (1 - f2)
    q = f"一盒彩色筆先用掉 {_fmt_fraction(f1)}，剩下的又用掉 {_fmt_fraction(f2)}，最後剩幾分之幾？"
    steps = _steps(
        f"第一次先用掉 {_fmt_fraction(f1)}，所以第一次剩下比例：1 - {_fmt_fraction(f1)} = {_fmt_fraction(1 - f1)}。",
        f"第二次是『在剩下裡』用掉 {_fmt_fraction(f2)}，先算第二次剩下比例：1 - {_fmt_fraction(f2)} = {_fmt_fraction(1 - f2)}。",
        f"最後剩下比例：{_fmt_fraction(1 - f1)} × {_fmt_fraction(1 - f2)} = {_fmt_fraction(remain_frac)}。",
    )
    return {"question": q, "answer": _fmt_fraction(remain_frac), "steps": steps}


def _template_divide_fraction_by_int() -> Dict[str, Any]:
    base = Fraction(random.randint(1, 3), random.choice([4, 5, 6, 8]))
    cups = random.randint(4, 8)
    each = base / cups
    q = f"把 {_fmt_fraction(base)} 公升果汁平均倒入 {cups} 杯，每杯多少公升？"
    steps = _steps(
        "平均分配就是除以杯數。",
        f"{_fmt_fraction(base)} ÷ {cups} = {_fmt_fraction(base)}/{cups} = {_fmt_fraction(each)}。",
        "答案是每杯容量。",
    )
    return {"question": q, "answer": _fmt_fraction(each), "steps": steps}


def _template_add_fractions_total() -> Dict[str, Any]:
    f1 = Fraction(random.randint(1, 3), random.choice([4, 5, 6, 8]))
    f2 = Fraction(random.randint(1, 3), random.choice([4, 5, 6, 8]))
    total = f1 + f2
    if total >= 1:
        f2 = Fraction(1, 6)
        total = f1 + f2
    q = f"小華吃了披薩的 {_fmt_fraction(f1)}，小美又吃了 {_fmt_fraction(f2)}，一共吃了幾分之幾？"
    steps = _steps(
        f"同一個整體直接相加：{_fmt_fraction(f1)} + {_fmt_fraction(f2)}。",
        f"通分後相加得到 {_fmt_fraction(total)}。",
        "答案是吃掉的比例。",
    )
    return {"question": q, "answer": _fmt_fraction(total), "steps": steps}


def _template_discount_original_price() -> Dict[str, Any]:
    discount = Fraction(random.randint(1, 3), random.choice([4, 5, 6]))
    remain_frac = 1 - discount
    original = _choose_total_divisible(remain_frac.denominator, 200, 600)
    sale = Fraction(original) * remain_frac
    q = f"一件衣服打折 {_fmt_fraction(discount)}，折後售價 {int(sale)} 元，原價是多少元？"
    steps = _steps(
        f"折後價是原價的 {_fmt_fraction(remain_frac)}。",
        f"原價 = 折後價 ÷ {_fmt_fraction(remain_frac)} = {int(sale)} ÷ {_fmt_fraction(remain_frac)}。",
        f"計算得到原價 = {original} 元。",
    )
    return {"question": q, "answer": str(original), "steps": steps}


def _template_fill_pool_fraction() -> Dict[str, Any]:
    first = Fraction(random.randint(1, 3), random.choice([4, 5, 6]))
    second = Fraction(random.randint(1, 3), random.choice([2, 3, 4]))
    final = first + (1 - first) * second
    q = f"水池先注滿了 {_fmt_fraction(first)}，再把剩下的注滿其中的 {_fmt_fraction(second)}，現在水量占全池幾分之幾？"
    steps = _steps(
        f"第一次後剩下比例：1 - {_fmt_fraction(first)} = {_fmt_fraction(1 - first)}。",
        f"第二次增加：{_fmt_fraction(1 - first)} × {_fmt_fraction(second)} = {_fmt_fraction((1 - first) * second)}。",
        f"總水量 = {_fmt_fraction(first)} + {_fmt_fraction((1 - first) * second)} = {_fmt_fraction(final)}。",
    )
    return {"question": q, "answer": _fmt_fraction(final), "steps": steps}


def _template_time_ratio() -> Dict[str, Any]:
    f_part = Fraction(random.randint(3, 7), 8)
    f_dist = Fraction(random.randint(3, 5), 6)
    total_time = f_part / f_dist
    q = f"走完全程需要多少小時？若走了全程的 {_fmt_fraction(f_dist)} 時，用了 {_fmt_fraction(f_part)} 小時。"
    steps = _steps(
        "已用時間是全程時間的部分，用除法求全程時間。",
        f"全程時間 = {_fmt_fraction(f_part)} ÷ {_fmt_fraction(f_dist)}。",
        f"計算：{_fmt_fraction(f_part)} × {f_dist.denominator}/{f_dist.numerator} = {_fmt_fraction(total_time)} 小時。",
    )
    return {"question": q, "answer": _fmt_fraction(total_time), "steps": steps}


def _template_recipe_scale() -> Dict[str, Any]:
    base = Fraction(random.randint(1, 3), random.choice([4, 5, 6, 8]))
    scale = Fraction(random.randint(1, 3), random.choice([2, 3, 4]))
    need = base * scale
    q = f"做 1 份蛋糕要用糖 {_fmt_fraction(base)} 杯，現在只做 {_fmt_fraction(scale)} 份，需要多少杯糖？"
    steps = _steps(
        "份量縮小，用原來用量乘以比例。",
        f"{_fmt_fraction(base)} × {_fmt_fraction(scale)} = {_fmt_fraction(need)} 杯。",
        "答案是需要的糖量。",
    )
    return {"question": q, "answer": _fmt_fraction(need), "steps": steps}


def _template_share_distance() -> Dict[str, Any]:
    den = random.choice([5, 6, 8, 10])
    num = random.randint(1, den - 1)
    total = _choose_total_divisible(den, 20, 80)
    part = Fraction(total) * Fraction(num, den)
    q = f"全程 {total} 公里，小明走了其中的 {_fmt_fraction(Fraction(num, den))}，他走了多少公里？"
    steps = _steps(
        "用總長乘以所占分數。",
        f"{total} × {_fmt_fraction(Fraction(num, den))} = {_fmt_fraction(part)}。",
        "答案是公里數。",
    )
    return {"question": q, "answer": _fmt_fraction(part), "steps": steps}


def _template_remaining_after_fill() -> Dict[str, Any]:
    total = _choose_total_divisible(4, 24, 80)
    filled = Fraction(random.randint(1, 3), 4)
    remain = Fraction(total) * (1 - filled)
    q = f"水桶容量 {total} 公升，已裝了 {_fmt_fraction(filled)}，還可以裝多少公升？"
    steps = _steps(
        f"剩下比例是 1 - {_fmt_fraction(filled)} = {_fmt_fraction(1 - filled)}。",
        f"可再裝 = {total} × {_fmt_fraction(1 - filled)} = {_fmt_fraction(remain)} 公升。",
        "答案是還能裝的容量。",
    )
    return {"question": q, "answer": _fmt_fraction(remain), "steps": steps}


def generate_fraction_word_problem_g5() -> Dict[str, Any]:
    item: Dict[str, Any] = {}
    for _ in range(24):
        candidate = random.choice(_templates())()
        if not _is_ambiguous_wording(str(candidate.get("question", ""))):
            item = candidate
            break
    if not item:
        item = _template_fraction_of_quantity()

    raw_steps = list(item.get("steps", []) or [])
    q = str(item["question"])
    kind = _infer_kind(q)
    scaffold = _scaffold_steps(kind)
    # Put conceptual guidance first (good for 3-level hints), then the numeric work.
    steps = scaffold + raw_steps + ["檢查：答案是否合理、單位是否正確，最後再寫成最簡分數/帶分數。"]
    explanation = "\n".join([f"步驟 {i + 1}：{s}" for i, s in enumerate(steps)])
    return {
        "topic": "分數應用題(五年級)",
        "difficulty": "medium",
        "question": q,
        "answer": item["answer"],
        "steps": steps,
        "explanation": explanation,
    }


def template_count() -> int:
    return len(_templates())


def _templates() -> List[Callable[[], Dict[str, Any]]]:
    return [
        _template_fraction_of_quantity,
        _template_remaining_after_fraction,
        _template_two_fractions_used,
        _template_fraction_of_fraction,
        _template_read_pages,
        _template_mixed_number_remaining,
        _template_class_boys,
        _template_money_original,
        _template_orchard,
        _template_tank_pour_out,
        _template_area_fraction,
        _template_distance_total,
        _template_oil_remaining,
        _template_used_then_used_remaining,
        _template_divide_fraction_by_int,
        _template_add_fractions_total,
        _template_discount_original_price,
        _template_fill_pool_fraction,
        _template_time_ratio,
        _template_recipe_scale,
        _template_share_distance,
        _template_remaining_after_fill,
    ]


def _infer_kind(qtext: str) -> str:
    qtext = str(qtext or "")
    if re.search(r"平均.*(杯|份|段|人|盒|袋|盤)", qtext):
        return "average_division"
    if re.search(r"(?:走了全程的|做了全程的|完成了)\s*\d+\s*/\s*\d+", qtext) and re.search(r"用[了]?\s*\d+\s*/\s*\d+\s*(小時|分鐘)", qtext):
        return "reverse_fraction"
    if re.search(r"(原來|原價|全程(長|需要)|原本)", qtext) and re.search(r"(還剩|折後|剩)", qtext):
        return "reverse_fraction"
    if re.search(r"剩下的又", qtext) or (
        re.search(r"剩下的", qtext)
        and re.search(r"(又|再)", qtext)
        and re.search(r"\d+\s*/\s*\d+", qtext)
    ):
        return "remain_then_fraction"
    if re.search(r"(先|又).*(吃|用|看|走).*(先|又)", qtext):
        return "two_steps_used"
    if re.search(r"其中的", qtext) and re.search(r"占", qtext):
        return "fraction_of_fraction"
    if re.search(r"(倒出|用了|吃了|看了|走了).*(剩下多少|還剩|剩多少)", qtext):
        return "remaining_after_fraction"
    if re.search(r"(倒出|走了|用掉|占).*(\d+\s*/\s*\d+)", qtext):
        return "fraction_of_quantity"
    return "generic_fraction_word"


def _scaffold_steps(kind: str) -> List[str]:
    # IMPORTANT: First 3 steps should not reveal the final numeric answer.
    s1 = "圈出題目已知：『總量/剩下量』、『分數』、『單位』。"
    if kind == "average_division":
        s2 = "判斷題型：『平均分配』通常用除法（總量 ÷ 份數）。"
        s3 = "先列式（不急著算）：把總量寫成分數或帶分數，再除以份數。"
    elif kind == "reverse_fraction":
        s2 = "判斷題型：這是反推題，已知『全程的一部分』對應的量（或剩下/折後），要倒回去求全程。"
        s3 = "可列式：全程 × 已知分率 = 已知量；倒回去算用『已知量 ÷ 已知分率』（除以分數=乘倒數）。"
    elif kind == "remain_then_fraction":
        s2 = "判斷題型：『先用掉一些 → 剩下一些 → 再用掉剩下的一部分』，分兩段。"
        s3 = "列式：第一次剩下 = 1 − 第一次用掉分數；第二次用掉 = 第一次剩下 × 第二次用掉分數；最後剩下 = 第一次剩下 − 第二次用掉（或 第一次剩下 × (1 − 第二次用掉分數)）。"
    elif kind == "two_steps_used":
        s2 = "判斷題型：『同一個整體』先用掉一些（第一次），又用掉一些（第二次），兩次都是針對原來的整體。"
        s3 = "列式：總用掉 = 第一次用掉分數 + 第二次用掉分數（先通分再相加）；若問『剩下』：剩下 = 1 − 總用掉；若問『用掉』：答案就是總用掉。"
    elif kind == "fraction_of_fraction":
        s2 = "判斷題型：『其中的…』是『分數的分數』，用乘法。"
        s3 = "先列式（不急著算）：占全體 = 第一個分數 × 第二個分數。"
    elif kind == "remaining_after_fraction":
        s2 = "判斷題型：題目問『剩下』，先求剩下比例（1 - 用掉比例）。"
        s3 = "用：剩下量 = 總量 × 剩下比例（再視情況約分）。"
    elif kind == "fraction_of_quantity":
        s2 = "判斷題型：『某量的幾分之幾』，用乘法（總量 × 分數）。"
        s3 = "先列式（不急著算）：總量 × (分子/分母)，可先做約分讓計算更快。"
    else:
        s2 = "把文字轉算式：看到『幾分之幾的…』多半用乘法；看到『平均』多半用除法。"
        s3 = "先列式，再計算，最後約分到最簡並檢查合理性。"
    return [s1, s2, s3]
