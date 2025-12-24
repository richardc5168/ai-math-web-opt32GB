#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命令列版：數學出題 + 解題 + 錯題紀錄系統（V4 最終穩定版）

更新日誌：
1. 最終修正：修復所有 SyntaxError 和 IndentationError (包括括號不平衡問題)，確保程式碼在標準環境下運行。
2. 強化：分數加減法詳解中，明確加入 GCD 和 LCM 的計算步驟，引導學生通分。
3. 擴充：小學五年級數學核心題型 (GCD/LCM, 小數運算, 體積/面積) 完整收錄。
"""

import sqlite3
import random
from fractions import Fraction
from datetime import datetime
import os
import sys
import re
import math # 引入 math 庫，用於 GCD/LCM

DB_PATH = "math_log.db"

# 嘗試載入 sympy（強烈建議安裝: pip install sympy）
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
            mode TEXT,              -- 'auto' or 'custom'
            topic TEXT,             -- 'integer', 'fraction', 'equation', 'custom', 'lcm', 'decimal', 'volume'
            difficulty TEXT,        -- 'easy','medium','hard','unknown'
            question TEXT,
            correct_answer TEXT,
            user_answer TEXT,
            is_correct INTEGER,     -- 1 / 0 / NULL
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

def gen_integer_arith():
    """整數四則運算題 (小學 3-4 年級)"""
    a = random.randint(2, 50)
    b = random.randint(2, 50)
    op = random.choice(["+", "-", "*", "/"])

    if op == "+":
        ans = a + b
        explanation = [f"{a} + {b} = {ans}"]
        op_text = "+"
    elif op == "-":
        if a < b:
            a, b = b, a
        ans = a - b
        explanation = [f"{a} - {b} = {ans}"]
        op_text = "-"
    elif op == "*":
        ans = a * b
        explanation = [f"{a} * {b} = {ans}"]
        op_text = "*"
    else:  # / (除法保證整除)
        ans = random.randint(2, 12)
        b = random.randint(2, 12)
        a = ans * b
        explanation = [f"{a} / {b} = {ans}"]
        op_text = "/"

    return {
        "topic": "整數四則運算",
        "difficulty": "easy",
        "question": f"{a} {op_text} {b} = ?",
        "answer": str(ans),
        "explanation": "\n".join(explanation),
    }


def _fraction_core(a1, b1, a2, b2, op):
    """
    共用的分數加減核心 (小學 5 年級) - 強化通分引導
    """
    f1 = Fraction(a1, b1)
    f2 = Fraction(a2, b2)
    
    # 避免負數結果
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

    # === 強化通分引導的邏輯開始 ===
    # 1. 計算 GCD 和 LCM (最小公倍數作為公分母)
    gcd_val = math.gcd(b1, b2)
    lcm_val = (b1 * b2) // gcd_val
    
    # 2. 計算擴分倍數
    m1 = lcm_val // b1
    m2 = lcm_val // b2
    
    # 3. 擴分
    na1 = a1 * m1
    na2 = a2 * m2

    if op == "+":
        ns = na1 + na2
    else:
        ns = na1 - na2

    expl = [
        f"步驟 1: 尋找最小公倍數 (LCM) 作為公分母",
        f"  分母 {b1} 和 {b2} 的最大公因數 (GCD) = {gcd_val}",
        f"  最小公倍數 (LCM) = ({b1} × {b2}) ÷ {gcd_val} = {lcm_val}",
        f"步驟 2: 進行通分",
        f"  第一個分數: {a1}/{b1} = ({a1} × {m1})/({b1} × {m1}) = {na1}/{lcm_val}",
        f"  第二個分數: {a2}/{b2} = ({a2} × {m2})/({b2} × {m2}) = {na2}/{lcm_val}",
        f"步驟 3: 進行{op_text}並約分",
        f"= {na1}/{lcm_val} {sign_text} {na2}/{lcm_val}",
        f"= {ns}/{lcm_val}",
        f"= {result.numerator}/{result.denominator} (約分後)"
    ]
    # === 強化通分引導的邏輯結束 ===

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
    ans_str = f"{whole} {remain}/{result.denominator}" if remain != 0 else f"{whole}"
    if result.numerator < result.denominator:
         ans_str = f"{result.numerator}/{result.denominator}"

    expl = [
        "步驟 1: 化為假分數",
        f"  {w1} {a1}/{b1} -> {F1.numerator}/{F1.denominator}",
        f"  {w2} {a2}/{b2} -> {F2.numerator}/{F2.denominator}",
        "步驟 2: 進行分數運算 (通分詳解如下)"
    ] + expl_core

    return {
        "topic": "帶分數運算",
        "difficulty": "medium",
        "question": f"{w1} {a1}/{b1} {op} {w2} {a2}/{b2} = ?",
        "answer": ans_str,
        "explanation": "\n".join(expl),
    }

# --- 5 年級擴充題型 ---

def gen_gcd_lcm():
    """最大公因數 (GCD) 和 最小公倍數 (LCM) 題 (小學 5 年級)"""
    
    # 選擇兩個或三個數字
    count = random.choice([2, 3])
    if count == 2:
        a = random.randint(10, 50)
        b = random.randint(10, 50)
        
        gcd_val = math.gcd(a, b)
        lcm_val = (a * b) // gcd_val
        
        question = f"數字 {a} 和 {b} 的最大公因數(GCD)和最小公倍數(LCM)各是多少？\n請依序輸入：GCD LCM"
        topic = "GCD/LCM (二數)"
    else: # 3 個數字
        # 較小的數字範圍，避免 LCM 爆炸
        a = random.randint(5, 20)
        b = random.randint(5, 20)
        c = random.randint(5, 20)
        
        # 計算 GCD
        gcd_val = math.gcd(a, math.gcd(b, c))
        
        # 計算 LCM
        if HAS_SYMPY:
            lcm_val = sp.lcm(a, b, c)
        else:
            lcm_val = (a * b) // math.gcd(a, b)
            lcm_val = (lcm_val * c) // math.gcd(lcm_val, c)
            
        question = f"數字 {a}, {b}, {c} 的最大公因數(GCD)和最小公倍數(LCM)各是多少？\n請依序輸入：GCD LCM"
        topic = "GCD/LCM (三數)"
        
    answer = f"{gcd_val} {lcm_val}"
    explanation = [
        f"最大公因數 (GCD) = {gcd_val}",
        f"最小公倍數 (LCM) = {lcm_val}"
    ]
        
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
    op = random.choice(["+", "-", "*", "÷"])

    if op == '+':
        ans = a + b
    elif op == '-':
        if a < b: a, b = b, a
        ans = a - b
    elif op == '*':
        ans = a * b
    else: # ÷
        ans_target = round(random.uniform(1.0, 5.0), 2)
        # 修正: 確保 round 函數有閉括號
        a = round(b * ans_target, 2)
        ans = a / b

    final_ans = round(ans, 2)
    
    question = f"計算並將結果四捨五入到小數點後兩位：\n{a} {op} {b} = ?"
    explanation = [
        f"精確計算結果: {ans}",
        f"四捨五入到小數點後兩位: {final_ans}"
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
            expl = f"體積 = 邊長 × 邊長 × 邊長 = {length} × {length} × {length} = {ans}"
        else: # surface_area
            ans = 6 * (length ** 2)
            q_text = f"邊長為 {length} 公分的{shape}，表面積是多少平方公分？"
            expl = f"表面積 = 6 × (邊長 × 邊長) = 6 × {length * length} = {ans}"
            
    else:
        shape = "長方體"
        dims = f"長 {length}、寬 {width}、高 {height}"
        
        if q_type == "volume":
            ans = length * width * height
            q_text = f"{dims} 公分的{shape}，體積是多少立方公分？"
            expl = f"體積 = 長 × 寬 × 高 = {length} × {width} × {height} = {ans}"
        else: # surface_area
            ans = 2 * (length * width + length * height + width * height)
            q_text = f"{dims} 公分的{shape}，表面積是多少平方公分？"
            expl = f"表面積 = 2 × (長×寬 + 長×高 + 寬×高) = 2 × ({length*width} + {length*height} + {width*height}) = {ans}"

    return {
        "topic": f"{shape} {q_type.replace('_',' ')}",
        "difficulty": "easy",
        "question": q_text,
        "answer": str(ans),
        "explanation": expl,
    }


def gen_linear_equation():
    """一元一次方程 (國中預備/數學深化)"""
    x_val = random.randint(-9, 9)
    a = random.randint(2, 9)
    b = random.randint(-10, 10)
    c = a * x_val + b
    
    question = f"{a}x + {b} = {c}, 求 x"
    expl = [
        f"{a}x + {b} = {c}",
        f"{a}x = {c} - {b}",
        f"{a}x = {c - b}",
        f"x = ({c - b}) / {a}",
        f"x = {x_val}"
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
    "1": ("整數四則運算 (3-4年級)", gen_integer_arith),
    "2": ("真分數加減 (5年級/通分引導)", gen_fraction_add),
    "3": ("帶分數加減 (5年級/通分引導)", gen_fraction_mixed),
    "4": ("最大公因數/最小公倍數 (5年級)", gen_gcd_lcm),
    "5": ("小數四則運算 (5年級)", gen_decimal_arith),
    "6": ("長/正方體積與表面積 (5年級)", gen_volume_area),
}

if HAS_SYMPY:
    GENERATORS["7"] = ("一元一次方程 (國中預備)", gen_linear_equation)

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
    """將使用者輸入轉成 Fraction 或 None"""
    text = text.strip()
    if not text:
        return None
    try:
        if " " in text and "/" in text:
            parts = text.split()
            if len(parts) == 2:
                w = int(parts[0])
                f = Fraction(parts[1])
                # 處理帶分數 w a/b = w + a/b
                return (Fraction(w, 1) + f) if w >= 0 else (Fraction(w, 1) - f)
        
        # 處理純分數/小數/整數
        return Fraction(text)
    except Exception:
        return None

def check_correct(user: str, correct: str) -> int | None:
    """
    檢查使用者答案與正確答案是否一致。
    處理 GCD/LCM 答案 ("X Y" 格式) 和 分數/小數/整數 格式。
    """
    user = user.strip()
    correct = correct.strip()

    # 處理 GCD/LCM 格式 ("X Y")
    if " " in correct:
        if user.upper().replace(' ', '') == correct.upper().replace(' ', ''): # 忽略空格和大小寫
            return 1
        return 0
        
    # 處理分數/小數/整數
    u = parse_answer(user)
    c = parse_answer(correct)

    if u is None or c is None:
        return None
        
    return 1 if u == c else 0


# =========================
# 自訂題目自動解題邏輯
# =========================
def simple_solver(question_text):
    """嘗試解析並計算自訂題目的答案。"""
    q = question_text.strip()
    
    # 1. 處理方程式 (含有 =)
    if "=" in q:
        if not HAS_SYMPY:
            return None, "未安裝 SymPy，無法自動解方程式"
        try:
            lhs_str, rhs_str = q.split("=")
            x = sp.Symbol('x')
            lhs = sp.sympify(lhs_str)
            rhs = sp.sympify(rhs_str)
            sol = sp.solve(sp.Eq(lhs, rhs), x)
            if sol:
                ans_str = str(Fraction(sol[0]).limit_denominator())
                return ans_str, f"系統自動解題 (SymPy): x = {ans_str}"
            else:
                return None, "無解或無限多解"
        except Exception as e:
            return None, f"方程式解析失敗: {e}"

    # 2. 處理一般算式
    try:
        clean_q = q.replace("×", "*").replace("÷", "/").replace(",", "")
        
        if HAS_SYMPY:
            expr = sp.sympify(clean_q)
            f_ans = Fraction(expr).limit_denominator()
            ans = f"{f_ans.numerator}/{f_ans.denominator}"
            return ans, f"系統自動計算 (SymPy): {ans}"
        else:
            ans = eval(clean_q)
            f_ans = Fraction(ans).limit_denominator()
            ans_str = f"{f_ans.numerator}/{f_ans.denominator}"
            return ans_str, f"系統自動計算 (Fraction): {ans_str}"
            
    except Exception as e:
        return None, f"無法計算: {e}"


# =========================
# 統計與顯示
# =================