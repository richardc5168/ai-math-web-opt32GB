#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import random
from fractions import Fraction
from datetime import datetime
import os
import sys
import re
import math

# 啟動檢測：如果看到這一行，代表程式有成功跑起來
print("正在初始化系統，請稍候...")

# =========================
# ANSI 顏色定義
# =========================
class Colors:
    GOLD = '\033[38;2;218;165;32m' 
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'

# =========================
# 數據庫初始化 (修復之前的 NameError)
# =========================
DB_PATH = "math_learning_log.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
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
    """)
    conn.commit()
    return conn

def log_record(conn, mode, topic, difficulty, question, correct_answer, user_answer, is_correct, explanation):
    ts = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        "INSERT INTO records (ts, mode, topic, difficulty, question, correct_answer, user_answer, is_correct, explanation) VALUES (?,?,?,?,?,?,?,?,?)",
        (ts, mode, topic, difficulty, question, correct_answer, user_answer, is_correct, explanation)
    )
    conn.commit()

# =========================
# 智慧建議與教學內容
# =========================
def get_smart_hint(topic):
    hints = {
        "四則運算 (順序)": "💡 祕訣：『括號』最先，『乘除』其次，最後才做『加減』。由左往右算！",
        "百分比與折數": "💡 祕訣：打 8 折就是 ×0.8，打 75 折就是 ×0.75。10% off 就是打 9 折。",
        "時間換算": "💡 祕訣：記得！時間是 60 進位。1 小時 = 60 分鐘，不是 100 分鐘喔！",
        "分數通分": "💡 祕訣：找出分母的最小公倍數，分母變大幾倍，分子也要跟著變大幾倍。"
    }
    return hints.get(topic, "💡 建議：仔細再看一次詳解步驟，找出錯誤的小地方。")

# =========================
# 題目產生器
# =========================
def gen_order_of_ops():
    a, b, c = random.randint(10, 50), random.randint(2, 9), random.randint(2, 9)
    q = f"{a} + {b} × {c} = ?"
    ans = a + (b * c)
    return {"topic": "四則運算 (順序)", "difficulty": "medium", "question": q, "answer": str(ans), "explanation": f"依照運算順序，要先算 {b}×{c}={b*c}，再加上 {a}，所以答案是 {ans}。"}

def gen_ratio_percentage():
    price = random.randint(10, 50) * 20
    off_pct = random.choice([10, 20, 25, 30])
    discount = 100 - off_pct
    ans = int(price * discount / 100)
    q = f"原價 {price} 元的衣服，打 {discount/10:g} 折後是多少元？"
    return {"topic": "百分比與折數", "difficulty": "medium", "question": q, "answer": str(ans), "explanation": f"打折計算：{price} × {discount}% = {ans}。"}

def gen_time_conv():
    h = random.randint(1, 4)
    m = random.randint(1, 59)
    ans = h * 60 + m
    q = f"{h} 小時 {m} 分鐘等於多少分鐘？"
    return {"topic": "時間換算", "difficulty": "easy", "question": q, "answer": str(ans), "explanation": f"{h} 小時等於 {h}×60={h*60} 分，加上原本的 {m} 分，總共 {ans} 分。"}

GENERATORS = {
    "1": ("四則運算練習", gen_order_of_ops),
    "2": ("百分比與折數", gen_ratio_percentage),
    "3": ("時間單位換算", gen_time_conv)
}

# =========================
# 主程式邏輯
# =========================
def show_report(conn):
    cur = conn.cursor()
    data = cur.execute("SELECT topic, COUNT(*), SUM(is_correct) FROM records WHERE is_correct IS NOT NULL GROUP BY topic").fetchall()
    
    print(f"\n{Colors.GOLD}--- 📊 學習進度與計畫 ---{Colors.END}")
    if not data:
        print("目前還沒有作答紀錄喔！先去練習幾題吧。")
        return

    weak_topics = []
    for topic, total, correct in data:
        acc = (correct / total * 100)
        status = "✅ 優秀" if acc >= 80 else "⚠️ 需注意"
        print(f"[{topic}] 練習: {total} | 正確: {correct} | 正確率: {acc:.1f}% -> {status}")
        if acc < 75: weak_topics.append(topic)
    
    if weak_topics:
        print(f"\n{Colors.YELLOW}【下週改進計畫建議】{Colors.END}")
        for t in weak_topics:
            print(f" • {t}: {get_smart_hint(t)}")
    else:
        print(f"\n{Colors.GREEN}太棒了！目前的觀念都很穩固，請繼續保持。{Colors.END}")

def practice(conn, tid=None):
    gen_func = GENERATORS[tid][1] if tid in GENERATORS else random.choice(list(GENERATORS.values()))[1]
    qobj = gen_func()
    
    print(f"\n{Colors.YELLOW}題目：{qobj['question']}{Colors.END}")
    user = input("請輸入答案 (s 跳過): ").strip()
    if user.lower() == 's': return

    is_correct = 1 if user == qobj["answer"] else 0
    if is_correct:
        print(f"{Colors.GREEN}🎉 答對了！你真棒！{Colors.END}")
    else:
        print(f"{Colors.RED}❌ 可惜答錯了。標準答案是：{qobj['answer']}{Colors.END}")
        print(f"{Colors.YELLOW}{get_smart_hint(qobj['topic'])}{Colors.END}")
        print(f"別擔心，看不懂的話週三或六日可以問阿爸喔！")

    print(f"\n{Colors.BLUE}[詳解]{Colors.END}\n{qobj['explanation']}")
    log_record(conn, "auto", qobj['topic'], "medium", qobj['question'], qobj['answer'], user, is_correct, qobj['explanation'])

def main():
    conn = init_db()
    while True:
        print(f"\n{Colors.GOLD}==============================={Colors.END}")
        print(f"   數學練習系統 V15.1 智慧版")
        print(f"==============================={Colors.END}")
        print(" 1. 隨機綜合練習")
        print(" 2. 選擇特定題型")
        print(" 3. 查看分析報告與改進計畫")
        print(" 0. 離開程式")
        
        choice = input("\n請選擇功能 (0-3): ").strip()
        
        if choice == '1':
            practice(conn)
        elif choice == '2':
            for k, v in GENERATORS.items(): print(f"  {k}. {v[0]}")
            practice(conn, input("請輸入題型代號: ").strip())
        elif choice == '3':
            show_report(conn)
        elif choice == '0':
            print("再見！下次再一起練習數學！")
            break
        else:
            print("輸入無效，請重新選擇。")

# 確保程式會執行 main()
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"系統發生錯誤：{e}")
        input("按 Enter 鍵結束...")