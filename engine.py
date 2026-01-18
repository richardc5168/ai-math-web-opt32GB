#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ALL-IN-ONE: Math Practice MVP (FastAPI backend + Engine in one file)
- 單檔可直接跑：含出題/判題/自訂題目解題(solve_custom)/作答記錄/報表
- 多學生（同一付費帳號下可綁多學生）
- 訂閱 gate（MVP：DB subscription.status=active 才能用）
- Auth（MVP：用 X-API-Key 對應 account）

啟動：
  pip install fastapi uvicorn
  uvicorn math_app:app --reload --port 8000
或：
  python3 math_app.py

測試：
  1) 建立測試帳號+訂閱+學生：
     curl -X POST "http://127.0.0.1:8000/admin/bootstrap?name=TestAccount"
  2) 查學生：
     curl -H "X-API-Key: <api_key>" "http://127.0.0.1:8000/v1/students"
  3) 出題：
     curl -X POST -H "X-API-Key: <api_key>" "http://127.0.0.1:8000/v1/questions/next?student_id=1"
  4) 交卷：
     curl -X POST -H "X-API-Key: <api_key>" -H "Content-Type: application/json" \
       -d '{"student_id":1,"question_id":1,"user_answer":"1/2","time_spent_sec":12}' \
       "http://127.0.0.1:8000/v1/answers/submit"
  5) 自訂題目解題：
     curl -X POST -H "X-API-Key: <api_key>" -H "Content-Type: application/json" \
       -d '{"question":"1/2 + 1/3"}' \
       "http://127.0.0.1:8000/v1/custom/solve"
  6) 自訂題目記錄作答（可用 auto 或手動答案）：
     curl -X POST -H "X-API-Key: <api_key>" -H "Content-Type: application/json" \
       -d '{"student_id":1,"question":"1/2+1/3","final_answer":"5/6","user_answer":"5/6","time_spent_sec":20}' \
       "http://127.0.0.1:8000/v1/custom/submit"
"""

import os
import re
import math
import json
import random
import sqlite3
from datetime import datetime, timedelta
from fractions import Fraction
from typing import Optional, Dict, Any, List, Tuple

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

# -------------------------
# Optional: SymPy
# -------------------------
try:
    import sympy as sp
    HAS_SYMPY = True
except Exception:
    HAS_SYMPY = False


# ======================================================================
# ENGINE (出題 / 判題 / 自訂題目解題)
# ======================================================================

MAX_2DIGIT = 99

def _within_2digit_int(x: int) -> bool:
    return abs(int(x)) <= MAX_2DIGIT

def _within_2digit_fraction(f: Fraction) -> bool:
    return abs(f.numerator) <= MAX_2DIGIT and abs(f.denominator) <= MAX_2DIGIT

def _lcm(a: int, b: int) -> int:
    return (a * b) // math.gcd(a, b)

def _lcm3(a: int, b: int, c: int) -> int:
    ab = _lcm(a, b)
    return _lcm(ab, c)

# -------------------------
# Answer parsing & checking
# -------------------------
def parse_answer(text: str) -> Optional[Fraction]:
    text = (text or "").strip()
    if not text:
        return None
    try:
        # 帶分數 "1 1/2"
        if " " in text and "/" in text:
            parts = text.split()
            if len(parts) == 2:
                w = int(parts[0])
                f = Fraction(parts[1])
                return (Fraction(w, 1) + f) if w >= 0 else (Fraction(w, 1) - f)
        # 假分數/整數
        return Fraction(text)
    except Exception:
        return None

def check(user_answer: str, correct_answer: str) -> Optional[int]:
    """
    return:
      1 = correct
      0 = incorrect
      None = invalid format / cannot parse
    """
    user = (user_answer or "").strip()
    correct = (correct_answer or "").strip()

    # 多值答案（以空格分隔）：GCD LCM、通分、公分母 新分子...
    user_clean = re.sub(r'[^0-9\s]', '', user)
    correct_clean = re.sub(r'[^0-9\s]', '', correct)

    if correct_clean.count(' ') > 0:
        return 1 if ' '.join(user_clean.split()) == ' '.join(correct_clean.split()) else 0

    u = parse_answer(user)
    c = parse_answer(correct)
    if u is None or c is None:
        return None
    return 1 if u == c else 0


# -------------------------
# Weakness diagnosis (internal)
# -------------------------
def _ints_from_text(text: str) -> List[int]:
    return [int(x) for x in re.findall(r"-?\d+", (text or ""))]


def _hint_pack(*levels: str) -> List[str]:
    packed = [l.strip() for l in levels if l and l.strip()]
    # Always provide 3 levels for API simplicity.
    while len(packed) < 3:
        packed.append(packed[-1] if packed else "請先整理題意，逐步計算。")
    return packed[:3]


def _drill(topic_key: str, count: int, note: str = "") -> Dict[str, Any]:
    name = GENERATORS.get(topic_key, (topic_key, None))[0]
    return {"topic_key": topic_key, "topic_name": name, "count": int(count), "note": note}


def get_question_hints(qobj: Dict[str, Any]) -> Dict[str, str]:
    """Generate 3-level hint strings WITHOUT revealing the final answer."""
    topic = str(qobj.get("topic") or "")
    qtext = str(qobj.get("question") or "")

    # 通分
    if "通分" in topic or "依序輸入：公分母" in qtext:
        h = _hint_pack(
            "先找兩個分母的最小公倍數(LCM)，當作公分母。",
            "把每個分數的分母乘到 LCM；分子也要乘同樣倍數。",
            "檢查：新分母都一樣(=LCM)，再確認新分子是否同步乘上倍數。",
        )
        return {"level1": h[0], "level2": h[1], "level3": h[2]}

    # 約分
    if "約分" in topic or "約分到最簡" in qtext:
        h = _hint_pack(
            "找分子與分母的最大公因數(GCD)。",
            "分子、分母同時除以同一個 GCD。",
            "做到最簡：分子與分母不能再同時被 2,3,5... 整除。",
        )
        return {"level1": h[0], "level2": h[1], "level3": h[2]}

    # 分數加減/連續
    if "分數加減" in topic or "分數連續加減" in topic or re.search(r"\d+/\d+\s*[\+\-]", qtext):
        h = _hint_pack(
            "分母不同不能直接加減分子：先通分。",
            "用 LCM 當共同分母；把每個分數換成同分母後再做分子加減。",
            "最後記得約分到最簡(能約就約)。",
        )
        return {"level1": h[0], "level2": h[1], "level3": h[2]}

    # 帶分數
    if "帶分數" in topic or re.search(r"\d+\s+\d+/\d+", qtext):
        h = _hint_pack(
            "先把帶分數轉成假分數再運算。",
            "假分數：整數×分母 + 分子，分母不變。",
            "算完可再換回帶分數(整數 + 真分數)，並約分。",
        )
        return {"level1": h[0], "level2": h[1], "level3": h[2]}

    # 四則運算(順序)
    if "括號" in qtext or "×" in qtext or "÷" in qtext:
        h = _hint_pack(
            "口訣：括號 → 乘除 → 加減。",
            "先把括號算完，再做乘除，最後由左到右做加減。",
            "每一步寫出中間結果，避免跳步算錯。",
        )
        return {"level1": h[0], "level2": h[1], "level3": h[2]}

    h = _hint_pack("先整理題意，逐步計算。", "寫出中間步驟再檢查。", "若不確定，先把題目拆成小步驟。")
    return {"level1": h[0], "level2": h[1], "level3": h[2]}


def diagnose_attempt(qobj: Dict[str, Any], user_answer: str) -> Dict[str, Any]:
    """Classify common mistake patterns for G5 fractions + order-of-ops.

    Returns: {error_tag, error_detail, hint_plan, drill_reco}
    """
    topic = str(qobj.get("topic") or "")
    qtext = str(qobj.get("question") or "")
    correct = str(qobj.get("correct_answer") or qobj.get("answer") or "").strip()
    user = (user_answer or "").strip()

    # Default drill recos: keep small set.
    base_recos: List[Dict[str, Any]] = []

    # 通分題：答案格式：lcm na1 na2
    if "通分" in topic or "依序輸入：公分母" in qtext:
        c_parts = _ints_from_text(correct)
        u_parts = _ints_from_text(user)
        if len(u_parts) < 3:
            return {
                "error_tag": "FORMAT_INVALID",
                "error_detail": "通分題需要輸入 3 個整數：公分母 新分子1 新分子2。",
                "hint_plan": _hint_pack(
                    "請輸入三個數字，用空格分開：LCM 新分子1 新分子2。",
                    "先求 LCM(分母1, 分母2)。",
                    "用 LCM 通分：分母乘幾倍，分子也乘幾倍。",
                ),
                "drill_reco": [_drill("2", 8, "先把通分練熟")],
            }
        if len(c_parts) >= 3:
            c_lcm, c_na1, c_na2 = c_parts[0], c_parts[1], c_parts[2]
        else:
            c_lcm, c_na1, c_na2 = 0, 0, 0

        u_lcm, u_na1, u_na2 = u_parts[0], u_parts[1], u_parts[2]
        if u_lcm != c_lcm:
            return {
                "error_tag": "LCM_WRONG",
                "error_detail": f"公分母(LCM) 應為 {c_lcm}，你填的是 {u_lcm}。",
                "hint_plan": _hint_pack(
                    "先只做一件事：找兩個分母的 LCM。",
                    "列倍數法：寫出兩個分母的倍數，找到第一個相同的。",
                    "用 gcd：LCM(a,b) = a*b/gcd(a,b)。",
                ),
                "drill_reco": [_drill("2", 10, "加強 LCM/通分")],
            }
        if (u_na1, u_na2) != (c_na1, c_na2):
            return {
                "error_tag": "COMMON_DENOM_WRONG",
                "error_detail": "公分母對了，但至少一個新分子不對（可能倍數沒有同步乘到分子）。",
                "hint_plan": _hint_pack(
                    "先算倍數：LCM ÷ 原分母 = 要乘的倍數。",
                    "新分子 = 原分子 × 倍數（兩個分數都要做）。",
                    "檢查：換成新分數後，分母都等於 LCM。",
                ),
                "drill_reco": [_drill("2", 8, "通分的倍數要一致")],
            }

        return {
            "error_tag": "OTHER",
            "error_detail": "與典型通分錯誤模式不匹配。",
            "hint_plan": _hint_pack("再檢查一次倍數是否正確。", "把每一步寫出來。", "確認新分母都等於 LCM。"),
            "drill_reco": [_drill("2", 5, "再練幾題通分")],
        }

    # 約分題：答案格式：num den
    if "約分" in topic or "約分到最簡" in qtext:
        c_parts = _ints_from_text(correct)
        u_parts = _ints_from_text(user)
        # Extract original from question: first fraction in text.
        m = re.search(r"(\d+)\s*/\s*(\d+)", qtext)
        orig = Fraction(int(m.group(1)), int(m.group(2))) if m else None

        if len(u_parts) < 2:
            return {
                "error_tag": "FORMAT_INVALID",
                "error_detail": "約分題需要輸入 2 個整數：分子 分母。",
                "hint_plan": _hint_pack(
                    "請輸入兩個數字，用空格分開：分子 分母。",
                    "找分子分母的 GCD。",
                    "同除以 GCD，直到最簡。",
                ),
                "drill_reco": [_drill("3", 10, "先把約分練熟")],
            }

        try:
            u_frac = Fraction(int(u_parts[0]), int(u_parts[1]))
        except Exception:
            u_frac = None

        # If numerically correct but not simplest, tag REDUCTION_MISSED.
        if orig is not None and u_frac is not None:
            if u_frac == orig and math.gcd(int(u_parts[0]), int(u_parts[1])) != 1:
                return {
                    "error_tag": "REDUCTION_MISSED",
                    "error_detail": "分數等值，但還沒有約到最簡。",
                    "hint_plan": _hint_pack(
                        "還可以再約：找出分子分母共同因數。",
                        "用 GCD 直接一次約到最簡。",
                        "最簡檢查：gcd(分子,分母)=1。",
                    ),
                    "drill_reco": [_drill("3", 12, "約到最簡")],
                }

        # If user used a divisor but applied incorrectly.
        if m and len(u_parts) >= 2:
            on, od = int(m.group(1)), int(m.group(2))
            un, ud = int(u_parts[0]), int(u_parts[1])
            if un != 0 and ud != 0:
                if on % un == 0:
                    d = on // un
                    if d > 1 and od % d == 0 and ud != od // d:
                        return {
                            "error_tag": "COMMON_DENOM_WRONG",
                            "error_detail": "你似乎有除以同一個數，但分母沒有同步除對。",
                            "hint_plan": _hint_pack(
                                "約分要『分子分母同除以同一個數』。",
                                "先求 GCD，再同除一次就到最簡。",
                                "算完用 gcd(分子,分母)=1 做檢查。",
                            ),
                            "drill_reco": [_drill("3", 10, "分子分母要同步除")],
                        }

        return {
            "error_tag": "OTHER",
            "error_detail": "與典型約分錯誤模式不匹配。",
            "hint_plan": _hint_pack("再找一次 GCD。", "分子分母同除。", "確認已最簡。"),
            "drill_reco": [_drill("3", 6, "再練幾題約分")],
        }

    # 分數加減（含連續）與帶分數：用 Fraction 比較 + 典型錯誤模式
    if ("分數加減" in topic) or ("分數連續加減" in topic) or ("帶分數" in topic) or re.search(r"\d+/\d+\s*[\+\-]", qtext):
        u_frac = parse_answer(user)
        c_frac = parse_answer(correct)
        if u_frac is None:
            return {
                "error_tag": "FORMAT_INVALID",
                "error_detail": "答案格式無法解析（可用：整數、a/b、或帶分數 '1 1/2'）。",
                "hint_plan": _hint_pack(
                    "先確認你輸入的是整數或分數，例如 5/6。",
                    "分母不同先通分，不能直接分子相加減。",
                    "算完記得約分到最簡。",
                ),
                "drill_reco": [_drill("4", 8, "分數加減格式與通分")],
            }
        if c_frac is None:
            return {
                "error_tag": "OTHER",
                "error_detail": "系統題目答案解析失敗（請回報）。",
                "hint_plan": _hint_pack("先跳過這題。", "再出一題試試。", "若持續發生請回報。"),
                "drill_reco": [],
            }

        # Try to parse two-term add/sub from question for pattern checks.
        m2 = re.search(r"(\d+)\s*/\s*(\d+)\s*([\+\-])\s*(\d+)\s*/\s*(\d+)", qtext)
        if m2:
            a1, b1, op, a2, b2 = int(m2.group(1)), int(m2.group(2)), m2.group(3), int(m2.group(4)), int(m2.group(5))
            sgn = 1 if op == "+" else -1
            naive_keep_b1 = Fraction(a1 + sgn * a2, b1)
            naive_keep_b2 = Fraction(a1 + sgn * a2, b2)
            naive_add_den = Fraction(a1 + sgn * a2, b1 + b2)
            naive_mul_den = Fraction(a1 + sgn * a2, b1 * b2)
            if u_frac in (naive_keep_b1, naive_keep_b2, naive_add_den, naive_mul_den):
                return {
                    "error_tag": "COMMON_DENOM_WRONG",
                    "error_detail": "看起來你直接在不同分母下做分子加減（或分母處理不正確）。",
                    "hint_plan": _hint_pack(
                        "分母不同不能直接算分子：先通分。",
                        "用 LCM 當共同分母，再做分子加減。",
                        "最後再約分到最簡。",
                    ),
                    "drill_reco": [_drill("2", 6, "先練通分"), _drill("4", 8, "再練分數加減")],
                }
            if u_frac == -c_frac:
                return {
                    "error_tag": "SIGN_OR_ORDER_WRONG",
                    "error_detail": "結果正負號可能顛倒（加減方向或換位錯）。",
                    "hint_plan": _hint_pack(
                        "先判斷答案應該是正還是負/大小。",
                        "減法通常要用『較大的減較小的』(本題設計為正數)。",
                        "通分後再做分子相減，留意符號。",
                    ),
                    "drill_reco": [_drill("4", 8, "加減方向與比較")],
                }
            # Numerator slip when denominator seems right
            if u_frac.denominator == c_frac.denominator and u_frac != c_frac:
                return {
                    "error_tag": "NUMERATOR_OP_WRONG",
                    "error_detail": "分母看起來對，但分子加減可能算錯。",
                    "hint_plan": _hint_pack(
                        "通分後只做分子加減，分母保持不變。",
                        "把通分後的兩個新分子寫出來再運算。",
                        "算完再檢查是否需要約分。",
                    ),
                    "drill_reco": [_drill("4", 10, "分子加減熟練")],
                }

        return {
            "error_tag": "OTHER",
            "error_detail": "與任何典型錯誤模式不匹配。",
            "hint_plan": _hint_pack(
                "先把每一項通分成同分母。",
                "再做分子加減，最後約分。",
                "把中間步驟寫出來通常就能找到錯在哪。",
            ),
            "drill_reco": [_drill("2", 5, "通分"), _drill("4", 6, "分數加減")],
        }

    # 四則運算(順序)：偵測典型忽略乘除/括號
    if "(" in qtext and ("×" in qtext or "÷" in qtext):
        u_val = parse_answer(user)
        c_val = parse_answer(correct)
        if u_val is None:
            return {
                "error_tag": "FORMAT_INVALID",
                "error_detail": "答案格式無法解析（請輸入整數）。",
                "hint_plan": _hint_pack("先算括號。", "再算乘除。", "最後算加減(由左到右)。"),
                "drill_reco": [_drill("1", 8, "運算順序")],
            }
        if c_val is None:
            return {
                "error_tag": "OTHER",
                "error_detail": "系統答案解析失敗。",
                "hint_plan": _hint_pack("先跳過。", "再出一題。", "若持續請回報。"),
                "drill_reco": [],
            }

        # Pattern: (a ? b) op1 (x × y) op2 e  OR (x ÷ y)
        m3 = re.search(r"\((\d+)\s*([\+\-])\s*(\d+)\)\s*([\+\-])\s*(\d+)\s*[×\*]\s*(\d+)\s*([\+\-])\s*(\d+)", qtext)
        if m3:
            a, op_p, b, op1, x, y, op2, e = int(m3.group(1)), m3.group(2), int(m3.group(3)), m3.group(4), int(m3.group(5)), int(m3.group(6)), m3.group(7), int(m3.group(8))
            par = a + b if op_p == "+" else a - b
            mul = x * y
            # Wrong: left-to-right ignoring × priority: ((par op1 x) × y) op2 e
            tmp = (par + x) if op1 == "+" else (par - x)
            wrong_lr = (tmp * y)
            wrong_lr = (wrong_lr + e) if op2 == "+" else (wrong_lr - e)
            if u_val == wrong_lr:
                return {
                    "error_tag": "ORDER_OF_OPS_WRONG",
                    "error_detail": "看起來你把乘法當成跟加減同級，直接由左到右算了。",
                    "hint_plan": _hint_pack(
                        "先括號，再乘除，最後加減。",
                        "括號算完後，下一步要先算 ×/÷。",
                        "每一步把算式『改寫』成新的一行。",
                    ),
                    "drill_reco": [_drill("1", 10, "運算順序")],
                }

            # Wrong: treat as (par op1 mul) then op2 e but par computed wrong? Hard; skip.

        # Division variant
        m4 = re.search(r"\((\d+)\s*([\+\-])\s*(\d+)\)\s*([\+\-])\s*(\d+)\s*[÷\/]\s*(\d+)\s*([\+\-])\s*(\d+)", qtext)
        if m4:
            a, op_p, b, op1, x, y, op2, e = int(m4.group(1)), m4.group(2), int(m4.group(3)), m4.group(4), int(m4.group(5)), int(m4.group(6)), m4.group(7), int(m4.group(8))
            par = a + b if op_p == "+" else a - b
            # Wrong left-to-right: ((par op1 x) ÷ y) op2 e
            tmp = (par + x) if op1 == "+" else (par - x)
            try:
                wrong_lr = tmp / y
            except Exception:
                wrong_lr = None
            if wrong_lr is not None:
                wrong_lr2 = (wrong_lr + e) if op2 == "+" else (wrong_lr - e)
                if u_val == Fraction(wrong_lr2).limit_denominator():
                    return {
                        "error_tag": "ORDER_OF_OPS_WRONG",
                        "error_detail": "看起來你忽略了乘除優先，直接由左到右算了。",
                        "hint_plan": _hint_pack(
                            "先括號，再乘除，最後加減。",
                            "除法也屬於乘除，要先處理。",
                            "把每一步中間結果寫出來再繼續。",
                        ),
                        "drill_reco": [_drill("1", 10, "運算順序")],
                    }

        return {
            "error_tag": "OTHER",
            "error_detail": "與典型運算順序錯誤模式不匹配。",
            "hint_plan": _hint_pack("先括號。", "再乘除。", "最後加減。"),
            "drill_reco": [_drill("1", 6, "運算順序")],
        }

    return {
        "error_tag": "OTHER",
        "error_detail": "與任何典型錯誤模式不匹配。",
        "hint_plan": _hint_pack("先整理題意。", "寫出中間步驟。", "逐步檢查運算。"),
        "drill_reco": base_recos,
    }

# -------------------------
# Custom solver (solve_custom)
# -------------------------
def solve_custom(question_text: str) -> Tuple[Optional[str], str]:
    """
    支援：
      - 方程式：2*x + 3 = 9   (需要 SymPy)
      - 算式：1/2 + 1/3, 3*(2+5), 0.25+1.2, 12 ÷ 3 (會轉換符號)

    return (answer_str_or_None, explanation_str)
    """
    q = (question_text or "").strip()
    if not q:
        return None, "空題目"

    # Normalize symbols
    clean_q = q.replace("×", "*").replace("÷", "/").replace(",", "")

    # Equation
    if "=" in clean_q:
        if not HAS_SYMPY:
            return None, "未安裝 SymPy，無法自動解方程式（建議：pip install sympy）"
        try:
            lhs_str, rhs_str = clean_q.split("=", 1)
            x = sp.Symbol('x')
            lhs = sp.sympify(lhs_str)
            rhs = sp.sympify(rhs_str)
            sol = sp.solve(sp.Eq(lhs, rhs), x)
            if not sol:
                return None, "無解或無限多解"

            # Convert to Fraction for consistent display
            f_ans = Fraction(sol[0]).limit_denominator()
            ans_str = str(f_ans.numerator) if f_ans.denominator == 1 else f"{f_ans.numerator}/{f_ans.denominator}"
            return ans_str, f"系統自動解題 (SymPy): x = {ans_str}"
        except Exception as e:
            return None, f"方程式解析失敗: {e}"

    # Expression
    try:
        if HAS_SYMPY:
            expr = sp.sympify(clean_q)
            f_ans = Fraction(expr).limit_denominator()
            ans_str = str(f_ans.numerator) if f_ans.denominator == 1 else f"{f_ans.numerator}/{f_ans.denominator}"
            return ans_str, f"系統自動計算 (SymPy): {ans_str}"
        else:
            # Safe-ish eval for arithmetic only
            # Allowed chars: digits, operators, parentheses, dot, slash, whitespace
            if not re.fullmatch(r"[0-9\.\+\-\*\/\(\)\s]+", clean_q):
                return None, "算式包含不允許的字元（僅支援數字與 + - * / ( )）"
            ans = eval(clean_q, {"__builtins__": {}}, {})
            f_ans = Fraction(ans).limit_denominator()
            ans_str = str(f_ans.numerator) if f_ans.denominator == 1 else f"{f_ans.numerator}/{f_ans.denominator}"
            return ans_str, f"系統自動計算 (Fraction): {ans_str}"
    except Exception as e:
        return None, f"無法計算: {e}"


# -------------------------
# Generators
# -------------------------
def gen_order_of_ops_arith():
    op_mul_div = random.choice(["*", "/"])
    if op_mul_div == "*":
        b = random.randint(2, 10)
        c = random.randint(2, 10)
        result_mul_div = b * c
        sub_expr_md = f"{b} × {c}"
    else:
        result_div = random.randint(2, 5)
        c = random.randint(2, 10)
        b = result_div * c
        result_mul_div = result_div
        sub_expr_md = f"{b} ÷ {c}"

    a1 = random.randint(5, 30)
    a2 = random.randint(5, 30)
    op_add_sub_paren = random.choice(["+", "-"])
    if op_add_sub_paren == "+":
        paren_result = a1 + a2
        op_text_paren = "+"
    else:
        if a1 < a2:
            a1, a2 = a2, a1
        paren_result = a1 - a2
        op_text_paren = "-"

    paren_expr = f"({a1} {op_text_paren} {a2})"
    e = random.randint(1, 10)
    op1 = random.choice(["+", "-"])
    op2 = random.choice(["+", "-"])

    question = f"{paren_expr} {op1} {sub_expr_md} {op2} {e} = ?"
    ans = eval(f"({a1} {op_text_paren} {a2}) {op1} ({b} {op_mul_div} {c}) {op2} {e}")

    explanation_steps = [
        "步驟 1: **先算括號**",
        f"   -> {a1} {op_text_paren} {a2} = {paren_result}",
        f"   -> 算式變為: {paren_result} {op1} {sub_expr_md} {op2} {e}",
        "步驟 2: **再算乘除**",
        f"   -> {sub_expr_md} = {result_mul_div}",
        f"   -> 算式變為: {paren_result} {op1} {result_mul_div} {op2} {e}",
        "步驟 3: **最後算加減** (從左到右)",
        f"   -> 第一部分: {paren_result} {op1} {result_mul_div} = {eval(f'{paren_result} {op1} {result_mul_div}')}",
        f"   -> 第二部分: {eval(f'{paren_result} {op1} {result_mul_div}')} {op2} {e} = {ans}",
        f"最終答案: {ans}",
        "\n💡 口訣：括號 → 乘除 → 加減；同級運算由左到右。"
    ]

    return {
        "topic": "四則運算 (順序)",
        "difficulty": "medium",
        "question": question,
        "answer": str(ans),
        "explanation": "\n".join(explanation_steps),
    }

def gen_fraction_commondenom():
    """分數通分（LCM、新分子兩位數內）"""
    den_pool = [2, 3, 4, 5, 6, 8, 9, 10, 12]
    for _ in range(500):
        b1 = random.choice(den_pool)
        b2 = random.choice(den_pool)
        if b1 == b2:
            continue
        a1 = random.randint(1, b1 - 1)
        a2 = random.randint(1, b2 - 1)
        if a1 / b1 == a2 / b2:
            continue

        lcm_val = _lcm(b1, b2)
        if lcm_val > MAX_2DIGIT:
            continue

        m1 = lcm_val // b1
        m2 = lcm_val // b2
        na1 = a1 * m1
        na2 = a2 * m2
        if not (_within_2digit_int(na1) and _within_2digit_int(na2)):
            continue

        question = f"請將 {a1}/{b1} 和 {a2}/{b2} 通分。\n請依序輸入：公分母 新分子1 新分子2"
        answer = f"{lcm_val} {na1} {na2}"
        explanation = [
            f"LCM({b1}, {b2}) = {lcm_val}",
            f"{a1}/{b1} -> {na1}/{lcm_val}",
            f"{a2}/{b2} -> {na2}/{lcm_val}",
            f"答案：{answer}"
        ]
        return {
            "topic": "分數通分",
            "difficulty": "easy",
            "question": question,
            "answer": answer,
            "explanation": "\n".join(explanation),
        }

    return {"topic": "分數通分", "difficulty": "easy", "question": "（生成失敗）請重試。", "answer": "0 0 0", "explanation": "生成失敗"}

def gen_fraction_reduction():
    simplified_num = random.randint(1, 15)
    simplified_den = random.randint(simplified_num + 1, 20)
    while math.gcd(simplified_num, simplified_den) != 1:
        simplified_num = random.randint(1, 15)
        simplified_den = random.randint(simplified_num + 1, 20)

    multiplier = random.randint(2, 5)
    original_num = simplified_num * multiplier
    original_den = simplified_den * multiplier
    gcd_val = multiplier

    question = f"請將分數 {original_num}/{original_den} 約分到最簡。\n請輸入：分子 分母"
    answer = f"{simplified_num} {simplified_den}"
    explanation = [
        f"GCD({original_num}, {original_den}) = {gcd_val}",
        f"{original_num}/{original_den} -> {simplified_num}/{simplified_den}",
        f"答案：{answer}"
    ]
    return {"topic": "分數約分", "difficulty": "easy", "question": question, "answer": answer, "explanation": "\n".join(explanation)}

def _fraction_core(a1, b1, a2, b2, op):
    f1 = Fraction(a1, b1)
    f2 = Fraction(a2, b2)
    if op == "-" and f1 < f2:
        f1, f2 = f2, f1
        a1, b1, a2, b2 = f1.numerator, f1.denominator, f2.numerator, f2.denominator

    result = f1 + f2 if op == "+" else f1 - f2
    gcd_val = math.gcd(b1, b2)
    lcm_val = (b1 * b2) // gcd_val
    m1 = lcm_val // b1
    m2 = lcm_val // b2
    na1 = a1 * m1
    na2 = a2 * m2
    ns = na1 + na2 if op == "+" else na1 - na2

    expl = [
        f"LCM({b1}, {b2}) = {lcm_val}",
        f"{a1}/{b1} -> {na1}/{lcm_val}",
        f"{a2}/{b2} -> {na2}/{lcm_val}",
        f"分子運算：{na1} {'+' if op=='+' else '-'} {na2} = {ns}",
        f"得到：{ns}/{lcm_val}",
        f"約分：{result.numerator}/{result.denominator}"
    ]
    return result, expl

def gen_fraction_add():
    """分數加減（LCM<=99、通分分子<=99、結果<=99）"""
    den_pool = [2, 3, 4, 5, 6, 8, 9, 10, 12]
    for _ in range(500):
        b1 = random.choice(den_pool)
        b2 = random.choice(den_pool)
        a1 = random.randint(1, b1 - 1)
        a2 = random.randint(1, b2 - 1)
        op = random.choice(["+", "-"])

        lcm_val = _lcm(b1, b2)
        if lcm_val > MAX_2DIGIT:
            continue
        m1 = lcm_val // b1
        m2 = lcm_val // b2
        na1 = a1 * m1
        na2 = a2 * m2
        if not (_within_2digit_int(na1) and _within_2digit_int(na2)):
            continue

        f1 = Fraction(a1, b1)
        f2 = Fraction(a2, b2)
        if op == "-" and f1 < f2:
            f1, f2 = f2, f1
            a1, b1 = f1.numerator, f1.denominator
            a2, b2 = f2.numerator, f2.denominator

        result = f1 + f2 if op == "+" else f1 - f2
        if result <= 0:
            continue
        if not _within_2digit_fraction(result):
            continue

        _, expl = _fraction_core(a1, b1, a2, b2, op)
        question = f"{a1}/{b1} {op} {a2}/{b2} = ?"
        return {"topic": "分數加減", "difficulty": "medium", "question": question,
                "answer": f"{result.numerator}/{result.denominator}", "explanation": "\n".join(expl)}

    return {"topic": "分數加減", "difficulty": "medium", "question": "（生成失敗）請重試。", "answer": "0/1", "explanation": "生成失敗"}

def gen_fraction_mixed():
    w1 = random.randint(1, 5)
    w2 = random.randint(1, 5)
    b1 = random.randint(2, 9)
    b2 = random.randint(2, 9)
    a1 = random.randint(1, b1 - 1)
    a2 = random.randint(1, b2 - 1)
    op = random.choice(["+", "-"])

    F1 = Fraction(w1 * b1 + a1, b1)
    F2 = Fraction(w2 * b2 + a2, b2)
    result, expl = _fraction_core(F1.numerator, F1.denominator, F2.numerator, F2.denominator, op)

    whole = result.numerator // result.denominator
    remain = result.numerator % result.denominator
    ans_str = f"{whole} {remain}/{result.denominator}" if remain != 0 and whole != 0 else f"{result.numerator}/{result.denominator}"

    explanation = [
        f"先化成假分數：{w1} {a1}/{b1} -> {F1.numerator}/{F1.denominator}",
        f"             {w2} {a2}/{b2} -> {F2.numerator}/{F2.denominator}",
        "再做通分/運算：",
        *expl,
        f"答案(可寫帶分數)：{ans_str}"
    ]
    return {"topic": "帶分數運算", "difficulty": "medium",
            "question": f"{w1} {a1}/{b1} {op} {w2} {a2}/{b2} = ?",
            "answer": ans_str, "explanation": "\n".join(explanation)}

def gen_fraction_chain():
    """分數連續加減（2~3 項；LCM<=99、通分分子<=99、結果<=99）"""
    den_pool = [2, 3, 4, 5, 6, 8, 9, 10, 12]
    terms = random.choice([2, 3])

    for _ in range(800):
        fracs: List[Fraction] = []
        dens: List[int] = []
        for _i in range(terms):
            b = random.choice(den_pool)
            a = random.randint(1, b - 1)
            fracs.append(Fraction(a, b))
            dens.append(b)

        ops = [random.choice(["+", "-"]) for _ in range(terms - 1)]
        l = _lcm(dens[0], dens[1]) if terms == 2 else _lcm3(dens[0], dens[1], dens[2])
        if l > MAX_2DIGIT:
            continue

        result = fracs[0]
        for i, op in enumerate(ops, start=1):
            result = result + fracs[i] if op == "+" else result - fracs[i]
        if result <= 0 or (not _within_2digit_fraction(result)):
            continue

        scaled = []
        ok = True
        for f in fracs:
            m = l // f.denominator
            sn = f.numerator * m
            if not _within_2digit_int(sn):
                ok = False
                break
            scaled.append((f, m, sn))
        if not ok:
            continue

        parts = [f"{fracs[0].numerator}/{fracs[0].denominator}"]
        for i, op in enumerate(ops, start=1):
            parts.append(f"{op} {fracs[i].numerator}/{fracs[i].denominator}")
        question = " ".join(parts) + " = ?"

        expl = [
            f"LCM(所有分母) = {l}",
            "通分後："
        ]
        for (f, m, sn) in scaled:
            expl.append(f"{f.numerator}/{f.denominator} -> {sn}/{l}")

        cur = scaled[0][2]
        expr = f"{scaled[0][2]}"
        for i, op in enumerate(ops, start=1):
            if op == "+":
                cur += scaled[i][2]
                expr += f" + {scaled[i][2]}"
            else:
                cur -= scaled[i][2]
                expr += f" - {scaled[i][2]}"
        expl.append(f"分子：{expr} = {cur}")
        expl.append(f"得到：{cur}/{l}，約分 -> {result.numerator}/{result.denominator}")

        return {"topic": "分數連續加減(三項內)", "difficulty": "medium",
                "question": question, "answer": f"{result.numerator}/{result.denominator}",
                "explanation": "\n".join(expl)}

    return {"topic": "分數連續加減(三項內)", "difficulty": "medium",
            "question": "（生成失敗）請重試。", "answer": "0/1", "explanation": "生成失敗"}

def gen_gcd_lcm():
    count = random.choice([2, 3])
    if count == 2:
        a = random.randint(10, 50)
        b = random.randint(10, 50)
        gcd_val = math.gcd(a, b)
        lcm_val = (a * b) // gcd_val
        question = f"數字 {a} 和 {b} 的最大公因數(GCD)和最小公倍數(LCM)各是多少？\n請依序輸入：GCD LCM"
        answer = f"{gcd_val} {lcm_val}"
        explanation = f"GCD={gcd_val}\nLCM=({a}×{b})/GCD={lcm_val}\n答案：{answer}"
        topic = "GCD/LCM (二數)"
    else:
        a = random.randint(5, 20)
        b = random.randint(5, 20)
        c = random.randint(5, 20)
        gcd_val = math.gcd(a, math.gcd(b, c))
        lcm_ab = (a * b) // math.gcd(a, b)
        lcm_val = (lcm_ab * c) // math.gcd(lcm_ab, c)
        question = f"數字 {a}, {b}, {c} 的最大公因數(GCD)和最小公倍數(LCM)各是多少？\n請依序輸入：GCD LCM"
        answer = f"{gcd_val} {lcm_val}"
        explanation = f"GCD={gcd_val}\nLCM={lcm_val}\n答案：{answer}"
        topic = "GCD/LCM (三數)"

    return {"topic": topic, "difficulty": "medium", "question": question, "answer": answer, "explanation": explanation}

def gen_decimal_arith():
    a = round(random.uniform(0.5, 20.0), random.randint(1, 2))
    b = round(random.uniform(0.5, 10.0), random.randint(1, 2))
    op = random.choice(["+", "-", "×", "÷"])

    if op == '+':
        ans = a + b
    elif op == '-':
        if a < b:
            a, b = b, a
        ans = a - b
    elif op == '×':
        ans = a * b
    else:
        ans_target = round(random.uniform(1.0, 5.0), 2)
        b = round(random.uniform(1.0, 5.0), 1)
        a = round(b * ans_target, 2)
        ans = a / b

    final_ans = round(ans, 2)
    question = f"計算並將結果四捨五入到小數點後兩位：\n{a} {op} {b} = ?"
    explanation = f"先算出約 {ans}\n再四捨五入到小數點後兩位 -> {final_ans}"
    return {"topic": "小數四則運算", "difficulty": "medium",
            "question": question, "answer": str(final_ans), "explanation": explanation}

def gen_volume_area():
    length = random.randint(2, 10)
    width = random.randint(2, 10)
    height = random.randint(2, 10)
    q_type = random.choice(["volume", "surface_area"])

    if length == width == height:
        shape = "正方體"
        if q_type == "volume":
            ans = length ** 3
            q_text = f"邊長為 {length} 公分的{shape}，體積是多少立方公分？"
            expl = f"體積=邊長³={length}×{length}×{length}={ans}"
        else:
            ans = 6 * (length ** 2)
            q_text = f"邊長為 {length} 公分的{shape}，表面積是多少平方公分？"
            expl = f"表面積=6×邊長²=6×({length}×{length})={ans}"
    else:
        shape = "長方體"
        dims = f"長 {length}、寬 {width}、高 {height}"
        if q_type == "volume":
            ans = length * width * height
            q_text = f"{dims} 公分的{shape}，體積是多少立方公分？"
            expl = f"體積=長×寬×高={length}×{width}×{height}={ans}"
        else:
            lw = length * width
            lh = length * height
            wh = width * height
            ans = 2 * (lw + lh + wh)
            q_text = f"{dims} 公分的{shape}，表面積是多少平方公分？"
            expl = f"表面積=2×(長寬+長高+寬高)=2×({lw}+{lh}+{wh})={ans}"

    return {"topic": f"{shape} {q_type.replace('_',' ')}", "difficulty": "easy",
            "question": q_text, "answer": str(ans), "explanation": expl}

def gen_linear_equation():
    x_val = random.randint(-9, 9)
    a = random.randint(2, 9)
    b = random.randint(-10, 10)
    c = a * x_val + b
    question = f"{a}x + {b} = {c}, 求 x"
    explanation = f"移項：{a}x = {c} - ({b}) = {c - b}\n兩邊除以 {a}：x = {x_val}"
    return {"topic": "一元一次方程", "difficulty": "medium", "question": question, "answer": str(x_val), "explanation": explanation}


# -------------------------
# GENERATORS
# -------------------------
GENERATORS: Dict[str, Tuple[str, Any]] = {
    "1": ("四則運算 (含括號/乘除)", gen_order_of_ops_arith),
    "2": ("分數通分", gen_fraction_commondenom),
    "3": ("分數約分", gen_fraction_reduction),
    "4": ("分數加減", gen_fraction_add),
    "5": ("帶分數運算", gen_fraction_mixed),
    "6": ("GCD/LCM", gen_gcd_lcm),
    "7": ("小數四則運算", gen_decimal_arith),
    "8": ("長/正方體積/面積", gen_volume_area),
    "10": ("分數連續加減(三項內)", gen_fraction_chain),
}
if HAS_SYMPY:
    GENERATORS["9"] = ("一元一次方程", gen_linear_equation)

def get_random_generator(topic_filter: Optional[str] = None):
    if topic_filter and topic_filter in GENERATORS:
        return GENERATORS[topic_filter][1]
    k = random.choice(list(GENERATORS.keys()))
    return GENERATORS[k][1]

def next_question(topic_key: Optional[str] = None) -> Dict[str, Any]:
    gen_func = get_random_generator(topic_key)
    return gen_func()


# ======================================================================
# SERVER (FastAPI + DB + Subscription Gate)
# ======================================================================

DB_PATH = os.environ.get("DB_PATH", "app.db")
app = FastAPI(title="Math Practice MVP API (All-in-One)", version="0.2")

def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        api_key TEXT UNIQUE NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER NOT NULL,
        display_name TEXT NOT NULL,
        grade TEXT DEFAULT 'G5',
        created_at TEXT NOT NULL,
        FOREIGN KEY(account_id) REFERENCES accounts(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER NOT NULL,
        status TEXT NOT NULL,              -- active / inactive / past_due
        plan TEXT DEFAULT 'basic',
        seats INTEGER DEFAULT 1,
        current_period_end TEXT,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(account_id) REFERENCES accounts(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS question_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT,
        difficulty TEXT,
        question TEXT,
        correct_answer TEXT,
        explanation TEXT,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        mode TEXT NOT NULL,                -- auto/custom
        question_id INTEGER,
        topic TEXT,
        difficulty TEXT,
        question TEXT,
        correct_answer TEXT,
        user_answer TEXT,
        is_correct INTEGER,                -- 1/0/NULL
        time_spent_sec INTEGER DEFAULT 0,
        ts TEXT NOT NULL,
        explanation TEXT,
        FOREIGN KEY(account_id) REFERENCES accounts(id),
        FOREIGN KEY(student_id) REFERENCES students(id),
        FOREIGN KEY(question_id) REFERENCES question_cache(id)
    )
    """)

    conn.commit()
    conn.close()

init_db()

def get_account_by_api_key(api_key: str) -> sqlite3.Row:
    conn = db()
    row = conn.execute("SELECT * FROM accounts WHERE api_key = ?", (api_key,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return row

def ensure_subscription_active(account_id: int):
    conn = db()
    sub = conn.execute(
        "SELECT * FROM subscriptions WHERE account_id = ? ORDER BY updated_at DESC LIMIT 1",
        (account_id,)
    ).fetchone()
    conn.close()
    if not sub or sub["status"] != "active":
        raise HTTPException(status_code=402, detail="Subscription required (inactive)")

def ensure_student_belongs(account_id: int, student_id: int) -> sqlite3.Row:
    conn = db()
    st = conn.execute("SELECT * FROM students WHERE id=? AND account_id=?", (student_id, account_id)).fetchone()
    conn.close()
    if not st:
        raise HTTPException(status_code=404, detail="Student not found")
    return st

@app.get("/health")
def health():
    return {"ok": True, "ts": now_iso(), "has_sympy": HAS_SYMPY}

@app.post("/admin/bootstrap")
def admin_bootstrap(name: str = "TestAccount"):
    """
    MVP 用：建立一個 account + active 訂閱 + 預設 1 個學生，回傳 api_key
    上線後應替換為：正式登入 + Stripe webhook 寫入 subscriptions
    """
    import secrets
    api_key = secrets.token_urlsafe(24)

    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO accounts(name, api_key, created_at) VALUES (?,?,?)", (name, api_key, now_iso()))
    account_id = cur.lastrowid

    cur.execute("""INSERT INTO subscriptions(account_id,status,plan,seats,current_period_end,updated_at)
                   VALUES (?,?,?,?,?,?)""",
                (account_id, "active", "basic", 3,
                 (datetime.now() + timedelta(days=30)).isoformat(timespec="seconds"),
                 now_iso()))

    cur.execute("""INSERT INTO students(account_id, display_name, grade, created_at)
                   VALUES (?,?,?,?)""",
                (account_id, "Student-1", "G5", now_iso()))
    conn.commit()
    conn.close()

    return {"account_id": account_id, "api_key": api_key}

@app.get("/v1/students")
def list_students(x_api_key: str = Header(..., alias="X-API-Key")):
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])
    conn = db()
    rows = conn.execute("SELECT * FROM students WHERE account_id = ? ORDER BY id ASC", (acc["id"],)).fetchall()
    conn.close()
    return {"students": [dict(r) for r in rows]}

@app.post("/v1/students")
def create_student(display_name: str, grade: str = "G5", x_api_key: str = Header(..., alias="X-API-Key")):
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])
    conn = db()
    conn.execute("""INSERT INTO students(account_id, display_name, grade, created_at)
                    VALUES (?,?,?,?)""", (acc["id"], display_name, grade, now_iso()))
    conn.commit()
    conn.close()
    return {"ok": True}

@app.post("/v1/questions/next")
def api_next_question(student_id: int, topic_key: Optional[str] = None, x_api_key: str = Header(..., alias="X-API-Key")):
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])
    ensure_student_belongs(acc["id"], student_id)

    q = next_question(topic_key)

    conn = db()
    cur = conn.cursor()
    cur.execute("""INSERT INTO question_cache(topic,difficulty,question,correct_answer,explanation,created_at)
                   VALUES (?,?,?,?,?,?)""",
                (q["topic"], q["difficulty"], q["question"], q["answer"], q["explanation"], now_iso()))
    qid = cur.lastrowid
    conn.commit()
    conn.close()

    # 不回傳 answer，避免作弊
    return {
        "question_id": qid,
        "topic": q["topic"],
        "difficulty": q["difficulty"],
        "question": q["question"],
        "explanation_preview": "（交卷後顯示）"
    }

@app.post("/v1/answers/submit")
async def api_submit_answer(request: Request, x_api_key: str = Header(..., alias="X-API-Key")):
    """
    body:
      {
        "student_id": 1,
        "question_id": 123,
        "user_answer": "3/4",
        "time_spent_sec": 25
      }
    """
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])

    body = await request.json()
    student_id = int(body["student_id"])
    question_id = int(body["question_id"])
    user_answer = str(body.get("user_answer", "")).strip()
    time_spent = int(body.get("time_spent_sec", 0))

    ensure_student_belongs(acc["id"], student_id)

    conn = db()
    q = conn.execute("SELECT * FROM question_cache WHERE id=?", (question_id,)).fetchone()
    if not q:
        conn.close()
        raise HTTPException(status_code=404, detail="Question not found")

    is_correct = check(user_answer, q["correct_answer"])

    conn.execute("""INSERT INTO attempts(account_id, student_id, mode, question_id, topic, difficulty,
                    question, correct_answer, user_answer, is_correct, time_spent_sec, ts, explanation)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                 (acc["id"], student_id, "auto", question_id, q["topic"], q["difficulty"],
                  q["question"], q["correct_answer"], user_answer, is_correct, time_spent, now_iso(), q["explanation"]))
    conn.commit()
    conn.close()

    return {
        "is_correct": is_correct,
        "correct_answer": q["correct_answer"],
        "explanation": q["explanation"],
        "topic": q["topic"],
        "difficulty": q["difficulty"]
    }

@app.post("/v1/custom/solve")
async def api_custom_solve(request: Request, x_api_key: str = Header(..., alias="X-API-Key")):
    """
    body:
      { "question": "1/2 + 1/3" }
      { "question": "2*x + 3 = 9" }
    """
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])
    body = await request.json()
    q = str(body.get("question", "")).strip()
    ans, expl = solve_custom(q)
    return {"question": q, "auto_answer": ans, "explanation": expl, "has_sympy": HAS_SYMPY}

@app.post("/v1/custom/submit")
async def api_custom_submit(request: Request, x_api_key: str = Header(..., alias="X-API-Key")):
    """
    body:
      {
        "student_id": 1,
        "question": "1/2 + 1/3",
        "final_answer": "5/6",        # 可用 solve_custom 的答案或手動輸入
        "user_answer": "5/6",
        "time_spent_sec": 18
      }
    """
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])
    body = await request.json()

    student_id = int(body["student_id"])
    ensure_student_belongs(acc["id"], student_id)

    q_text = str(body.get("question", "")).strip()
    final_answer = str(body.get("final_answer", "")).strip()
    user_answer = str(body.get("user_answer", "")).strip()
    time_spent = int(body.get("time_spent_sec", 0))

    is_correct = None
    if user_answer and final_answer:
        is_correct = check(user_answer, final_answer)

    # 若 final_answer 空，嘗試用 solver 自動算
    explanation = "使用者提供標準答案"
    if not final_answer:
        auto_ans, auto_expl = solve_custom(q_text)
        if auto_ans:
            final_answer = auto_ans
            explanation = auto_expl
            if user_answer:
                is_correct = check(user_answer, final_answer)
        else:
            explanation = f"無法自動解題：{auto_expl}"

    conn = db()
    conn.execute("""INSERT INTO attempts(account_id, student_id, mode, question_id, topic, difficulty,
                    question, correct_answer, user_answer, is_correct, time_spent_sec, ts, explanation)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                 (acc["id"], student_id, "custom", None, "custom", "unknown",
                  q_text, final_answer, user_answer, is_correct, time_spent, now_iso(), explanation))
    conn.commit()
    conn.close()

    return {
        "ok": True,
        "is_correct": is_correct,
        "final_answer": final_answer,
        "explanation": explanation
    }

@app.get("/v1/reports/summary")
def api_report_summary(student_id: int, days: int = 30, x_api_key: str = Header(..., alias="X-API-Key")):
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])
    ensure_student_belongs(acc["id"], student_id)

    since = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")

    conn = db()
    totals = conn.execute("""
        SELECT
          SUM(CASE WHEN is_correct IN (0,1) THEN 1 ELSE 0 END) AS valid_total,
          SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) AS correct,
          SUM(CASE WHEN is_correct = 0 THEN 1 ELSE 0 END) AS wrong,
          SUM(CASE WHEN is_correct IS NULL THEN 1 ELSE 0 END) AS invalid
        FROM attempts
        WHERE student_id = ? AND ts >= ?
    """, (student_id, since)).fetchone()

    topics = conn.execute("""
        SELECT
          topic,
          COUNT(*) AS total,
          SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) AS correct,
          SUM(CASE WHEN is_correct = 0 THEN 1 ELSE 0 END) AS wrong,
          SUM(CASE WHEN is_correct IS NULL THEN 1 ELSE 0 END) AS invalid
        FROM attempts
        WHERE student_id = ? AND ts >= ?
        GROUP BY topic
        ORDER BY total DESC
    """, (student_id, since)).fetchall()

    wrongs = conn.execute("""
        SELECT ts, mode, topic, question, correct_answer, user_answer
        FROM attempts
        WHERE student_id = ? AND ts >= ? AND is_correct = 0
        ORDER BY ts DESC
        LIMIT 20
    """, (student_id, since)).fetchall()

    conn.close()

    valid_total = int(totals["valid_total"] or 0)
    correct_cnt = int(totals["correct"] or 0)
    acc_rate = (correct_cnt / valid_total * 100.0) if valid_total else 0.0

    return {
        "student_id": student_id,
        "window_days": days,
        "summary": {
            "valid_total": valid_total,
            "correct": correct_cnt,
            "wrong": int(totals["wrong"] or 0),
            "invalid": int(totals["invalid"] or 0),
            "accuracy": round(acc_rate, 2)
        },
        "topics": [dict(r) for r in topics],
        "recent_wrongs": [dict(r) for r in wrongs]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("math_app:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), reload=True)
