#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命令列版：數學出題 + 解題 + 錯題紀錄系統（強化版）

功能：
1) 系統自動出題（整數四則、分數、帶分數、三分數連加、一次方程）
2) 學生在命令列作答
3) 當場判斷對錯並顯示標準解題步驟
4) 所有紀錄寫入 math_log.db（SQLite）
5) 查看最近 10 題錯題（錯題本）
6) 查看整體與分題型統計
"""

import sqlite3
import random
from fractions import Fraction
from datetime import datetime
import os
import sys

DB_PATH = "math_log.db"

# 嘗試載入 sympy（可選）
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
            topic TEXT,             -- 'integer', 'fraction', 'fraction_mixed', 'fraction_multi', 'equation', 'custom'
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
# 出題邏輯（不靠 LLM）
# =========================

def gen_integer_arith():
    """整數四則運算題（+,-,*,/）"""
    a = random.randint(2, 50)
    b = random.randint(2, 50)
    op = random.choice(["+", "-", "×", "÷"])

    if op == "+":
        ans = a + b
        explanation = [
            f"題目：{a} + {b}",
            "步驟 1：直接相加。",
            f"步驟 2：{a} + {b} = {ans}",
            f"答案：{ans}",
        ]
    elif op == "-":
        if a < b:
            a, b = b, a  # 避免負數
        ans = a - b
        explanation = [
            f"題目：{a} - {b}",
            "步驟 1：較大的數減去較小的數。",
            f"步驟 2：{a} - {b} = {ans}",
            f"答案：{ans}",
        ]
    elif op == "×":
        ans = a * b
        explanation = [
            f"題目：{a} × {b}",
            "步驟 1：把兩個數相乘。",
            f"步驟 2：{a} × {b} = {ans}",
            f"答案：{ans}",
        ]
    else:  # ÷
        # 構造整除
        ans = random.randint(2, 12)
        b = random.randint(2, 12)
        a = ans * b
        explanation = [
            f"題目：{a} ÷ {b}",
            "步驟 1：用被除數除以除數。",
            f"步驟 2：{a} ÷ {b} = {ans}",
            f"答案：{ans}",
        ]

    question = f"{a} {op} {b} = ?"
    return {
        "topic": "integer",
        "difficulty": "easy",
        "question": question,
        "answer": str(ans),
        "explanation": "\n".join(explanation),
    }


def _fraction_core(a1, b1, a2, b2, op):
    """共用的分數加減核心，回傳 result(Fraction) 及解題步驟"""
    f1 = Fraction(a1, b1)
    f2 = Fraction(a2, b2)
    if op == "-":
        if f1 < f2:
            f1, f2 = f2, f1
            a1, b1, a2, b2 = f1.numerator, f1.denominator, f2.numerator, f2.denominator

    if op == "+":
        result = f1 + f2
        op_text = "加法"
    else:
        result = f1 - f2
        op_text = "減法"

    lcm = (b1 * b2) // Fraction(b1, b2).denominator
    m1 = lcm // b1
    m2 = lcm // b2
    na1 = a1 * m1
    na2 = a2 * m2

    if op == "+":
        ns = na1 + na2
        sign_text = "+"
    else:
        ns = na1 - na2
        sign_text = "-"

    explanation_lines = [
        f"步驟 1：這是一題分數{op_text}。",
        f"步驟 2：找共同分母（最小公倍數）：LCM({b1}, {b2}) = {lcm}",
        "步驟 3：通分：",
        f"  {a1}/{b1} = {a1}×{m1}/{b1}×{m1} = {na1}/{lcm}",
        f"  {a2}/{b2} = {a2}×{m2}/{b2}×{m2} = {na2}/{lcm}",
        f"步驟 4：分子相{op_text}：{na1} {sign_text} {na2} = {ns}，得到 {ns}/{lcm}",
        f"步驟 5：將 {ns}/{lcm} 約分，得到 {result.numerator}/{result.denominator}",
    ]
    return result, explanation_lines


def gen_fraction_add():
    """兩個真分數加減題"""
    b1 = random.randint(2, 9)
    b2 = random.randint(2, 9)
    a1 = random.randint(1, b1 - 1)
    a2 = random.randint(1, b2 - 1)
    op = random.choice(["+", "-"])

    result, expl = _fraction_core(a1, b1, a2, b2, op)
    question = f"{a1}/{b1} {op} {a2}/{b2} = ?"
    expl.insert(0, f"題目：{question}")
    expl.append(f"答案：{result.numerator}/{result.denominator}")

    return {
        "topic": "fraction",
        "difficulty": "medium",
        "question": question,
        "answer": f"{result.numerator}/{result.denominator}",
        "explanation": "\n".join(expl),
    }


def gen_fraction_mixed():
    """帶分數加減，例如 1 2/3 + 2 1/4"""
    # 整數部分 1~5，分數部分真分數
    w1 = random.randint(1, 5)
    w2 = random.randint(1, 5)
    b1 = random.randint(2, 9)
    b2 = random.randint(2, 9)
    a1 = random.randint(1, b1 - 1)
    a2 = random.randint(1, b2 - 1)
    op = random.choice(["+", "-"])

    f1 = w1 + Fraction(a1, b1)
    f2 = w2 + Fraction(a2, b2)

    # 用核心函式處理「假分數」部分
    F1 = Fraction(w1 * b1 + a1, b1)
    F2 = Fraction(w2 * b2 + a2, b2)
    result, expl_core = _fraction_core(F1.numerator, F1.denominator, F2.numerator, F2.denominator, op)

    # 結果轉回帶分數
    whole = result.numerator // result.denominator
    remain = result.numerator % result.denominator
    if remain == 0:
        ans_str = f"{whole}"
    else:
        ans_str = f"{whole} {remain}/{result.denominator}"

    question = f"{w1} {a1}/{b1} {op} {w2} {a2}/{b2} = ?"

    explanation_lines = [
        f"題目：{question}",
        "步驟 1：先把帶分數轉成假分數：",
        f"  第一個：{w1} {a1}/{b1} = ( {w1}×{b1} + {a1} ) / {b1} = {F1.numerator}/{F1.denominator}",
        f"  第二個：{w2} {a2}/{b2} = ( {w2}×{b2} + {a2} ) / {b2} = {F2.numerator}/{F2.denominator}",
        "步驟 2：對假分數做加減：",
    ]
    explanation_lines.extend(expl_core[1:])  # 略過核心的標題行
    explanation_lines.append("步驟 3：把結果轉回帶分數：")
    explanation_lines.append(
        f"  {result.numerator}/{result.denominator} = {whole} 又 {remain}/{result.denominator}"
        if remain != 0
        else f"  {result.numerator}/{result.denominator} = {whole}"
    )
    explanation_lines.append(f"答案：{ans_str}")

    return {
        "topic": "fraction_mixed",
        "difficulty": "medium",
        "question": question,
        "answer": ans_str,
        "explanation": "\n".join(explanation_lines),
    }


def gen_fraction_multi_add():
    """三個分數連加 a/b + c/d + e/f"""
    denoms = [random.randint(2, 9) for _ in range(3)]
    nums = [random.randint(1, d - 1) for d in denoms]
    fracs = [Fraction(n, d) for n, d in zip(nums, denoms)]
    result = fracs[0] + fracs[1] + fracs[2]

    question = f"{nums[0]}/{denoms[0]} + {nums[1]}/{denoms[1]} + {nums[2]}/{denoms[2]} = ?"

    explanation_lines = [
        f"題目：{question}",
        "步驟 1：可以先加前兩個分數，再加第三個。",
    ]

    # 前兩個
    intermediate, expl_12 = _fraction_core(
        fracs[0].numerator,
        fracs[0].denominator,
        fracs[1].numerator,
        fracs[1].denominator,
        "+",
    )
    explanation_lines.append("步驟 2：先計算前兩個分數之和：")
    explanation_lines.extend(expl_12[1:])  # 略過 expl_12 的題目標題
    explanation_lines.append(f"得到中間結果：{intermediate.numerator}/{intermediate.denominator}")

    # 中間結果 + 第三個
    final, expl_3 = _fraction_core(
        intermediate.numerator,
        intermediate.denominator,
        fracs[2].numerator,
        fracs[2].denominator,
        "+",
    )
    explanation_lines.append("步驟 3：再加上第三個分數：")
    explanation_lines.extend(expl_3[1:])
    explanation_lines.append(
        f"答案：{final.numerator}/{final.denominator}"
    )

    return {
        "topic": "fraction_multi",
        "difficulty": "hard",
        "question": question,
        "answer": f"{final.numerator}/{final.denominator}",
        "explanation": "\n".join(explanation_lines),
    }


def gen_linear_equation():
    """
    一元一次方程：ax + b = c
    解 x。
    """
    x_val = random.randint(-9, 9)  # 真實解
    a = random.randint(2, 9)
    b = random.randint(-10, 10)
    c = a * x_val + b

    question = f"{a}x + {b} = {c}, 求 x = ?"
    ans_str = str(x_val)

    explanation_lines = [
        f"題目：{question}",
        "步驟 1：把常數項移到等號右邊：",
        f"  {a}x + {b} = {c}",
        f"  {a}x = {c} - {b} = {c - b}",
        "步驟 2：兩邊同除以係數：",
        f"  x = ({c - b}) / {a} = {x_val}",
        f"答案：x = {x_val}",
    ]

    if HAS_SYMPY:
        x = sp.Symbol("x")
        eq = sp.Eq(a * x + b, c)
        sol = sp.solve(eq, x)
        explanation_lines.append("")
        explanation_lines.append("補充：利用 sympy 驗算：")
        explanation_lines.append(f"  解得 x = {sol}")

    return {
        "topic": "equation",
        "difficulty": "medium",
        "question": question,
        "answer": ans_str,
        "explanation": "\n".join(explanation_lines),
    }


def generate_question():
    """
    隨機選一種題型出題。
    若系統沒有 sympy，會自動略過 equation 題型。
    """
    generators = [
        gen_integer_arith,
        gen_fraction_add,
        gen_fraction_mixed,
        gen_fraction_multi_add,
    ]
    if HAS_SYMPY:
        generators.append(gen_linear_equation)

    gen_fn = random.choice(generators)
    return gen_fn()


# =========================
# 答案解析與比對
# =========================
def parse_answer(text: str) -> Fraction | None:
    """將使用者輸入轉成 Fraction（支援整數、小數、a/b）"""
    text = text.strip()
    if not text:
        return None
    # 分數形式
    if "/" in text and " " not in text:
        try:
            return Fraction(text)
        except Exception:
            return None

    # 帶分數形式（例如 "2 3/4"）
    if " " in text and "/" in text:
        try:
            w_part, f_part = text.split()
            f = Fraction(f_part)
            w = int(w_part)
            if w >= 0:
                return w + f
            else:
                return w - f
        except Exception:
            return None

    # 整數或小數
    try:
        if "." in text:
            from decimal import Decimal, getcontext

            getcontext().prec = 10
            return Fraction(Decimal(text))
        else:
            return Fraction(int(text), 1)
    except Exception:
        return None


def check_correct(user: str, correct: str) -> int | None:
    """
    回傳 1=對, 0=錯, None=無法判斷。
    對 Equation 題型，我們一律視「解 x 的數值」來比較。
    """
    u = parse_answer(user)
    c = parse_answer(correct)
    if u is None or c is None:
        return None
    return 1 if u == c else 0


# =========================
# 統計查詢與錯題本
# =========================
def show_stats(conn: sqlite3.Connection):
    cur = conn.cursor()
    total = cur.execute("SELECT COUNT(*) FROM records").fetchone()[0]
    correct = cur.execute(
        "SELECT COUNT(*) FROM records WHERE is_correct = 1"
    ).fetchone()[0]
    wrong = cur.execute(
        "SELECT COUNT(*) FROM records WHERE is_correct = 0"
    ).fetchone()[0]
    print("\n===== 統計概況 =====")
    print(f"總作答題數：{total}")
    print(f"答對：{correct}")
    print(f"答錯：{wrong}")
    if total > 0:
        rate = correct * 100.0 / total
        print(f"整體正確率：約 {rate:.1f}%")

    # 依題型統計
    print("\n按題型統計：")
    topics = cur.execute(
        "SELECT DISTINCT topic FROM records"
    ).fetchall()
    for (topic,) in topics:
        t_total = cur.execute(
            "SELECT COUNT(*) FROM records WHERE topic=?", (topic,)
        ).fetchone()[0]
        if t_total == 0:
            continue
        t_correct = cur.execute(
            "SELECT COUNT(*) FROM records WHERE topic=? AND is_correct=1",
            (topic,),
        ).fetchone()[0]
        t_rate = t_correct * 100.0 / t_total
        print(f"  {topic}: {t_total} 題，正確率 {t_rate:.1f}%")
    print("=====================\n")


def show_recent_wrong(conn: sqlite3.Connection, limit: int = 10):
    """顯示最近 N 題錯題（錯題本）"""
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT ts, topic, difficulty, question, correct_answer, user_answer
        FROM records
        WHERE is_correct = 0
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    print("\n===== 最近錯題列表（最多顯示 {0} 題） =====".format(limit))
    if not rows:
        print("目前沒有錯題紀錄。")
    else:
        for idx, (ts, topic, diff, q, ca, ua) in enumerate(rows, start=1):
            print("------------------------------")
            print(f"第 {idx} 題")
            print(f"時間：{ts}")
            print(f"題型：{topic} / 難度：{diff}")
            print(f"題目：{q}")
            print(f"正確答案：{ca}")
            print(f"你的答案：{ua}")
    print("========================================\n")


# =========================
# 互動主迴圈
# =========================
def practice_auto(conn: sqlite3.Connection):
    """模式 1：系統自動出題，學生作答"""
    qobj = generate_question()
    print("\n=== 自動出題 ===")
    print(f"題目：{qobj['question']}")
    print("請輸入你的答案（例如：12, 3/4, 0.75, 2 1/3），或輸入 's' 跳過：")

    user = input("你的答案 = ").strip()
    if user.lower() == "s":
        print("已跳過本題。\n")
        log_record(
            conn,
            mode="auto",
            topic=qobj["topic"],
            difficulty=qobj["difficulty"],
            question=qobj["question"],
            correct_answer=qobj["answer"],
            user_answer="(skipped)",
            is_correct=None,
            explanation=qobj["explanation"],
        )
        return

    is_correct = check_correct(user, qobj["answer"])

    print("\n=== 解題結果 ===")
    if is_correct == 1:
        print("結果：答對了！")
    elif is_correct == 0:
        print("結果：答錯了。")
    else:
        print("結果：無法自動判斷（格式無法解析）。")

    print("\n【標準解答步驟】")
    print(qobj["explanation"])
    print()

    log_record(
        conn,
        mode="auto",
        topic=qobj["topic"],
        difficulty=qobj["difficulty"],
        question=qobj["question"],
        correct_answer=qobj["answer"],
        user_answer=user,
        is_correct=is_correct,
        explanation=qobj["explanation"],
    )


def custom_question(conn: sqlite3.Connection):
    """模式 2：老師/學生自輸題目，只記錄，不自動解"""
    print("\n=== 自訂題目記錄 ===")
    q = input("請輸入題目內容（空行取消）：").strip()
    if not q:
        print("已取消。\n")
        return
    ans = input("若你知道標準答案，可輸入（可留空）：").strip()
    user = input("學生/你的作答（可留空）：").strip()

    is_correct = None
    if ans and user:
        is_correct = check_correct(user, ans)

    log_record(
        conn,
        mode="custom",
        topic="custom",
        difficulty="unknown",
        question=q,
        correct_answer=ans,
        user_answer=user,
        is_correct=is_correct,
        explanation="(custom question, no system solution)",
    )
    print("已記錄自訂題目與作答。\n")


def main():
    conn = init_db()
    print("===================================")
    print("命令列版 AI 數學練習 / 錯題紀錄（不開瀏覽器）")
    print("===================================\n")
    if HAS_SYMPY:
        print("提示：已偵測到 sympy，可出一次方程題目。")
    else:
        print("提示：未安裝 sympy，目前一次方程題目由內建邏輯處理。")

    while True:
        print("請選擇功能：")
        print("  1) 練習一題（系統自動出題）")
        print("  2) 自己輸入題目（只做紀錄）")
        print("  3) 查看最近 10 題錯題（錯題本）")
        print("  4) 查看作答統計")
        print("  0) 離開")
        choice = input("輸入選項：").strip()

        if choice == "1":
            practice_auto(conn)
        elif choice == "2":
            custom_question(conn)
        elif choice == "3":
            show_recent_wrong(conn, limit=10)
        elif choice == "4":
            show_stats(conn)
        elif choice == "0":
            print("結束，謝謝使用。")
            break
        else:
            print("無效選項，請重新輸入。\n")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass
    main()
