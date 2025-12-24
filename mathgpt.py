#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命令列版：數學練習系統（V11.3 深度教學版 - 強化分析報告 + 學習建議）
保留原功能：
- 出題/判題/紀錄 DB
- 顏色顯示、答對獎勵、答錯客製化回饋、詳解輸出
強化內容（不改 DB schema、不改原出題/判題邏輯）：
1) 報告納入「無效輸入」統計（is_correct IS NULL）
2) 近 7 天趨勢（▲/▼/→/·）
3) 優先級 P1/P2/P3 與 Action Plan（核心觀念/練習法/自我檢核/退出條件）
4) 弱項最近錯題 Spotlight（快速複盤）
5) 錯題清單限制為最近 50 筆（避免爆版）
"""

import sqlite3
import random
from fractions import Fraction
from datetime import datetime, timedelta
import os
import sys
import re
import math

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

# 嘗試載入 sympy
try:
    import sympy as sp
    HAS_SYMPY = True
except ImportError:
    HAS_SYMPY = False

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

# 答錯時的客製化回饋 (V11.2 客製化回饋)
INCORRECT_CUSTOM_FEEDBACK = (
    f"{Colors.RED}❌ 答案不對。標準答案是：{{answer}}{Colors.END}\n"
    f"{Colors.YELLOW}請看看詳細解答。如看不懂，先問一下親愛的媽，{Colors.END}\n"
    f"{Colors.YELLOW}帥阿爸要周三或六日才可以問喔！{Colors.END}"
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


# =========================
# DB 初始化與操作
# =========================
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
            explanation TEXT
        )
        """
    )

    # 可選：加速報告查詢（不影響功能）
    conn.execute("CREATE INDEX IF NOT EXISTS idx_records_topic_ts ON records(topic, ts)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_records_correct ON records(is_correct)")

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
):
    """
    紀錄作答結果到資料庫。
    """
    ts = datetime.now().isoformat(timespec="seconds")
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
        result_mul_div = b * c
        op_text_md = "×"
        sub_expr_md = f"{b} × {c}"
    else:  # /
        result_div = random.randint(2, 5)
        c = random.randint(2, 10)
        b = result_div * c
        result_mul_div = result_div
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
        if a1 < a2:
            a1, a2 = a2, a1
        paren_result = a1 - a2
        op_text_paren = "-"

    paren_expr = f"({a1} {op_text_paren} {a2})"

    # --- 步驟 3: 組合所有部分 ---
    e = random.randint(1, 10)

    op1 = random.choice(["+", "-"])
    op2 = random.choice(["+", "-"])

    question = f"{paren_expr} {op1} {sub_expr_md} {op2} {e} = ?"

    ans = eval(f"({a1} {op_text_paren} {a2}) {op1} ({b} {op_mul_div} {c}) {op2} {e}")

    explanation_steps = [
        f"步驟 1: **先算括號**",
        f"   -> {a1} {op_text_paren} {a2} = {paren_result}",
        f"   -> 算式變為: {paren_result} {op1} {sub_expr_md} {op2} {e}",
        f"步驟 2: **再算乘除**",
        f"   -> {sub_expr_md} = {result_mul_div}",
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


def gen_fraction_commondenom():
    """分數通分練習 (新增題型)"""
    b1 = random.choice([4, 6, 8, 10, 12])
    b2 = random.choice([4, 6, 8, 10, 12])
    a1 = random.randint(1, b1 - 1)
    a2 = random.randint(1, b2 - 1)

    while b1 == b2 or a1/b1 == a2/b2:
        b2 = random.choice([4, 6, 8, 10, 12])
        a2 = random.randint(1, b2 - 1)

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
    else:  # ÷
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
        else:  # surface_area
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
        else:  # surface_area
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


# 題型產生器映射表
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
        if " " in text and "/" in text:
            parts = text.split()
            if len(parts) == 2:
                w = int(parts[0])
                f = Fraction(parts[1])
                return (Fraction(w, 1) + f) if w >= 0 else (Fraction(w, 1) - f)

        return Fraction(text)
    except Exception:
        return None

def check_correct(user: str, correct: str) -> int | None:
    user = user.strip()
    correct = correct.strip()

    user_clean = re.sub(r'[^0-9\s]', '', user)
    correct_clean = re.sub(r'[^0-9\s]', '', correct)

    if correct_clean.count(' ') > 0:
        if ' '.join(user_clean.split()) == ' '.join(correct_clean.split()):
            return 1
        return 0

    u = parse_answer(user)
    c = parse_answer(correct)

    if u is None or c is None:
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
                ans_str = str(Fraction(sol[0]).limit_denominator())
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
            expr = sp.sympify(clean_q)
            f_ans = Fraction(expr).limit_denominator()
            ans_str = f"{f_ans.numerator}/{f_ans.denominator}"
            if f_ans.denominator == 1:
                ans_str = str(f_ans.numerator)
            return ans_str, f"系統自動計算 (SymPy): {ans_str}"
        else:
            ans = eval(clean_q)
            f_ans = Fraction(ans).limit_denominator()
            ans_str = f"{f_ans.numerator}/{f_ans.denominator}"
            if f_ans.denominator == 1:
                ans_str = str(f_ans.numerator)
            return ans_str, f"系統自動計算 (Fraction): {ans_str}"

    except Exception as e:
        return None, f"無法計算: {e}"


# =========================
# 報告強化：學習建議與分級規則
# =========================

TOPIC_PLAYBOOK = {
    "四則運算 (順序)": {
        "core": [
            "口訣：括號 → 乘除 → 加減；同級運算由左到右。",
            "每一步先「改寫算式」，避免跳步造成順序錯誤。"
        ],
        "drill": [
            "每題固定三行：①算括號 ②算乘除 ③算加減（左到右）。",
            "把每一步中間結果寫出來，做到可稽核。"
        ],
        "checklist": [
            "我有先算括號嗎？",
            "我有先做乘除再做加減嗎？",
            "加減是否由左到右？"
        ],
    },
    "分數通分": {
        "core": [
            "關鍵：找公分母＝LCM(分母1, 分母2)。",
            "分母放大幾倍，分子同步放大同倍數。"
        ],
        "drill": [
            "先練 LCM：用 gcd→lcm 公式快速算。",
            "每題固定寫：LCM、倍率m1/m2、新分子。"
        ],
        "checklist": [
            "我用的是最小公倍數嗎？",
            "倍率算對嗎（LCM/原分母）？",
            "分子有乘同一個倍率嗎？"
        ],
    },
    "分數約分": {
        "core": [
            "關鍵：GCD(分子, 分母)；分子分母同除以 GCD。",
            "最簡分數判定：GCD=1。"
        ],
        "drill": [
            "先練快速找 GCD（質因數或輾轉相除）。",
            "每題固定寫：GCD → 同除 → 最簡檢查(GCD=1)。"
        ],
        "checklist": [
            "我找的是最大公因數嗎？",
            "分子分母都同除同一個數嗎？",
            "最後 GCD 是否為 1？"
        ],
    },
    "分數加減": {
        "core": [
            "先通分（LCM）再做分子加/減，最後約分。",
            "減法若出現負數，先確認題意；本系統多數題目確保正結果。"
        ],
        "drill": [
            "固定四步：LCM → 通分 → 分子運算 → 約分。",
            "錯題回看只檢查「LCM/倍率/分子運算/約分」哪一步出錯。"
        ],
        "checklist": [
            "分母真的統一了嗎？",
            "分子運算是否跟著同分母？",
            "最後有約分嗎？"
        ],
    },
    "帶分數運算": {
        "core": [
            "先化假分數再做分數加減；最後再視需要化回帶分數。",
            "化假分數：整數×分母＋分子。"
        ],
        "drill": [
            "每題固定：化假分數→通分→運算→約分→（可選）化帶分數。",
            "專練「整數×分母＋分子」避免粗心。"
        ],
        "checklist": [
            "假分數轉換正確嗎？",
            "通分倍率算對嗎？",
            "最後約分/化帶分數是否正確？"
        ],
    },
    "GCD/LCM (二數)": {
        "core": [
            "GCD：最大公因數；LCM：最小公倍數。",
            "公式：LCM(a,b)=a*b/GCD(a,b)。"
        ],
        "drill": [
            "先穩定 GCD（輾轉相除），再套 LCM 公式。",
            "練習「先約分再乘」避免算錯或數字太大。"
        ],
        "checklist": [
            "GCD 算對了嗎？",
            "LCM 是否用 a*b/GCD？",
            "答案格式是否為：GCD LCM？"
        ],
    },
    "GCD/LCM (三數)": {
        "core": [
            "三數 GCD：GCD(a, GCD(b,c))。",
            "三數 LCM：先 LCM(a,b)，再 LCM(結果,c)。"
        ],
        "drill": [
            "固定流程兩段式：先算 ab，再帶入 c。",
            "每一步都寫出中間結果，避免跳步。"
        ],
        "checklist": [
            "有先算 LCM(a,b) 嗎？",
            "第二段 LCM(結果,c) 是否正確？",
            "答案格式是否為：GCD LCM？"
        ],
    },
    "小數四則運算": {
        "core": [
            "先算出未四捨五入的結果，再依題意四捨五入到小數點後兩位。",
            "加減對齊小數點；乘除注意位數與估算合理性。"
        ],
        "drill": [
            "每題固定兩段：①原始運算 ②四捨五入。",
            "加入估算：答案大小是否合理（避免小數點位置錯）。"
        ],
        "checklist": [
            "我有最後做四捨五入到兩位嗎？",
            "小數點位置是否合理？",
            "加減是否對齊小數點？"
        ],
    },
    "體積/表面積": {
        "core": [
            "正方體：體積 a³；表面積 6a²。",
            "長方體：體積 L×W×H；表面積 2(LW+LH+WH)。"
        ],
        "drill": [
            "先辨識形狀（正方體/長方體）再選公式。",
            "把已知量列成 L/W/H，代入公式後再計算。"
        ],
        "checklist": [
            "題目問的是體積還是表面積？",
            "形狀辨識正確嗎？",
            "代入的 L/W/H 有沒有寫錯？"
        ],
    },
    "一元一次方程": {
        "core": [
            "目標：把 x 單獨留在一邊。",
            "移項等量公理：兩邊同加減同一數；最後除以係數。"
        ],
        "drill": [
            "每題固定：①常數移項 ②除以係數。",
            "驗算：把 x 代回原式檢查是否相等。"
        ],
        "checklist": [
            "移項有改符號嗎？",
            "最後有除以係數嗎？",
            "有代回驗算嗎？"
        ],
    },
}

def _pct(n: int, d: int) -> float:
    return (n / d * 100.0) if d else 0.0

def _trend_symbol(overall_acc: float, recent_acc: float, recent_n: int, threshold: float = 5.0) -> str:
    if recent_n < 5:
        return "·"
    if recent_acc >= overall_acc + threshold:
        return "▲"
    if recent_acc <= overall_acc - threshold:
        return "▼"
    return "→"

def _mastery_label(acc: float, n: int) -> str:
    if n < 5:
        return "樣本不足"
    if acc >= 95:
        return "已穩固"
    if acc >= 85:
        return "熟練"
    if acc >= 70:
        return "待強化"
    return "高風險"

def _priority_bucket(acc: float, n: int) -> str:
    if n < 5:
        return "P3(補樣本)"
    if acc < 70:
        return "P1(立即加強)"
    if acc < 85:
        return "P2(強化熟練)"
    return "P3(維持複習)"

def _normalize_topic_for_playbook(topic: str) -> str:
    if topic.startswith("正方體") or topic.startswith("長方體"):
        return "體積/表面積"
    return topic

def _get_playbook(topic: str) -> dict:
    key = _normalize_topic_for_playbook(topic)
    return TOPIC_PLAYBOOK.get(key, {
        "core": ["建議：回到詳解，逐步對照「哪一步開始不一致」。"],
        "drill": ["固定流程：讀題→列式→分步計算→最後檢查。"],
        "checklist": ["是否看懂題意？", "是否寫出中間步驟？", "是否做最後檢查？"],
    })


# =========================
# 統計與分析報告（強化版）
# =========================
def show_analysis_report(conn: sqlite3.Connection):
    cur = conn.cursor()

    since = (datetime.now() - timedelta(days=7)).isoformat(timespec="seconds")

    overall = cur.execute(
        """
        SELECT
            SUM(CASE WHEN is_correct IN (0,1) THEN 1 ELSE 0 END) AS valid_total,
            SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) AS correct,
            SUM(CASE WHEN is_correct = 0 THEN 1 ELSE 0 END) AS wrong,
            SUM(CASE WHEN is_correct IS NULL THEN 1 ELSE 0 END) AS invalid
        FROM records;
        """
    ).fetchone()

    valid_total, correct_total, wrong_total, invalid_total = [int(x or 0) for x in overall]
    overall_acc = _pct(correct_total, valid_total)

    recent = cur.execute(
        """
        SELECT
            SUM(CASE WHEN ts >= ? AND is_correct IN (0,1) THEN 1 ELSE 0 END) AS valid_total,
            SUM(CASE WHEN ts >= ? AND is_correct = 1 THEN 1 ELSE 0 END) AS correct,
            SUM(CASE WHEN ts >= ? AND is_correct = 0 THEN 1 ELSE 0 END) AS wrong,
            SUM(CASE WHEN ts >= ? AND is_correct IS NULL THEN 1 ELSE 0 END) AS invalid
        FROM records;
        """,
        (since, since, since, since),
    ).fetchone()

    r_valid, r_correct, r_wrong, r_invalid = [int(x or 0) for x in recent]
    r_acc = _pct(r_correct, r_valid)

    print("\n" + f"{Colors.GOLD}═" * 85 + f"{Colors.END}")
    print(f"{Colors.YELLOW}📊 學習分析報告（強化版）{Colors.END}")
    print(f"{Colors.GOLD}═" * 85 + f"{Colors.END}")

    if valid_total == 0 and invalid_total == 0:
        print("尚無作答紀錄。")
        print(f"{Colors.GOLD}═" * 85 + f"{Colors.END}")
        return

    print(f"- 總有效作答（可判對錯）: {valid_total}  |  答對: {correct_total}  |  答錯: {wrong_total}  |  無效輸入: {invalid_total}")
    print(f"- 歷史正確率: {overall_acc:.2f}%")
    print(f"- 近 7 天（{since.split('T')[0]} ~ 今日）有效作答: {r_valid} | 正確率: {r_acc:.2f}% | 無效輸入: {r_invalid}")
    print(f"{Colors.GOLD}─" * 85 + f"{Colors.END}")

    topic_rows = cur.execute(
        """
        SELECT
            topic,
            SUM(CASE WHEN is_correct IN (0,1) THEN 1 ELSE 0 END) AS valid_total,
            SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) AS correct,
            SUM(CASE WHEN is_correct = 0 THEN 1 ELSE 0 END) AS wrong,
            SUM(CASE WHEN is_correct IS NULL THEN 1 ELSE 0 END) AS invalid,
            MAX(ts) AS last_ts
        FROM records
        GROUP BY topic;
        """
    ).fetchall()

    recent_rows = cur.execute(
        """
        SELECT
            topic,
            SUM(CASE WHEN ts >= ? AND is_correct IN (0,1) THEN 1 ELSE 0 END) AS valid_total,
            SUM(CASE WHEN ts >= ? AND is_correct = 1 THEN 1 ELSE 0 END) AS correct
        FROM records
        GROUP BY topic;
        """,
        (since, since),
    ).fetchall()
    recent_map = {t: (int(v or 0), int(c or 0)) for (t, v, c) in recent_rows}

    enriched = []
    for topic, n_valid, n_correct, n_wrong, n_invalid, last_ts in topic_rows:
        n_valid = int(n_valid or 0)
        n_correct = int(n_correct or 0)
        n_wrong = int(n_wrong or 0)
        n_invalid = int(n_invalid or 0)
        acc = _pct(n_correct, n_valid)

        r_n, r_c = recent_map.get(topic, (0, 0))
        r_acc_topic = _pct(r_c, r_n)

        trend = _trend_symbol(acc, r_acc_topic, r_n)

        if n_valid >= 5:
            score = (n_wrong / max(n_valid, 1)) * math.log10(n_valid + 1) * 100.0
        else:
            score = (n_wrong / max(n_valid, 1)) * 10.0

        invalid_rate = (n_invalid / (n_valid + n_invalid)) if (n_valid + n_invalid) else 0.0
        score = score * (1.0 + min(invalid_rate, 0.5))

        enriched.append({
            "topic": topic,
            "valid": n_valid,
            "correct": n_correct,
            "wrong": n_wrong,
            "invalid": n_invalid,
            "acc": acc,
            "r_valid": r_n,
            "r_acc": r_acc_topic,
            "trend": trend,
            "last_ts": last_ts or "",
            "mastery": _mastery_label(acc, n_valid),
            "priority": _priority_bucket(acc, n_valid),
            "score": score,
            "invalid_rate": invalid_rate,
        })

    enriched_by_volume = sorted(enriched, key=lambda x: (x["valid"], x["invalid"]), reverse=True)

    print(f"{Colors.YELLOW}📚 主題別分類報告（含：答對/答錯/無效輸入 + 近7天趨勢）{Colors.END}")
    print(f"{Colors.GOLD}{'主題':<18}{'有效':>6}{'答對':>6}{'答錯':>6}{'無效':>6}{'正確率':>9}{'7D正確':>10}{'趨勢':>4}{'等級':>10}{'優先級':>12}{Colors.END}")
    print(f"{Colors.GOLD}─" * 85 + f"{Colors.END}")

    for x in enriched_by_volume:
        topic = x["topic"]
        last_date = x["last_ts"].split("T")[0] if x["last_ts"] else "-"
        line = (
            f"{topic:<18}"
            f"{x['valid']:>6}"
            f"{x['correct']:>6}"
            f"{x['wrong']:>6}"
            f"{x['invalid']:>6}"
            f"{x['acc']:>8.1f}%"
            f"{x['r_acc']:>9.1f}%"
            f"{x['trend']:>4}"
            f"{x['mastery']:>10}"
            f"{x['priority']:>12}"
        )
        print(line)

        if x["invalid_rate"] >= 0.20 and (x["valid"] + x["invalid"]) >= 5:
            print(f"  {Colors.RED}※ 無效輸入偏高（{x['invalid_rate']*100:.1f}%）：建議先修正輸入格式/答案格式再追求速度。{Colors.END}")

        print(f"  最後作答日期: {last_date}")

    print(f"{Colors.GOLD}═" * 85 + f"{Colors.END}")

    enriched_by_priority = sorted(enriched, key=lambda x: x["score"], reverse=True)

    p1 = [x for x in enriched_by_priority if x["priority"].startswith("P1")]
    p2 = [x for x in enriched_by_priority if x["priority"].startswith("P2")]
    p3_need_sample = [x for x in enriched_by_priority if x["priority"].startswith("P3(補樣本)") and (x["valid"] + x["invalid"]) > 0]

    print(f"\n{Colors.YELLOW}🎯 Action Plan：學習建議與加強方向（系統自動生成）{Colors.END}")

    if not p1 and not p2 and not p3_need_sample:
        print("目前資料不足，先多做幾題再產生建議。")
        return

    def _print_topic_plan(item: dict):
        topic = item["topic"]
        pb = _get_playbook(topic)

        if item["priority"].startswith("P1"):
            daily = "每天 12~20 題（先慢後快），連續 3 天"
            exit_rule = "近 20 題正確率 ≥ 85%（且無效輸入 < 10%）後降為 P2"
        elif item["priority"].startswith("P2"):
            daily = "每天 8~12 題，連續 2~3 天"
            exit_rule = "近 20 題正確率 ≥ 90% 後降為 P3"
        else:
            daily = "先補樣本：連續做 10 題再評估"
            exit_rule = "累積有效樣本 ≥ 5 題後重新分級"

        print(f"\n{Colors.GOLD}【{topic}】{Colors.END}  ({item['priority']} / 等級:{item['mastery']} / 歷史:{item['acc']:.1f}% / 7D:{item['r_acc']:.1f}% {item['trend']})")
        print(f"- 建議練習節奏: {daily}")
        print(f"- Exit Criteria: {exit_rule}")

        print("- 核心觀念:")
        for s in pb["core"]:
            print(f"  • {s}")

        print("- 強化練習法:")
        for s in pb["drill"]:
            print(f"  • {s}")

        print("- 自我檢核清單:")
        for s in pb["checklist"]:
            print(f"  • {s}")

        wrongs = cur.execute(
            """
            SELECT ts, question, correct_answer, user_answer
            FROM records
            WHERE topic = ? AND is_correct = 0
            ORDER BY ts DESC
            LIMIT 2;
            """,
            (topic,),
        ).fetchall()

        if wrongs:
            print(f"- 最近錯題 Spotlight（建議逐步對照詳解，定位錯在哪一步）:")
            for ts, q, ca, ua in wrongs:
                d = ts.split("T")[0]
                print(f"  • [{d}] {q}")
                print(f"    正解: {ca} | 你答: {ua}")

    for item in p1[:3]:
        _print_topic_plan(item)
    for item in p2[:2]:
        _print_topic_plan(item)

    if p3_need_sample:
        print(f"\n{Colors.YELLOW}📌 補樣本提醒（題數不足，暫時無法做穩健判斷）{Colors.END}")
        for item in p3_need_sample[:3]:
            print(f"- {item['topic']}: 目前有效 {item['valid']} / 無效 {item['invalid']}，先做 10 題再看趨勢。")

    all_wrong = cur.execute(
        """
        SELECT ts, topic, question, correct_answer, user_answer
        FROM records
        WHERE is_correct = 0
        ORDER BY ts DESC
        LIMIT 50;
        """
    ).fetchall()

    print(f"\n{Colors.RED}=== 📚 歷史錯題（最近 50 筆）=== {Colors.END}")
    if not all_wrong:
        print(f"{Colors.GREEN}沒有錯誤紀錄。太棒了！{Colors.END}")
    else:
        for ts, topic, question, correct_answer, user_answer in all_wrong:
            ts_simple = ts.split('T')[0]
            print(f"[{ts_simple}][{topic}] 題目: {question}")
            print(f"  -> {Colors.GREEN}正解: {correct_answer}{Colors.END} | {Colors.RED}你答: {user_answer}{Colors.END}")
    print(f"{Colors.RED}=" * 30 + f"{Colors.END}\n")


# =========================
# 主流程
# =========================
def practice_auto(conn: sqlite3.Connection, topic_key=None):
    """自動出題模式"""
    gen_func = get_random_generator(topic_key)
    qobj = gen_func()

    print(f"\n{Colors.GOLD}--------------------------------{Colors.END}")
    print(f"【{qobj['topic']}】 題目： {Colors.YELLOW}{qobj['question']}{Colors.END}")
    print(f"{Colors.GOLD}--------------------------------{Colors.END}")

    user = input("請作答 (輸入 's' 跳過): ").strip()
    if user.lower() == 's':
        print("已跳過。")
        return

    is_correct = check_correct(user, qobj["answer"])

    if is_correct == 1:
        reward_message = random.choice(CORRECT_MESSAGES)
        print(f"{Colors.GREEN}{reward_message}{Colors.END}")

    elif is_correct == 0:
        feedback = INCORRECT_CUSTOM_FEEDBACK.format(answer=qobj['answer'])
        print(feedback)

    else:
        print(f"{Colors.RED}! 格式無法判斷或答案無效。{Colors.END}標準答案是：{qobj['answer']}")

    print(f"\n{Colors.YELLOW}[詳解]{Colors.END}\n{qobj['explanation']}\n")

    if is_correct in (1, 0):
        update_counters(is_correct)
        display_reward()

    log_record(conn, "auto", qobj['topic'], qobj['difficulty'], qobj['question'],
               qobj['answer'], user, is_correct, qobj['explanation'])


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
        is_correct = check_correct(user_ans, final_ans)
        print(f"{Colors.GREEN}V 答對{Colors.END}" if is_correct == 1 else f"{Colors.RED}X 答錯{Colors.END}")

    log_record(conn, "custom", "custom", "unknown", q_text, final_ans, user_ans, is_correct, explanation)
    print("已記錄。\n")


def main():
    print(f"{Colors.GOLD}--- 程式啟動 ---{Colors.END}")
    conn = init_db()

    try:
        cur = conn.cursor()
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
        print(f"\n{Colors.GOLD}==========================={Colors.END}")
        print(f" {Colors.GOLD}數學練習系統 V11.3 (深度教學版){Colors.END}")
        print(f"{Colors.GOLD}==========================={Colors.END}")
        print(f" {Colors.YELLOW}1. 隨機綜合練習{Colors.END}")
        print(f" {Colors.YELLOW}2. 選擇特定題型練習{Colors.END}")
        print(f" {Colors.YELLOW}3. 自訂題目 (含自動解題){Colors.END}")
        print(f" {Colors.YELLOW}4. 查看分析報告{Colors.END}")
        print(f" {Colors.YELLOW}0. 離開{Colors.END}")

        c = input("請選擇: ").strip()

        if c == '1':
            practice_auto(conn, None)
        elif c == '2':
            print(f"\n{Colors.YELLOW}[選擇題型]{Colors.END}")
            sorted_keys = sorted(GENERATORS.keys(), key=lambda x: int(x) if x.isdigit() else float('inf'))
            for k in sorted_keys:
                v = GENERATORS[k]
                print(f"  {k}. {v[0]}")

            k = input("請輸入代號: ").strip()
            if k in GENERATORS:
                practice_auto(conn, k)
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
        except:
            pass
    main()
