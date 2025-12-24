#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命令列版：數學練習系統（V9 深度教學版 - 強化通分、約分和整數運算）
新增功能：加入 ANSI 顏色代碼，模擬暖色系介面 (金色/黃色)。

更新日誌：
1. **顏色新增：** 導入 Colors class，定義 GOLD, YELLOW, GREEN, RED 等顏色。
2. **暖色應用：** 主菜單、題目邊框和詳解標題改為金色/黃色。
3. **結果視覺化：** 答對 (GREEN) / 答錯 (RED) 訊息顏色強化。
4. **題型維持：** 完整保留分數通分、約分、整數四則運算等深度引導功能。

***重要修改***
- 原 gen_integer_arith 替換為 gen_order_of_ops_arith，專門用於四則運算順序教學。
- 題目強化：包含括號、乘除，數字範圍在 100 以內，乘除保證整除且數字好算。
"""

import sqlite3
import random
from fractions import Fraction
from datetime import datetime
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
    YELLOW = '\033[93m'             # 暖色系 - 標準亮黃色
    GREEN = '\033[92m'              # 答對 (綠色)
    RED = '\033[91m'                # 答錯 (紅色)
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
            mode TEXT,              -- 'auto' or 'custom'
            topic TEXT,             -- 'integer', 'fraction', 'equation', 'custom', 'lcm', 'decimal', 'volume'
            difficulty TEXT,        -- 'easy','medium','hard','unknown'
            question TEXT,
            correct_answer TEXT,
            user_answer TEXT,
            is_correct INTEGER,     -- 1 / 0 / NULL
            explanation TEXT
        )
        """
    )
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
    else: # /
        # 乘積 <= 50，除數 2~10
        result_div = random.randint(2, 5)
        c = random.randint(2, 10)
        b = result_div * c
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
    
    # 移除隨機選擇，強制執行這組邏輯，以確保變數被定義
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

# -------------------------------------------------------------
# 注意：以下是程式的其餘部分，僅替換 gen_integer_arith
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
        f"  -> 公分母必須是 {b1} 和 {b2} 的公倍數，最小的公倍數即為 **最小公倍數 (LCM)**。",
        f"  -> 計算結果: LCM({b1}, {b2}) = {lcm_val} (這是您的第一個答案)",
        f"步驟 2: **計算第一個新分子**",
        f"  -> 原分母 {b1} 擴大 {m1} 倍成為 {lcm_val}。",
        f"  -> 根據分數基本性質，分子 {a1} 也需擴大 {m1} 倍: {a1} × {m1} = {na1} (這是您的第二個答案)",
        f"步驟 3: **計算第二個新分子**",
        f"  -> 原分母 {b2} 擴大 {m2} 倍成為 {lcm_val}。",
        f"  -> 分子 {a2} 也需擴大 {m2} 倍: {a2} × {m2} = {na2} (這是您的第三個答案)",
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
        f"  -> GCD 是能同時整除分子 {original_num} 和分母 {original_den} 的最大整數。",
        f"  -> 計算結果: GCD({original_num}, {original_den}) = {gcd_val}",
        f"步驟 2: **進行約分**",
        f"  -> 根據分數基本性質，分子和分母同時除以這個 GCD。",
        f"  -> 新分子: {original_num} ÷ {gcd_val} = {simplified_num} (這是您的第一個答案)",
        f"  -> 新分母: {original_den} ÷ {gcd_val} = {simplified_den} (這是您的第二個答案)",
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
        f"  -> 計算結果: LCM({b1}, {b2}) = {lcm_val}",
        f"步驟 2: **進行通分** - 轉換為分母為 {lcm_val} 的等值分數：",
        f"  -> {a1}/{b1} 擴大 {m1} 倍變為 {na1}/{lcm_val}",
        f"  -> {a2}/{b2} 擴大 {m2} 倍變為 {na2}/{lcm_val}",
        f"步驟 3: **計算分子** - 進行 {op_text} 運算：",
        f"= {na1}/{lcm_val} {sign_text} {na2}/{lcm_val} = {ns}/{lcm_val}",
        f"步驟 4: **結果約分** - 將結果 {ns}/{lcm_val} 化簡為最簡分數：",
        f"  -> 最終答案: {result.numerator}/{result.denominator}"
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
        f"  -> 第一個數: {w1} {a1}/{b1} -> {F1.numerator}/{F1.denominator}",
        f"  -> 第二個數: {w2} {a2}/{b2} -> {F2.numerator}/{F2.denominator}",
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
            f"  -> GCD 是能同時整除所有數字的最大數。計算結果: {gcd_val}",
            f"步驟 2: **最小公倍數 (LCM)**",
            f"  -> LCM 是所有數字的公倍數中最小的一個。",
            f"  -> 公式：LCM(a, b) = (|a * b|) / GCD(a, b)",
            f"  -> 計算：({a} × {b}) ÷ {gcd_val} = {lcm_val}",
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
            f"  -> 連續求兩數的 GCD：GCD({a}, {b})，再求 GCD(結果, {c})。計算結果: {gcd_val}",
            f"步驟 2: **最小公倍數 (LCM)**",
            f"  -> 逐次計算：LCM({a}, {b}) = {lcm_val_ab}。",
            f"  -> 再求 LCM({lcm_val_ab}, {c})。計算結果: {lcm_val}",
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
        f"  -> 四捨五入後答案: {final_ans}"
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
        f"  -> 將 {b} 移到右邊，符號改變：",
        f"  -> {a}x = {c} - ({b})",
        f"  -> {a}x = {c - b}",
        f"步驟 2: **求解 x** - 將 x 的係數 {a} 移到右邊。",
        f"  -> (兩邊同時除以 {a})",
        f"  -> x = ({c - b}) / {a}",
        f"  -> x = {x_val}",
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
    "1": ("四則運算 (含括號/乘除)", gen_order_of_ops_arith), # <<< 已修改
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
# 遊戲化/獎勵邏輯
# =========================
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


# =========================
# 統計與分析報告
# =========================
def show_analysis_report(conn: sqlite3.Connection):
    cur = conn.cursor()
    
    # 1. 執行分類統計查詢
    query = """
    SELECT
        topic,
        COUNT(*) AS total,
        SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) AS correct,
        SUM(CASE WHEN is_correct = 0 THEN 1 ELSE 0 END) AS incorrect
    FROM records
    WHERE is_correct IS NOT NULL 
    GROUP BY topic
    ORDER BY total DESC; 
    """
    topic_data = cur.execute(query).fetchall()

    # 2. 顯示總體統計 (暖色強化)
    total_q = cur.execute("SELECT COUNT(*) FROM records WHERE is_correct IS NOT NULL").fetchone()[0]
    total_c = cur.execute("SELECT COUNT(*) FROM records WHERE is_correct = 1").fetchone()[0]
    
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
    all_wrong = cur.execute("SELECT ts, topic, question, correct_answer, user_answer FROM records WHERE is_correct=0 ORDER BY ts DESC").fetchall()
    
    print(f"\n{Colors.RED}=== 📚 歷史累計錯題詳情 (全部紀錄) ==={Colors.END}")
    if not all_wrong:
        print(f"{Colors.GREEN}沒有錯誤紀錄。太棒了！{Colors.END}")
        
    else:
        for ts, topic, question, correct_answer, user_answer in all_wrong:
            ts_simple = ts.split('T')[0] 
            print(f"[{ts_simple}][{topic}] 題目: {question}")
            print(f"  -> {Colors.GREEN}正解: {correct_answer}{Colors.END} | {Colors.RED}你答: {user_answer}{Colors.END}")
    print(f"{Colors.RED}=" * 30 + f"{Colors.END}\n")


# =========================
# 主流程
# =========================
def practice_auto(conn: sqlite3.Connection, topic_key=None):
    """自動出題模式"""
    gen_func = get_random_generator(topic_key)
    qobj = gen_func()
    
    # 暖色邊框
    print(f"\n{Colors.GOLD}--------------------------------{Colors.END}")
    # 題目使用黃色突出
    print(f"【{qobj['topic']}】 題目： {Colors.YELLOW}{qobj['question']}{Colors.END}")
    print(f"{Colors.GOLD}--------------------------------{Colors.END}")
    
    user = input("請作答 (輸入 's' 跳過): ").strip()
    if user.lower() == 's':
        print("已跳過。")
        return

    is_correct = check_correct(user, qobj["answer"])
    
    # 顯示結果 (綠色/紅色)
    if is_correct == 1:
        print(f"{Colors.GREEN}V 答對了！{Colors.END}")
    elif is_correct == 0:
        print(f"{Colors.RED}X 答錯了。{Colors.END}標準答案是：{qobj['answer']}")
    else:
        print(f"{Colors.RED}! 格式無法判斷或答案無效。{Colors.END}標準答案是：{qobj['answer']}")
        
    # 詳解標題使用黃色
    print(f"\n{Colors.YELLOW}[詳解]{Colors.END}\n{qobj['explanation']}\n")
    
    # 遊戲化更新
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
    
    # 初始化全局計數器
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
        # 主選單標題使用金色/暖色突出
        print(f"\n{Colors.GOLD}==========================={Colors.END}")
        print(f" {Colors.GOLD}數學練習系統 V9 (深度教學版){Colors.END}")
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
            # 確保使用 GENERATORS 字典的排序來顯示選單
            sorted_keys = sorted(GENERATORS.keys(), key=lambda x: int(x) if x.isdigit() else float('inf'))
            for k in sorted_keys:
                 v = GENERATORS[k]
                 print(f"  {k}. {v[0]}")

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
        except: pass
    main()