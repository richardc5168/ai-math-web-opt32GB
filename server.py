#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MVP Backend: 多學生 + 訂閱 gate + 出題/交卷/報表
- Auth(暫定MVP): X-API-Key 對應 account
- DB: sqlite (上線改 Postgres 很容易)
- Engine: 直接 import 你現有的出題/判題函式

啟動:
  pip install fastapi uvicorn
  python3 server.py
或:
  uvicorn server:app --reload --port 8000
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

# ========= 1) 這裡接你的 engine =========
# 建議你把 math_cli.py 中的：
# - GENERATORS / get_random_generator / check_correct / gen_* / show_analysis_report(改成回傳結構)
# 抽成 engine.py
#
# 這裡示範用「函式名」呼叫，你只要確保 engine.py 有以下 API:
#   engine.next_question(topic_key: Optional[str]) -> dict {topic,difficulty,question,answer,explanation}
#   engine.check(user_answer: str, correct_answer: str) -> int|None
#
try:
    import engine  # 你要新增 engine.py
except Exception:
    engine = None

DB_PATH = os.environ.get("DB_PATH", "app.db")

app = FastAPI(title="Math Practice MVP API", version="0.1")

# ========= 2) DB =========
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
        question_id INTEGER,
        mode TEXT NOT NULL DEFAULT 'interactive',
        topic TEXT,
        difficulty TEXT,
        question TEXT,
        correct_answer TEXT,
        user_answer TEXT,
        is_correct INTEGER,                 -- 1/0/NULL
        time_spent_sec INTEGER DEFAULT 0,
        ts TEXT NOT NULL,
        FOREIGN KEY(account_id) REFERENCES accounts(id),
        FOREIGN KEY(student_id) REFERENCES students(id),
        FOREIGN KEY(question_id) REFERENCES question_cache(id)
    )
    """)

    conn.commit()
    conn.close()

init_db()


# Ensure DB is initialized on FastAPI startup (helps TestClient and other runtimes)
@app.on_event("startup")
def _startup_init_db():
    try:
        init_db()
    except Exception:
        pass

# ========= 3) Auth + Subscription Gate =========
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

# ========= 4) Helper: JSON =========
def now_iso():
    return datetime.now().isoformat(timespec="seconds")

def row_to_dict(r: sqlite3.Row) -> Dict[str, Any]:
    return {k: r[k] for k in r.keys()}

# ========= 5) API =========
@app.get("/health")
def health():
    return {"ok": True, "ts": now_iso()}

@app.post("/admin/bootstrap")
def admin_bootstrap(name: str = "Richard-Account"):
    """
    MVP 用：建立一個 account + 一個 active 訂閱 + 一個學生，回傳 api_key
    上線後這段要拿掉，改 Stripe webhook + 正式登入。
    """
    import secrets
    api_key = secrets.token_urlsafe(24)

    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO accounts(name, api_key, created_at) VALUES (?,?,?)",
                (name, api_key, now_iso()))
    account_id = cur.lastrowid

    # 預設一個 active 訂閱（MVP 方便測）
    cur.execute("""INSERT INTO subscriptions(account_id,status,plan,seats,current_period_end,updated_at)
                   VALUES (?,?,?,?,?,?)""",
                (account_id, "active", "basic", 3,
                 (datetime.now() + timedelta(days=30)).isoformat(timespec="seconds"),
                 now_iso()))

    # 預設學生
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
    return {"students": [row_to_dict(r) for r in rows]}

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
def next_question(student_id: int,
                  topic_key: Optional[str] = None,
                  x_api_key: str = Header(..., alias="X-API-Key")):
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])

    if engine is None:
        raise HTTPException(status_code=500, detail="engine.py not found. Please create engine.py and expose next_question().")

    # 驗證 student 屬於此 account
    conn = db()
    st = conn.execute("SELECT * FROM students WHERE id=? AND account_id=?", (student_id, acc["id"])).fetchone()
    conn.close()
    if not st:
        raise HTTPException(status_code=404, detail="Student not found")

    q = engine.next_question(topic_key)  # {topic,difficulty,question,answer,explanation}

    conn = db()
    cur = conn.cursor()
    cur.execute("""INSERT INTO question_cache(topic,difficulty,question,correct_answer,explanation,created_at)
                   VALUES (?,?,?,?,?,?)""",
                (q["topic"], q["difficulty"], q["question"], q["answer"], q["explanation"], now_iso()))
    qid = cur.lastrowid
    conn.commit()
    conn.close()

    # 注意：前端拿到 qid，但不直接拿 answer（避免作弊）
    return {
        "question_id": qid,
        "topic": q["topic"],
        "difficulty": q["difficulty"],
        "question": q["question"],
        "explanation_preview": "（交卷後顯示）"
    }

@app.post("/v1/answers/submit")
async def submit_answer(request: Request, x_api_key: str = Header(..., alias="X-API-Key")):
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

    if engine is None:
        raise HTTPException(status_code=500, detail="engine.py not found. Please create engine.py and expose check().")

    body = await request.json()
    student_id = int(body["student_id"])
    question_id = int(body["question_id"])
    user_answer = str(body.get("user_answer", "")).strip()
    time_spent = int(body.get("time_spent_sec", 0))

    conn = db()
    st = conn.execute("SELECT * FROM students WHERE id=? AND account_id=?", (student_id, acc["id"])).fetchone()
    if not st:
        conn.close()
        raise HTTPException(status_code=404, detail="Student not found")

    q = conn.execute("SELECT * FROM question_cache WHERE id=?", (question_id,)).fetchone()
    if not q:
        conn.close()
        raise HTTPException(status_code=404, detail="Question not found")
    is_correct = engine.check(user_answer, q["correct_answer"])  # 1/0/None

    conn.execute("""INSERT INTO attempts(account_id, student_id, question_id, mode, topic, difficulty,
                    question, correct_answer, user_answer, is_correct, time_spent_sec, ts)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                 (acc["id"], student_id, question_id, 'interactive', q["topic"], q["difficulty"],
                  q["question"], q["correct_answer"], user_answer, is_correct, time_spent, now_iso()))
    conn.commit()
    conn.close()

    # 回傳詳解與結果（你現有 INCORRECT_CUSTOM_FEEDBACK 可在前端呈現）
    return {
        "is_correct": is_correct,
        "correct_answer": q["correct_answer"],
        "explanation": q["explanation"],
        "topic": q["topic"],
        "difficulty": q["difficulty"]
    }


@app.post("/v1/custom/solve")
async def custom_solve(request: Request, x_api_key: str = Header(..., alias="X-API-Key")):
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])

    if engine is None:
        raise HTTPException(status_code=500, detail="engine.py not found. Please create engine.py and expose solve_custom().")

    body = await request.json()
    q = body.get("question")
    if not q:
        raise HTTPException(status_code=400, detail="Missing question in body")

    ans, expl = engine.solve_custom(q)
    return {"final_answer": ans, "explanation": expl}

@app.get("/v1/reports/summary")
def report_summary(student_id: int, days: int = 30, x_api_key: str = Header(..., alias="X-API-Key")):
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])

    since = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")

    conn = db()
    st = conn.execute("SELECT * FROM students WHERE id=? AND account_id=?", (student_id, acc["id"])).fetchone()
    if not st:
        conn.close()
        raise HTTPException(status_code=404, detail="Student not found")

    # 總覽
    totals = conn.execute("""
        SELECT
          SUM(CASE WHEN is_correct IN (0,1) THEN 1 ELSE 0 END) AS valid_total,
          SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) AS correct,
          SUM(CASE WHEN is_correct = 0 THEN 1 ELSE 0 END) AS wrong,
          SUM(CASE WHEN is_correct IS NULL THEN 1 ELSE 0 END) AS invalid
        FROM attempts
        WHERE student_id = ? AND ts >= ?
    """, (student_id, since)).fetchone()

    # 主題分類
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

    # 最近錯題
    wrongs = conn.execute("""
        SELECT ts, topic, question, correct_answer, user_answer
        FROM attempts
        WHERE student_id = ? AND ts >= ? AND is_correct = 0
        ORDER BY ts DESC
        LIMIT 20
    """, (student_id, since)).fetchall()

    conn.close()

    valid_total = int(totals["valid_total"] or 0)
    correct = int(totals["correct"] or 0)
    acc_rate = (correct / valid_total * 100.0) if valid_total else 0.0

    return {
        "student": {"id": st["id"], "display_name": st["display_name"], "grade": st["grade"]},
        "window_days": days,
        "summary": {
            "valid_total": valid_total,
            "correct": correct,
            "wrong": int(totals["wrong"] or 0),
            "invalid": int(totals["invalid"] or 0),
            "accuracy": round(acc_rate, 2)
        },
        "topics": [dict(r) for r in topics],
        "recent_wrongs": [dict(r) for r in wrongs]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), reload=True)
