#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命令列版：數學練習系統（V12.0 智慧導師版）
新增功能：
1. 智慧導師建議：根據錯題類型提供具體解題心法。
2. 新增題型：比率與百分比、時間單位換算。
3. 學習改進計畫：在分析報告中自動生成針對性建議。
4. 結構強化：模組化建議邏輯，保持原有暖色系介面。
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
# 全局變數
# =========================
TOTAL_COUNT = 0
CORRECT_COUNT = 0
DB_PATH = "math_log_v12.db"

try:
    import sympy as sp
    HAS_SYMPY = True
except ImportError:
    HAS_SYMPY = False

# =========================
# 智慧型回饋邏輯 (V12.0 核心)
# =========================

def get_smart_hint(topic):
    """根據不同題型提供專屬的『診斷式提醒』"""
    hints = {
        "四則運算 (順序)": "💡 檢查看看：是不是先做了加減法？記得『先乘除後加減』，括號要最先處理喔！",
        "分數通分": "💡 核心提醒：通分找的是『最小公倍數』。檢查一下分母變大幾倍，分子也要跟著變大幾倍！",
        "分數約分": "💡 核心提醒：找找看分子分母有沒有『公因數』？試試看用 2, 3, 5 來除除看。",
        "分數加減": "💡 檢查點：分母不同時不能直接加減！必須先通分。相加後記得看看能不能約分喔。",
        "帶分數運算": "💡 小撇步：把帶分數變成『假分數』再來計算，通常會簡單很多！",
        "GCD/LCM": "💡 診斷建議：短除法是你的好幫手。左側全部相乘是 GCD，左側加下方全部相乘是 LCM。",
        "百分比與折數": "💡 核心概念：『折』是 1/10，『%』是 1/100。定價 × 折數 = 售價喔！",
        "時間換算": "💡 提醒：時間是『60 進位』不是 100 進位！1 小時 = 60 分鐘，別算錯囉。"
    }
    return hints.get(topic, "💡 建議：再仔細看一遍題目要求，或許答案就在細節裡。")

# =========================
# 數學出題邏輯 (新增題型)
# =========================

def gen_ratio_percentage():
    """比率與百分比練習 (新增)"""
    original_price = random.randint(1, 20) * 100
    discount_off = random.choice([10, 20, 25, 30, 50, 75]) # 幾 % off
    # 換算成折數
    discount_rate = (100 - discount_off)
    ans = int(original_price * (discount_rate / 100))
    
    q_type = random.choice(["percent", "discount"])
    if q_type == "percent":
        question = f"商品原價 {original_price} 元，打 {discount_rate} 折後的售價是多少元？"
        topic = "百分比與折數"
    else:
        question = f"商品原價 {original_price} 元，若提供 {discount_off}% 的折扣 (off)，售價是多少元？"
        topic = "百分比與折數"
        
    explanation = [
        f"步驟 1: 理解折扣意義。打 {discount_rate} 折代表售價是原價的 {discount_rate}%。",
        f"  -> 計算式: {original_price} × {discount_rate}/100",
        f"步驟 2: 執行計算: {original_price} × {discount_rate/100:.2f} = {ans}",
        f"最終答案: {ans} 元"
    ]
    return {
        "topic": topic, "difficulty": "medium", "question": question,
        "answer": str(ans), "explanation": "\n".join(explanation)
    }

def gen_time_conversion():
    """時間單位換算 (新增)"""
    hours = random.randint(1, 5)
    minutes = random.randint(1, 55)
    total_minutes = hours * 60 + minutes
    
    q_type = random.choice(["to_min", "to_hour_min"])
    if q_type == "to_min":
        question = f"{hours} 小時 {minutes} 分鐘等於多少分鐘？"
        ans = str(total_minutes)
        expl = f"計算: ({hours} × 60) + {minutes} = {total_minutes} 分鐘。"
    else:
        question = f"{total_minutes} 分鐘等於幾小時幾分鐘？\n請依序輸入：小時 分鐘"
        ans = f"{hours} {minutes}"
        expl = f"計算: {total_minutes} ÷ 60 = {hours} 餘 {minutes}。所以是 {hours} 小時 {minutes} 分鐘。"
        
    return {
        "topic": "時間換算", "difficulty": "easy", "question": question,
        "answer": ans, "explanation": expl
    }

# --- 舊有題型整合 (略，保持原有函數) ---
# [gen_order_of_ops_arith, gen_fraction_commondenom, gen_fraction_reduction, 
#  gen_fraction_add, gen_fraction_mixed, gen_gcd_lcm, gen_decimal_arith, gen_volume_area]

# =========================
# 學習改進計畫系統
# =========================

def generate_learning_plan(topic_stats):
    """根據統計數據生成學習改進計畫"""
    plan = []
    weak_topics = [t for t, total, acc in topic_stats if acc < 75 and total >= 3]
    mastered_topics = [t for t, total, acc in topic_stats if acc >= 90 and total >= 5]
    
    plan.append(f"\n{Colors.BLUE}┌────────────────學習改進建議────────────────┐{Colors.END}")
    
    if not weak_topics and not mastered_topics:
        plan.append(f"│ 目前數據尚不足，請繼續完成更多練習以利診斷。 │")
    
    if weak_topics:
        plan.append(f"│ {Colors.RED}針對性加強：{Colors.END}                                 │")
        for topic in weak_topics[:2]:
            plan.append(f"│ • {topic.ljust(15)} : 建議回到課本重新複習基本概念。 │")
            plan.append(f"│   {get_smart_hint(topic).ljust(40)} │")
            
    if mastered_topics:
        plan.append(f"│ {Colors.GREEN}優勢保持：{Colors.END}                                   │")
        for topic in mastered_topics[:1]:
            plan.append(f"│ • {topic.ljust(15)} : 表現優異！可嘗試更高難度。   │")

    plan.append(f"│ {Colors.YELLOW}每日目標：{Colors.END} 建議每日練習 10 題，保持手感。      │")
    plan.append(f"{Colors.BLUE}└────────────────────────────────────────────┘{Colors.END}")
    return "\n".join(plan)

# =========================
# 修改後的分析報告
# =========================

def show_analysis_report(conn: sqlite3.Connection):
    cur = conn.cursor()
    query = """
    SELECT topic, COUNT(*), SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END)
    FROM records WHERE is_correct IS NOT NULL GROUP BY topic
    """
    topic_data = cur.execute(query).fetchall()
    
    stats_for_plan = []
    print(f"\n{Colors.GOLD}📊 深度學習分析報告{Colors.END}")
    print("-" * 60)
    print(f"{'主題':<15} | {'題數':<5} | {'正確率':<8} | {'狀況'}")
    
    for topic, total, correct in topic_data:
        acc = (correct / total) * 100
        stats_for_plan.append((topic, total, acc))
        status = f"{Colors.GREEN}優良{Colors.END}" if acc >= 85 else f"{Colors.YELLOW}尚可{Colors.END}"
        if acc < 70: status = f"{Colors.RED}需加強{Colors.END}"
        print(f"{topic:<15} | {total:<5} | {acc:>6.1f}% | {status}")
    
    # 顯示改進計畫
    print(generate_learning_plan(stats_for_plan))

# =========================
# 核心出題映射 (更新版)
# =========================

GENERATORS = {
    "1": ("四則運算 (順序)", None), # 這裡會填入對應函數
    "2": ("分數通分", None),
    "3": ("分數約分", None),
    "4": ("分數加減", None),
    "5": ("帶分數運算", None),
    "6": ("GCD/LCM", None),
    "7": ("百分比與折數", gen_ratio_percentage), # 新增
    "8": ("時間換算", gen_time_conversion),      # 新增
}

# (註：開發時請將原本的 gen 函數填入上方 None 位置)

# =========================
# 修改後的 practice_auto
# =========================

def practice_auto(conn: sqlite3.Connection, topic_key=None):
    # 此處假設 get_random_generator 已更新包含新增題型
    # ... 原有邏輯 ...
    # 在答錯時：
    # if is_correct == 0:
    #     print(f"{Colors.RED}❌ 答案不對。標準答案是：{qobj['answer']}{Colors.END}")
    #     print(f"{Colors.YELLOW}{get_smart_hint(qobj['topic'])}{Colors.END}")
    #     print(f"{Colors.YELLOW}若還是不通，先問媽，帥爸週三/六日上線。{Colors.END}")
    pass

# --- 以下代碼為示意，將原有功能與新結構縫合 ---
# (為了節省空間，這裡不重複貼出所有的 gen_* 函數，但應保留在您的腳本中)