#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命令列版：數學練習系統（V8 教學強化版 - 詳細步驟引導）

更新日誌：
1. **教學強化：** 強化了分數加減、GCD/LCM 和一元一次方程的「詳解」部分。
   - 分數：更明確地解釋通分 (LCM) 的原因和步驟。
   - GCD/LCM：提供計算 GCD 和 LCM 的基本思維引導。
   - 方程式：明確說明「等量公理」（移項）的應用，讓解題思路更清晰。
2. 延續 V7 所有功能：穩定運作、計數、獎勵、主題分析報告。
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
    """共用的分數加減核心 - 強化通分引導 (教學強化)"""
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

    # V8 教學強化詳解
    expl = [
        f"步驟 1: **確定運算目標** - 分數相加或相減，必須找到相同的分母 (通分)。",
        f"步驟 2: **尋找公分母** - 找出兩個分母 ({b1} 和 {b2}) 的最小公倍數 (LCM)。",
        f"  -> 計算結果: LCM({b1}, {b2}) = {lcm_val}",
        f"步驟 3: **進行通分** - 將兩個分數都轉換為分母為 {lcm_val} 的等值分數：",
        f"  -> 第一個分數: {a1}/{b1} 需擴大 {m1} 倍，變為 {na1}/{lcm_val}",
        f"  -> 第二個分數: {a2}/{b2} 需擴大 {m2} 倍，變為 {na2}/{lcm_val}",
        f"步驟 4: **計算分子** - 既然分母相同，直接計算分子：",
        f"  -> {na1} {sign_text} {na2} = {ns}",
        f"  -> 運算結果是 {ns}/{lcm_val}",
        f"步驟 5: **結果約分** - 將假分數或非最簡分數 {ns}/{lcm_val} 進行化簡：",
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
    
    # 這裡調用核心函數，它會處理減法時的順序問題
    result, expl_core = _fraction_core(F1.numerator, F1.denominator, F2.numerator, F2.denominator, op)

    whole = result.numerator // result.denominator
    remain = result.numerator % result.denominator
    # 帶分數格式輸出
    ans_str = f"{whole} {remain}/{result.denominator}" if remain != 0 and whole != 0 else f"{result.numerator}/{result.denominator}"

    expl = [
        "步驟 1: **化為假分數** - 將帶分數轉換為假分數，方便統一運算。",
        f"  -> 第一個數: {w1} {a1}/{b1} 轉換為 {F1.numerator}/{F1.denominator}",
        f"  -> 第二個數: {w2} {a2}/{b2} 轉換為 {F2.numerator}/{F2.denominator}",
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
        
        # V8 教學強化詳解 (二數)
        explanation = [
            f"計算目標：數字 {a} 和 {b} 的 GCD 和 LCM。",
            f"步驟 1: **最大公因數 (GCD)**",
            f"  -> GCD 是能同時整除所有數字的最大數。",
            f"  -> 通過短除法或質因數分解，得到 GCD = {gcd_val}",
            f"步驟 2: **最小公倍數 (LCM)**",
            f"  -> LCM 是所有數字的公倍數中最小的一個。",
            f"  -> 對於兩個數：LCM(a, b) = (|a * b|) / GCD(a, b)",
            f"  -> LCM = ({a} * {b}) / {gcd_val} = {lcm_val}",
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
        
        # V8 教學強化詳解 (三數)
        explanation = [
            f"計算目標：數字 {a}, {b}, {c} 的 GCD 和 LCM。",
            f"步驟 1: **最大公因數 (GCD)**",
            f"  -> GCD 是能同時整除所有數字的最大數。",
            f"  -> 通過連續短除法或質因數分解，得到 GCD = {gcd_val}",
            f"步驟 2: **最小公倍數 (LCM)**",
            f"  -> LCM 必須包含所有數字的全部質因數。",
            f"  -> 計算過程簡化為：LCM({a}, {b}, {c}) = LCM( LCM({a}, {b}), {c} )",
            f"  -> 先求 LCM({a}, {b}) = {lcm_val_ab}",
            f"  -> 再求 LCM({lcm_val_ab}, {c}) = {lcm_val}",
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
        a = round(b * ans_target, 2)
        ans = a / b

    final_ans = round(ans, 2)
    
    question = f"計算並將結果四捨五入到小數點後兩位：\n{a} {op} {b} = ?"
    explanation = [
        f"步驟 1: 進行運算 (忽略四捨五入): {a} {op} {b} ≈ {ans}",
        f"步驟 2: 檢查四捨五入位數 (小數點後兩位)。",
        f"步驟 3: 精確計算結果: {ans}",
        f"步驟 4: 四捨五入到小數點後兩位: {final_ans}",
        "(注意：小數運算容易因浮點數精度導致微小誤差，請以四捨五入後的結果為準)"
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
            expl = f"表面積公式: 6 × (邊長 × 邊長) (6個完全相同的面)\n= 6 × ({length} × {length}) = {ans}"
            
    else:
        shape = "長方體"
        dims = f"長 {length}、寬 {width}、高 {height}"
        
        if q_type == "volume":
            ans = length * width * height
            q_text = f"{dims} 公分的{shape}，體積是多少立方公分？"
            expl = f"體積公式: 長 × 寬 × 高\n= {length} × {width} × {height} = {ans}"
        else: # surface_area
            ans = 2 * (length * width + length * height + width * height)
            q_text = f"{dims} 公分的{shape}，表面積是多少平方公分？"
            expl = f"表面積公式: 2 × (長×寬 + 長×高 + 寬×高) (三組不同面積的兩兩相對的面)\n= 2 × ({length*width} + {length*height} + {width*height}) = {ans}"

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
    
    # V8 教學強化詳解
    expl = [
        f"給定方程式: {a}x + {b} = {c}",
        f"步驟 1: **分離常數項** - 運用等量公理，將常數 {b} 移到等號的右邊。",
        f"  -> (兩邊同時減去 {b})",
        f"  -> {a}x = {c} - ({b})",
        f"  -> {a}x = {c - b}",
        f"步驟 2: **求解 x** - 運用等量公理，將 x 的係數 {a} 移到右邊。",
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
    "1": ("整數四則運算", gen_integer_arith),
    "2": ("分數加減", gen_fraction_add),
    "3": ("帶分數運算", gen_fraction_mixed),
    "4": ("GCD/LCM", gen_gcd_lcm),
    "5": ("小數四則運算", gen_decimal_arith),
    "6": ("長/正方體積/面積", gen_volume_area),
}

if HAS_SYMPY:
    GENERATORS["7"] = ("一元一次方程", gen_linear_equation)

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

    # 特殊情況：如果正確答案是 "GCD LCM" 這種格式，直接比對字串（忽略空格和大小寫）
    if " " in correct and (correct.count(' ') > 0 or not correct.isdigit()):
        if user.upper().replace(' ', '') == correct.upper().replace(' ', ''): 
            return 1
        return 0
        
    u = parse_answer(user)
    c = parse_answer(correct)

    if u is None or c is None:
        return None
        
    return 1 if u == c else 0


# =========================
# 自訂題目自動解題邏輯
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
    """根據答對題數，顯示圖形獎勵。"""
    global CORRECT_COUNT 
    if CORRECT_COUNT > 0 and CORRECT_COUNT % 5 == 0:
        index = (CORRECT_COUNT // 5 - 1) % len(REWARDS)
        icon, message = REWARDS[index]
        
        print("\n" + "═"*40)
        print(f"║ {icon*3} 達成里程碑！{icon*3} ║")
        print(f"║ {message.center(36)} ║")
        print("═"*40 + "\n")

def update_counters(is_correct: int | None):
    """更新全局計數器"""
    global TOTAL_COUNT, CORRECT_COUNT
    
    TOTAL_COUNT += 1
    if is_correct == 1:
        CORRECT_COUNT += 1

    print(f"\n[進度] 總作答：{TOTAL_COUNT} 題 | 答對：{CORRECT_COUNT} 題 (正確率: {(CORRECT_COUNT/TOTAL_COUNT*100) if TOTAL_COUNT else 0:.1f}%)")


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

    # 2. 顯示總體統計
    total_q = cur.execute("SELECT COUNT(*) FROM records WHERE is_correct IS NOT NULL").fetchone()[0]
    total_c = cur.execute("SELECT COUNT(*) FROM records WHERE is_correct = 1").fetchone()[0]
    
    print("\n" + "═" * 65)
    print(f"| {'📊 歷史總體統計報告'.center(61)} |")
    print("═" * 65)
    if total_q == 0:
        print("| 尚無有效作答紀錄。".ljust(63) + "|")
        print("═" * 65)
        
    else:
        accuracy = (total_c / total_q) * 100
        print(f"| 總作答題數: {str(total_q).ljust(6)} | 總答對題數: {str(total_c).ljust(6)} | 歷史總正確率: {accuracy:.2f}% | 繼續努力！ |")
        print("═" * 65)
    
        # 3. 顯示按主題分類的詳細報告
        print(f"\n| {'📚 按主題分類報告 (依作答數排序)'.center(61)} |")
        print("╠" + "═" * 65 + "╣")
        print(f"| {'主題'.ljust(15)} | {'總數'.ljust(4)} | {'答對'.ljust(4)} | {'答錯'.ljust(4)} | {'正確率'.ljust(8)} | {'難點分析與建議'.ljust(18)} |")
        print("╠" + "═" * 65 + "╣")

        for topic, total, correct, incorrect in topic_data:
            acc = (correct / total) * 100
            analysis = ""
            if acc < 70 and total >= 5: 
                analysis = "🚨 重點加強題型"
            elif acc >= 95 and total >= 5: 
                analysis = "✅ 已穩固掌握"
            elif total < 5:
                analysis = "資料不足，多練習"
                
            print(f"| {topic.ljust(15)} | {str(total).ljust(4)} | {str(correct).ljust(4)} | {str(incorrect).ljust(4)} | {acc:.2f}% | {analysis.ljust(18)} |")

        print("═" * 65 + "\n")

    # 4. 顯示所有歷史錯題 (取代 Top 5 錯題)
    all_wrong = cur.execute("SELECT ts, topic, question, correct_answer, user_answer FROM records WHERE is_correct=0 ORDER BY ts DESC").fetchall()
    
    print("\n=== 📚 歷史累計錯題詳情 (全部紀錄) ===")
    if not all_wrong:
        print("沒有錯誤紀錄。太棒了！")
        
    else:
        for ts, topic, question, correct_answer, user_answer in all_wrong:
            ts_simple = ts.split('T')[0] 
            print(f"[{ts_simple}][{topic}] 題目: {question}")
            print(f"  -> 正解: {correct_answer} | 你答: {user_answer}")
    print("=" * 30 + "\n")


# =========================
# 主流程
# =========================
def practice_auto(conn: sqlite3.Connection, topic_key=None):
    """自動出題模式"""
    gen_func = get_random_generator(topic_key)
    qobj = gen_func()
    
    print("\n--------------------------------")
    print(f"【{qobj['topic']}】 題目： {qobj['question']}")
    print("--------------------------------")
    
    user = input("請作答 (輸入 's' 跳過): ").strip()
    if user.lower() == 's':
        print("已跳過。")
        return

    is_correct = check_correct(user, qobj["answer"])
    
    # 顯示結果
    if is_correct == 1:
        print("V 答對了！")
    elif is_correct == 0:
        print(f"X 答錯了。標準答案是：{qobj['answer']}")
    else:
        print(f"! 格式無法判斷或答案無效。標準答案是：{qobj['answer']}")
        
    print(f"\n[詳解]\n{qobj['explanation']}\n")
    
    # 遊戲化更新
    update_counters(is_correct)
    display_reward()
    
    log_record(conn, "auto", qobj['topic'], qobj['difficulty'], qobj['question'], 
               qobj['answer'], user, is_correct, qobj['explanation'])


def custom_question_mode(conn: sqlite3.Connection):
    """自訂題目 + 自動解題"""
    print("\n=== 自訂題目與解題 ===")
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
        print(f"系統算出答案為: {auto_ans}")
        use_auto = input("是否使用此答案作為標準答案? (y/n): ").strip().lower()
        if use_auto == 'y':
            final_ans = auto_ans
            explanation = auto_expl
        else:
            final_ans = input("請手動輸入正確答案: ").strip()
            explanation = "使用者手動輸入答案"
    else:
        print(f"系統無法自動解題 ({auto_expl})")
        final_ans = input("請手動輸入正確答案: ").strip()
        explanation = "系統無法解題，手動輸入"

    user_ans = input("您的作答 (直接按 Enter 可略過): ").strip()
    
    is_correct = None
    if user_ans and final_ans:
        is_correct = check_correct(user_ans, final_ans)
        print("V 答對" if is_correct == 1 else "X 答錯")

    log_record(conn, "custom", "custom", "unknown", q_text, final_ans, user_ans, is_correct, explanation)
    print("已記錄。\n")


def main():
    print("--- 程式啟動 ---")
    conn = init_db()
    
    # 初始化全局計數器
    try:
        cur = conn.cursor()
        # 讀取上次的歷史數據來初始化計數器，只計算 mode='auto' 的有效作答
        total_q = cur.execute("SELECT COUNT(*) FROM records WHERE mode = 'auto' AND is_correct IS NOT NULL").fetchone()[0]
        correct_c = cur.execute("SELECT COUNT(*) FROM records WHERE mode = 'auto' AND is_correct = 1").fetchone()[0]
        global TOTAL_COUNT, CORRECT_COUNT
        TOTAL_COUNT = total_q
        CORRECT_COUNT = correct_c
        
        if TOTAL_COUNT > 0:
            print(f"載入歷史進度：總作答 {TOTAL_COUNT} 題，答對 {CORRECT_COUNT} 題 ({(CORRECT_COUNT/TOTAL_COUNT*100):.1f}%)")
        
    except Exception as e:
        print(f"無法載入歷史計數器: {e}")
        pass
    
    while True:
        print("\n===========================")
        print(" 數學練習系統 V8 (教學強化版)")
        print("===========================")
        print(" 1. 隨機綜合練習")
        print(" 2. 選擇特定題型練習")
        print(" 3. 自訂題目 (含自動解題)")
        print(" 4. 查看分析報告") 
        print(" 0. 離開")
        
        c = input("請選擇: ").strip()
        
        if c == '1':
            practice_auto(conn, None)
        elif c == '2':
            print("\n[選擇題型]")
            for k, v in GENERATORS.items():
                print(f"  {k}. {v[0]}")
            k = input("請輸入代號: ").strip()
            if k in GENERATORS:
                practice_auto(conn, k)
            else:
                print("無效代號")
        elif c == '3':
            custom_question_mode(conn)
        elif c == '4':
            show_analysis_report(conn) 
        elif c == '0':
            print("Bye!")
            break
        else:
            print("無效輸入")

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except: pass
    main()