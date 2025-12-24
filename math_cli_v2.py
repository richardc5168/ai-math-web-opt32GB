#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命令列版：數學出題 + 解題 + 錯題紀錄系統（V2 強化版 - Windows 相容修正）

更新日誌：
1. 新增「選擇特定題型練習」功能。
2. 增強「自訂題目」模式：支援自動計算輸入算式的答案。
3. 修正：將所有 Unicode 符號替換為 ASCII 符號，解決 Windows 命令列的 SyntaxError。
"""

import sqlite3
import random
from fractions import Fraction
from datetime import datetime
import os
import sys
import re

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
            topic TEXT,             -- 'integer', 'fraction', 'equation', 'custom'
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
# 出題邏輯 (Generator)
# =========================

def gen_integer_arith():
    """整數四則運算題"""
    a = random.randint(2, 50)
    b = random.randint(2, 50)
    op = random.choice(["+", "-", "*", "/"]) # 符號已換成 ASCII

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
        "topic": "整數運算",
        "difficulty": "easy",
        "question": f"{a} {op_text} {b} = ?",
        "answer": str(ans),
        "explanation": "\n".join(explanation),
    }


def _fraction_core(a1, b1, a2, b2, op):
    """共用的分數加減核心"""
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

    # 最小公倍數 (LCM) 簡化計算
    lcm = (b1 * b2) // Fraction(b1, b2).denominator
    m1 = lcm // b1
    m2 = lcm // b2
    na1 = a1 * m1
    na2 = a2 * m2

    if op == "+":
        ns = na1 + na2
    else:
        ns = na1 - na2

    expl = [
        f"步驟：通分 (LCM={lcm})",
        f"{a1}/{b1} {sign_text} {a2}/{b2}",
        f"= {na1}/{lcm} {sign_text} {na2}/{lcm}",
        f"= {ns}/{lcm}",
        f"= {result.numerator}/{result.denominator} (約分後)"
    ]
    return result, expl


def gen_fraction_add():
    """真分數加減"""
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
    """帶分數加減"""
    w1 = random.randint(1, 5)
    w2 = random.randint(1, 5)
    b1 = random.randint(2, 9)
    b2 = random.randint(2, 9)
    a1 = random.randint(1, b1 - 1)
    a2 = random.randint(1, b2 - 1)
    op = random.choice(["+", "-"])

    # 轉假分數運算
    F1 = Fraction(w1 * b1 + a1, b1)
    F2 = Fraction(w2 * b2 + a2, b2)
    result, expl_core = _fraction_core(F1.numerator, F1.denominator, F2.numerator, F2.denominator, op)

    # 轉回帶分數顯示
    whole = result.numerator // result.denominator
    remain = result.numerator % result.denominator
    ans_str = f"{whole} {remain}/{result.denominator}" if remain != 0 else f"{whole}"
    if result.numerator < result.denominator: # 真分數
         ans_str = f"{result.numerator}/{result.denominator}"

    expl = [
        "步驟 1：化為假分數",
        f"{w1} {a1}/{b1} -> {F1.numerator}/{F1.denominator}",
        f"{w2} {a2}/{b2} -> {F2.numerator}/{F2.denominator}",
        "步驟 2：進行分數運算"
    ] + expl_core

    return {
        "topic": "帶分數運算",
        "difficulty": "medium",
        "question": f"{w1} {a1}/{b1} {op} {w2} {a2}/{b2} = ?",
        "answer": ans_str,
        "explanation": "\n".join(expl),
    }


def gen_linear_equation():
    """一元一次方程"""
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
    "1": ("整數四則運算", gen_integer_arith),
    "2": ("真分數加減", gen_fraction_add),
    "3": ("帶分數加減", gen_fraction_mixed),
}

if HAS_SYMPY:
    GENERATORS["4"] = ("一元一次方程", gen_linear_equation)

def get_random_generator(topic_filter=None):
    """
    根據篩選器回傳出題函數。
    topic_filter: 如果是 None，代表全隨機。如果是 key (str)，則回傳該 key 對應的 function。
    """
    if topic_filter and topic_filter in GENERATORS:
        return GENERATORS[topic_filter][1]
    
    # 隨機選擇
    keys = list(GENERATORS.keys())
    k = random.choice(keys)
    return GENERATORS[k][1]


# =========================
# 答案解析與比對
# =========================
def parse_answer(text: str) -> Fraction | None:
    """將使用者輸入轉成 Fraction"""
    text = text.strip()
    if not text:
        return None
    try:
        # 處理帶分數 "1 1/2" -> 1.5
        if " " in text and "/" in text:
            parts = text.split()
            if len(parts) == 2:
                w = int(parts[0])
                f = Fraction(parts[1])
                return (Fraction(w, 1) + f) if w >= 0 else (Fraction(w, 1) - f)
        
        # 處理小數或整數或分數
        return Fraction(text)
    except Exception:
        return None

def check_correct(user: str, correct: str) -> int | None:
    u = parse_answer(user)
    c = parse_answer(correct)
    # 針對方程式的整數答案容許度更高
    if u is None and c is not None:
         # 嘗試直接比較整數或浮點數
         try:
             if float(user) == float(c):
                 return 1
         except:
             return None

    if u is None or c is None:
        return None
        
    return 1 if u == c else 0


# =========================
# 自訂題目自動解題邏輯
# =========================
def simple_solver(question_text):
    """
    嘗試解析並計算自訂題目的答案。
    """
    q = question_text.strip()
    
    # 1. 處理方程式 (含有 =)
    if "=" in q:
        if not HAS_SYMPY:
            return None, "未安裝 SymPy，無法自動解方程式"
        try:
            # 假設方程式為 ... = ...
            lhs_str, rhs_str = q.split("=")
            x = sp.Symbol('x')
            # 使用 sympify 解析字串為表達式
            lhs = sp.sympify(lhs_str)
            rhs = sp.sympify(rhs_str)
            sol = sp.solve(sp.Eq(lhs, rhs), x)
            if sol:
                # 確保答案格式一致
                ans_str = str(Fraction(sol[0]).limit_denominator())
                return ans_str, f"系統自動解題 (SymPy): x = {ans_str}"
            else:
                return None, "無解或無限多解"
        except Exception as e:
            return None, f"方程式解析失敗: {e}"

    # 2. 處理一般算式
    try:
        # 替換常見符號
        clean_q = q.replace("*", "*").replace("/", "/") # 保持 ASCII 符號
        
        # 嘗試利用 sympy 計算 (最準確，支援分數)
        if HAS_SYMPY:
            expr = sp.sympify(clean_q)
            # 轉換為分數並約分
            f_ans = Fraction(expr).limit_denominator()
            ans = f"{f_ans.numerator}/{f_ans.denominator}"
            return ans, f"系統自動計算 (SymPy): {ans}"
        else:
            # 退化到 python eval (會變小數)
            ans = eval(clean_q)
            # 嘗試轉分數顯示
            f_ans = Fraction(ans).limit_denominator()
            ans_str = f"{f_ans.numerator}/{f_ans.denominator}"
            return ans_str, f"系統自動計算 (Fraction): {ans_str}"
            
    except Exception as e:
        return None, f"無法計算: {e}"


# =========================
# 統計與顯示
# =========================
def show_stats(conn: sqlite3.Connection):
    cur = conn.cursor()
    total = cur.execute("SELECT COUNT(*) FROM records").fetchone()[0]
    correct = cur.execute("SELECT COUNT(*) FROM records WHERE is_correct = 1").fetchone()[0]
    print(f"\n[統計] 總題數：{total} | 答對：{correct} | 正確率：{(correct/total*100) if total else 0:.1f}%")

def show_recent_wrong(conn: sqlite3.Connection):
    cur = conn.cursor()
    rows = cur.execute("SELECT topic, question, correct_answer, user_answer FROM records WHERE is_correct=0 ORDER BY id DESC LIMIT 5").fetchall()
    print("\n=== 最近錯題 (Top 5) ===")
    if not rows:
        print("沒有錯誤紀錄。")
        return
        
    for r in rows:
        print(f"[{r[0]}] {r[1]} | 正解: {r[2]} | 你答: {r[3]}")
    print()


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
    
    # 替換了原本的特殊符號
    if is_correct == 1:
        print("V 答對了！")
    elif is_correct == 0:
        print(f"X 答錯了。標準答案是：{qobj['answer']}")
    else:
        print(f"! 格式無法判斷或答案無效。標準答案是：{qobj['answer']}")
        
    print(f"\n[詳解]\n{qobj['explanation']}\n")
    
    log_record(conn, "auto", qobj['topic'], qobj['difficulty'], qobj['question'], 
               qobj['answer'], user, is_correct, qobj['explanation'])


def custom_question_mode(conn: sqlite3.Connection):
    """自訂題目 + 自動解題"""
    print("\n=== 自訂題目與解題 ===")
    print("說明：您可以輸入算式（如 1/2 + 1/3）或方程式（如 2*x + 3 = 9）。")
    print("注意：乘法請用 *，除法用 /。")
    
    q_text = input("請輸入題目: ").strip()
    if not q_text:
        return

    # 嘗試自動解題
    print("系統正在計算答案...")
    auto_ans, auto_expl = simple_solver(q_text)
    
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

    # 讓使用者作答 (選用)
    user_ans = input("您的作答 (直接按 Enter 可略過): ").strip()
    
    is_correct = None
    if user_ans and final_ans:
        is_correct = check_correct(user_ans, final_ans)
        # 替換了原本的特殊符號
        print("V 答對" if is_correct else "X 答錯")

    log_record(conn, "custom", "custom", "unknown", q_text, final_ans, user_ans, is_correct, explanation)
    print("已記錄。\n")


def main():
    conn = init_db()
    
    while True:
        print("\n===========================")
        print(" 數學練習系統 V2 (修正版)")
        print("===========================")
        print(" 1. 隨機綜合練習")
        print(" 2. 選擇特定題型練習")
        print(" 3. 自訂題目 (含自動解題)")
        print(" 4. 查看錯題與統計")
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
            show_stats(conn)
            show_recent_wrong(conn)
        elif c == '0':
            print("Bye!")
            break
        else:
            print("無效輸入")

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            # 這是原本為了解決亂碼的程式碼，可能不需要，但保留以防萬一。
            # 核心修正已在程式碼內完成。
            sys.stdout.reconfigure(encoding="utf-8")
        except: pass
    main()