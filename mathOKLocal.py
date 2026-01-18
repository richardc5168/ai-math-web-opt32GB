#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命令列版：數學練習系統（V11.2 深度教學版 - 修正 UnboundLocalError + 客製化回饋）
新增功能：
1. **修復：** 修正 gen_order_of_ops_arith 函數中的 UnboundLocalError 錯誤。
2. **顏色維持：** 導入 Colors class，定義 GOLD, YELLOW, GREEN, RED 等顏色。
3. **客製化答錯回饋：** 答錯時不提供評語，改為提示查看詳解並提供家人諮詢建議。
"""

import sqlite3
import random
from fractions import Fraction
from datetime import datetime
from collections import deque
import os
import sys
import re
import math 

from app_identity import Identity, select_or_create_identity, record_attempt_to_app_db

# =========================
# ANSI 顏色定義 (用於模擬暖色系介面)
# =========================
class Colors:
    # 暖色系：金色/淺棕色 (使用 24-bit 顏色，若終端機不支援會顯示為默認顏色)
    GOLD = '\033[38;2;218;165;32m' 
    YELLOW = '\033[93m'              # 暖色系 - 標準亮黃色
    GREEN = '\033[92m'               # 答對 (綠色)
    RED = '\033[91m'                 # 答錯 (紅色)
    END = '\033[0m'                  # 重置顏色

# =========================
# 全局變數 (即時計數器)
# =========================
TOTAL_COUNT = 0
CORRECT_COUNT = 0
DB_PATH = "math_log.db"

APP_DB_PATH = "app.db"
CURRENT_IDENTITY: Identity | None = None
RECORDS_HAS_IDENTITY_COLUMNS = False
RECORDS_HAS_COACH_COLUMNS = False

# 連續答對（用於自動解鎖更高難度）
STREAK_CORRECT = 0
FRACTION_STREAK = 0

# 四則運算應用題（文字題）連續答對：用於由簡單到深入的出題
ARITH_APP_STREAK = 0

# 連勝里程碑鼓勵（整合自 mathOK.py；不影響既有解鎖/獎勵邏輯）
STREAK_MILESTONE_MESSAGES: dict[int, str] = {
    2: "真棒！連勝 2 啦～",
    4: "哇～你超穩的！連勝 4！",
    6: "太強了吧！連勝 6！再來一題～",
    8: "你今天開掛！連勝 8！",
    10: "超級天才！連勝 10！給你大拇指～",
    12: "連勝 12｜銀牌衝刺中！",
    14: "連勝 14｜金牌玩家登場！",
    16: "連勝 16｜傳說段位：數學王者！",
    18: "連勝 18｜完爆等級!!!",
}

# 分數闖關解鎖曲線（3 段）：到達門檻後逐步提高乘除比例
FRACTION_UNLOCK_STAGE1_AT = 3  # 80% 加減 / 20% 乘除
FRACTION_UNLOCK_STAGE2_AT = 5  # 60% 加減 / 40% 乘除
FRACTION_UNLOCK_STAGE3_AT = 7  # 40% 加減 / 60% 乘除

# 最近 N 題去重（只作用於本次程式執行，避免連續抽到完全相同題目）
RECENT_QUESTION_DEDUP_N = 12
_RECENT_Q_SIGS: deque[str] = deque(maxlen=RECENT_QUESTION_DEDUP_N)

# 嘗試載入 sympy
try:
    import sympy as sp
    HAS_SYMPY = True
except ImportError:
    HAS_SYMPY = False


# =========================
# 教練式 UX（反挫折 + 分層提示 + 等價檢查）
# =========================

DEFAULT_DAILY_GOAL = 3

MISTAKE_TAGS_LIBRARY = {
    "運算順序": ["括號", "乘除優先", "加減由左至右"],
    "分配律": ["分配律", "合併同類項"],
    "結合律": ["結合律", "先合併好算的一組"],
    "通分": ["通分", "最小公倍數", "分子同步擴大"],
    "約分": ["最大公因數", "分子分母同除"],
    "移項": ["移項", "符號改變", "等量公理"],
    "小數四捨五入": ["小數點", "四捨五入", "位數"],
}


def _maybe_print_streak_milestone_encouragement() -> None:
    """Print encouragement when the correct streak hits milestones.

    Rules:
    - Exact milestones use STREAK_MILESTONE_MESSAGES.
    - Above 18: every even streak prints "連勝 N｜完爆等級!!!".
    """
    if STREAK_CORRECT in STREAK_MILESTONE_MESSAGES:
        msg = STREAK_MILESTONE_MESSAGES[STREAK_CORRECT]
    elif STREAK_CORRECT > 18 and STREAK_CORRECT % 2 == 0:
        msg = f"連勝 {STREAK_CORRECT}｜完爆等級!!!"
    else:
        return

    print(f"{Colors.GREEN}{msg}{Colors.END}")


def _update_streak(is_correct: int | None, topic: str) -> None:
    """Update global streak counters.

    - STREAK_CORRECT: any topic
    - FRACTION_STREAK: only fraction-related topics
    """
    global STREAK_CORRECT, FRACTION_STREAK, ARITH_APP_STREAK
    if is_correct == 1:
        STREAK_CORRECT += 1
        _maybe_print_streak_milestone_encouragement()
        if "應用題" in (topic or ""):
            ARITH_APP_STREAK += 1
        if any(k in (topic or "") for k in ("分數", "帶分數", "整數與分數")):
            before = FRACTION_STREAK
            FRACTION_STREAK += 1
            # Stage-up notifications
            if before < FRACTION_UNLOCK_STAGE1_AT <= FRACTION_STREAK:
                print(
                    f"{Colors.GREEN}🔓 解鎖第 1 段！你已連續答對 {FRACTION_UNLOCK_STAGE1_AT} 題分數題："
                    f"接下來會『以加減為主，混少量乘除』(約 80%/20%)。{Colors.END}"
                )
            if before < FRACTION_UNLOCK_STAGE2_AT <= FRACTION_STREAK:
                print(
                    f"{Colors.GREEN}⬆️ 升級第 2 段！乘除比例提高 (約 60%/40%)。{Colors.END}"
                )
            if before < FRACTION_UNLOCK_STAGE3_AT <= FRACTION_STREAK:
                print(
                    f"{Colors.GREEN}⬆️ 升級第 3 段！乘除比例再提高 (約 40%/60%)。{Colors.END}"
                )
    elif is_correct == 0:
        STREAK_CORRECT = 0
        if "應用題" in (topic or ""):
            ARITH_APP_STREAK = 0
        if any(k in (topic or "") for k in ("分數", "帶分數", "整數與分數")):
            FRACTION_STREAK = 0


def _pick_easy_common_denom(max_d: int = 99) -> int:
    """Pick a 2-digit-ish common denominator that's easy to work with."""
    candidates = [
        6, 8, 9, 10, 12, 15, 16, 18, 20, 24, 25, 30, 32, 36, 40, 45, 48,
        50, 60, 72, 75, 80, 90, 96,
    ]
    candidates = [c for c in candidates if 2 <= c <= max_d]
    return random.choice(candidates) if candidates else random.randint(2, max_d)


def _divisors(n: int) -> list[int]:
    ds = []
    for d in range(2, n + 1):
        if n % d == 0:
            ds.append(d)
    return ds


def _make_easy_fraction_with_lcm(D: int) -> tuple[int, int]:
    """Return (numerator, denominator) such that denom divides D and numbers are easy.

    Strategy:
    - pick denom as a divisor of D
    - pick numerator small (<=9) and avoid 0
    """
    ds = _divisors(D)
    denom = random.choice(ds) if ds else D
    max_num = min(9, denom - 1)
    if max_num < 1:
        denom = max(2, denom)
        max_num = min(9, denom - 1)
    num = random.randint(1, max_num)
    return num, denom


def _format_fraction(fr: Fraction) -> str:
    fr2 = Fraction(fr).limit_denominator()
    if fr2.denominator == 1:
        return str(fr2.numerator)
    return f"{fr2.numerator}/{fr2.denominator}"


def gen_fraction_addsub_easy():
    """分數 +/−（好算版）

    需求：
    - 分母 2 位數以內（<=99）
    - 通分完的分母也 2 位數以內（LCM<=99）
    - 數值好算（分子小、倍率小）
    """
    D = _pick_easy_common_denom(60)
    a1, b1 = _make_easy_fraction_with_lcm(D)
    a2, b2 = _make_easy_fraction_with_lcm(D)

    # Ensure not identical and not trivially same
    if b1 == b2 and a1 == a2:
        a2 = max(1, (a2 % (b2 - 1)) + 1) if b2 > 2 else 1

    op = random.choice(["+", "-"])
    f1 = Fraction(a1, b1)
    f2 = Fraction(a2, b2)

    # For subtraction keep positive and easy
    if op == "-" and f1 < f2:
        f1, f2 = f2, f1
        a1, b1, a2, b2 = f1.numerator, f1.denominator, f2.numerator, f2.denominator

    result = f1 + f2 if op == "+" else f1 - f2
    result = result.limit_denominator()

    # Build explanation using common denom D' (LCM)
    gcd_val = math.gcd(b1, b2)
    lcm_val = (b1 * b2) // gcd_val
    # ensure lcm within 2 digits; if not, regenerate (rare due to construction)
    if lcm_val > 99:
        return gen_fraction_addsub_easy()

    m1 = lcm_val // b1
    m2 = lcm_val // b2
    na1 = a1 * m1
    na2 = a2 * m2
    ns = na1 + na2 if op == "+" else na1 - na2
    unsimplified = Fraction(ns, lcm_val)

    question = f"{a1}/{b1} {op} {a2}/{b2} = ?"
    expl = [
        "步驟 1: **先通分**（讓分母一樣）",
        f"  -> LCM({b1}, {b2}) = {lcm_val}",
        f"  -> {a1}/{b1} 擴大 {m1} 倍 → {na1}/{lcm_val}",
        f"  -> {a2}/{b2} 擴大 {m2} 倍 → {na2}/{lcm_val}",
        "步驟 2: **分母不變、只算分子**",
        f"  -> {na1}/{lcm_val} {op} {na2}/{lcm_val} = {ns}/{lcm_val}",
        "步驟 3: **約分到最簡**",
        f"  -> {ns}/{lcm_val} = {_format_fraction(unsimplified)}",
        f"最終答案: {_format_fraction(result)}",
    ]

    return {
        "topic": "分數加減（好算）",
        "difficulty": "easy",
        "question": question,
        "answer": _format_fraction(result),
        "explanation": "\n".join(expl),
    }


def gen_int_fraction_addsub_easy():
    """整數 與 分數 的 +/−（答案用分數表示，好算、2位數內）"""
    # Choose denom first, then bound k so that (k*b + a) <= 99
    b = _pick_easy_common_denom(30)
    a = random.randint(1, min(9, b - 1))
    k_max = max(1, (99 - a) // b)
    k = random.randint(1, min(20, k_max))
    op = random.choice(["+", "-"])

    f = Fraction(a, b)
    base = Fraction(k, 1)

    if op == "-":
        # Ensure non-negative and not too large
        if base < f:
            op = "+"

    result = base + f if op == "+" else base - f
    result = result.limit_denominator()

    # Keep answer as fraction (improper ok) per request
    question = f"{k} {op} {a}/{b} = ?（答案用分數表示）"
    expl = [
        "步驟 1: **把整數寫成同分母的分數**",
        f"  -> {k} = {k*b}/{b}",
        "步驟 2: **分母不變、只算分子**",
        f"  -> {k*b}/{b} {op} {a}/{b} = {(k*b + a)}/{b}" if op == "+" else f"  -> {k*b}/{b} {op} {a}/{b} = {(k*b - a)}/{b}",
        "步驟 3: **約分到最簡**",
        f"最終答案: {_format_fraction(result)}",
    ]
    return {
        "topic": "整數與分數（好算）",
        "difficulty": "easy",
        "question": question,
        "answer": _format_fraction(result),
        "explanation": "\n".join(expl),
    }


def gen_fraction_four_ops_easy():
    """分數四則運算（解鎖後）— 仍維持好算、分母二位數內。"""
    op = random.choice(["+", "-", "×", "÷"])

    if op in ("+", "-"):
        q = gen_fraction_addsub_easy()
        q["topic"] = "分數四則（解鎖）"
        return q

    # For × / ÷ keep small and reducible
    b1 = random.choice([2, 3, 4, 5, 6, 8, 9, 10, 12, 15])
    b2 = random.choice([2, 3, 4, 5, 6, 8, 9, 10, 12, 15])
    a1 = random.randint(1, min(9, b1 - 1))
    a2 = random.randint(1, min(9, b2 - 1))

    f1 = Fraction(a1, b1)
    f2 = Fraction(a2, b2)
    if op == "×":
        result = (f1 * f2).limit_denominator()
        question = f"{a1}/{b1} × {a2}/{b2} = ?"
        expl = [
            "步驟 1: **分子乘分子、分母乘分母**",
            f"  -> ({a1}×{a2})/({b1}×{b2}) = {a1*a2}/{b1*b2}",
            "步驟 2: **約分到最簡**",
            f"最終答案: {_format_fraction(result)}",
        ]
    else:
        # division: multiply by reciprocal
        if a2 == 0:
            a2 = 1
        result = (f1 / f2).limit_denominator()
        question = f"{a1}/{b1} ÷ {a2}/{b2} = ?"
        expl = [
            "步驟 1: **除以分數 = 乘以倒數**",
            f"  -> {a1}/{b1} ÷ {a2}/{b2} = {a1}/{b1} × {b2}/{a2}",
            "步驟 2: **相乘並約分**",
            f"  -> ({a1}×{b2})/({b1}×{a2}) = {a1*b2}/{b1*a2}",
            f"最終答案: {_format_fraction(result)}",
        ]

    # Ensure denominators not too large after simplify (still could exceed 99 in rare cases)
    if isinstance(result, Fraction) and result.denominator > 99:
        return gen_fraction_four_ops_easy()

    return {
        "topic": "分數四則（解鎖）",
        "difficulty": "medium",
        "question": question,
        "answer": _format_fraction(result),
        "explanation": "\n".join(expl),
    }


def gen_fraction_muldiv_easy():
    """分數乘除（好算版）— 分母二位數內、數字小、可約分。"""
    op = random.choice(["×", "÷"])

    b1 = random.choice([2, 3, 4, 5, 6, 8, 9, 10, 12, 15])
    b2 = random.choice([2, 3, 4, 5, 6, 8, 9, 10, 12, 15])
    a1 = random.randint(1, min(9, b1 - 1))
    a2 = random.randint(1, min(9, b2 - 1))

    f1 = Fraction(a1, b1)
    f2 = Fraction(a2, b2)

    if op == "×":
        result = (f1 * f2).limit_denominator()
        question = f"{a1}/{b1} × {a2}/{b2} = ?"
        expl = [
            "步驟 1: **分子乘分子、分母乘分母**",
            f"  -> ({a1}×{a2})/({b1}×{b2}) = {a1*a2}/{b1*b2}",
            "步驟 2: **約分到最簡**",
            f"最終答案: {_format_fraction(result)}",
        ]
    else:
        result = (f1 / f2).limit_denominator()
        question = f"{a1}/{b1} ÷ {a2}/{b2} = ?"
        expl = [
            "步驟 1: **除以分數 = 乘以倒數**",
            f"  -> {a1}/{b1} ÷ {a2}/{b2} = {a1}/{b1} × {b2}/{a2}",
            "步驟 2: **相乘並約分**",
            f"  -> ({a1}×{b2})/({b1}×{a2}) = {a1*b2}/{b1*a2}",
            f"最終答案: {_format_fraction(result)}",
        ]

    if result.denominator > 99:
        return gen_fraction_muldiv_easy()

    return {
        "topic": "分數乘除（好算）",
        "difficulty": "medium",
        "question": question,
        "answer": _format_fraction(result),
        "explanation": "\n".join(expl),
    }


def gen_distributive_law_easy():
    """分配律（好算版）：設計成不用分配律也能算，但用分配律會更快。"""
    # Choose a* (base ± delta) where base is a multiple of 10 or 25 to be mental-math friendly.
    a = random.choice([2, 3, 4, 5, 6, 7, 8, 9])
    base = random.choice([10, 20, 30, 40, 50, 60, 25, 75])
    delta = random.randint(1, 9)
    op = random.choice(["+", "-"])
    if op == "-" and base - delta <= 0:
        op = "+"

    b = base
    c = delta
    expr = f"{a}×({b} {op} {c})"
    ans = a * (b + c) if op == "+" else a * (b - c)

    # Explanation highlights distributive law
    expl = [
        "步驟 1: **先判斷是不是分配律**（嚴謹版）",
        "  -> 只有看到『外面是 ×，括號裡是 + 或 −』這種 a×(b±c)，才用分配律。",
        "  -> 只是有括號不一定是分配律；像 (a+b)+c 那是『結合律』在換括號。",
        f"  -> {a}×({b} {op} {c}) = {a}×{b} {op} {a}×{c}",
        "步驟 2: **先算『最好算的那一塊』，再算另一塊**",
        "  -> 為什麼常說 25 好算？因為 25×4=100，所以 25×2=50、25×8=200，很容易變整十整百。",
        "  -> 看到 75 也可以想成 3×25，所以常常也很好算。",
        f"  -> {a}×{b} = {a*b}",
        f"  -> {a}×{c} = {a*c}",
        f"步驟 3: 合併：{a*b} {op} {a*c} = {ans}",
        f"最終答案: {ans}",
        "\n💡 分配律：a×(b±c)=a×b±a×c。",
    ]

    return {
        "topic": "分配律（好算）",
        "difficulty": "easy",
        "question": f"用分配律會更快：計算 {expr} = ?",
        "answer": str(ans),
        "explanation": "\n".join(expl),
    }


def gen_arith_application_problem() -> dict:
    """四則運算應用題（文字題）

    目標：增加「看得懂、算得出」的一步或兩步故事題，讓孩子把文字轉成算式。
    - 不需要括號/公式
    - 答案為整數
    """

    # Difficulty progression (由簡單到深入):
    # - early: only +/−
    # - mid: +/−/×/÷
    # - later: include 2-step problems
    if ARITH_APP_STREAK < 2:
        kind = random.choice(["add", "sub"])
        difficulty = "easy"
    elif ARITH_APP_STREAK < 5:
        kind = random.choice(["add", "sub", "mul", "div"])
        difficulty = "easy"
    else:
        kind = random.choice(["add", "sub", "mul", "div", "two_step_mul_sub", "two_step_add_sub"])
        difficulty = "medium"

    if kind == "add":
        a = random.randint(12, 90)
        b = random.randint(5, 60)
        question = (
            f"小明有 {a} 張貼紙，媽媽又給他 {b} 張。\n"
            f"請問小明現在一共有幾張貼紙？"
        )
        ans = a + b
        expl = [
            "步驟 1: 先找題目在問什麼：『一共』＝合起來。",
            "步驟 2: 把文字變成算式：原本 + 又來的。",
            f"  -> {a} + {b} = {ans}",
            f"最終答案: {ans}",
        ]
        return {
            "topic": "四則運算（應用題）",
            "difficulty": difficulty,
            "question": question,
            "answer": str(ans),
            "explanation": "\n".join(expl),
        }

    if kind == "sub":
        a = random.randint(30, 120)
        b = random.randint(5, min(60, a - 1))
        question = (
            f"書架上原本有 {a} 本書，小美借走了 {b} 本。\n"
            f"書架上還剩下幾本書？"
        )
        ans = a - b
        expl = [
            "步驟 1: 先找題目在問什麼：『剩下』＝從原本的拿掉。",
            "步驟 2: 把文字變成算式：原本 − 借走的。",
            f"  -> {a} - {b} = {ans}",
            f"最終答案: {ans}",
        ]
        return {
            "topic": "四則運算（應用題）",
            "difficulty": difficulty,
            "question": question,
            "answer": str(ans),
            "explanation": "\n".join(expl),
        }

    if kind == "mul":
        packs = random.randint(3, 9)
        each = random.randint(2, 12)
        question = (
            f"有 {packs} 包餅乾，每包有 {each} 片。\n"
            f"請問一共有幾片餅乾？"
        )
        ans = packs * each
        expl = [
            "步驟 1: 先找題目在問什麼：『每包一樣多』→ 用乘法更快。",
            "步驟 2: 把文字變成算式：包數 × 每包幾片。",
            f"  -> {packs} × {each} = {ans}",
            f"最終答案: {ans}",
        ]
        return {
            "topic": "四則運算（應用題）",
            "difficulty": difficulty,
            "question": question,
            "answer": str(ans),
            "explanation": "\n".join(expl),
        }

    if kind == "div":
        groups = random.randint(2, 9)
        each = random.randint(2, 12)
        total = groups * each
        question = (
            f"老師把 {total} 枝鉛筆平均分給 {groups} 位同學。\n"
            f"每位同學可以拿到幾枝鉛筆？"
        )
        ans = total // groups
        expl = [
            "步驟 1: 先找題目在問什麼：『平均分』→ 用除法。",
            "步驟 2: 把文字變成算式：總數 ÷ 人數。",
            f"  -> {total} ÷ {groups} = {ans}",
            f"最終答案: {ans}",
        ]
        return {
            "topic": "四則運算（應用題）",
            "difficulty": difficulty,
            "question": question,
            "answer": str(ans),
            "explanation": "\n".join(expl),
        }

    if kind == "two_step_mul_sub":
        packs = random.randint(3, 9)
        each = random.randint(3, 12)
        eaten = random.randint(2, min(25, packs * each - 1))
        total = packs * each
        question = (
            f"小華買了 {packs} 包糖果，每包有 {each} 顆。\n"
            f"回家後他吃了 {eaten} 顆。\n"
            f"請問他還剩下幾顆糖果？"
        )
        ans = total - eaten
        expl = [
            "步驟 1: 先算『一共有多少』：包數 × 每包幾顆。",
            f"  -> {packs} × {each} = {total}",
            "步驟 2: 再算『剩下多少』：一共 − 吃掉的。",
            f"  -> {total} - {eaten} = {ans}",
            f"最終答案: {ans}",
        ]
        return {
            "topic": "四則運算（應用題）",
            "difficulty": difficulty,
            "question": question,
            "answer": str(ans),
            "explanation": "\n".join(expl),
        }

    # two_step_add_sub
    start = random.randint(20, 120)
    got = random.randint(5, 60)
    gave = random.randint(5, min(70, start + got - 1))
    ans = start + got - gave
    question = (
        f"小莉原本有 {start} 元零用錢，今天又得到 {got} 元。\n"
        f"她買東西花了 {gave} 元。\n"
        f"請問她現在還有幾元？"
    )
    expl = [
        "步驟 1: 先把『又得到』加上去。",
        f"  -> {start} + {got} = {start + got}",
        "步驟 2: 再把『花掉的』減掉。",
        f"  -> {start + got} - {gave} = {ans}",
        f"最終答案: {ans}",
    ]
    return {
        "topic": "四則運算（應用題）",
        "difficulty": difficulty,
        "question": question,
        "answer": str(ans),
        "explanation": "\n".join(expl),
    }


def _select_arith_app_progress_generator():
    """Adaptive progression for application problems (由簡單到深入)."""
    return gen_arith_application_problem


def gen_associative_law_easy():
    """結合律（好算版）：設計成『換括號』才能快速心算的題。"""
    mode = random.choice(["add", "mul"])

    if mode == "add":
        # Make a+(b+c) where b+c forms a round number (10/20/30/50/100)
        target = random.choice([10, 20, 30, 40, 50, 60, 80, 100])
        b = random.randint(1, 9)
        c = target - b
        # Keep c within 2 digits and positive
        if c <= 0 or c > 99:
            c = random.randint(1, 20)
            b = random.randint(1, 20)
            target = b + c

        a = random.randint(10, 99)
        # Mix parentheses so student should regroup (associative)
        if random.choice([True, False]):
            expr = f"({a} + {b}) + {c}"
        else:
            expr = f"{a} + ({b} + {c})"
        ans = a + b + c

        expl = [
            "步驟 1: **結合律：加法可以先把好算的一組先加**",
            f"  -> ({b} + {c}) = {b+c}（先湊整數更快）",
            f"步驟 2: {a} + {b+c} = {ans}",
            f"最終答案: {ans}",
            "\n💡 結合律： (a+b)+c = a+(b+c)。",
        ]
        return {
            "topic": "結合律（加法・好算）",
            "difficulty": "easy",
            "question": f"用結合律會更快：計算 {expr} = ?",
            "answer": str(ans),
            "explanation": "\n".join(expl),
        }

    # multiplication associative: (a×b)×c where regrouping makes 10/100
    # Choose numbers such that one regroup yields a round number.
    a, b, c = random.choice(
        [
            (4, 25, 3),   # (4×25)=100
            (8, 125, 2),  # (8×125)=1000 (but 125 is 3 digits) -> avoid
            (2, 50, 7),
            (5, 20, 6),
            (4, 25, 2),
            (2, 25, 8),
            (5, 12, 2),
            (3, 4, 25),
        ]
    )
    # Ensure all within 2 digits
    if max(a, b, c) > 99:
        a, b, c = 4, 25, 3

    # Randomize bracket placement
    if random.choice([True, False]):
        expr = f"({a} × {b}) × {c}"
    else:
        expr = f"{a} × ({b} × {c})"
    ans = a * b * c

    expl = [
        "步驟 1: **結合律：乘法可以先把好算的一組先乘**",
        f"  -> 例如先算 ({a}×{b}) 或 ({b}×{c})，選那個會變整十/整百的。",
        f"  -> {a}×{b} = {a*b}",
        f"步驟 2: {a*b}×{c} = {ans}",
        f"最終答案: {ans}",
        "\n💡 結合律： (a×b)×c = a×(b×c)。",
    ]

    return {
        "topic": "結合律（乘法・好算）",
        "difficulty": "easy",
        "question": f"用結合律會更快：計算 {expr} = ?",
        "answer": str(ans),
        "explanation": "\n".join(expl),
    }


def _today_ymd() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _clean_math_text(text: str) -> str:
    return (
        text.replace("×", "*")
        .replace("÷", "/")
        .replace("，", ",")
        .strip()
    )


def _question_signature(qobj: dict) -> str:
    topic = str(qobj.get("topic", "")).strip()
    q = str(qobj.get("question", "")).strip()
    # Normalize whitespace only; do NOT change math content.
    q = " ".join(q.split())
    return f"{topic}||{q}"


def generate_unique_question(gen_func, recent_sigs: deque[str] | None = None, max_tries: int = 30) -> dict:
    """Generate a question not present in recent_sigs; fallback after max_tries."""
    recent = recent_sigs if recent_sigs is not None else _RECENT_Q_SIGS
    last = None
    for _ in range(max_tries):
        qobj = gen_func()
        sig = _question_signature(qobj)
        last = qobj
        if sig not in recent:
            recent.append(sig)
            return qobj
    # Fallback: accept last but still record to prevent immediate reprint.
    if last is None:
        last = gen_func()
    try:
        recent.append(_question_signature(last))
    except Exception:
        pass
    return last


def _is_numeric_expression(text: str) -> bool:
    # Allow digits, spaces, parentheses, operators, slash, dot, minus
    t = _clean_math_text(text)
    return bool(re.fullmatch(r"[0-9\s\+\-\*\/\(\)\.]+", t))


def check_equivalent_answer(user: str, correct: str) -> int | None:
    """More tolerant equivalence checking.

    - Keeps existing numeric/fraction behavior.
    - Additionally accepts forms like "x=3" or "x = 3" when correct is "3".
    - If SymPy exists, can compare numeric expressions like "(1/2)+(1/3)" to "5/6".
    """
    user_s = user.strip()
    correct_s = correct.strip()
    if not user_s or not correct_s:
        return None

    # Accept x = ... style for equation answers.
    m = re.fullmatch(r"\s*[xX]\s*=\s*(.+)\s*", user_s)
    if m:
        user_s = m.group(1).strip()

    # Keep original multi-number behavior
    base = check_correct(user_s, correct_s)
    if base in (0, 1):
        return base

    # SymPy numeric expression equivalence (safe-ish) for numeric-only.
    if HAS_SYMPY and (_is_numeric_expression(user_s) or _is_numeric_expression(correct_s)):
        try:
            u_expr = sp.sympify(_clean_math_text(user_s))
            c_expr = sp.sympify(_clean_math_text(correct_s))
            diff = sp.simplify(u_expr - c_expr)
            return 1 if diff == 0 else 0
        except Exception:
            return None

    return None


def diagnose_mistake(topic: str, question: str, user_answer: str, correct_answer: str) -> tuple[list[str], str, str]:
    """Return (tags, short_fix_path, actionable_feedback)."""
    t = topic or ""
    q = question or ""
    user = (user_answer or "").strip()
    correct = (correct_answer or "").strip()

    tags: list[str] = []
    short_fix = ""
    actionable = ""

    if "四則運算" in t and "應用題" in t:
        tags = ["讀題", "選對運算（+ − × ÷）", "單位/人數/每份"]
        short_fix = "先用一句話回答：題目在問『一共/剩下/每包/平均分』哪一種？再選 + − × ÷。"
        actionable = "先圈『問句』，再圈『每/平均/剩下/一共』這些關鍵字，最後把它翻成一行算式。"
    elif "四則運算" in t:
        tags = MISTAKE_TAGS_LIBRARY["運算順序"]
        short_fix = "先圈出括號 → 再找乘除 → 最後加減（同級由左到右）。"
        actionable = "常見卡點是：先算加減、忘了先算括號、或把乘除順序做反。"
    elif "通分" in t:
        tags = MISTAKE_TAGS_LIBRARY["通分"]
        short_fix = "先找兩個分母的 LCM → 算每個分母要乘幾倍 → 分子也同步乘同樣倍數。"
        actionable = "如果公分母對了但新分子錯，通常是『分子沒有同步乘倍數』。"
    elif "約分" in t:
        tags = MISTAKE_TAGS_LIBRARY["約分"]
        short_fix = "先找分子分母的 GCD → 分子分母同時除以 GCD。"
        actionable = "如果只除分子或只除分母，就會變成不等值分數。"
    elif "分數" in t or "帶分數" in t:
        tags = ["通分", "分子運算", "約分"]
        short_fix = "先通分 → 再做分子加/減 → 最後約分到最簡。"
        actionable = "最常見錯在：忘了通分就直接加分子，或結果沒約分。"
    elif "GCD/LCM" in t:
        tags = ["最大公因數", "最小公倍數", "質因數分解"]
        short_fix = "先算 GCD → 再用 LCM = (a*b)/GCD（多數時逐步算）。"
        actionable = "若 LCM 特別大或不整除，通常是 GCD 算錯或乘除順序搞混。"
    elif "小數" in t:
        tags = MISTAKE_TAGS_LIBRARY["小數四捨五入"]
        short_fix = "先算出結果 → 看『小數點後第 3 位』決定第 2 位進位與否。"
        actionable = "常見錯在：看錯位數或把四捨五入方向做反。"
    elif "方程" in t or ("x" in q and "=" in q):
        tags = MISTAKE_TAGS_LIBRARY["移項"]
        short_fix = "先把常數移到另一邊（符號改變）→ 再兩邊同除係數。"
        actionable = "最常見錯在：移項時符號沒變（例如把 -3 移到右邊仍寫 -3）。"
    else:
        tags = ["算式抄寫", "符號", "計算細節"]
        short_fix = "先確認題目抄對 → 再慢慢算一遍 → 最後檢查符號與分數化簡。"
        actionable = "先別急著否定自己：這類錯多半是『可定位、可修復』的小細節。"

    # If we can detect a specific mismatch pattern for multi-number answers, make it actionable.
    correct_nums = re.sub(r"[^0-9\s]", "", correct)
    user_nums = re.sub(r"[^0-9\s]", "", user)
    if correct_nums.count(" ") > 0 and user_nums:
        c_parts = correct_nums.split()
        u_parts = user_nums.split()
        if len(c_parts) == len(u_parts) and len(c_parts) >= 2:
            # e.g. commondenom: [lcm, na1, na2]
            mismatch_indices = [i for i, (a, b) in enumerate(zip(u_parts, c_parts), start=1) if a != b]
            if mismatch_indices:
                actionable = f"你已經很接近了：第 {mismatch_indices[0]} 個欄位不一致。先只修正那一格就好。"

    return tags, short_fix, actionable


def build_progressive_hints(qobj: dict) -> tuple[str, str, str]:
    """Create 3 layered hints from explanation/topic.

    Hint1: tells next action (no formula)
    Hint2: partial formula/key transformation
    Hint3: full next step with a blank for learner
    """
    topic = qobj.get("topic", "")
    expl = qobj.get("explanation", "")

    # Try to extract the first "步驟" block.
    lines = [ln.strip() for ln in str(expl).splitlines() if ln.strip()]
    step_lines = [ln for ln in lines if ln.startswith("步驟") or ln.startswith("  ->") or ln.startswith("->")]
    first_step = ""
    for ln in step_lines:
        if ln.startswith("步驟"):
            first_step = ln
            break

    if "四則運算" in topic and "應用題" in topic:
        h1 = "先看最後一句『在問什麼』：一共(加)、剩下(減)、每包×幾包(乘)、平均分(除)。"
        h2 = (
            "1) 先圈『問句』：要找的是什麼？\n"
            "2) 再圈關鍵字：一共/又來/剩下/每…/平均分\n"
            "3) 把文字變成算式（先寫算式，不急著算）"
        )
        h3 = "先寫出算式（先不要算）：____"
        return h1, h2, h3
    if "四則運算" in topic:
        h1 = "先做『括號』那一小段，先不要管外面。"
        h2 = "1) 先把括號算成一個數\n2) 再把乘/除那一段算成一個數\n3) 最後只剩加減，從左到右算"
        h3 = "請先把括號算出來：括號結果 = ____ （把數字填上）"
        return h1, h2, h3
    if "通分" in topic:
        h1 = "先找兩個分母的『最小公倍數』當公分母。"
        h2 = "1) 公分母 = LCM(分母1, 分母2)\n2) 倍率1 = 公分母/分母1、倍率2 = 公分母/分母2\n3) 新分子 = 原分子×倍率（分子也要同步）"
        h3 = "請先填：公分母 = ____（只填數字）"
        return h1, h2, h3
    if "約分" in topic:
        h1 = "先找分子和分母的『最大公因數』。"
        h2 = "1) 先找 GCD(分子, 分母)\n2) 分子 ÷ GCD\n3) 分母 ÷ GCD（兩邊要同除）"
        h3 = "請先填：GCD = ____（只填數字）"
        return h1, h2, h3
    if "分數" in topic:
        h1 = "先通分，讓兩個分數的分母一樣。"
        h2 = "1) 先通分讓分母相同\n2) 分母不變，只算分子加/減\n3) 最後約分到最簡"
        h3 = "先填：公分母 = ____（只填數字）"
        return h1, h2, h3
    if "方程" in topic:
        h1 = "先把常數移到等號右邊（移項時符號要改）。"
        h2 = "1) 把常數移到另一邊（符號改變）\n2) 得到： (係數)x = 右邊的數\n3) 兩邊同除係數，得到 x"
        h3 = "請先寫出移項後那一行： (係數)x = ____（把右邊填上）"
        return h1, h2, h3

    if "分配律" in topic:
        h1 = (
            "先『判斷』是不是分配律：\n"
            "- 只有看到『外面是 ×，括號裡是 + 或 −』(a×(b±c))，才用分配律拆括號。\n"
            "- 如果只是三個數相加/相乘在換括號，那是『結合律』，不是分配律。"
        )
        h2 = (
            "1) 先拆括號：a×(b±c)=a×b ± a×c（先不要急著算出數字）\n"
            "2) 先算比較好算的那一邊（通常是整十、或有 25/75 這類）\n"
            "   - 為什麼 25 好算：25×4=100，所以 25×2=50、25×8=200，很容易變整十整百\n"
            "   - 75 也常好算：75=3×25\n"
            "3) 再算另一邊，最後把兩個結果做加/減"
        )
        h3 = "先把括號拆開：a×(b±c) = a×b ± a×____（把空格補上）"
        return h1, h2, h3

    if "結合律" in topic:
        h1 = "這題是『結合律』：三個數相加/相乘時，只是『換括號位置』讓它更好算（不是拆括號）。"
        h2 = "1) 換括號： (a+b)+c = a+(b+c) 或 (a×b)×c = a×(b×c)\n2) 先挑一組最順手的（湊 10/20/50/100 或整百）\n3) 再把剩下的補上"
        h3 = "先把最好算的兩個先括起來：____（把你選的那一組寫出來）"
        return h1, h2, h3


def _sanitize_step_hint_line(line: str) -> str | None:
    """Make step-by-step hints helpful but not reveal computed numeric results."""
    s = (line or "").strip()
    if not s:
        return None
    if "最終答案" in s:
        return None

    # If a line is an explicit calculation result, hide the computed value.
    # Examples:
    #   "-> 2×75 = 150"  -> "-> 2×75 = ____"
    #   "... = 5/6"      -> "... = ____"
    m = re.match(r"^(\s*(?:->|·|\*|\-|\+)?\s*.*?=)\s*([-+0-9./]+)\s*$", s)
    if m:
        left = m.group(1).rstrip()
        return f"{left} ____"

    # If the line is "combine" step with numbers, keep it as an instruction.
    if "合併" in s and "=" in s:
        # Keep the step label if present.
        if s.startswith("步驟"):
            return "步驟 3: 把兩邊的結果做加/減，算出最後一個數。"
        return "把兩邊的結果做加/減，算出最後一個數。"

    return s

    # Fallback hints
    next_action = "先把題目拆成最小一步：先做最內層/最關鍵那一步。"
    partial = first_step if first_step else "把第一個『步驟』做完，答案通常就會開始變清楚。"
    blank = "請先完成下一步並留一個空格給自己檢查：____"
    return next_action, partial, blank


def prompt_step_by_step_check(question_text: str) -> list[str]:
    q = (question_text or "").strip()
    is_equation_like = ("x" in q.lower()) or ("=" in q)

    print(f"\n{Colors.YELLOW}[逐步檢查（小學生版）]{Colors.END}")
    print("你現在要做的事很簡單：")
    print("1) 先把『題目』抄下來（當作第 1 行）")
    print("2) 每次只做『一個小動作』，再寫成下一行")
    print("   - 小動作例子：換括號位置、先算括號裡、先算好算的一組、先通分、先約分…")
    print("3) 直到你寫出最後答案")
    print("重點：每一行都要跟上一行『一樣的意思』（只是換寫法或算掉一部分）。")

    if is_equation_like:
        print("\n範例（方程式）：")
        print("  2*x+3=9")
        print("  2*x=6")
        print("  x=3")
        print("（最後一行寫出 x 是多少）")
    else:
        print("\n範例（三個數相加，用結合律換括號更好算）：")
        print("  (14 + 9) + 31")
        print("  14 + (9 + 31)     （把括號換位置）")
        print("  14 + 40           （先算 9+31）")
        print("  54                （最後算 14+40）")
        print("（最後一行可以只寫數字答案）")

    print("\n開始吧！每行輸入一個步驟；直接按 Enter（空白行）就結束。")
    steps: list[str] = []
    while True:
        line = input("step> ").strip()
        if not line:
            break
        steps.append(line)
    return steps


def run_step_by_step_hints(qobj: dict) -> None:
    """Step-by-step hints (guided), for students who don't know what to type.

    - Shows solution steps progressively (from explanation), without forcing user input.
    - Avoids revealing the final answer unless the student explicitly asks.
    """
    topic = str(qobj.get("topic", "")).strip()
    question = str(qobj.get("question", "")).strip()
    explanation = str(qobj.get("explanation", "")).strip()
    # Intentionally do NOT allow showing the final answer here.

    raw_lines = [ln.strip() for ln in explanation.splitlines() if ln.strip()]

    # Keep only "step-like" lines; then sanitize so we don't reveal computed results.
    step_lines: list[str] = []
    for ln in raw_lines:
        if ln.startswith("步驟") or "->" in ln or ln.startswith("💡"):
            cleaned = _sanitize_step_hint_line(ln)
            if cleaned:
                step_lines.append(cleaned)

    # Fallback: if explanation format is unusual, still provide something useful.
    if not step_lines:
        for ln in raw_lines[:10]:
            cleaned = _sanitize_step_hint_line(ln)
            if cleaned:
                step_lines.append(cleaned)

    print(f"\n{Colors.YELLOW}[逐步提示]{Colors.END}（系統一步一步帶你算）")
    if topic:
        print(f"題型：{topic}")
    if question:
        print(f"題目：{question}")

    if not step_lines:
        print(f"{Colors.YELLOW}這題目前沒有可拆分的提示。你可以改用 Hint 1/2/3，或直接看詳解。{Colors.END}")
        return

    print("\n玩法：按 Enter 看下一步；輸入 q 離開。")
    idx = 0
    total = len(step_lines)
    while idx < total:
        cmd = input(f"(逐步提示 {idx+1}/{total}) 你的選擇 [Enter/q]: ").strip().lower()
        if cmd == "q":
            print(f"{Colors.YELLOW}已離開逐步提示。你可以回去繼續作答。{Colors.END}")
            return
        if cmd == "a":
            print(f"{Colors.YELLOW}這裡不提供看答案喔！我們用提示一步一步做，你一定做得到。{Colors.END}")
            continue

        # Show next hint line
        print(f"{Colors.YELLOW}{step_lines[idx]}{Colors.END}")
        idx += 1

    print(f"\n{Colors.GREEN}逐步提示已全部看完！現在回去再試著作答看看。{Colors.END}")


def _sympy_parse_line(line: str):
    line_c = _clean_math_text(line)
    if "=" in line_c:
        lhs_str, rhs_str = [p.strip() for p in line_c.split("=", 1)]
        lhs = sp.sympify(lhs_str)
        rhs = sp.sympify(rhs_str)
        return sp.Eq(lhs, rhs)
    return sp.sympify(line_c)


def check_steps_equivalence(question_text: str, steps: list[str]) -> tuple[int | None, str]:
    """Return (first_wrong_line_index_1based or None, feedback)."""
    if not steps:
        return None, "未輸入步驟。"

    # Extract a math-only baseline from common question formats.
    raw_q = str(question_text)
    # If there is a comma/Chinese comma, keep the left part.
    raw_q = raw_q.split(",")[0].split("，")[0]
    # Remove trailing prompts.
    raw_q = raw_q.replace("= ?", "").replace("=?", "")
    raw_q = raw_q.replace("求 x", "").replace("求x", "")
    q = _clean_math_text(raw_q)

    # If SymPy available, use it.
    if HAS_SYMPY:
        try:
            # Determine baseline: equation or expression.
            baseline = _sympy_parse_line(q) if ("=" in q or "x" in q or "X" in q) else sp.sympify(q)
            prev = baseline
            for idx, raw in enumerate(steps, start=1):
                cur = _sympy_parse_line(raw)

                # Compare equivalence.
                if isinstance(prev, sp.Equality) and isinstance(cur, sp.Equality):
                    x = sp.Symbol('x')
                    prev_sol = sp.solve(prev, x)
                    cur_sol = sp.solve(cur, x)
                    if prev_sol != cur_sol:
                        return idx, "這一步改寫後的解集不同。常見原因：移項時符號沒變、或兩邊操作不一致（例如只對一邊除以某數）。"
                else:
                    # numeric/expression value equivalence
                    diff = sp.simplify(prev - cur)
                    if diff != 0:
                        return idx, "這一步的結果與上一行不等價。常見原因：運算順序（括號/乘除）或正負號。"

                prev = cur
            return None, "每一步看起來都等價！如果答案還不對，可能是最後一步格式/約分/四捨五入。"
        except Exception as e:
            return 1, f"逐步檢查解析失敗：{e}（可改用純數字算式，或先安裝 sympy）"

    # Fallback: numeric-only (no variables, no '='), compare as Fractions.
    if any(("x" in s.lower() or "=" in s) for s in steps) or ("x" in q.lower()) or ("=" in q):
        return 1, "目前環境未安裝 SymPy，逐步等價檢查只支援純數字算式。若要檢查方程式，請安裝 sympy。"

    # numeric baseline
    if not _is_numeric_expression(q):
        return 1, "題目不是純數字算式，無法在未安裝 SymPy 時做等價檢查。"

    def eval_fraction(expr: str) -> Fraction | None:
        s = _clean_math_text(expr)
        if not _is_numeric_expression(s):
            return None
        try:
            # Use Python eval on restricted alphabet; acceptable in local CLI.
            val = eval(s, {"__builtins__": {}}, {})
            return Fraction(val).limit_denominator()
        except Exception:
            return None

    prev_val = eval_fraction(q)
    if prev_val is None:
        return 1, "無法解析題目算式。"
    for idx, raw in enumerate(steps, start=1):
        cur_val = eval_fraction(raw)
        if cur_val is None:
            return idx, "這一行包含無法解析的符號。建議只用數字與 + - * / ( )。"
        if cur_val != prev_val:
            return idx, "這一步的數值與上一行不同。常見原因：括號/乘除優先順序或正負號。"
        prev_val = cur_val
    return None, "每一步的數值都一致！"

# =========================
# 遊戲化/獎勵邏輯 (答對/答錯回饋)
# =========================

# 答對時的隨機鼓勵 (強調成就與方法) - 保持不變
CORRECT_MESSAGES = [
    "🎉 **太棒了！答案完全正確！** 你真的非常專心，方法用對了，答案就出來了！",
    "🌟 **厲害！** 你又解決了一個複雜的算式，你真的是一個小小數學家！",
    "💯 **答對了！** 你的計算速度和準確度都在進步喔！太棒了！",
    "🥇 **恭喜你！** 這次的表現非常出色，每一步思考的痕跡都很清楚。",
    "💡 **成功！** 你用的方法很聰明，找到對的路徑，問題就迎刃而解！",
    "🚀 **真是驚人的表現！** 你具備了學好數學的潛力，繼續保持！"
]

# 答錯時的客製化回饋（反挫折：不貼標籤，只給可操作下一步）
INCORRECT_CUSTOM_FEEDBACK = (
    f"{Colors.RED}這題目前還沒對上，但你不是不會。{Colors.END}\n"
    f"{Colors.YELLOW}我會先幫你定位卡點，給你最短補救路徑；如果你想，也可以再試一次。{Colors.END}"
)


REWARDS = [
    ("✨", "太棒了！你像數學超人！"),
    ("⭐", "天才！繼續保持！"),
    ("🏆", "恭喜獲得獎杯！"),
    ("💯", "完美！你已經超越了自我！"),
    ("🚀", "速度與精準的結合！"),
]

def display_reward():
    """根據答對題數，顯示圖形獎勵 (暖色強化)。"""
    global CORRECT_COUNT 
    if CORRECT_COUNT > 0 and CORRECT_COUNT % 5 == 0:
        index = (CORRECT_COUNT // 5 - 1) % len(REWARDS)
        icon, message = REWARDS[index]
        
        print(f"\n{Colors.YELLOW}═"*40)
        # 標題和訊息使用暖色 (YELLOW) 顯示
        print(f"║ {icon*3} {message.upper().center(29)} {icon*3} ║")
        print(f"║ {message.center(36)} ║")
        print(f"═"*40 + f"{Colors.END}\n")

def update_counters(is_correct: int | None):
    """更新全局計數器"""
    global TOTAL_COUNT, CORRECT_COUNT
    
    TOTAL_COUNT += 1
    if is_correct == 1:
        CORRECT_COUNT += 1

    print(f"\n{Colors.GOLD}[進度]{Colors.END} 總作答：{TOTAL_COUNT} 題 | 答對：{CORRECT_COUNT} 題 (正確率: {(CORRECT_COUNT/TOTAL_COUNT*100) if TOTAL_COUNT else 0:.1f}%)")


def get_today_attempts(conn: sqlite3.Connection) -> int:
    """Count today's auto attempts (correct or incorrect; excludes invalid)."""
    today = _today_ymd()
    cur = conn.cursor()
    where = "WHERE mode = 'auto' AND is_correct IN (0,1) AND ts LIKE ?"
    params: list = [f"{today}%"]
    if CURRENT_IDENTITY is not None and RECORDS_HAS_IDENTITY_COLUMNS:
        where += " AND student_id = ?"
        params.append(CURRENT_IDENTITY.student_id)
    try:
        return int(cur.execute(f"SELECT COUNT(*) FROM records {where}", tuple(params)).fetchone()[0])
    except Exception:
        return 0


def print_daily_mission_status(conn: sqlite3.Connection) -> None:
    done = get_today_attempts(conn)
    goal = DEFAULT_DAILY_GOAL
    remaining = max(0, goal - done)
    if done < goal:
        print(f"{Colors.GOLD}[今日任務]{Colors.END} {done}/{goal} 題（剩 {remaining} 題一定做得到）")
    else:
        print(f"{Colors.GREEN}[今日任務]{Colors.END} {done}/{goal} 已完成！你已把今天的基本功打卡了。")


def maybe_offer_easter_egg(conn: sqlite3.Connection) -> None:
    """After daily goal, offer one optional bonus question as a small surprise."""
    done = get_today_attempts(conn)
    # Offer only once when the goal is first reached.
    if done != DEFAULT_DAILY_GOAL:
        return
    choice = input(f"{Colors.YELLOW}彩蛋解鎖：要不要加玩 1 題『彩蛋題』？(y/n): {Colors.END}").strip().lower()
    if choice != 'y':
        return
    # Use random generator but keep it lightweight.
    gen_func = get_random_generator(None)
    qobj = generate_unique_question(gen_func)
    print(f"\n{Colors.YELLOW}[彩蛋題]{Colors.END} {qobj['topic']}：{Colors.YELLOW}{qobj['question']}{Colors.END}")
    user = input("你的答案: ").strip()
    is_correct = check_equivalent_answer(user, qobj["answer"])
    if is_correct == 1:
        print(f"{Colors.GREEN}完成彩蛋！你解鎖了一張小技能卡：『把難題切成最小一步』{Colors.END}")
    else:
        print(f"{Colors.YELLOW}彩蛋題是加分題，答錯也完全 OK。標準答案：{qobj['answer']}{Colors.END}")
    print(f"\n{Colors.YELLOW}[彩蛋詳解]{Colors.END}\n{qobj['explanation']}\n")


# =========================
# DB 初始化與操作
# =========================
def _ensure_records_identity_columns(conn: sqlite3.Connection) -> None:
    """Add account/student columns to math_log.db records table (non-destructive)."""
    global RECORDS_HAS_IDENTITY_COLUMNS
    cols = {r[1] for r in conn.execute("PRAGMA table_info(records)").fetchall()}
    # Keep names simple and aligned with app.db concept.
    wanted = {
        "account_id": "INTEGER",
        "student_id": "INTEGER",
        "api_key": "TEXT",
        "student_name": "TEXT",
    }
    for col, col_type in wanted.items():
        if col not in cols:
            conn.execute(f"ALTER TABLE records ADD COLUMN {col} {col_type}")
    conn.commit()
    # After migration, treat as available.
    cols2 = {r[1] for r in conn.execute("PRAGMA table_info(records)").fetchall()}
    RECORDS_HAS_IDENTITY_COLUMNS = all(c in cols2 for c in wanted)


def _ensure_records_coach_columns(conn: sqlite3.Connection) -> None:
    """Add coaching columns for mistake tags and coach notes (non-destructive)."""
    global RECORDS_HAS_COACH_COLUMNS
    cols = {r[1] for r in conn.execute("PRAGMA table_info(records)").fetchall()}
    wanted = {
        "mistake_tags": "TEXT",
        "coach_note": "TEXT",
    }
    for col, col_type in wanted.items():
        if col not in cols:
            conn.execute(f"ALTER TABLE records ADD COLUMN {col} {col_type}")
    conn.commit()
    cols2 = {r[1] for r in conn.execute("PRAGMA table_info(records)").fetchall()}
    RECORDS_HAS_COACH_COLUMNS = all(c in cols2 for c in wanted)


def init_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    """建立/開啟 math_log.db，並建立紀錄表"""
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            mode TEXT, 
            topic TEXT, 
            difficulty TEXT, 
            question TEXT,
            correct_answer TEXT,
            user_answer TEXT,
            is_correct INTEGER, 
            explanation TEXT,
            mistake_tags TEXT,
            coach_note TEXT
        )
        """
    )
    _ensure_records_identity_columns(conn)
    _ensure_records_coach_columns(conn)
    conn.commit()
    return conn


def log_record(
    conn: sqlite3.Connection,
    mode: str,
    topic: str,
    difficulty: str,
    question: str,
    correct_answer: str,
    user_answer: str,
    is_correct: int | None,
    explanation: str,
    mistake_tags: str = "",
    coach_note: str = "",
):
    """
    紀錄作答結果到資料庫。
    """
    ts = datetime.now().isoformat(timespec="seconds")
    # Ensure flags are correct even if db existed before.
    has_coach_cols = RECORDS_HAS_COACH_COLUMNS
    if not has_coach_cols:
        try:
            _ensure_records_coach_columns(conn)
            has_coach_cols = RECORDS_HAS_COACH_COLUMNS
        except Exception:
            has_coach_cols = False

    if CURRENT_IDENTITY is not None and RECORDS_HAS_IDENTITY_COLUMNS:
        if has_coach_cols:
            conn.execute(
                """
                INSERT INTO records
                (ts, mode, topic, difficulty, question, correct_answer,
                 user_answer, is_correct, explanation,
                 mistake_tags, coach_note,
                 account_id, student_id, api_key, student_name)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    ts,
                    mode,
                    topic,
                    difficulty,
                    question,
                    correct_answer,
                    user_answer,
                    is_correct,
                    explanation,
                    mistake_tags,
                    coach_note,
                    CURRENT_IDENTITY.account_id,
                    CURRENT_IDENTITY.student_id,
                    CURRENT_IDENTITY.api_key,
                    CURRENT_IDENTITY.student_name,
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO records
                (ts, mode, topic, difficulty, question, correct_answer,
                 user_answer, is_correct, explanation,
                 account_id, student_id, api_key, student_name)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    ts,
                    mode,
                    topic,
                    difficulty,
                    question,
                    correct_answer,
                    user_answer,
                    is_correct,
                    explanation,
                    CURRENT_IDENTITY.account_id,
                    CURRENT_IDENTITY.student_id,
                    CURRENT_IDENTITY.api_key,
                    CURRENT_IDENTITY.student_name,
                ),
            )
    else:
        if has_coach_cols:
            conn.execute(
                """
                INSERT INTO records
                (ts, mode, topic, difficulty, question, correct_answer,
                 user_answer, is_correct, explanation, mistake_tags, coach_note)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    ts,
                    mode,
                    topic,
                    difficulty,
                    question,
                    correct_answer,
                    user_answer,
                    is_correct,
                    explanation,
                    mistake_tags,
                    coach_note,
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO records
                (ts, mode, topic, difficulty, question, correct_answer,
                 user_answer, is_correct, explanation)
                VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    ts,
                    mode,
                    topic,
                    difficulty,
                    question,
                    correct_answer,
                    user_answer,
                    is_correct,
                    explanation,
                ),
            )
    conn.commit()


# =========================
# 數學出題邏輯 (Generator)
# =========================

def gen_order_of_ops_arith():
    """
    四則運算題 (含括號、乘除) - 核心教學目標：運算順序
    數字範圍 <= 100，乘除結果確保整數且數字好算。
    
    V11.2 FIX: 解決 UnboundLocalError 
    """
    
    # --- 步驟 1: 設計乘除部分 (簡單整數) ---
    op_mul_div = random.choice(["*", "/"])
    
    if op_mul_div == "*":
        # 2~10 * 2~10
        b = random.randint(2, 10)
        c = random.randint(2, 10)
        result_mul_div = b * c          # <-- 乘法結果存入此變數
        op_text_md = "×"
        sub_expr_md = f"{b} × {c}"
    else: # /
        # 乘積 <= 50，除數 2~10
        result_div = random.randint(2, 5)
        c = random.randint(2, 10)
        b = result_div * c
        result_mul_div = result_div     # <-- 除法結果存入此變數 (FIX)
        op_text_md = "÷"
        sub_expr_md = f"{b} ÷ {c}"

    # --- 步驟 2: 設計括號內的加減 ---
    a1 = random.randint(5, 30)
    a2 = random.randint(5, 30)
    op_add_sub_paren = random.choice(["+", "-"])
    
    if op_add_sub_paren == "+":
        paren_result = a1 + a2
        op_text_paren = "+"
    else:
        # 減法確保結果為正
        if a1 < a2:
            a1, a2 = a2, a1
        paren_result = a1 - a2
        op_text_paren = "-"
    
    paren_expr = f"({a1} {op_text_paren} {a2})"

    # --- 步驟 3: 組合所有部分 (確保所有數字不超過 100) ---
    
    e = random.randint(1, 10)
    
    # 算式結構: (A op B) op1 (C op D) op2 E
    op1 = random.choice(["+", "-"])
    op2 = random.choice(["+", "-"])
    
    # 組裝題目字串 (使用符號轉化)
    question = f"{paren_expr} {op1} {sub_expr_md} {op2} {e} = ?"
    
    # 嚴謹計算答案 (Python eval)
    ans = eval(f"({a1} {op_text_paren} {a2}) {op1} ({b} {op_mul_div} {c}) {op2} {e}")
    
    # V9 運算順序強化詳解
    explanation_steps = [
        f"步驟 1: **先算括號**",
        f"   -> {a1} {op_text_paren} {a2} = {paren_result}",
        f"   -> 算式變為: {paren_result} {op1} {sub_expr_md} {op2} {e}",
        f"步驟 2: **再算乘除**",
        f"   -> {sub_expr_md} = {result_mul_div}", # <-- 使用統一變數 result_mul_div
        f"   -> 算式變為: {paren_result} {op1} {result_mul_div} {op2} {e}",
        f"步驟 3: **最後算加減** (從左到右)",
        f"   -> 第一部分: {paren_result} {op1} {result_mul_div} = {eval(f'{paren_result} {op1} {result_mul_div}')}",
        f"   -> 第二部分: {eval(f'{paren_result} {op1} {result_mul_div}')} {op2} {e} = {ans}",
        f"最終答案: {ans}",
        f"\n💡 運算順序口訣：**括號** 優先，**乘除** 次之，**加減** 最後，同級運算 **由左至右**。"
    ]

    return {
        "topic": "四則運算 (順序)",
        "difficulty": "medium",
        "question": question,
        "answer": str(ans),
        "explanation": "\n".join(explanation_steps),
    }

# -------------------------------------------------------------
# 以下所有 gen_* 函數均保持不變
# -------------------------------------------------------------

def gen_fraction_commondenom():
    """分數通分練習 (新增題型)"""
    b1 = random.choice([4, 6, 8, 10, 12])
    b2 = random.choice([4, 6, 8, 10, 12])
    a1 = random.randint(1, b1 - 1)
    a2 = random.randint(1, b2 - 1)

    # 確保 b1 != b2 且分數不相等
    while b1 == b2 or a1/b1 == a2/b2:
        b2 = random.choice([4, 6, 8, 10, 12])
        a2 = random.randint(1, b2 - 1)
    
    # 計算 LCM 作為公分母
    gcd_val = math.gcd(b1, b2)
    lcm_val = (b1 * b2) // gcd_val
    m1 = lcm_val // b1
    m2 = lcm_val // b2
    
    na1 = a1 * m1
    na2 = a2 * m2
    
    question = f"請將 {a1}/{b1} 和 {a2}/{b2} 通分。\n請依序輸入：公分母 新分子1 新分子2"
    topic = "分數通分"
    answer = f"{lcm_val} {na1} {na2}"
    
    explanation = [
        f"目標：將 {a1}/{b1} 和 {a2}/{b2} 轉換為相同分母的等值分數。",
        f"步驟 1: **關鍵步驟 - 尋找公分母**",
        f"  -> 公分母必須是 {b1} 和 {b2} 的公倍數，最小的公倍數即為 **最小公倍數 (LCM)**。",
        f"  -> 計算結果: LCM({b1}, {b2}) = {lcm_val} (這是您的第一個答案)",
        f"步驟 2: **計算第一個新分子**",
        f"  -> 原分母 {b1} 擴大 {m1} 倍成為 {lcm_val}。",
        f"  -> 根據分數基本性質，分子 {a1} 也需擴大 {m1} 倍: {a1} × {m1} = {na1} (這是您的第二個答案)",
        f"步驟 3: **計算第二個新分子**",
        f"  -> 原分母 {b2} 擴大 {m2} 倍成為 {lcm_val}。",
        f"  -> 分子 {a2} 也需擴大 {m2} 倍: {a2} × {m2} = {na2} (這是您的第三個答案)",
        f"最終答案 (公分母 新分子1 新分子2) 為: {answer}"
    ]

    return {
        "topic": topic,
        "difficulty": "easy",
        "question": question,
        "answer": answer,
        "explanation": "\n".join(explanation),
    }


def gen_fraction_reduction():
    """分數約分練習 (新增題型)"""
    # 產生一個簡化後的分數
    simplified_num = random.randint(1, 15)
    simplified_den = random.randint(simplified_num + 1, 20)
    
    # 確保簡化後的分數已經是最簡 (GCD=1)
    while math.gcd(simplified_num, simplified_den) != 1:
        simplified_num = random.randint(1, 15)
        simplified_den = random.randint(simplified_num + 1, 20)

    # 選擇一個擴大倍數 (GCD)
    multiplier = random.randint(2, 5)
    
    # 產生原始題目
    original_num = simplified_num * multiplier
    original_den = simplified_den * multiplier
    
    gcd_val = multiplier
    
    question = f"請將分數 {original_num}/{original_den} 約分到最簡。\n請輸入：分子 分母"
    topic = "分數約分"
    answer = f"{simplified_num} {simplified_den}"
    
    explanation = [
        f"目標：將 {original_num}/{original_den} 轉換為最簡分數。",
        f"步驟 1: **關鍵步驟 - 尋找最大公因數 (GCD)**",
        f"  -> GCD 是能同時整除分子 {original_num} 和分母 {original_den} 的最大整數。",
        f"  -> 計算結果: GCD({original_num}, {original_den}) = {gcd_val}",
        f"步驟 2: **進行約分**",
        f"  -> 根據分數基本性質，分子和分母同時除以這個 GCD。",
        f"  -> 新分子: {original_num} ÷ {gcd_val} = {simplified_num} (這是您的第一個答案)",
        f"  -> 新分母: {original_den} ÷ {gcd_val} = {simplified_den} (這是您的第二個答案)",
        f"最終答案 (分子 分母) 為: {simplified_num} {simplified_den}"
    ]

    return {
        "topic": topic,
        "difficulty": "easy",
        "question": question,
        "answer": answer,
        "explanation": "\n".join(explanation),
    }


def _fraction_core(a1, b1, a2, b2, op):
    """共用的分數加減核心 - 強化通分引導"""
    f1 = Fraction(a1, b1)
    f2 = Fraction(a2, b2)
    
    # 確保減法結果為正
    if op == "-":
        if f1 < f2:
            f1, f2 = f2, f1
            a1, b1, a2, b2 = f1.numerator, f1.denominator, f2.numerator, f2.denominator

    if op == "+":
        result = f1 + f2
        op_text = "加法"
        sign_text = "+"
    else:
        result = f1 - f2
        op_text = "減法"
        sign_text = "-"

    gcd_val = math.gcd(b1, b2)
    lcm_val = (b1 * b2) // gcd_val
    m1 = lcm_val // b1
    m2 = lcm_val // b2
    
    na1 = a1 * m1
    na2 = a2 * m2

    if op == "+":
        ns = na1 + na2
    else:
        ns = na1 - na2

    # V9 教學強化詳解
    expl = [
        f"步驟 1: **準備通分** - 分數相加或相減，必須找到公分母 (即 {b1} 和 {b2} 的 LCM)。",
        f"  -> 計算結果: LCM({b1}, {b2}) = {lcm_val}",
        f"步驟 2: **進行通分** - 轉換為分母為 {lcm_val} 的等值分數：",
        f"  -> {a1}/{b1} 擴大 {m1} 倍變為 {na1}/{lcm_val}",
        f"  -> {a2}/{b2} 擴大 {m2} 倍變為 {na2}/{lcm_val}",
        f"步驟 3: **計算分子** - 進行 {op_text} 運算：",
        f"= {na1}/{lcm_val} {sign_text} {na2}/{lcm_val} = {ns}/{lcm_val}",
        f"步驟 4: **結果約分** - 將結果 {ns}/{lcm_val} 化簡為最簡分數：",
        f"  -> 最終答案: {result.numerator}/{result.denominator}"
    ]

    return result, expl


def gen_fraction_add():
    """真分數加減 (小學 5 年級)"""
    b1 = random.randint(2, 9)
    b2 = random.randint(2, 9)
    a1 = random.randint(1, b1 - 1)
    a2 = random.randint(1, b2 - 1)
    op = random.choice(["+", "-"])

    result, expl = _fraction_core(a1, b1, a2, b2, op)
    question = f"{a1}/{b1} {op} {a2}/{b2} = ?"
    
    return {
        "topic": "分數加減",
        "difficulty": "medium",
        "question": question,
        "answer": f"{result.numerator}/{result.denominator}",
        "explanation": "\n".join(expl),
    }


def gen_fraction_mixed():
    """帶分數加減 (小學 5 年級)"""
    w1 = random.randint(1, 5)
    w2 = random.randint(1, 5)
    b1 = random.randint(2, 9)
    b2 = random.randint(2, 9)
    a1 = random.randint(1, b1 - 1)
    a2 = random.randint(1, b2 - 1)
    op = random.choice(["+", "-"])

    F1 = Fraction(w1 * b1 + a1, b1)
    F2 = Fraction(w2 * b2 + a2, b2)
    
    result, expl_core = _fraction_core(F1.numerator, F1.denominator, F2.numerator, F2.denominator, op)

    whole = result.numerator // result.denominator
    remain = result.numerator % result.denominator
    ans_str = f"{whole} {remain}/{result.denominator}" if remain != 0 and whole != 0 else f"{result.numerator}/{result.denominator}"

    expl = [
        "步驟 1: **化為假分數** - 將帶分數轉換為假分數，方便統一運算。",
        f"  -> 第一個數: {w1} {a1}/{b1} -> {F1.numerator}/{F1.denominator}",
        f"  -> 第二個數: {w2} {a2}/{b2} -> {F2.numerator}/{F2.denominator}",
        "步驟 2: **進行分數運算** (通分、加/減、約分詳解如下)"
    ] + expl_core

    return {
        "topic": "帶分數運算",
        "difficulty": "medium",
        "question": f"{w1} {a1}/{b1} {op} {w2} {a2}/{b2} = ?",
        "answer": ans_str,
        "explanation": "\n".join(expl),
    }


def gen_gcd_lcm():
    """最大公因數 (GCD) 和 最小公倍數 (LCM) 題 (教學強化)"""
    count = random.choice([2, 3])
    if count == 2:
        a = random.randint(10, 50)
        b = random.randint(10, 50)
        
        gcd_val = math.gcd(a, b)
        lcm_val = (a * b) // gcd_val
        
        question = f"數字 {a} 和 {b} 的最大公因數(GCD)和最小公倍數(LCM)各是多少？\n請依序輸入：GCD LCM"
        topic = "GCD/LCM (二數)"
        
        explanation = [
            f"計算目標：數字 {a} 和 {b} 的 GCD 和 LCM。",
            f"步驟 1: **最大公因數 (GCD)**",
            f"  -> GCD 是能同時整除所有數字的最大數。計算結果: {gcd_val}",
            f"步驟 2: **最小公倍數 (LCM)**",
            f"  -> 公式：LCM(a, b) = (|a * b|) / GCD(a, b)",
            f"  -> 計算：({a} × {b}) ÷ {gcd_val} = {lcm_val}",
            f"答案格式為 GCD LCM，所以答案是: {gcd_val} {lcm_val}"
        ]

    else: 
        a = random.randint(5, 20)
        b = random.randint(5, 20)
        c = random.randint(5, 20)
        
        gcd_val = math.gcd(a, math.gcd(b, c))
        
        # 使用 math.gcd 輔助計算 LCM
        lcm_val_ab = (a * b) // math.gcd(a, b)
        lcm_val = (lcm_val_ab * c) // math.gcd(lcm_val_ab, c)
            
        question = f"數字 {a}, {b}, {c} 的最大公因數(GCD)和最小公倍數(LCM)各是多少？\n請依序輸入：GCD LCM"
        topic = "GCD/LCM (三數)"
        
        explanation = [
            f"計算目標：數字 {a}, {b}, {c} 的 GCD 和 LCM。",
            f"步驟 1: **最大公因數 (GCD)**",
            f"  -> 連續求兩數的 GCD：GCD({a}, {b})，再求 GCD(結果, {c})。計算結果: {gcd_val}",
            f"步驟 2: **最小公倍數 (LCM)**",
            f"  -> 逐次計算：LCM({a}, {b}) = {lcm_val_ab}。",
            f"  -> 再求 LCM({lcm_val_ab}, {c})。計算結果: {lcm_val}",
            f"答案格式為 GCD LCM，所以答案是: {gcd_val} {lcm_val}"
        ]
        
    answer = f"{gcd_val} {lcm_val}"
        
    return {
        "topic": topic,
        "difficulty": "medium",
        "question": question,
        "answer": answer,
        "explanation": "\n".join(explanation),
    }


def gen_decimal_arith():
    """小數加減乘除題 (小學 5 年級)"""
    a = round(random.uniform(0.5, 20.0), random.randint(1, 2))
    b = round(random.uniform(0.5, 10.0), random.randint(1, 2))
    op = random.choice(["+", "-", "×", "÷"])

    if op == '+':
        ans = a + b
    elif op == '-':
        if a < b: a, b = b, a
        ans = a - b
    elif op == '×':
        ans = a * b
    else: # ÷
        ans_target = round(random.uniform(1.0, 5.0), 2)
        b = round(random.uniform(1.0, 5.0), 1)
        a = round(b * ans_target, 2)
        ans = a / b

    final_ans = round(ans, 2)
    
    question = f"計算並將結果四捨五入到小數點後兩位：\n{a} {op} {b} = ?"
    explanation = [
        f"步驟 1: 進行運算: {a} {op} {b} ≈ {ans}",
        f"步驟 2: 根據題目要求，將結果 {ans} 四捨五入到小數點後兩位。",
        f"  -> 四捨五入後答案: {final_ans}"
    ]

    return {
        "topic": "小數四則運算",
        "difficulty": "medium",
        "question": question,
        "answer": str(final_ans),
        "explanation": "\n".join(explanation),
    }


def gen_volume_area():
    """體積與面積 (正方體/長方體) (小學 5 年級)"""
    length = random.randint(2, 10)
    width = random.randint(2, 10)
    height = random.randint(2, 10)
    
    q_type = random.choice(["volume", "surface_area"])
    
    if length == width == height:
        shape = "正方體"
        
        if q_type == "volume":
            ans = length ** 3
            q_text = f"邊長為 {length} 公分的{shape}，體積是多少立方公分？"
            expl = f"體積公式: 邊長 × 邊長 × 邊長\n= {length} × {length} × {length} = {ans}"
        else: # surface_area
            ans = 6 * (length ** 2)
            q_text = f"邊長為 {length} 公分的{shape}，表面積是多少平方公分？"
            expl = f"表面積公式: 6 × (邊長 × 邊長)\n= 6 × ({length} × {length}) = {ans}"
            
    else:
        shape = "長方體"
        dims = f"長 {length}、寬 {width}、高 {height}"
        
        if q_type == "volume":
            ans = length * width * height
            q_text = f"{dims} 公分的{shape}，體積是多少立方公分？"
            expl = f"體積公式: 長 × 寬 × 高\n= {length} × {width} × {height} = {ans}"
        else: # surface_area
            lw = length * width
            lh = length * height
            wh = width * height
            ans = 2 * (lw + lh + wh)
            q_text = f"{dims} 公分的{shape}，表面積是多少平方公分？"
            expl = f"表面積公式: 2 × (長×寬 + 長×高 + 寬×高)\n= 2 × ({lw} + {lh} + {wh}) = {ans}"

    return {
        "topic": f"{shape} {q_type.replace('_',' ')}",
        "difficulty": "easy",
        "question": q_text,
        "answer": str(ans),
        "explanation": expl,
    }


def gen_linear_equation():
    """一元一次方程 (教學強化)"""
    x_val = random.randint(-9, 9)
    a = random.randint(2, 9)
    b = random.randint(-10, 10)
    c = a * x_val + b
    
    question = f"{a}x + {b} = {c}, 求 x"
    
    # V9 教學強化詳解
    expl = [
        f"給定方程式: {a}x + {b} = {c}",
        f"步驟 1: **應用等量公理 (移項)** - 目標是將 x 以外的常數移到等號的另一邊。",
        f"  -> 將 {b} 移到右邊，符號改變：",
        f"  -> {a}x = {c} - ({b})",
        f"  -> {a}x = {c - b}",
        f"步驟 2: **求解 x** - 將 x 的係數 {a} 移到右邊。",
        f"  -> (兩邊同時除以 {a})",
        f"  -> x = ({c - b}) / {a}",
        f"  -> x = {x_val}",
        f"最終答案: x = {x_val}"
    ]

    return {
        "topic": "一元一次方程",
        "difficulty": "medium",
        "question": question,
        "answer": str(x_val),
        "explanation": "\n".join(expl),
    }


# 題型產生器映射表 (已重新編號)
GENERATORS = {
    "1": ("四則運算 (含括號/乘除)", gen_order_of_ops_arith),
    "2": ("分數通分", gen_fraction_commondenom),
    "3": ("分數約分", gen_fraction_reduction),
    "4": ("分數加減", gen_fraction_add),
    "5": ("帶分數運算", gen_fraction_mixed),
    "6": ("GCD/LCM", gen_gcd_lcm),
    "7": ("小數四則運算", gen_decimal_arith),
    "8": ("長/正方體積/面積", gen_volume_area),
}

if HAS_SYMPY:
    GENERATORS["9"] = ("一元一次方程", gen_linear_equation)

# 新增：分數好算闖關題型
GENERATORS["10"] = ("分數加減（好算）", gen_fraction_addsub_easy)
GENERATORS["11"] = ("整數與分數（好算）", gen_int_fraction_addsub_easy)
GENERATORS["12"] = ("分數四則（解鎖）", gen_fraction_four_ops_easy)
GENERATORS["13"] = ("分配律（好算）", gen_distributive_law_easy)
GENERATORS["14"] = ("結合律（好算）", gen_associative_law_easy)

# 新增：四則運算應用題（文字題）
GENERATORS["15"] = ("四則運算（應用題）", gen_arith_application_problem)


def _select_fraction_progress_generator(topic_key: str):
    """Adaptive progression: after consecutive correct fraction answers, unlock four ops."""
    # Base generator depends on selected training mode.
    base_gen = gen_fraction_addsub_easy if topic_key == "10" else gen_int_fraction_addsub_easy

    # 3-stage curve: gradually increase mul/div share.
    if FRACTION_STREAK < FRACTION_UNLOCK_STAGE1_AT:
        return base_gen

    if FRACTION_STREAK < FRACTION_UNLOCK_STAGE2_AT:
        p_muldiv = 0.20
    elif FRACTION_STREAK < FRACTION_UNLOCK_STAGE3_AT:
        p_muldiv = 0.40
    else:
        p_muldiv = 0.60

    def _gen():
        if random.random() < p_muldiv:
            # Prefer fraction×÷fraction for mul/div stage.
            return gen_fraction_muldiv_easy()
        # Otherwise keep add/sub practice (topic 10) or int±frac (topic 11)
        return base_gen()

    return _gen

def get_random_generator(topic_filter=None):
    """根據篩選器回傳出題函數。"""
    if topic_filter and topic_filter in GENERATORS:
        return GENERATORS[topic_filter][1]
    
    keys = list(GENERATORS.keys())
    k = random.choice(keys)
    return GENERATORS[k][1]


# =========================
# 答案解析與比對
# =========================
def parse_answer(text: str) -> Fraction | None:
    text = text.strip()
    if not text:
        return None
    try:
        # 處理帶分數 e.g. "1 1/2"
        if " " in text and "/" in text:
            parts = text.split()
            if len(parts) == 2:
                w = int(parts[0])
                f = Fraction(parts[1])
                return (Fraction(w, 1) + f) if w >= 0 else (Fraction(w, 1) - f)
        
        # 處理假分數或整數 e.g. "3/2" 或 "5"
        return Fraction(text)
    except Exception:
        return None

def check_correct(user: str, correct: str) -> int | None:
    user = user.strip()
    correct = correct.strip()

    # 特殊情況：處理多數值答案 (如 GCD LCM, 通分, 約分)
    # 這類答案都以空格分隔，且答案只包含數字
    user_clean = re.sub(r'[^0-9\s]', '', user)
    correct_clean = re.sub(r'[^0-9\s]', '', correct)
    
    if correct_clean.count(' ') > 0:
        # 直接比對經過清理的字串 (忽略多餘空格和大小寫)
        if ' '.join(user_clean.split()) == ' '.join(correct_clean.split()):
            return 1
        return 0
        
    # 一般分數或整數運算
    u = parse_answer(user)
    c = parse_answer(correct)

    if u is None or c is None:
        # 如果任一邊無法解析為數字 (如用戶輸入非數字)
        return None
        
    return 1 if u == c else 0


# =========================
# 自訂題目自動解題邏輯 (保持 V8 穩定性)
# =========================
def simple_solver(question_text):
    q = question_text.strip()
    
    if "=" in q:
        if not HAS_SYMPY:
            return None, "未安裝 SymPy (建議執行 pip install sympy)，無法自動解方程式"
        try:
            lhs_str, rhs_str = q.split("=")
            x = sp.Symbol('x')
            lhs = sp.sympify(lhs_str)
            rhs = sp.sympify(rhs_str)
            sol = sp.solve(sp.Eq(lhs, rhs), x)
            if sol:
                # 嘗試將結果轉換為最簡分數
                ans_str = str(Fraction(sol[0]).limit_denominator())
            
                # 如果是整數，只顯示整數
                if '/' in ans_str and ans_str.endswith('/1'):
                    ans_str = ans_str[:-2]
                    
                return ans_str, f"系統自動解題 (SymPy): x = {ans_str}"
            else:
                return None, "無解或無限多解"
        except Exception as e:
            return None, f"方程式解析失敗: {e}"

    try:
        clean_q = q.replace("×", "*").replace("÷", "/").replace(",", "")
        
        if HAS_SYMPY:
            # 確保 SymPy 計算結果被轉換為 Fraction 以便統一處理
            expr = sp.sympify(clean_q)
            f_ans = Fraction(expr).limit_denominator()
            ans_str = f"{f_ans.numerator}/{f_ans.denominator}"
            
            # 如果是整數，只顯示整數
            if f_ans.denominator == 1:
                ans_str = str(f_ans.numerator)

            return ans_str, f"系統自動計算 (SymPy): {ans_str}"
        else:
            ans = eval(clean_q)
            f_ans = Fraction(ans).limit_denominator()
            ans_str = f"{f_ans.numerator}/{f_ans.denominator}"
            
            # 如果是整數，只顯示整數
            if f_ans.denominator == 1:
                ans_str = str(f_ans.numerator)

            return ans_str, f"系統自動計算 (Fraction): {ans_str}"
            
    except Exception as e:
        return None, f"無法計算: {e}"


# =========================
# 統計與分析報告
# =========================
def show_analysis_report(conn: sqlite3.Connection):
    cur = conn.cursor()

    where = "WHERE is_correct IS NOT NULL"
    params: tuple = ()
    if CURRENT_IDENTITY is not None and RECORDS_HAS_IDENTITY_COLUMNS:
        where += " AND student_id = ?"
        params = (CURRENT_IDENTITY.student_id,)
    
    # 1. 執行分類統計查詢
    query = """
    SELECT
        topic,
        COUNT(*) AS total,
        SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) AS correct,
        SUM(CASE WHEN is_correct = 0 THEN 1 ELSE 0 END) AS incorrect
    FROM records
    """ + where + """
    GROUP BY topic
    ORDER BY total DESC; 
    """
    topic_data = cur.execute(query, params).fetchall()

    # 2. 顯示總體統計 (暖色強化)
    total_q = cur.execute(f"SELECT COUNT(*) FROM records {where}", params).fetchone()[0]
    total_c = cur.execute(f"SELECT COUNT(*) FROM records {where} AND is_correct = 1", params).fetchone()[0]
    
    print("\n" + f"{Colors.GOLD}═" * 65)
    print(f"| {Colors.YELLOW}{'📊 歷史總體統計報告'.center(61)}{Colors.END} |")
    print(f"{Colors.GOLD}═" * 65 + f"{Colors.END}")
    if total_q == 0:
        print("| 尚無有效作答紀錄。".ljust(63) + "|")
        print(f"{Colors.GOLD}═" * 65 + f"{Colors.END}")
        
    else:
        accuracy = (total_c / total_q) * 100
        print(f"| 總作答題數: {str(total_q).ljust(6)} | 總答對題數: {str(total_c).ljust(6)} | 歷史總正確率: {accuracy:.2f}% | 繼續努力！ |")
        print(f"{Colors.GOLD}═" * 65 + f"{Colors.END}")
    
        # 3. 顯示按主題分類的詳細報告 (暖色強化)
        print(f"\n| {Colors.YELLOW}{'📚 按主題分類報告 (依作答數排序)'.center(61)}{Colors.END} |")
        print("╠" + f"{Colors.GOLD}═" * 65 + "╣")
        print(f"| {'主題'.ljust(15)} | {'總數'.ljust(4)} | {'答對'.ljust(4)} | {'答錯'.ljust(4)} | {'正確率'.ljust(8)} | {'難點分析與建議'.ljust(18)} |")
        print("╠" + f"{Colors.GOLD}═" * 65 + "╣")

        for topic, total, correct, incorrect in topic_data:
            acc = (correct / total) * 100
            analysis = ""
            if acc < 70 and total >= 5: 
                analysis = f"{Colors.RED}🚨 重點加強題型{Colors.END}"
            elif acc >= 95 and total >= 5: 
                analysis = f"{Colors.GREEN}✅ 已穩固掌握{Colors.END}"
            elif total < 5:
                analysis = "資料不足，多練習"
                
            print(f"| {topic.ljust(15)} | {str(total).ljust(4)} | {str(correct).ljust(4)} | {str(incorrect).ljust(4)} | {acc:.2f}% | {analysis.ljust(29).strip()}{Colors.END} |")

        print(f"{Colors.GOLD}═" * 65 + f"{Colors.END}\n")

        # 4. 顯示所有歷史錯題 (暖色強化)
        # Include mistake tags if the column exists.
        has_coach = RECORDS_HAS_COACH_COLUMNS
        if not has_coach:
            try:
                _ensure_records_coach_columns(conn)
                has_coach = RECORDS_HAS_COACH_COLUMNS
            except Exception:
                has_coach = False

        if has_coach:
            all_wrong = cur.execute(
                f"SELECT ts, topic, question, correct_answer, user_answer, mistake_tags FROM records {where} AND is_correct=0 ORDER BY ts DESC",
                params,
            ).fetchall()
        else:
            all_wrong = cur.execute(
                f"SELECT ts, topic, question, correct_answer, user_answer FROM records {where} AND is_correct=0 ORDER BY ts DESC",
                params,
            ).fetchall()
        
        print(f"\n{Colors.RED}=== 📚 歷史累計錯題詳情 (全部紀錄) ==={Colors.END}")
        if not all_wrong:
            print(f"{Colors.GREEN}沒有錯誤紀錄。太棒了！{Colors.END}")
            
        else:
            for row in all_wrong:
                if has_coach:
                    ts, topic, question, correct_answer, user_answer, mistake_tags = row
                else:
                    ts, topic, question, correct_answer, user_answer = row
                    mistake_tags = ""

                ts_simple = ts.split('T')[0]
                tag_text = f" | 錯因: {mistake_tags}" if mistake_tags else ""
                print(f"[{ts_simple}][{topic}] 題目: {question}{tag_text}")
                print(f"  -> {Colors.GREEN}正解: {correct_answer}{Colors.END} | {Colors.RED}你答: {user_answer}{Colors.END}")
        print(f"{Colors.RED}=" * 30 + f"{Colors.END}\n")


def run_coaching_flow(conn: sqlite3.Connection, qobj: dict, initial_answer: str) -> tuple[str, int | None, str, str, bool]:
    """Coaching loop after a wrong answer.

    Returns: (final_user_answer, final_is_correct, mistake_tags_str, coach_note, reveal_solution)
    """
    topic = qobj.get("topic", "")
    question = qobj.get("question", "")
    correct = qobj.get("answer", "")

    tags, short_fix, actionable = diagnose_mistake(topic, question, initial_answer, correct)
    hint1, hint2, hint3 = build_progressive_hints(qobj)

    print(f"\n{Colors.YELLOW}[定位卡點]{Colors.END} {INCORRECT_CUSTOM_FEEDBACK}")
    print(f"{Colors.GOLD}你可能卡在（可多選）：{Colors.END}")
    for i, tag in enumerate(tags, start=1):
        print(f"  {i}. {tag}")

    picked = input("你覺得像哪幾個？(例: 1 3，直接 Enter 先用系統建議): ").strip()
    chosen_tags = tags
    if picked:
        idxs = []
        for tok in picked.split():
            if tok.isdigit():
                idxs.append(int(tok))
        chosen_tags = [tags[i - 1] for i in idxs if 1 <= i <= len(tags)] or tags

    print(f"\n{Colors.YELLOW}[最短補救路徑]{Colors.END} {short_fix}")
    print(f"{Colors.YELLOW}[可操作提示]{Colors.END} {actionable}")

    hint_level = 0
    retries = 0
    reveal_solution = False
    user = initial_answer
    is_correct: int | None = 0

    while True:
        print(f"\n{Colors.GOLD}--- 你想怎麼繼續？---{Colors.END}")
        print("  1) Hint 1（只告訴下一步）")
        print("  2) Hint 2（給關鍵轉換/局部算式）")
        print("  3) Hint 3（給完整下一步，但留空格讓你補）")
        print("  4) 逐步提示（系統一步一步帶你算）")
        print("  5) 再試一次（重新作答）")
        print("  6) 直接看完整詳解")
        print("  0) 先跳過這題")
        choice = input("選擇: ").strip()

        if choice == '1':
            hint_level = max(hint_level, 1)
            print(f"\n{Colors.YELLOW}[Hint 1]{Colors.END} {hint1}")
        elif choice == '2':
            hint_level = max(hint_level, 2)
            print(f"\n{Colors.YELLOW}[Hint 2]{Colors.END} {hint2}")
        elif choice == '3':
            hint_level = max(hint_level, 3)
            print(f"\n{Colors.YELLOW}[Hint 3]{Colors.END} {hint3}")
            _ = input("把 ____ 補上你的答案（輸入即可，不會扣分）: ")
        elif choice == '4':
            run_step_by_step_hints(qobj)
        elif choice == '5':
            retries += 1
            user = input("再試一次： ").strip()
            is_correct = check_equivalent_answer(user, correct)
            if is_correct == 1:
                print(f"{Colors.GREEN}✅ 對上了！這代表你只是剛剛卡在一個小細節。{Colors.END}")
                break
            if is_correct is None:
                print(f"{Colors.RED}格式無法判斷。你可以用整數/分數（例如 3 或 5/6）或空格分隔多個數字。{Colors.END}")
            else:
                print(f"{Colors.YELLOW}還差一點點，我們再用提示把它拉回來。{Colors.END}")

            if retries >= 2:
                print(f"{Colors.YELLOW}你已經很努力了。想不想直接看完整詳解，再挑戰類似題？{Colors.END}")
        elif choice == '6':
            reveal_solution = True
            break
        elif choice == '0':
            # Skip without forcing full solution; still logs tags for later review.
            reveal_solution = False
            break
        else:
            print(f"{Colors.RED}無效選擇{Colors.END}")

    mistake_tags_str = ",".join(chosen_tags)
    coach_note = f"initial={initial_answer} | chosen_tags={mistake_tags_str} | hint_level={hint_level} | retries={retries}"
    return user, is_correct, mistake_tags_str, coach_note, reveal_solution


def offer_alternative_solutions(qobj: dict) -> None:
    """Offer 2–3 alternative ways (algebra/intuition/check) after the main solution."""
    topic = qobj.get("topic", "")
    question = qobj.get("question", "")
    answer = qobj.get("answer", "")

    options: list[tuple[str, str]] = []

    if "四則運算" in topic:
        options = [
            ("直覺法", "先把括號當成一個『小盒子』，盒子算完再處理外面，避免同時看太多符號。"),
            ("檢查法", "把每一步算完都『回代到原式』快速檢查：括號→乘除→加減，確保中間數沒有抄錯。"),
        ]
    elif "分數" in topic or "帶分數" in topic:
        options = [
            ("代數法", "把目標拆成：通分 → 分子運算 → 約分。每一步只做一件事，錯也容易定位。"),
            ("檢查法", "用『交叉相乘』或轉小數（只用來檢查）確認結果是否合理，再回到分數最簡。"),
        ]
    elif "GCD/LCM" in topic:
        options = [
            ("公式法", "LCM(a,b)=|a*b|/GCD(a,b)。先求 GCD，再套公式就很穩。"),
            ("直覺法", "列倍數/因數快速找：小數字時先用倍數列舉，能更快抓到 LCM。"),
        ]
    elif "小數" in topic:
        options = [
            ("位數法", "把小數點後位數寫成『格子』：第 1 位、第 2 位（要保留）、第 3 位（決定進位）。"),
            ("檢查法", "用估算檢查：先取整數或一位小數估一下範圍，避免四捨五入跑太遠。"),
        ]
    elif "方程" in topic:
        options = [
            ("等量天平", "把等號想成天平：你對左邊做什麼，就必須對右邊也做同樣的事。"),
            ("代回檢查", f"把你的答案 x={answer} 代回原式（只算一次）看左右是否相等，能秒抓符號錯。"),
        ]
    else:
        options = [
            ("檢查法", "用『反向驗算』：把答案帶回題目或用另一種表示法檢查一次。"),
            ("切小步", "把一步拆成兩小步：先處理符號，再處理數字。"),
        ]

    if not options:
        return

    pick = input(f"{Colors.YELLOW}想看 1–2 個不同思路嗎？(y/n): {Colors.END}").strip().lower()
    if pick != 'y':
        return

    print(f"\n{Colors.YELLOW}[解法探索]{Colors.END} 同題不同路徑（選一個看就好）")
    for i, (name, _) in enumerate(options, start=1):
        print(f"  {i}. {name}")
    sel = input("選擇代號（直接 Enter 看全部）: ").strip()
    if sel.isdigit():
        i = int(sel)
        if 1 <= i <= len(options):
            name, text = options[i - 1]
            print(f"\n{Colors.YELLOW}[{name}]{Colors.END} {text}")
            return
    for name, text in options:
        print(f"\n{Colors.YELLOW}[{name}]{Colors.END} {text}")


def _print_question_card(qobj: dict, header: str | None = None) -> None:
    if header:
        print(f"\n{Colors.GOLD}{header}{Colors.END}")
    print(f"\n{Colors.GOLD}--------------------------------{Colors.END}")
    print(f"{Colors.YELLOW}🕹️ 小任務：把這題解開！{Colors.END}")
    print(f"【{qobj['topic']}】 題目： {Colors.YELLOW}{qobj['question']}{Colors.END}")
    print(f"{Colors.GOLD}--------------------------------{Colors.END}")


def run_single_question_freeplay(
    conn: sqlite3.Connection,
    qobj: dict,
    header: str | None = None,
    show_card: bool = True,
) -> tuple[int | None, str, str]:
    """Run one question in freeplay mode.

    Returns: (is_correct, mistake_tags, final_user_answer)
    """
    if show_card:
        _print_question_card(qobj, header=header)

    attempts: list[str] = []
    mistake_tags = ""
    coach_note = ""
    reveal_solution = True

    hint1, hint2, hint3 = build_progressive_hints(qobj)

    while True:
        user = input("作答（Enter 提交；h 一次提示／c 逐步提示／u 回溯／s 跳過）: ").strip()

        if user.lower() == 's':
            print("已跳過（不計分）。")
            return None, "", ""

        if user.lower() == 'h':
            # 一次提示：只給一個不含答案的「下一步該做什麼」
            print(f"\n{Colors.YELLOW}[一次提示]{Colors.END} {hint1}")
            continue

        if user.lower() == 'c':
            run_step_by_step_hints(qobj)
            continue

        if user.lower() == 'u':
            if not attempts:
                print(f"{Colors.YELLOW}目前還沒有可回溯的作答。{Colors.END}")
                continue
            print(f"{Colors.YELLOW}[回溯]{Colors.END} 你之前輸入過：")
            for i, a in enumerate(attempts[-5:], start=max(1, len(attempts) - 4)):
                print(f"  {i}. {a}")
            continue

        if not user:
            continue

        attempts.append(user)
        is_correct = check_equivalent_answer(user, qobj["answer"])

        if is_correct == 1:
            reward_message = random.choice(CORRECT_MESSAGES)
            print(f"{Colors.GREEN}{reward_message}{Colors.END}")
            print(f"\n{Colors.YELLOW}[詳解]{Colors.END}\n{qobj['explanation']}\n")
            try:
                offer_alternative_solutions(qobj)
            except Exception:
                pass
            return 1, "", user

        if is_correct == 0:
            final_user, final_is_correct, mistake_tags, coach_note, reveal_solution = run_coaching_flow(conn, qobj, user)
            user = final_user
            is_correct = final_is_correct

            if is_correct == 1:
                reward_message = random.choice(CORRECT_MESSAGES)
                print(f"{Colors.GREEN}{reward_message}{Colors.END}")
            elif is_correct == 0:
                print(f"{Colors.YELLOW}沒關係，這題我們把它當成『定位卡點』。標準答案是：{qobj['answer']}{Colors.END}")
            else:
                print(f"{Colors.RED}! 格式無法判斷或答案無效。{Colors.END}標準答案是：{qobj['answer']}")

            if is_correct == 1 or reveal_solution:
                print(f"\n{Colors.YELLOW}[詳解]{Colors.END}\n{qobj['explanation']}\n")
                try:
                    offer_alternative_solutions(qobj)
                except Exception:
                    pass
            else:
                print(f"\n{Colors.YELLOW}[提示]{Colors.END} 你可以再試一次或用逐步提示；需要時再打開詳解。")

            return is_correct, mistake_tags, user

        print(f"{Colors.RED}格式無法判斷。{Colors.END}你可以用整數/分數（例如 3 或 5/6）或空格分隔多個數字。")


def practice_challenge(conn: sqlite3.Connection, topic_key: str | None = None, n: int = 3) -> None:
    """Daily mission campaign: n consecutive questions with end summary + one easter egg."""
    start_ts = datetime.now()
    results: list[dict] = []

    print(f"\n{Colors.GOLD}==========================={Colors.END}")
    print(f" {Colors.GOLD}🧩 今日任務：闖關模式（{n} 題）{Colors.END}")
    print(f"{Colors.GOLD}==========================={Colors.END}")
    print(f"{Colors.YELLOW}規則：每題你可以先用提示/逐步提示，再提交答案；錯了也不是失敗，是定位卡點。{Colors.END}")

    for i in range(1, n + 1):
        if topic_key in ("10", "11"):
            gen_func = _select_fraction_progress_generator(str(topic_key))
        elif topic_key == "15":
            gen_func = _select_arith_app_progress_generator()
        else:
            gen_func = get_random_generator(topic_key)
        qobj = generate_unique_question(gen_func)

        header = f"=== 關卡 {i}/{n} ==="

        # Run with hint/rollback commands.
        # We reuse the same coaching flow, but logging/counters happen here.
        is_correct, mistake_tags, final_user = run_single_question_freeplay(conn, qobj, header=header, show_card=True)

        # Persist + counters (skip doesn't count)
        if is_correct in (0, 1):
            _update_streak(is_correct, qobj.get('topic', ''))
            update_counters(is_correct)
            display_reward()

        log_record(
            conn,
            "auto",
            qobj['topic'],
            qobj['difficulty'],
            qobj['question'],
            qobj['answer'],
            final_user,
            is_correct,
            qobj['explanation'],
            mistake_tags=mistake_tags,
            coach_note=(f"challenge={i}/{n}"),
        )

        if CURRENT_IDENTITY is not None:
            try:
                record_attempt_to_app_db(
                    identity=CURRENT_IDENTITY,
                    qobj=qobj,
                    user_answer=final_user,
                    is_correct=is_correct,
                    mode="auto",
                    app_db_path=APP_DB_PATH,
                )
            except Exception as e:
                print(f"{Colors.RED}寫入 app.db 失敗: {e}{Colors.END}")

        results.append(
            {
                "topic": qobj.get("topic", ""),
                "question": qobj.get("question", ""),
                "answer": qobj.get("answer", ""),
                "is_correct": is_correct,
                "mistake_tags": mistake_tags,
            }
        )

    # End summary
    elapsed = (datetime.now() - start_ts).total_seconds()
    correct_cnt = sum(1 for r in results if r["is_correct"] == 1)
    wrong_cnt = sum(1 for r in results if r["is_correct"] == 0)
    skip_cnt = sum(1 for r in results if r["is_correct"] is None)

    print(f"\n{Colors.GOLD}==========================={Colors.END}")
    print(f" {Colors.GOLD}🏁 闖關結算{Colors.END}")
    print(f"{Colors.GOLD}==========================={Colors.END}")
    print(f"用時：約 {int(elapsed)} 秒 | 答對 {correct_cnt} 題 | 答錯 {wrong_cnt} 題 | 跳過 {skip_cnt} 題")

    for idx, r in enumerate(results, start=1):
        status = "✅" if r["is_correct"] == 1 else ("❌" if r["is_correct"] == 0 else "⏭")
        tag = f" | 錯因: {r['mistake_tags']}" if r.get("mistake_tags") else ""
        print(f"{idx}. {status} [{r['topic']}] {r['question']}{tag}")

    # 今日任務狀態 + 彩蛋（只在闖關結束時提示一次）
    print_daily_mission_status(conn)
    try:
        maybe_offer_easter_egg(conn)
    except Exception:
        pass


# =========================
# 主流程
# =========================
def practice_auto(conn: sqlite3.Connection, topic_key=None):
    """自動出題模式"""
    if topic_key in ("10", "11"):
        gen_func = _select_fraction_progress_generator(str(topic_key))
    elif topic_key == "15":
        gen_func = _select_arith_app_progress_generator()
    else:
        gen_func = get_random_generator(topic_key)
    qobj = generate_unique_question(gen_func)

    # 今日任務（可預期的進步）
    print_daily_mission_status(conn)
    
    # 暖色邊框
    print(f"\n{Colors.GOLD}--------------------------------{Colors.END}")
    print(f"{Colors.YELLOW}🕹️ 小任務：把這題解開！{Colors.END}")
    # 題目使用黃色突出
    print(f"【{qobj['topic']}】 題目： {Colors.YELLOW}{qobj['question']}{Colors.END}")
    print(f"{Colors.GOLD}--------------------------------{Colors.END}")
    
    user = input("請作答 (輸入 's' 跳過): ").strip()
    if user.lower() == 's':
        print("已跳過。")
        return

    is_correct = check_equivalent_answer(user, qobj["answer"])
    mistake_tags = ""
    coach_note = ""
    reveal_solution = True
    
    # 顯示結果 (綠色/紅色) 並給予回饋 (V11.2 客製化強化)
    if is_correct == 1:
        # 答對：給予隨機獎勵話語
        reward_message = random.choice(CORRECT_MESSAGES)
        print(f"{Colors.GREEN}{reward_message}{Colors.END}")

    elif is_correct == 0:
        # 答錯：先定位卡點 + 分層提示 + 允許再試
        final_user, final_is_correct, mistake_tags, coach_note, reveal_solution = run_coaching_flow(conn, qobj, user)
        user = final_user
        is_correct = final_is_correct
        if is_correct == 1:
            reward_message = random.choice(CORRECT_MESSAGES)
            print(f"{Colors.GREEN}{reward_message}{Colors.END}")
        elif is_correct == 0:
            # 仍未答對：不貼標籤，改為提供答案 + 下一題再練
            print(f"{Colors.YELLOW}沒關係，這題我們把它當成『定位卡點』。標準答案是：{qobj['answer']}{Colors.END}")
        
    else:
        # 無效輸入：不計入分數，但仍顯示答案
        print(f"{Colors.RED}! 格式無法判斷或答案無效。{Colors.END}標準答案是：{qobj['answer']}")
        
    # 逐步揭露：答錯時先提示，再由使用者決定是否看完整詳解
    if is_correct == 1 or reveal_solution:
        print(f"\n{Colors.YELLOW}[詳解]{Colors.END}\n{qobj['explanation']}\n")
        try:
            offer_alternative_solutions(qobj)
        except Exception:
            pass
    else:
        print(f"\n{Colors.YELLOW}[提示]{Colors.END} 你可以再試一次或用逐步提示；需要時再打開詳解。")
    
    # 遊戲化更新
    if is_correct in (1, 0): # 答對或答錯才計數，格式無效不計入
        _update_streak(is_correct, qobj.get('topic', ''))
        update_counters(is_correct)
        display_reward()
    
    log_record(
        conn,
        "auto",
        qobj['topic'],
        qobj['difficulty'],
        qobj['question'],
        qobj['answer'],
        user,
        is_correct,
        qobj['explanation'],
        mistake_tags=mistake_tags,
        coach_note=coach_note,
    )

    if CURRENT_IDENTITY is not None:
        try:
            record_attempt_to_app_db(
                identity=CURRENT_IDENTITY,
                qobj=qobj,
                user_answer=user,
                is_correct=is_correct,
                mode="auto",
                app_db_path=APP_DB_PATH,
            )
        except Exception as e:
            print(f"{Colors.RED}寫入 app.db 失敗: {e}{Colors.END}")

    # 小驚喜：完成每日任務後可選彩蛋
    try:
        maybe_offer_easter_egg(conn)
    except Exception:
        pass


def custom_question_mode(conn: sqlite3.Connection):
    """自訂題目 + 自動解題"""
    print(f"\n{Colors.YELLOW}=== 自訂題目與解題 ==={Colors.END}")
    print("說明：您可以輸入算式（如 1/2 + 1/3）或方程式（如 2*x + 3 = 9）。")
    print("注意：乘法請用 *，除法用 /。分數請用 a/b 格式。")
    
    q_text = input("請輸入題目: ").strip()
    if not q_text:
        return

    print("系統正在計算答案...")
    auto_ans, auto_expl = simple_solver(q_text)
    
    final_ans = ""
    explanation = ""
    
    if auto_ans:
        print(f"系統算出答案為: {Colors.YELLOW}{auto_ans}{Colors.END}")
        use_auto = input("是否使用此答案作為標準答案? (y/n): ").strip().lower()
        if use_auto == 'y':
            final_ans = auto_ans
            explanation = auto_expl
        else:
            final_ans = input("請手動輸入正確答案: ").strip()
            explanation = "使用者手動輸入答案"
    else:
        print(f"{Colors.RED}系統無法自動解題 ({auto_expl}){Colors.END}")
        final_ans = input("請手動輸入正確答案: ").strip()
        explanation = "系統無法解題，手動輸入"

    user_ans = input("您的作答 (直接按 Enter 可略過): ").strip()
    
    is_correct = None
    if user_ans and final_ans:
        is_correct = check_equivalent_answer(user_ans, final_ans)
        # 自訂題目模式維持簡潔回饋（但仍納入連勝里程碑鼓勵）
        print(f"{Colors.GREEN}V 答對{Colors.END}" if is_correct == 1 else f"{Colors.RED}X 答錯{Colors.END}")

        # 連勝里程碑：只要連續答對就會觸發（答錯則重置）
        if is_correct in (0, 1):
            _update_streak(is_correct, "custom")

    # Minimal coaching metadata for custom mode.
    mistake_tags = ""
    coach_note = ""
    if is_correct == 0:
        tags, short_fix, actionable = diagnose_mistake("custom", q_text, user_ans, final_ans)
        mistake_tags = ",".join(tags)
        coach_note = f"custom | {short_fix} | {actionable}"

    log_record(
        conn,
        "custom",
        "custom",
        "unknown",
        q_text,
        final_ans,
        user_ans,
        is_correct,
        explanation,
        mistake_tags=mistake_tags,
        coach_note=coach_note,
    )
    if CURRENT_IDENTITY is not None:
        qobj = {
            "topic": "custom",
            "difficulty": "unknown",
            "question": q_text,
            "answer": final_ans,
            "explanation": explanation,
        }
        try:
            record_attempt_to_app_db(
                identity=CURRENT_IDENTITY,
                qobj=qobj,
                user_answer=user_ans,
                is_correct=is_correct,
                mode="custom",
                app_db_path=APP_DB_PATH,
            )
        except Exception as e:
            print(f"{Colors.RED}寫入 app.db 失敗: {e}{Colors.END}")
    print("已記錄。\n")


def main():
    print(f"{Colors.GOLD}--- 程式啟動 ---{Colors.END}")
    global CURRENT_IDENTITY
    try:
        CURRENT_IDENTITY = select_or_create_identity(app_db_path=APP_DB_PATH, default_account_name="MathOK")
    except Exception as e:
        print(f"{Colors.RED}身分載入失敗（將只寫入 math_log.db）: {e}{Colors.END}")
        CURRENT_IDENTITY = None
    conn = init_db()
    
    # 初始化全局計數器
    try:
        cur = conn.cursor()
        if CURRENT_IDENTITY is not None and RECORDS_HAS_IDENTITY_COLUMNS:
            total_q = cur.execute(
                "SELECT COUNT(*) FROM records WHERE mode = 'auto' AND is_correct IS NOT NULL AND student_id=?",
                (CURRENT_IDENTITY.student_id,),
            ).fetchone()[0]
            correct_c = cur.execute(
                "SELECT COUNT(*) FROM records WHERE mode = 'auto' AND is_correct = 1 AND student_id=?",
                (CURRENT_IDENTITY.student_id,),
            ).fetchone()[0]
        else:
            total_q = cur.execute("SELECT COUNT(*) FROM records WHERE mode = 'auto' AND is_correct IS NOT NULL").fetchone()[0]
            correct_c = cur.execute("SELECT COUNT(*) FROM records WHERE mode = 'auto' AND is_correct = 1").fetchone()[0]
        global TOTAL_COUNT, CORRECT_COUNT
        TOTAL_COUNT = total_q
        CORRECT_COUNT = correct_c
        
        if TOTAL_COUNT > 0:
            print(f"載入歷史進度：總作答 {TOTAL_COUNT} 題，答對 {CORRECT_COUNT} 題 ({(CORRECT_COUNT/TOTAL_COUNT*100):.1f}%)")
        
    except Exception as e:
        print(f"{Colors.RED}無法載入歷史計數器: {e}{Colors.END}")
        pass
    
    while True:
        # 主選單標題使用金色/暖色突出
        print(f"\n{Colors.GOLD}==========================={Colors.END}")
        print(f" {Colors.GOLD}數學練習系統 V11.2 (深度教學版){Colors.END}")
        print(f"{Colors.GOLD}==========================={Colors.END}")
        print(f" {Colors.YELLOW}1. 今日任務闖關（隨機 3 題）{Colors.END}")
        print(f" {Colors.YELLOW}2. 今日任務闖關（指定題型 3 題）{Colors.END}")
        print(f" {Colors.YELLOW}3. 自訂題目 (含自動解題){Colors.END}")
        print(f" {Colors.YELLOW}4. 查看分析報告{Colors.END}") 
        print(f" {Colors.YELLOW}0. 離開{Colors.END}")
        
        c = input("請選擇: ").strip()
        
        if c == '1':
            mode = input("Enter 開始闖關(3題)；輸入 f 自由練(單題): ").strip().lower()
            if mode == 'f':
                practice_auto(conn, None)
            else:
                practice_challenge(conn, None, n=3)
        elif c == '2':
            print(f"\n{Colors.YELLOW}[選擇題型]{Colors.END}")
            # 確保使用 GENERATORS 字典的排序來顯示選單
            sorted_keys = sorted(GENERATORS.keys(), key=lambda x: int(x) if x.isdigit() else float('inf'))
            for k in sorted_keys:
                 v = GENERATORS[k]
                 print(f"  {k}. {v[0]}")

            k = input("請輸入代號: ").strip()
            if k in GENERATORS:
                mode = input("Enter 開始闖關(3題)；輸入 f 自由練(單題): ").strip().lower()
                if mode == 'f':
                    practice_auto(conn, k)
                else:
                    practice_challenge(conn, k, n=3)
            else:
                print(f"{Colors.RED}無效代號{Colors.END}")
        elif c == '3':
            custom_question_mode(conn)
        elif c == '4':
            show_analysis_report(conn) 
        elif c == '0':
            print(f"{Colors.GOLD}Bye! 期待下次再見！{Colors.END}")
            break
        else:
            print(f"{Colors.RED}無效輸入{Colors.END}")

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except: pass
    main()