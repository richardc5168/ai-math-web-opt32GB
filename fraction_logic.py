#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, TYPE_CHECKING
from urllib.parse import quote_plus

try:
    import sympy as sp

    Rational = sp.Rational
except Exception:  # pragma: no cover
    sp = None
    Rational = None

if TYPE_CHECKING:  # pragma: no cover
    import sympy as _sp

    SympyRational = _sp.Rational
else:
    SympyRational = Any


# 國小五年級分數乘法技能樹 (DAG)
# id 以 E1..E5 對應關卡，prereqs 以 id 表示依賴。
fraction_graph: Dict[str, Dict[str, Any]] = {
    "整數乘法與因數": {"id": "E1", "prereqs": []},
    "約分與最簡分數": {"id": "E2", "prereqs": ["E1"]},
    "帶分數與假分數互換": {"id": "E3", "prereqs": []},
    "真分數乘法": {"id": "E4", "prereqs": ["E2"]},
    "帶分數乘法": {"id": "E5", "prereqs": ["E3", "E4"]},
}


@dataclass(frozen=True)
class DiagnoseResult:
    ok: bool
    weak_point: str
    weak_id: str
    diagnosis_code: str
    message: str
    next_hint: str
    retry_prompt: str
    resource_url: str
    expected_step1: str
    expected_step2: str
    expected_step3: str
    expected_mixed: str


def _normalize_text(s: str) -> str:
    return (
        str(s or "")
        .strip()
        .replace("−", "-")
        .replace("／", "/")
        .replace("，", ",")
        .replace("、", ",")
        .replace("＝", "=")
    )


def _require_sympy():
    if sp is None or Rational is None:
        raise RuntimeError("sympy is required for fraction_logic")


def parse_rational(text: str) -> SympyRational:
    """Parse integer / a/b / mixed (a b/c) into exact Rational."""

    _require_sympy()

    s = _normalize_text(text)
    if not s:
        raise ValueError("empty")

    # mixed: a b/c
    import re

    m = re.fullmatch(r"\s*(-?\d+)\s+(\d+)\s*/\s*(\d+)\s*", s)
    if m:
        whole = int(m.group(1))
        num = int(m.group(2))
        den = int(m.group(3))
        if den == 0:
            raise ValueError("zero denominator")
        if num < 0 or den < 0:
            raise ValueError("mixed numerator/denominator must be positive")
        sign = -1 if whole < 0 else 1
        abs_whole = abs(whole)
        return Rational(sign * (abs_whole * den + num), den)

    # fraction: a/b
    m = re.fullmatch(r"\s*(-?\d+)\s*/\s*(\d+)\s*", s)
    if m:
        num = int(m.group(1))
        den = int(m.group(2))
        if den == 0:
            raise ValueError("zero denominator")
        return Rational(num, den)

    # integer
    m = re.fullmatch(r"\s*(-?\d+)\s*", s)
    if m:
        return Rational(int(m.group(1)), 1)

    raise ValueError("unsupported format")


def rational_to_frac_str(r: SympyRational) -> str:
    _require_sympy()
    r = sp.Rational(r)
    if r.q == 1:
        return str(int(r))
    return f"{int(r.p)}/{int(r.q)}"


def rational_to_mixed_str(r: SympyRational) -> str:
    _require_sympy()

    r = sp.Rational(r)
    if r.q == 1:
        return str(int(r))

    sign = -1 if r < 0 else 1
    n = abs(int(r.p))
    d = int(r.q)

    whole = n // d
    rem = n % d

    if whole == 0:
        return ("-" if sign < 0 else "") + f"{rem}/{d}"

    return ("-" if sign < 0 else "") + f"{whole} {rem}/{d}"


def recommend_fraction_resource(weak_point: str) -> str:
    search_map = {
        "帶分數與假分數互換": "帶分數 變 假分數 教學",
        "約分與最簡分數": "五年級 約分 觀念",
        "真分數乘法": "分數 乘法 分子分母 怎麼算",
        "帶分數乘法": "帶分數 乘法 怎麼算",
    }

    query = f"國小數學 五年級 {search_map.get(weak_point, weak_point)} 均一"
    return "https://www.youtube.com/results?search_query=" + quote_plus(query)


def _id_for_point(name: str) -> str:
    node = fraction_graph.get(name)
    if node and isinstance(node, dict):
        return str(node.get("id") or "")
    return ""


def diagnose_mixed_multiply(
    left: str,
    right: str,
    step1: Optional[str] = None,
    step2: Optional[str] = None,
    step3: Optional[str] = None,
) -> DiagnoseResult:
    """Diagnose a student's mixed-number multiplication process.

    Steps (suggested):
      step1: convert left mixed number to improper fraction
      step2: multiply (raw result; not necessarily reduced)
      step3: simplify to lowest terms / mixed number

    Returns teacher-like guidance + a YouTube search URL.
    """

    _require_sympy()

    left_r = parse_rational(left)
    right_r = parse_rational(right)

    expected1 = left_r
    raw = Rational(left_r.p * right_r.p, left_r.q * right_r.q)
    expected3 = sp.together(left_r * right_r)

    # Normalize expected strings
    expected_step1 = rational_to_frac_str(expected1)
    expected_step2 = f"{int(raw.p)}/{int(raw.q)}"
    expected_step3 = rational_to_frac_str(expected3)
    expected_mixed = rational_to_mixed_str(expected3)

    def try_parse(x: Optional[str]) -> Optional[SympyRational]:
        if x is None:
            return None
        x = _normalize_text(x)
        if not x:
            return None
        try:
            return parse_rational(x)
        except Exception:
            return None

    s1 = try_parse(step1)
    s2 = try_parse(step2)
    s3 = try_parse(step3)

    # Also keep original text to detect "needs simplification" cases.
    step3_text = _normalize_text(step3 or "")

    # --- decision rules (simple + kid-friendly) ---
    if s1 is None or sp.simplify(s1 - expected1) != 0:
        weak_point = "帶分數與假分數互換"
        weak_id = _id_for_point(weak_point) or "E3"

        # Common mistakes: (whole+num)/den, num/den
        import re

        friendly_tip = ""
        # Try to infer whole/num/den from left input if it looks like mixed
        m = re.fullmatch(r"\s*(-?\d+)\s+(\d+)\s*/\s*(\d+)\s*", _normalize_text(left))
        if m:
            whole = int(m.group(1))
            num = int(m.group(2))
            den = int(m.group(3))
            wrong1 = Rational(whole + num, den)  # forgot "×den"
            wrong2 = Rational(num, den)  # dropped whole part
            if s1 is not None and sp.simplify(s1 - wrong1) == 0:
                friendly_tip = (
                    "我猜你把它算成 (整數 + 分子)/分母 了。\n"
                    "記得是：整數要先『乘分母』才加分子喔！"
                )
            elif s1 is not None and sp.simplify(s1 - wrong2) == 0:
                friendly_tip = (
                    "我猜你只留下了分數的部分，忘記把整數也算進去。\n"
                    "帶分數 = 整數 + 真分數，整數不能不見。"
                )

        msg = (
            "我們先做一個小任務：把左邊『帶分數』換成『假分數』。\n"
            "這一步做好了，後面就很順。"
        )
        if friendly_tip:
            msg = msg + "\n\n" + friendly_tip
        hint = "公式：a b/c → (a×c+b)/c（整數要先×分母，再+分子）"

        retry = "先只做 Step 1：你可以再算一次 (整數×分母+分子)/分母 嗎？"
        m2 = re.fullmatch(r"\s*(-?\d+)\s+(\d+)\s*/\s*(\d+)\s*", _normalize_text(left))
        if m2:
            whole = int(m2.group(1))
            num = int(m2.group(2))
            den = int(m2.group(3))
            retry = (
                f"先算：{abs(whole)}×{den}+{num} = ?\n"
                f"再把它寫成：(?)/{den}。"
            )

        return DiagnoseResult(
            ok=False,
            weak_point=weak_point,
            weak_id=weak_id,
            diagnosis_code="E3_CONVERT_TO_IMPROPER",
            message=msg,
            next_hint=hint,
            retry_prompt=retry,
            resource_url=recommend_fraction_resource(weak_point),
            expected_step1=expected_step1,
            expected_step2=expected_step2,
            expected_step3=expected_step3,
            expected_mixed=expected_mixed,
        )

    # Step2: accept either raw result OR any equivalent value (some kids simplify early).
    if s2 is None or (sp.simplify(s2 - raw) != 0 and sp.simplify(s2 - expected3) != 0):
        weak_point = "真分數乘法"
        weak_id = _id_for_point(weak_point) or "E4"
        # Try to detect common kid mistakes to give a sharper, more teacher-like hint.
        friendly_tip = ""
        if s2 is not None:
            try:
                # If right is an integer k:
                if int(right_r.q) == 1:
                    k = int(right_r.p)
                    # Common wrong: multiply only the denominator (a/b)*k -> a/(b*k)
                    wrong_divide_like = Rational(int(expected1.p), int(expected1.q) * k)
                    if k != 0 and sp.simplify(s2 - wrong_divide_like) == 0:
                        friendly_tip = (
                            "我猜你把『×整數』做成『分母也乘一次』了。\n"
                            "提醒：乘法要讓分子也一起乘，才會變大：a/b × k = (a×k)/b。"
                        )

                # If right is a fraction c/d:
                if int(right_r.q) != 1:
                    a = int(expected1.p)
                    b = int(expected1.q)
                    c = int(right_r.p)
                    d = int(right_r.q)

                    # Common wrong: a/b × c/d -> (a×c)/(b+d)
                    wrong_add_den = Rational(a * c, b + d) if (b + d) != 0 else None
                    if wrong_add_den is not None and sp.simplify(s2 - wrong_add_den) == 0:
                        friendly_tip = (
                            "我猜你把分母做『相加』了。\n"
                            "分數乘法不是通分相加：要『分子×分子、分母×分母』喔！"
                        )

                    # Common wrong: (a/b) × (c/d) -> (a+c)/(b+d)
                    wrong_add_both = Rational(a + c, b + d) if (b + d) != 0 else None
                    if not friendly_tip and wrong_add_both is not None and sp.simplify(s2 - wrong_add_both) == 0:
                        friendly_tip = (
                            "我猜你把分子分母都做『相加』了。\n"
                            "提醒：乘法要用『乘』，不是相加：a/b × c/d = (a×c)/(b×d)。"
                        )
            except Exception:
                pass

        msg = "帶分數換成假分數做對了 👍\n下一步：分子×分子、分母×分母。"
        if friendly_tip:
            msg = msg + "\n\n" + friendly_tip
        hint = "規則：a/b × c/d = (a×c)/(b×d)。先寫未約分也可以。"
        retry = f"請把 {expected_step1} × {rational_to_frac_str(right_r)} 寫成一個分數（分子相乘 / 分母相乘）。"
        return DiagnoseResult(
            ok=False,
            weak_point=weak_point,
            weak_id=weak_id,
            diagnosis_code="E4_FRACTION_MULTIPLY",
            message=msg,
            next_hint=hint,
            retry_prompt=retry,
            resource_url=recommend_fraction_resource(weak_point),
            expected_step1=expected_step1,
            expected_step2=expected_step2,
            expected_step3=expected_step3,
            expected_mixed=expected_mixed,
        )

    if s3 is None:
        weak_point = "約分與最簡分數"
        weak_id = _id_for_point(weak_point) or "E2"
        msg = "乘法結果有了！最後一步：把分數約分到最簡（需要時再轉回帶分數）。"
        hint = "做法：找分子分母的公因數（2、3、5…），分子分母同除同一個數，直到不能再除。"
        return DiagnoseResult(
            ok=False,
            weak_point=weak_point,
            weak_id=weak_id,
            diagnosis_code="E2_SIMPLIFY_MISSING",
            message=msg,
            next_hint=hint,
            retry_prompt=f"把 Step 2 的 {expected_step2} 約分成最簡，寫成 Step 3。",
            resource_url=recommend_fraction_resource(weak_point),
            expected_step1=expected_step1,
            expected_step2=expected_step2,
            expected_step3=expected_step3,
            expected_mixed=expected_mixed,
        )

    # If step3 equals expected3 but student's representation not reduced? our parse already reduces; compare.
    if sp.simplify(s3 - expected3) != 0:
        weak_point = "約分與最簡分數"
        weak_id = _id_for_point(weak_point) or "E2"
        msg = "快完成了，但最後化簡結果不正確。"
        hint = "提醒：分子分母要同除『同一個數』，而且要除到不能再除。"
        return DiagnoseResult(
            ok=False,
            weak_point=weak_point,
            weak_id=weak_id,
            diagnosis_code="E2_SIMPLIFY_WRONG",
            message=msg,
            next_hint=hint,
            retry_prompt=f"從 {expected_step2} 開始：先試同除 2，再試同除 3…直到不能再除。",
            resource_url=recommend_fraction_resource(weak_point),
            expected_step1=expected_step1,
            expected_step2=expected_step2,
            expected_step3=expected_step3,
            expected_mixed=expected_mixed,
        )

    # Special: if they typed a reducible fraction equivalent to the final answer, nudge them to reduce.
    # This is kid-friendly and helps build the E2 habit.
    if step3_text and "/" in step3_text and " " not in step3_text:
        try:
            n_str, d_str = step3_text.split("/", 1)
            n0 = int(n_str.strip())
            d0 = int(d_str.strip())
            if d0 != 0:
                from math import gcd as _gcd

                g0 = _gcd(abs(n0), abs(d0))
                if g0 != 1 and sp.simplify(Rational(n0, d0) - expected3) == 0:
                    weak_point = "約分與最簡分數"
                    weak_id = _id_for_point(weak_point) or "E2"
                    msg = "你的值其實是對的，但還可以再約分一次，讓答案更漂亮（最簡分數）。"
                    hint = f"你這個分數分子分母還能同除 {g0}：分子÷{g0}、分母÷{g0}。"
                    return DiagnoseResult(
                        ok=False,
                        weak_point=weak_point,
                        weak_id=weak_id,
                        diagnosis_code="E2_NEEDS_REDUCTION",
                        message=msg,
                        next_hint=hint,
                        retry_prompt="把分子分母同除一樣的數，寫出最簡分數。",
                        resource_url=recommend_fraction_resource(weak_point),
                        expected_step1=expected_step1,
                        expected_step2=expected_step2,
                        expected_step3=expected_step3,
                        expected_mixed=expected_mixed,
                    )
        except Exception:
            pass

    weak_point = "帶分數乘法"
    weak_id = _id_for_point(weak_point) or "E5"
    msg = "太好了！你的每一步都正確 ✅"
    hint = "下一題也用同樣流程：換成假分數 → 相乘 → 約分 →（需要時）轉回帶分數。"
    return DiagnoseResult(
        ok=True,
        weak_point=weak_point,
        weak_id=weak_id,
        diagnosis_code="E5_ALL_CORRECT",
        message=msg,
        next_hint=hint,
        retry_prompt="",
        resource_url=recommend_fraction_resource(weak_point),
        expected_step1=expected_step1,
        expected_step2=expected_step2,
        expected_step3=expected_step3,
        expected_mixed=expected_mixed,
    )
