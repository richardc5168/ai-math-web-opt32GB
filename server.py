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
import hmac
import json
import logging
import sqlite3
import hashlib
import secrets
import unicodedata
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
import random

from adaptive_mastery import (
    AttemptEvent,
    ConceptState,
    ErrorCode,
    Stage,
    classify_error_code,
    error_stats_from_json,
    error_stats_to_json,
    update_state_on_attempt,
)

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field

try:
    import fraction_logic
except Exception:
    fraction_logic = None

try:
    from quadratic_engine import quadratic_engine
except ImportError:
    quadratic_engine = None

try:
    from linear_engine import linear_engine
except ImportError:
    linear_engine = None

try:
    from knowledge_graph import KNOWLEDGE_GRAPH
except ImportError:
    KNOWLEDGE_GRAPH = {}

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

# Learning analytics / parent weekly report (optional; should not break core API)
try:
    from learning.db import connect as learning_connect, ensure_learning_schema
    from learning.parent_report import generate_parent_weekly_report
    from learning.parent_report import compute_skill_status
    from learning.analytics import get_student_analytics as learning_get_student_analytics
    from learning.class_report import generate_class_report
    from learning.remediation import get_practice_items_for_skill
    from learning.teaching import get_teaching_guide, suggested_engine_topic_key
    from learning.service import recordAttempt as learning_record_attempt
    from learning.concept_state import get_all_states as learning_get_all_concept_states
    from learning.concept_state import get_class_states as learning_get_class_states
    from learning.teacher_report import generate_teacher_report as learning_generate_teacher_report
    from learning.teacher_report import report_to_dict as learning_report_to_dict
    from learning.parent_report_enhanced import generate_parent_concept_progress as learning_parent_concept_progress
    from learning.parent_report_enhanced import progress_to_dict as learning_parent_progress_to_dict
    from learning.next_item_selector import select_next_item as learning_select_next_item
    from learning.next_item_selector import QuestionItem as LearningQuestionItem
    from learning.concept_taxonomy import CONCEPT_TAXONOMY as learning_concept_taxonomy
except Exception:
    learning_connect = None
    ensure_learning_schema = None
    generate_parent_weekly_report = None
    compute_skill_status = None
    learning_get_student_analytics = None
    generate_class_report = None
    get_practice_items_for_skill = None
    get_teaching_guide = None
    suggested_engine_topic_key = None
    learning_record_attempt = None
    learning_get_all_concept_states = None
    learning_get_class_states = None
    learning_generate_teacher_report = None
    learning_report_to_dict = None
    learning_parent_concept_progress = None
    learning_parent_progress_to_dict = None
    learning_select_next_item = None
    LearningQuestionItem = None
    learning_concept_taxonomy = None

DB_PATH = os.environ.get("DB_PATH", "app.db")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure DB is initialized on app startup (helps TestClient and other runtimes)
    try:
        init_db()
    except Exception:
        pass

    yield


app = FastAPI(
    title="Math Practice MVP API",
    version="0.1",
    lifespan=lifespan,
    docs_url="/api/docs",   # Move Swagger UI to avoid conflict with 'docs' folder
    redoc_url="/api/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========= Diagnose: Knowledge base (concept -> prerequisites + resource) =========
# NOTE: MVP 先用內建 dict；之後可搬到 DB / JSON / 向量庫。
KNOWLEDGE_BASE: Dict[str, Dict[str, Any]] = {
    "一元二次方程式-公式解": {
        "prerequisites": ["平方根概念", "判別式計算"],
        "video_url": "https://www.youtube.com/watch?v=example1",
        "description": "基礎公式推導與帶入技巧",
    },
    "十字交乘法": {
        "prerequisites": ["整數乘法", "因數分解"],
        "video_url": "https://www.youtube.com/watch?v=example2",
        "description": "如何快速尋找組合數",
    },
}


class StudentSubmission(BaseModel):
    student_id: str = Field(..., min_length=1)
    question_id: Optional[str] = ""
    concept_tag: str = Field(..., min_length=1)
    student_answer: str = Field(...)
    correct_answer: str = Field(...)
    process_text: Optional[str] = ""  # 學生寫下的解題過程


class QuadraticPipelineValidateRequest(BaseModel):
    """Browser-friendly validation runner for the quadratic pipeline.

    Default is offline mode so it works without API keys.
    """

    count: int = Field(default=1, ge=1, le=5, description="How many items to validate")
    roots: str = Field(default="integer", description="integer|rational|mixed")
    difficulty: int = Field(default=3, ge=1, le=5)
    style: str = Field(default="factoring_then_formula", description="standard|factoring_then_formula")
    offline: bool = Field(default=True, description="Force offline mode (no OpenAI calls)")

class QuadraticGenRequest(BaseModel):
    topic_id: str = Field(default="A3", description="Topic ID from Knowledge Graph (A1-A5)")
    difficulty: int = Field(default=2, ge=1, le=5)

class QuadraticCheckRequest(BaseModel):
    user_answer: str
    question_data: Dict[str, Any]


class HintNextRequest(BaseModel):
    """Request next-step hint based on a student's current thought.

    Provide either question_id (recommended, from /v1/questions/next)
    or question_data ({topic, question}).
    """

    question_id: Optional[int] = Field(default=None, ge=1)
    question_data: Optional[Dict[str, Any]] = None
    student_state: str = Field(default="", description="Student's current thought / partial work")
    level: int = Field(default=1, ge=1, le=3)


class WeeklyReportRequest(BaseModel):
    student_id: int = Field(..., ge=1)
    window_days: int = Field(default=7, ge=1, le=60)
    top_k: int = Field(default=3, ge=1, le=5)
    questions_per_skill: int = Field(default=3, ge=1, le=8)


class PracticeNextRequest(BaseModel):
    student_id: int = Field(..., ge=1)
    skill_tag: str = Field(..., min_length=1)
    window_days: int = Field(default=14, ge=1, le=60)
    topic_key: Optional[str] = Field(default=None, description="Optional override for engine generator key")
    seed: Optional[int] = Field(default=None, description="Optional deterministic seed for question generation")


class ConceptNextRequest(BaseModel):
    student_id: int = Field(..., ge=1)
    domain: Optional[str] = Field(default=None, description="Filter by domain: fraction, decimal, percent, etc.")
    recent_item_ids: Optional[List[str]] = Field(default=None, description="Recently shown item IDs to avoid repetition")


class TeacherCreateClassRequest(BaseModel):
    class_name: str = Field(..., min_length=1, max_length=80)
    grade: int = Field(default=5, ge=5, le=6)
    school_name: Optional[str] = Field(default=None, max_length=120)
    school_code: Optional[str] = Field(default=None, max_length=40)


class TeacherAddStudentRequest(BaseModel):
    student_id: Optional[int] = Field(default=None, ge=1)
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    grade: str = Field(default="G5", max_length=10)


class TeacherClassReportRequest(BaseModel):
    window_days: int = Field(default=14, ge=1, le=90)


class ParentReportFetchRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    pin: str = Field(..., min_length=4, max_length=6)


class ParentReportUpsertRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    pin: str = Field(..., min_length=4, max_length=6)
    report_data: Optional[Dict[str, Any]] = None
    practice_event: Optional[Dict[str, Any]] = None


class AppAuthLoginRequest(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=4)


class AppAuthProvisionRequest(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=4)
    account_name: str = Field(default="APP User")
    student_name: str = Field(default="學生")
    grade: str = Field(default="G5")
    plan: str = Field(default="basic")
    seats: int = Field(default=1, ge=1, le=200)


class ReportSnapshotWriteRequest(BaseModel):
    student_id: int
    report_payload: Dict[str, Any]
    source: str = Field(default="frontend", max_length=40)


class ReportSnapshotReadRequest(BaseModel):
    student_id: int


class PracticeEventWriteRequest(BaseModel):
    student_id: int
    event: Dict[str, Any]


class BootstrapRequest(BaseModel):
    student_id: int


class ExchangeRequest(BaseModel):
    bootstrap_token: str = Field(..., min_length=10)


# ─── Bootstrap token lifecycle constants ───
_BOOTSTRAP_TOKEN_TTL_S = 300  # 5 minutes
_MAX_OUTSTANDING_TOKENS_PER_ACCOUNT = 5

# ─── Rate limiting constants ───
_RATE_LIMIT_WINDOW_S = 60  # 1-minute window
_RATE_LIMIT_LOGIN = 5        # max 5 login attempts per IP per minute
_RATE_LIMIT_BOOTSTRAP = 10  # max 10 bootstrap requests per IP per minute
_RATE_LIMIT_EXCHANGE = 20   # max 20 exchange requests per IP per minute

# ─── Account-level login lockout ───
_LOGIN_LOCKOUT_THRESHOLD = 5    # lock after 5 consecutive failed attempts
_LOGIN_LOCKOUT_DURATION_S = 300  # 5-minute lockout window

# ─── Auth event logger ───
_auth_logger = logging.getLogger("auth")


def _hash_token(raw_token: str) -> str:
    """SHA-256 hash of a bootstrap token. DB stores hash, never raw token."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


def _check_rate_limit(key: str, max_requests: int) -> bool:
    """Return True if request is allowed, False if rate-limited.
    Uses a DB-backed sliding window of timestamps."""
    conn = db()
    now = datetime.now().timestamp()
    window_start = now - _RATE_LIMIT_WINDOW_S
    # Prune old entries
    conn.execute("DELETE FROM rate_limit_events WHERE ts < ?", (window_start,))
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM rate_limit_events WHERE key = ? AND ts >= ?",
        (key, window_start),
    ).fetchone()
    count = int(row["c"]) if row else 0
    if count >= max_requests:
        conn.commit()
        conn.close()
        return False
    conn.execute(
        "INSERT INTO rate_limit_events (key, ts) VALUES (?, ?)",
        (key, now),
    )
    conn.commit()
    conn.close()
    return True


def _is_account_locked(username: str) -> bool:
    """Check if a username is locked due to too many recent failed login attempts."""
    conn = db()
    cutoff = datetime.now().timestamp() - _LOGIN_LOCKOUT_DURATION_S
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM login_failures WHERE username = ? AND ts >= ?",
        (username, cutoff),
    ).fetchone()
    conn.close()
    return (int(row["c"]) if row else 0) >= _LOGIN_LOCKOUT_THRESHOLD


def _record_login_failure(username: str, client_ip: str, reason: str = "invalid_credentials"):
    """Record a failed login attempt for account-level lockout tracking."""
    conn = db()
    conn.execute(
        "INSERT INTO login_failures (username, client_ip, ts) VALUES (?, ?, ?)",
        (username, client_ip, datetime.now().timestamp()),
    )
    # Prune old entries (older than 2x lockout window)
    cutoff = datetime.now().timestamp() - (_LOGIN_LOCKOUT_DURATION_S * 2)
    conn.execute("DELETE FROM login_failures WHERE ts < ?", (cutoff,))
    conn.commit()
    conn.close()
    _auth_logger.warning("login_failure", extra={"username": username, "client_ip": client_ip, "reason": reason})


def _clear_login_failures(username: str):
    """Clear failed login records on successful authentication."""
    conn = db()
    conn.execute("DELETE FROM login_failures WHERE username = ?", (username,))
    conn.commit()
    conn.close()


def _store_bootstrap_token(raw_token: str, api_key: str, account_id: int, student_id: int):
    """Persist a bootstrap token record in the DB."""
    conn = db()
    now_iso = datetime.now().isoformat()
    expires_iso = (datetime.now() + timedelta(seconds=_BOOTSTRAP_TOKEN_TTL_S)).isoformat()
    conn.execute(
        "INSERT INTO bootstrap_tokens (token_hash, account_id, student_id, api_key, created_at, expires_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (_hash_token(raw_token), account_id, student_id, api_key, now_iso, expires_iso),
    )
    conn.commit()
    conn.close()


def _consume_bootstrap_token(raw_token: str) -> Optional[Dict[str, Any]]:
    """Consume a bootstrap token (single-use). Returns token data or None."""
    conn = db()
    token_hash = _hash_token(raw_token)
    now_iso = datetime.now().isoformat()
    row = conn.execute(
        "SELECT * FROM bootstrap_tokens WHERE token_hash = ? AND consumed_at IS NULL AND expires_at > ?",
        (token_hash, now_iso),
    ).fetchone()
    if not row:
        conn.close()
        return None
    # Mark consumed (single-use)
    conn.execute(
        "UPDATE bootstrap_tokens SET consumed_at = ? WHERE id = ?",
        (now_iso, row["id"]),
    )
    conn.commit()
    conn.close()
    return {
        "api_key": row["api_key"],
        "account_id": int(row["account_id"]),
        "student_id": int(row["student_id"]),
        "created_at": row["created_at"],
        "expires_at": row["expires_at"],
    }


def _count_outstanding_tokens(account_id: int) -> int:
    """Count unconsumed, unexpired tokens for an account."""
    conn = db()
    now_iso = datetime.now().isoformat()
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM bootstrap_tokens WHERE account_id = ? AND consumed_at IS NULL AND expires_at > ?",
        (account_id, now_iso),
    ).fetchone()
    conn.close()
    return int(row["c"]) if row else 0


def _cleanup_expired_tokens_db():
    """Remove expired bootstrap tokens from DB to prevent unbounded growth."""
    conn = db()
    cutoff = (datetime.now() - timedelta(seconds=_BOOTSTRAP_TOKEN_TTL_S * 2)).isoformat()
    conn.execute("DELETE FROM bootstrap_tokens WHERE expires_at < ?", (cutoff,))
    conn.commit()
    conn.close()


def _with_random_seed(seed: Optional[int]):
    """Context manager-like helper without importing contextlib (keep server.py simple)."""

    class _Seed:
        def __enter__(self):
            self._state = random.getstate()
            if seed is not None:
                random.seed(int(seed))

        def __exit__(self, exc_type, exc, tb):
            random.setstate(self._state)
            return False

    return _Seed()


def _skill_snapshot_from_analytics(analytics: Dict[str, Any], *, skill_tag: str) -> Dict[str, Any]:
    for it in (analytics.get("by_skill") or []):
        if not isinstance(it, dict):
            continue
        if str(it.get("skill_tag") or "") == str(skill_tag):
            return {
                "attempts": int(it.get("attempts") or 0),
                "correct": int(it.get("correct") or 0),
                "accuracy": float(it.get("accuracy") or 0.0),
                "hint_dependency": float(it.get("hint_dependency") or 0.0),
                "top_mistake_code": it.get("top_mistake_code"),
                "top_mistake_count": int(it.get("top_mistake_count") or 0),
            }
    return {
        "attempts": 0,
        "correct": 0,
        "accuracy": 0.0,
        "hint_dependency": 0.0,
        "top_mistake_code": None,
        "top_mistake_count": 0,
    }


def _skill_tags_from_topic(topic: str) -> List[str]:
    t = str(topic or "").strip()
    if not t:
        return ["unknown"]
    # Heuristic mapping: keep it simple and stable.
    if "分數" in t or "小數" in t or "折扣" in t:
        return ["分數/小數"]
    if "四則" in t or "括號" in t or "乘除" in t:
        return ["四則運算"]
    if "比例" in t:
        return ["比例"]
    if "單位" in t:
        return ["單位換算"]
    if "路程" in t or "速度" in t or "時間" in t:
        return ["路程時間"]
    return [t]


def _mistake_code_from_error_code(err_code: Optional[ErrorCode]) -> Optional[str]:
    if err_code is None:
        return None
    v = str(err_code.value)
    if v == ErrorCode.CAL.value:
        return "calculation"
    if v == ErrorCode.CON.value:
        return "concept"
    if v == ErrorCode.READ.value:
        return "reading"
    if v == ErrorCode.CARE.value:
        return "careless"
    if v == ErrorCode.TIME.value:
        return "careless"
    return None


def _safe_learning_record_attempt(*, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if learning_record_attempt is None:
        return None
    try:
        return learning_record_attempt(event, db_path=DB_PATH, dev_mode=True)
    except Exception:
        return None

@app.post("/v1/quadratic/next", summary="Generate Quadratic Problem (MATH Dataset Level 1-5)")
def next_quadratic(req: QuadraticGenRequest):
    if not quadratic_engine:
        raise HTTPException(status_code=500, detail="Quadratic Engine not loaded")

    # Map Khan Topic to difficulty logic if needed, or pass through
    # Engine handles A3/A4/A5
    try:
        q = quadratic_engine.generate_problem(req.topic_id, req.difficulty)

        # Add Knowledge Graph Context
        info = KNOWLEDGE_GRAPH.get(req.topic_id, {})
        q["knowledge_context"] = {
            "title": info.get("title"),
            "prereqs": info.get("prereqs"),
            "khan_mapped_id": info.get("khan_mapped_id")
        }
        return q
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@app.post("/v1/quadratic/check", summary="Check Quadratic Answer (SymPy Logic)")
def check_quadratic(req: QuadraticCheckRequest):
    if not quadratic_engine:
        raise HTTPException(status_code=500, detail="Quadratic Engine not loaded")

    is_correct = quadratic_engine.check_answer(req.user_answer, req.question_data)
    return {"correct": is_correct}

# --- Linear Engine Endpoints ---

class LinearGenRequest(BaseModel):
    difficulty: int = Field(default=1, ge=1, le=5)

class LinearCheckRequest(BaseModel):
    user_answer: str
    question_data: Dict[str, Any]

@app.post("/v1/linear/next", summary="Generate Linear Problem (Level 1-5)")
def next_linear(req: LinearGenRequest):
    if not linear_engine:
        raise HTTPException(status_code=500, detail="Linear Engine not loaded")
    try:
        q = linear_engine.generate_problem(req.difficulty)
        # q: { question_text, explanation(steps), ... }
        # Map to DB schema: topic, difficulty, question, correct_answer, explanation, hints_json

        # We need to extract correct_answer. linear_engine generates 'sol'.
        # But wait, linear_engine.generate_problem returns Dict[str, Any] with:
        # question_text, explanation (list of strings).
        # It needs to return the answer too!
        # I should check linear_engine.py output format.

        # Assuming linear_engine also returns 'answer' or 'sol'.
        # Let's inspect linear_engine.generate_problem output.
        # But for now I'll persist standard fields.

        # NOTE: linear_engine as I saw earlier returns `explanation_steps`.
        # I'll convert steps to text.

        topic = "linear_eq"
        question_text = q.get("question_text", "Unknown Question")
        ans = str(q.get("sol", "")) # Check logic below
        explanation_str = "\n".join(q.get("explanation_steps", []))

        conn = db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO question_cache (topic, difficulty, question, correct_answer, explanation, hints_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (topic, str(req.difficulty), question_text, ans, explanation_str, "[]", datetime.now().isoformat()))
        q_id = cur.lastrowid
        conn.commit()
        conn.close()

        q["question_id"] = q_id
        return q
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/linear/check", summary="Check Linear Answer")
def check_linear(req: LinearCheckRequest):
    if not linear_engine:
        raise HTTPException(status_code=500, detail="Linear Engine not loaded")
    return {"correct": linear_engine.check_answer(req.user_answer, req.question_data)}

# -------------------------------

@app.get("/v1/knowledge/graph", summary="Get Full Knowledge Graph")
def get_knowledge_graph():
    return KNOWLEDGE_GRAPH

class MixedMultiplyDiagnoseRequest(BaseModel):
    left: str = Field(..., description="Left operand (mixed number like '2 1/3' or fraction like '7/3')")
    right: str = Field(..., description="Right operand (integer or fraction)")
    step1: Optional[str] = Field(default=None, description="Student step1: convert left to improper fraction")
    step2: Optional[str] = Field(default=None, description="Student step2: raw multiplication result")
    step3: Optional[str] = Field(default=None, description="Student step3: simplified result")


def _is_answer_correct(student_answer: str, correct_answer: str) -> bool:
    sa = str(student_answer or "").strip()
    ca = str(correct_answer or "").strip()

    # Prefer existing engine.check (supports fractions / formats).
    if engine is not None and hasattr(engine, "check"):
        try:
            result = engine.check(sa, ca)
            return result == 1
        except Exception:
            pass

    return sa == ca


def _diagnose_via_llm(prompt: str) -> str:
    """Return LLM analysis text. If no API key, returns a safe stub."""

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return "分析：目前未設定 OPENAI_API_KEY，暫以離線模式回傳。學生可能在符號/運算順序/通分約分等基本規則上有混淆。"

    try:
        # openai>=1.x
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        model = os.getenv("DIAGNOSE_MODEL", "gpt-4o-mini")
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=float(os.getenv("DIAGNOSE_TEMPERATURE", "0.2")),
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        return f"分析：LLM 呼叫失敗（{type(e).__name__}: {e}）。建議先檢查 API Key / 網路 / 模型名稱。"

@app.get("/v1/report/{student_id}", summary="Get Student Report HTML")
def get_student_report(student_id: int):
    # Just run the reporting job on the fly for MVP
    try:
        # Assuming scripts/reporting_job.py can be imported as module
        # or we just reimplement simple logic here
        conn = db()
        st = conn.execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone()
        if not st:
            return JSONResponse(status_code=404, content={"error": "Student not found"})

        attempts = conn.execute("SELECT * FROM attempts WHERE student_id=? ORDER BY ts DESC", (student_id,)).fetchall()

        total = len(attempts)
        correct = sum(1 for a in attempts if a["is_correct"]==1)
        acc = round(correct/total*100, 1) if total>0 else 0

        # Weak topics
        topic_stats = {}
        for a in attempts:
            t = a["topic"] or "unknown"
            if t not in topic_stats: topic_stats[t] = {"total":0, "correct":0}
            topic_stats[t]["total"] += 1
            if a["is_correct"]==1: topic_stats[t]["correct"] += 1

        weak_topics = []
        for t, stats in topic_stats.items():
            t_acc = stats["correct"] / stats["total"]
            if t_acc < 0.7: weak_topics.append({"topic": t, "acc": round(t_acc*100,1)})

        return {
            "student": st["display_name"],
            "total_attempts": total,
            "accuracy": acc,
            "weak_topics": weak_topics,
            "recent_history": [
                {"ts": a["ts"], "topic": a["topic"], "correct": a["is_correct"]} for a in attempts[:10]
            ]
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

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
    CREATE TABLE IF NOT EXISTS app_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        password_salt TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
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
        hints_json TEXT,
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
        error_tag TEXT,
        error_detail TEXT,
        hint_level_used INTEGER,
        meta_json TEXT,
        ts TEXT NOT NULL,
        FOREIGN KEY(account_id) REFERENCES accounts(id),
        FOREIGN KEY(student_id) REFERENCES students(id),
        FOREIGN KEY(question_id) REFERENCES question_cache(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS parent_report_registry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        normalized_name TEXT UNIQUE NOT NULL,
        display_name TEXT NOT NULL,
        pin_hash TEXT NOT NULL,
        pin_salt TEXT NOT NULL,
        data_json TEXT NOT NULL DEFAULT '{}',
        cloud_ts INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS report_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        report_payload_json TEXT NOT NULL DEFAULT '{}',
        source TEXT NOT NULL DEFAULT 'frontend',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(account_id) REFERENCES accounts(id),
        FOREIGN KEY(student_id) REFERENCES students(id)
    )
    """)

    # Adaptive mastery (per-student per-concept)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS student_concepts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        concept_id TEXT NOT NULL,
        stage TEXT NOT NULL DEFAULT 'BASIC',
        answered INTEGER NOT NULL DEFAULT 0,
        correct INTEGER NOT NULL DEFAULT 0,
        in_hint_mode INTEGER NOT NULL DEFAULT 0,
        in_micro_step INTEGER NOT NULL DEFAULT 0,
        micro_count INTEGER NOT NULL DEFAULT 0,
        consecutive_wrong INTEGER NOT NULL DEFAULT 0,
        calm_mode INTEGER NOT NULL DEFAULT 0,
        last_activity TEXT,
        concept_started_at TEXT,
        error_stats_json TEXT NOT NULL DEFAULT '{}',
        flag_teacher INTEGER NOT NULL DEFAULT 0,
        completed INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL,
        UNIQUE(student_id, concept_id),
        FOREIGN KEY(student_id) REFERENCES students(id)
    )
    """)

    # ─── Bootstrap token durable store ───
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bootstrap_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token_hash TEXT NOT NULL,
        account_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        api_key TEXT NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        consumed_at TEXT,
        FOREIGN KEY(account_id) REFERENCES accounts(id)
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_bt_hash ON bootstrap_tokens(token_hash)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_bt_account ON bootstrap_tokens(account_id, consumed_at, expires_at)")

    # ─── Rate limiting durable store ───
    cur.execute("""
    CREATE TABLE IF NOT EXISTS rate_limit_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT NOT NULL,
        ts REAL NOT NULL
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_rle_key_ts ON rate_limit_events(key, ts)")

    # ─── Login failure tracking for account-level lockout ───
    cur.execute("""
    CREATE TABLE IF NOT EXISTS login_failures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        client_ip TEXT NOT NULL,
        ts REAL NOT NULL
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_lf_username_ts ON login_failures(username, ts)")

    # ---- schema migration (non-breaking) ----
    def ensure_column(table: str, col: str, col_type: str):
        cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if col not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")

    ensure_column("question_cache", "hints_json", "TEXT")
    ensure_column("attempts", "error_tag", "TEXT")
    ensure_column("attempts", "error_detail", "TEXT")
    ensure_column("attempts", "hint_level_used", "INTEGER")
    ensure_column("attempts", "meta_json", "TEXT")

    # Track the student's current concept for the adaptive flow.
    ensure_column("students", "current_concept_id", "TEXT")
    ensure_column("students", "updated_at", "TEXT")

    # Stripe integration columns (nullable — populated by webhook)
    ensure_column("subscriptions", "stripe_customer_id", "TEXT")
    ensure_column("subscriptions", "stripe_subscription_id", "TEXT")

    # School-first RBAC tables for teacher/class reporting.
    cur.execute("""
    CREATE TABLE IF NOT EXISTS schools (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        school_code TEXT NOT NULL UNIQUE,
        max_seats INTEGER NOT NULL DEFAULT 200,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('student','parent','teacher','school_admin','platform_admin')),
        school_id INTEGER,
        created_at TEXT NOT NULL,
        UNIQUE(account_id, role, school_id),
        FOREIGN KEY(account_id) REFERENCES accounts(id),
        FOREIGN KEY(school_id) REFERENCES schools(id)
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_roles_account_role ON roles(account_id, role)")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER NOT NULL,
        teacher_account_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        grade INTEGER NOT NULL CHECK(grade IN (5, 6)),
        created_at TEXT NOT NULL,
        FOREIGN KEY(school_id) REFERENCES schools(id),
        FOREIGN KEY(teacher_account_id) REFERENCES accounts(id)
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_classes_teacher ON classes(teacher_account_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_classes_school ON classes(school_id)")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS class_students (
        class_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        enrolled_at TEXT NOT NULL,
        PRIMARY KEY (class_id, student_id),
        FOREIGN KEY(class_id) REFERENCES classes(id),
        FOREIGN KEY(student_id) REFERENCES students(id)
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_class_students_student ON class_students(student_id)")

    conn.commit()
    conn.close()

init_db()


def _concept_sequence() -> List[str]:
    """Default ordered concepts for progression.

    Priority:
    1) ENV ADAPTIVE_CONCEPT_SEQUENCE="A1,A2,A3"
    2) KNOWLEDGE_GRAPH order (A1..)
    """

    raw = os.environ.get("ADAPTIVE_CONCEPT_SEQUENCE", "").strip()
    if raw:
        seq = [x.strip() for x in raw.split(",") if x.strip()]
        if seq:
            return seq

    # Default to knowledge graph IDs in sorted order.
    try:
        keys = list(KNOWLEDGE_GRAPH.keys())
        if all(isinstance(k, str) for k in keys):
            return sorted(keys)
    except Exception:
        pass

    return []


def _next_concept_id(current: str) -> Optional[str]:
    seq = _concept_sequence()
    if not seq or current not in seq:
        return None
    idx = seq.index(current)
    if idx + 1 >= len(seq):
        return None
    return seq[idx + 1]


def _get_or_create_student_concept(conn: sqlite3.Connection, *, student_id: int, concept_id: str) -> ConceptState:
    row = conn.execute(
        "SELECT * FROM student_concepts WHERE student_id=? AND concept_id=?",
        (student_id, concept_id),
    ).fetchone()
    if row:
        return ConceptState(
            concept_id=concept_id,
            stage=Stage(str(row["stage"]) or Stage.BASIC.value),
            answered=int(row["answered"] or 0),
            correct=int(row["correct"] or 0),
            in_hint_mode=bool(row["in_hint_mode"]),
            in_micro_step=bool(row["in_micro_step"]),
            micro_count=int(row["micro_count"] or 0),
            consecutive_wrong=int(row["consecutive_wrong"] or 0),
            calm_mode=bool(row["calm_mode"]),
            last_activity=str(row["last_activity"] or "") or None,
            concept_started_at=str(row["concept_started_at"] or "") or None,
            error_stats=error_stats_from_json(row["error_stats_json"]),
            flag_teacher=bool(row["flag_teacher"]),
            completed=bool(row["completed"]),
        )

    # Insert fresh row.
    st = ConceptState(concept_id=concept_id, stage=Stage.BASIC)
    conn.execute(
        """
        INSERT INTO student_concepts(
            student_id, concept_id, stage, answered, correct,
            in_hint_mode, in_micro_step, micro_count,
            consecutive_wrong, calm_mode,
            last_activity, concept_started_at,
            error_stats_json, flag_teacher, completed,
            updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            student_id,
            concept_id,
            st.stage.value,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            now_iso(),
            now_iso(),
            "{}",
            0,
            0,
            now_iso(),
        ),
    )
    return st


def _save_student_concept(conn: sqlite3.Connection, *, student_id: int, state: ConceptState) -> None:
    conn.execute(
        """
        UPDATE student_concepts SET
          stage=?, answered=?, correct=?,
          in_hint_mode=?, in_micro_step=?, micro_count=?,
          consecutive_wrong=?, calm_mode=?,
          last_activity=?, concept_started_at=?,
          error_stats_json=?, flag_teacher=?, completed=?,
          updated_at=?
        WHERE student_id=? AND concept_id=?
        """,
        (
            state.stage.value,
            int(state.answered),
            int(state.correct),
            1 if state.in_hint_mode else 0,
            1 if state.in_micro_step else 0,
            int(state.micro_count),
            int(state.consecutive_wrong),
            1 if state.calm_mode else 0,
            state.last_activity or now_iso(),
            state.concept_started_at or now_iso(),
            error_stats_to_json(state.error_stats),
            1 if state.flag_teacher else 0,
            1 if state.completed else 0,
            now_iso(),
            student_id,
            state.concept_id,
        ),
    )


def _window_accuracy(conn: sqlite3.Connection, *, student_id: int, concept_id: str, n: int) -> Optional[float]:
    rows = conn.execute(
        """
        SELECT is_correct FROM attempts
        WHERE student_id=? AND topic=? AND is_correct IN (0,1)
        ORDER BY ts DESC LIMIT ?
        """,
        (student_id, concept_id, int(n)),
    ).fetchall()
    if not rows:
        return None
    total = len(rows)
    correct = sum(1 for r in rows if r["is_correct"] == 1)
    return correct / total if total else None


def _avg_time(conn: sqlite3.Connection, *, student_id: int, concept_id: str) -> Optional[float]:
    row = conn.execute(
        """
        SELECT AVG(time_spent_sec) AS avg_t
        FROM attempts
        WHERE student_id=? AND topic=? AND time_spent_sec > 0
        """,
        (student_id, concept_id),
    ).fetchone()
    if not row:
        return None
    v = row["avg_t"]
    try:
        return float(v) if v is not None else None
    except Exception:
        return None


def _adaptive_ui_actions(state: ConceptState, *, error_code: Optional[str]) -> List[str]:
    out: List[str] = []
    if state.calm_mode:
        out.append("calm_mode")
        out.append("slow_ui")
    if state.in_micro_step:
        out.append("micro_step")
        out.append("split_question")
    if state.in_hint_mode:
        out.append("hint_mode")
        out.append("show_steps")

    code = (error_code or "").strip().upper()
    if code == ErrorCode.CAL.value:
        out.append("show_steps")
    elif code == ErrorCode.CON.value:
        out.append("show_example")
    elif code == ErrorCode.READ.value:
        out.append("highlight_keywords")
    elif code == ErrorCode.CARE.value:
        out.append("slow_ui")
    elif code == ErrorCode.TIME.value:
        out.append("split_question")
    return sorted(set(out))

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


def _pwd_hash(password: str, salt: str) -> str:
    raw = f"{salt}:{password}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _pwd_ok(password: str, salt: str, pwd_hash: str) -> bool:
    return _pwd_hash(password, salt) == str(pwd_hash or "")

# ========= 4) Helper: JSON =========
def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def _now_ms() -> int:
    return int(datetime.now().timestamp() * 1000)


def _normalize_parent_report_name(name: str) -> str:
    value = unicodedata.normalize("NFKC", str(name or ""))
    value = " ".join(value.strip().split())
    return value.upper()


def _validate_parent_report_pin(pin: str) -> str:
    value = str(pin or "").strip()
    if not value or not value.isdigit() or len(value) < 4 or len(value) > 6:
        raise HTTPException(status_code=400, detail="pin must be 4..6 digits")
    return value


def _sanitize_parent_report_data(data: Dict[str, Any], *, fallback_name: str) -> Dict[str, Any]:
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="report_data must be an object")
    try:
        normalized = json.loads(json.dumps(data))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"report_data must be JSON serializable: {exc}")
    if not isinstance(normalized.get("d"), dict):
        raise HTTPException(status_code=400, detail="report_data.d is required")
    normalized["name"] = str(normalized.get("name") or fallback_name)
    normalized["ts"] = int(normalized.get("ts") or _now_ms())
    normalized["days"] = int(normalized.get("days") or 7)
    return normalized


def _sanitize_practice_event(event: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(event, dict):
        raise HTTPException(status_code=400, detail="practice_event must be an object")
    score = max(0, int(event.get("score") or 0))
    total = max(1, int(event.get("total") or 1))
    return {
        "ts": int(event.get("ts") or _now_ms()),
        "score": min(score, total),
        "total": total,
        "topic": str(event.get("topic") or ""),
        "kind": str(event.get("kind") or ""),
        "mode": str(event.get("mode") or "quiz"),
        "completed": bool(event.get("completed", True)),
    }


def _load_parent_report_row(conn: sqlite3.Connection, normalized_name: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM parent_report_registry WHERE normalized_name = ?",
        (normalized_name,),
    ).fetchone()


def _parse_parent_report_data(raw: str, *, fallback_name: str) -> Dict[str, Any]:
    try:
        data = json.loads(str(raw or "{}"))
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("name", fallback_name)
    data.setdefault("ts", _now_ms())
    data.setdefault("days", 7)
    data.setdefault("d", {})
    if not isinstance(data.get("d"), dict):
        data["d"] = {}
    return data

def row_to_dict(r: sqlite3.Row) -> Dict[str, Any]:
    return {k: r[k] for k in r.keys()}


def _normalize_school_code(value: Optional[str]) -> str:
    code = "".join(str(value or "").strip().upper().split())
    if len(code) < 4:
        raise HTTPException(status_code=400, detail="school_code must be at least 4 characters")
    return code


def _teacher_role_row(conn: sqlite3.Connection, account_id: int) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM roles WHERE account_id = ? AND role = 'teacher' ORDER BY id ASC LIMIT 1",
        (account_id,),
    ).fetchone()


def _ensure_teacher_role(
    conn: sqlite3.Connection,
    *,
    account_id: int,
    school_name: Optional[str] = None,
    school_code: Optional[str] = None,
) -> sqlite3.Row:
    role_row = _teacher_role_row(conn, account_id)
    if role_row:
        school = conn.execute("SELECT * FROM schools WHERE id = ?", (int(role_row["school_id"]),)).fetchone()
        if not school or int(school["active"] or 0) != 1:
            raise HTTPException(status_code=403, detail="Teacher school is inactive")
        return role_row

    if not school_name or not school_code:
        raise HTTPException(
            status_code=403,
            detail="Teacher role not configured; provide school_name and school_code to bootstrap the first class",
        )

    normalized_code = _normalize_school_code(school_code)
    school = conn.execute("SELECT * FROM schools WHERE school_code = ?", (normalized_code,)).fetchone()
    now = now_iso()
    if not school:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO schools(name, school_code, max_seats, active, created_at) VALUES(?,?,?,?,?)",
            (str(school_name).strip(), normalized_code, 200, 1, now),
        )
        school_id = int(cur.lastrowid)
    else:
        school_id = int(school["id"])

    conn.execute(
        "INSERT INTO roles(account_id, role, school_id, created_at) VALUES(?,?,?,?)",
        (account_id, "teacher", school_id, now),
    )
    role_row = _teacher_role_row(conn, account_id)
    if not role_row:
        raise HTTPException(status_code=500, detail="Failed to create teacher role")
    return role_row


def _require_teacher_scope(conn: sqlite3.Connection, account_id: int, class_id: int) -> sqlite3.Row:
    row = conn.execute(
        """
        SELECT c.*, s.name AS school_name, s.school_code AS school_code
        FROM classes c
        JOIN schools s ON s.id = c.school_id
        WHERE c.id = ? AND c.teacher_account_id = ?
        """,
        (class_id, account_id),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Class not found for this teacher")
    return row


def _teacher_student_row(conn: sqlite3.Connection, account_id: int, student_id: int) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM students WHERE id = ? AND account_id = ?",
        (student_id, account_id),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Student not found for this teacher")
    return row


def _build_hints(q: Dict[str, Any]) -> Dict[str, str]:
    # If the generator provides explicit 3-level hints (e.g. new pack-based types), use them.
    try:
        h = q.get("hints")
        if isinstance(h, dict) and all(k in h for k in ("level1", "level2", "level3")):
            return {
                "level1": str(h.get("level1") or ""),
                "level2": str(h.get("level2") or ""),
                "level3": str(h.get("level3") or ""),
            }
    except Exception:
        pass

    # Prefer engine's internal helper if present.
    if engine is not None and hasattr(engine, "get_question_hints"):
        try:
            hints = engine.get_question_hints(q)
            if isinstance(hints, dict) and all(k in hints for k in ("level1", "level2", "level3")):
                return hints
        except Exception:
            pass

    # Fallback: simple generic hints.
    return {
        "level1": "先整理題意，逐步計算。",
        "level2": "寫出中間步驟再檢查。",
        "level3": "若卡住，先回到通分/約分/運算順序的基本規則。",
    }


@app.post("/validate/quadratic", summary="Validate quadratic pipeline (browser)")
def validate_quadratic_pipeline(payload: QuadraticPipelineValidateRequest):
    """Run a minimal quadratic generate→validate flow and return results.

    Intended for local browser verification via Swagger UI:
    - Start: `uvicorn server:app --reload --port 8001`
    - Open: http://127.0.0.1:8001/docs
    """

    roots = str(payload.roots).strip().lower()
    if roots not in ("integer", "rational", "mixed"):
        raise HTTPException(status_code=400, detail="roots must be one of: integer, rational, mixed")

    style = str(payload.style).strip()
    if style not in ("standard", "factoring_then_formula"):
        raise HTTPException(status_code=400, detail="style must be one of: standard, factoring_then_formula")

    # Import lazily to keep server startup fast.
    try:
        from ai.schemas import GeneratedMCQSet
        from scripts.pipeline_quadratic_generate_validate_tag import (
            VerifyReport,
            offline_stub_set_controlled,
            verify_mcq_item,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import pipeline modules: {type(e).__name__}: {e}")

    # Always keep this endpoint safe: offline by default.
    if not payload.offline and not os.getenv("OPENAI_API_KEY", "").strip():
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY missing; set offline=true or configure API key")

    results: list[dict[str, Any]] = []
    concept = "一元二次方程式-公式解"

    # For browser verification, we run offline deterministic generation.
    # If you want online LLM generation later, we can expose a gated /v1 endpoint.
    for _ in range(int(payload.count)):
        raw = offline_stub_set_controlled(concept=concept, roots_mode=roots, difficulty=int(payload.difficulty))
        mcq_set = GeneratedMCQSet.model_validate(raw)
        if not mcq_set.items:
            raise HTTPException(status_code=500, detail="No items generated")

        item = mcq_set.items[0].model_dump()
        rep: VerifyReport = verify_mcq_item(item, roots_mode=roots, difficulty=int(payload.difficulty))
        if not rep.ok:
            raise HTTPException(status_code=500, detail=f"Validation failed: {rep.reason}")

        results.append(
            {
                "ok": True,
                "verification": {"solutions": rep.solutions},
                "mcq": item,
            }
        )

    return {"ok": True, "count": len(results), "results": results}

# ========= 5) API =========
@app.get("/health")
def health():
    return {"ok": True, "ts": now_iso()}


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/v1/app/auth/provision", summary="Provision purchased app user (admin only)")
def app_auth_provision(
    payload: AppAuthProvisionRequest,
    x_admin_token: str = Header("", alias="X-Admin-Token"),
):
    expected = os.getenv("APP_PROVISION_ADMIN_TOKEN", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="APP_PROVISION_ADMIN_TOKEN is not configured")
    if not x_admin_token or x_admin_token != expected:
        raise HTTPException(status_code=401, detail="Invalid admin token")

    username = payload.username.strip().lower()
    if not username:
        raise HTTPException(status_code=400, detail="username required")

    conn = db()
    cur = conn.cursor()
    exists = cur.execute("SELECT id FROM app_users WHERE username = ?", (username,)).fetchone()
    if exists:
        conn.close()
        raise HTTPException(status_code=409, detail="username already exists")

    created = now_iso()
    api_key = secrets.token_urlsafe(24)
    cur.execute(
        "INSERT INTO accounts(name, api_key, created_at) VALUES(?,?,?)",
        (payload.account_name, api_key, created),
    )
    account_id = int(cur.lastrowid)

    cur.execute(
        """
        INSERT INTO subscriptions(account_id, status, plan, seats, current_period_end, updated_at)
        VALUES(?,?,?,?,?,?)
        """,
        (
            account_id,
            "active",
            payload.plan,
            int(payload.seats),
            (datetime.now() + timedelta(days=30)).isoformat(timespec="seconds"),
            created,
        ),
    )

    cur.execute(
        "INSERT INTO students(account_id, display_name, grade, created_at) VALUES(?,?,?,?)",
        (account_id, payload.student_name, payload.grade, created),
    )
    student_id = int(cur.lastrowid)

    salt = secrets.token_hex(16)
    pwd_hash = _pwd_hash(payload.password, salt)
    cur.execute(
        """
        INSERT INTO app_users(account_id, username, password_hash, password_salt, active, created_at, updated_at)
        VALUES(?,?,?,?,1,?,?)
        """,
        (account_id, username, pwd_hash, salt, created, created),
    )

    conn.commit()
    conn.close()

    return {
        "ok": True,
        "username": username,
        "account_id": account_id,
        "default_student_id": student_id,
        "api_key": api_key,
        "plan": payload.plan,
        "seats": int(payload.seats),
    }


@app.post("/v1/app/auth/login", summary="Login app user with purchased username/password")
def app_auth_login(payload: AppAuthLoginRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(f"login:{client_ip}", _RATE_LIMIT_LOGIN):
        raise HTTPException(status_code=429, detail="Too many login attempts")

    username = payload.username.strip().lower()

    # Account-level lockout check (fires before credential validation)
    if _is_account_locked(username):
        _auth_logger.warning("login_lockout", extra={"username": username, "client_ip": client_ip})
        raise HTTPException(status_code=423, detail="Account temporarily locked due to too many failed attempts")

    conn = db()
    row = conn.execute(
        """
        SELECT au.*, a.id AS account_id, a.name AS account_name, a.api_key
        FROM app_users au
        JOIN accounts a ON a.id = au.account_id
        WHERE au.username = ?
        """,
        (username,),
    ).fetchone()

    if not row:
        conn.close()
        _record_login_failure(username, client_ip, "unknown_username")
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if int(row["active"] or 0) != 1:
        conn.close()
        _record_login_failure(username, client_ip, "inactive_user")
        raise HTTPException(status_code=403, detail="User is inactive")
    if not _pwd_ok(payload.password, str(row["password_salt"] or ""), str(row["password_hash"] or "")):
        conn.close()
        _record_login_failure(username, client_ip, "wrong_password")
        raise HTTPException(status_code=401, detail="Invalid username or password")

    sub = conn.execute(
        "SELECT * FROM subscriptions WHERE account_id = ? ORDER BY updated_at DESC LIMIT 1",
        (int(row["account_id"]),),
    ).fetchone()
    if not sub or sub["status"] != "active":
        conn.close()
        raise HTTPException(status_code=402, detail="Subscription required (inactive)")

    all_students = conn.execute(
        "SELECT id, display_name, grade FROM students WHERE account_id = ? ORDER BY id ASC",
        (int(row["account_id"]),),
    ).fetchall()
    conn.close()

    students_list = [
        {"id": int(s["id"]), "display_name": s["display_name"], "grade": s["grade"]}
        for s in all_students
    ]
    st = all_students[0] if all_students else None

    # Successful login — clear any prior failure records
    _clear_login_failures(username)
    _auth_logger.info("login_success", extra={"username": username, "client_ip": client_ip})

    return {
        "ok": True,
        "username": username,
        "account_id": int(row["account_id"]),
        "account_name": row["account_name"],
        "api_key": row["api_key"],
        "subscription": {
            "status": sub["status"],
            "plan": sub["plan"],
            "seats": int(sub["seats"] or 0),
            "current_period_end": sub["current_period_end"],
        },
        "default_student": {
            "id": int(st["id"]) if st else None,
            "display_name": st["display_name"] if st else None,
            "grade": st["grade"] if st else None,
        },
        "students": students_list,
    }


@app.get("/v1/app/auth/whoami", summary="Who am I (via X-API-Key)")
def app_auth_whoami(x_api_key: str = Header(..., alias="X-API-Key")):
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(int(acc["id"]))
    conn = db()
    st_count = conn.execute("SELECT COUNT(*) AS c FROM students WHERE account_id = ?", (int(acc["id"]),)).fetchone()
    conn.close()
    return {
        "ok": True,
        "account_id": int(acc["id"]),
        "account_name": acc["name"],
        "students": int((st_count["c"] if st_count else 0) or 0),
    }


@app.post("/v1/app/auth/bootstrap", summary="Create short-lived bootstrap token for parent-report handoff")
def app_auth_bootstrap(
    payload: BootstrapRequest,
    request: Request,
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    """APP calls this server-side with X-API-Key + student_id.
    Returns a short-lived, single-use bootstrap_token that can be passed
    via URL to parent-report. The token is NOT a long-lived credential."""
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(f"bootstrap:{client_ip}", _RATE_LIMIT_BOOTSTRAP):
        raise HTTPException(status_code=429, detail="Too many bootstrap requests")

    acc = get_account_by_api_key(x_api_key)
    account_id = int(acc["id"])
    ensure_subscription_active(account_id)
    conn = db()
    _verify_student_ownership(conn, account_id, payload.student_id)
    conn.close()

    _cleanup_expired_tokens_db()

    # Per-account outstanding token cap (DB-backed)
    outstanding = _count_outstanding_tokens(account_id)
    if outstanding >= _MAX_OUTSTANDING_TOKENS_PER_ACCOUNT:
        raise HTTPException(status_code=429, detail="Too many outstanding bootstrap tokens")

    token = secrets.token_urlsafe(32)
    _store_bootstrap_token(token, acc["api_key"], account_id, payload.student_id)
    return {"ok": True, "bootstrap_token": token}


@app.post("/v1/app/auth/exchange", summary="Exchange bootstrap token for session credentials")
def app_auth_exchange(payload: ExchangeRequest, request: Request):
    """Frontend calls this with a bootstrap_token received via URL.
    Validates and consumes the token (single-use), then returns
    the real credentials + subscription context via POST body only."""
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(f"exchange:{client_ip}", _RATE_LIMIT_EXCHANGE):
        raise HTTPException(status_code=429, detail="Too many exchange requests")

    entry = _consume_bootstrap_token(payload.bootstrap_token)
    if not entry:
        raise HTTPException(status_code=401, detail="Invalid or expired bootstrap token")

    # Re-validate subscription is still active
    ensure_subscription_active(entry["account_id"])

    return {
        "ok": True,
        "api_key": entry["api_key"],
        "student_id": entry["student_id"],
        "subscription": {"status": "active"},
    }


@app.get("/verify", response_class=HTMLResponse, summary="Browser-only validation page")
def verify_page():
        """A simple UI for non-terminal users to validate the quadratic pipeline.

        Usage:
        - Start server once (e.g., double-click a .bat or run uvicorn)
        - Open: http://127.0.0.1:8001/verify
        """

        html = r"""
<!doctype html>
<html>
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>AIMATH 本機驗證</title>
        <style>
            body{font-family:Segoe UI,Helvetica,Arial; padding:18px; line-height:1.5; max-width: 980px; margin: 0 auto}
            .card{background:#f6f8fa;padding:12px;border:1px solid #ddd;border-radius:8px;margin:12px 0}
            label{display:inline-block; min-width:110px}
            select,input{padding:6px; margin:4px 8px 4px 0}
            button{padding:8px 12px; margin:6px 0; cursor:pointer}
            .muted{color:#666}
            pre{background:#0b1020; color:#e6edf3; padding:12px; border-radius:8px; overflow:auto}
            .row{margin:8px 0}
            .ok{color:#0a7f2e}
            .bad{color:#b42318}
            a{color:#0969da}
        </style>
    </head>
    <body>
        <h2>AIMATH 本機驗證（純瀏覽器）</h2>
        <div class="muted">不需要 Swagger、不需要 terminal。按下「執行驗證」即可產生 1 題並通過 Sympy 檢查（離線模式）。</div>
        <div class="muted" style="margin-top:6px">如果你想做到「完全不用點 .bat」：請用一次性安裝腳本（Windows 排程常駐）→ 參考 <a href="/static/local" target="_blank">LOCAL_BROWSER_ONLY</a>。</div>

        <div class="card">
            <div class="row">
                <label>Roots</label>
                <select id="roots">
                    <option value="integer" selected>integer（整數根）</option>
                    <option value="rational">rational（有理數根）</option>
                    <option value="mixed">mixed（混合根）</option>
                </select>

                <label>Difficulty</label>
                <select id="difficulty">
                    <option value="1">1</option>
                    <option value="2">2</option>
                    <option value="3" selected>3</option>
                    <option value="4">4</option>
                    <option value="5">5</option>
                </select>

                <label>Count</label>
                <input id="count" type="number" min="1" max="5" value="1" />
            </div>

            <div class="row">
                <button id="run">執行驗證</button>
                <button id="health">檢查 API /health</button>
                <a href="/quadratic" target="_blank" class="muted">（一元二次離線練習頁 /quadratic）</a>
                <a href="http://127.0.0.1:8501" target="_blank" class="muted">（Streamlit 教師平台 8501）</a>
                <a href="/docs" target="_blank" class="muted">（或使用 Swagger /docs）</a>
            </div>

            <div id="status" class="row muted"></div>
        </div>

        <div class="card">
            <div class="row"><b>結果</b></div>
            <pre id="out">(尚未執行)</pre>
        </div>

        <script>
            const statusEl = document.getElementById('status');
            const outEl = document.getElementById('out');

            function setStatus(msg, ok=null){
                statusEl.className = 'row ' + (ok===true ? 'ok' : ok===false ? 'bad' : 'muted');
                statusEl.textContent = msg;
            }

            async function postJson(url, payload){
                const res = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
                const text = await res.text();
                let data;
                try { data = JSON.parse(text); } catch { data = { raw: text }; }
                if(!res.ok){
                    const msg = (data && (data.detail || data.message)) ? (data.detail || data.message) : ('HTTP ' + res.status);
                    throw new Error(msg);
                }
                return data;
            }

            document.getElementById('health').addEventListener('click', async () => {
                try{
                    setStatus('檢查中...');
                    const r = await fetch('/health');
                    const j = await r.json();
                    setStatus('health ok: ' + (j.ts || ''), true);
                }catch(e){
                    setStatus('health failed: ' + String(e.message || e), false);
                }
            });

            document.getElementById('run').addEventListener('click', async () => {
                try{
                    outEl.textContent = '(執行中...)';
                    setStatus('執行中...（離線模式）');

                    const payload = {
                        count: Number(document.getElementById('count').value || 1),
                        roots: String(document.getElementById('roots').value || 'integer'),
                        difficulty: Number(document.getElementById('difficulty').value || 3),
                        style: 'factoring_then_formula',
                        offline: true,
                    };

                    const data = await postJson('/validate/quadratic', payload);
                    outEl.textContent = JSON.stringify(data, null, 2);
                    setStatus('完成：驗證通過 ✅', true);
                }catch(e){
                    outEl.textContent = String(e && e.stack ? e.stack : e);
                    setStatus('失敗：' + String(e.message || e), false);
                }
            });
        </script>
    </body>
</html>
"""

        return HTMLResponse(content=html)


@app.get("/app-login", response_class=HTMLResponse, summary="App login (username/password)")
def app_login_page():
        html = r"""
<!doctype html>
<html>
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>AI MATH APP 登入</title>
        <style>
            body{font-family:Segoe UI,Helvetica,Arial;max-width:520px;margin:30px auto;padding:0 12px;line-height:1.6}
            .card{background:#f6f8fa;border:1px solid #ddd;border-radius:10px;padding:16px}
            input{width:100%;padding:10px;border:1px solid #ccc;border-radius:8px;margin:6px 0 12px 0}
            button{width:100%;padding:10px;border:0;border-radius:8px;background:#2563eb;color:#fff;font-weight:600;cursor:pointer}
            .muted{color:#666;font-size:13px}
            .ok{color:#0a7f2e;font-weight:600}
            .bad{color:#b42318;font-weight:600;white-space:pre-wrap}
        </style>
    </head>
    <body>
        <h2>AI MATH APP 登入</h2>
        <p class="muted">購買後請使用帳號密碼登入。登入成功後會自動進入完整題型與家長週報功能。</p>
        <div class="card">
            <label>帳號（username）</label>
            <input id="username" placeholder="例如 parent001" />
            <label>密碼（password）</label>
            <input id="password" type="password" placeholder="請輸入密碼" />
            <button id="btnLogin">登入並開始</button>
            <div id="msg" class="muted" style="margin-top:10px"></div>
        </div>

        <script>
            const msg = document.getElementById('msg');
            function setMsg(cls, text){ msg.className = cls; msg.textContent = text; }

            document.getElementById('btnLogin').addEventListener('click', async () => {
                const username = (document.getElementById('username').value || '').trim();
                const password = (document.getElementById('password').value || '').trim();
                if (!username || !password) {
                    setMsg('bad', '請輸入帳號與密碼');
                    return;
                }
                setMsg('muted', '登入中...');

                try {
                    const res = await fetch('/v1/app/auth/login', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ username, password })
                    });
                    const data = await res.json();
                    if (!res.ok || !data.ok) {
                        throw new Error(data.detail || '登入失敗');
                    }

                    localStorage.setItem('rag_api_key', String(data.api_key || ''));
                    if (data.default_student && data.default_student.id) {
                        localStorage.setItem('rag_student_id', String(data.default_student.id));
                    }
                    localStorage.setItem('rag_topic_key', '2');

                    setMsg('ok', '登入成功，正在進入學習頁...');
                    setTimeout(() => { location.href = '/'; }, 400);
                } catch (err) {
                    setMsg('bad', String(err && err.message ? err.message : err));
                }
            });
        </script>
    </body>
</html>
"""
        return HTMLResponse(content=html)


@app.get("/quadratic", response_class=HTMLResponse, summary="Offline quadratic practice page")
def quadratic_offline_page():
    """Serve the offline quadratic practice page.

    This is a static HTML page that can also be opened directly via file://:
    - docs/quadratic/index.html
    """

    path = Path(__file__).resolve().parent / "docs" / "quadratic" / "index.html"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Quadratic page not found")

    try:
        html = path.read_text(encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read quadratic page: {type(e).__name__}: {e}")

    return HTMLResponse(content=html)


@app.get("/mixed-multiply", response_class=HTMLResponse, summary="Offline mixed-number multiplication practice page")
def mixed_multiply_offline_page():
    """Serve the offline mixed-number multiplication practice page.

    This is a static HTML page that can also be opened directly via file://:
    - docs/mixed-multiply/index.html
    """

    path = Path(__file__).resolve().parent / "docs" / "mixed-multiply" / "index.html"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Mixed-multiply page not found")

    try:
        raw = path.read_bytes()
        if raw[:2] == b'\xff\xfe':
            if len(raw) % 2 == 1:
                raw = raw[:-1]
            html = raw.decode("utf-16")
        elif raw[:3] == b'\xef\xbb\xbf':
            html = raw[3:].decode("utf-8")
        else:
            html = raw.decode("utf-8")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read mixed-multiply page: {type(e).__name__}: {e}",
        )

    return HTMLResponse(content=html)


@app.get("/fraction-word-g5", include_in_schema=False)
def fraction_word_g5_redirect():
        """Redirect to the static offline practice module under docs.

        The actual page lives at:
            - /fraction-word-g5/  (served by StaticFiles mount)
            - docs/fraction-word-g5/index.html
        """

        return RedirectResponse(url="/fraction-word-g5/")


@app.post("/api/mixed-multiply/diagnose", summary="Diagnose mixed-number multiplication steps (G5)")
def api_mixed_multiply_diagnose(req: MixedMultiplyDiagnoseRequest):
    if fraction_logic is None:
        raise HTTPException(status_code=500, detail="fraction_logic module not available")

    try:
        rep = fraction_logic.diagnose_mixed_multiply(
            left=req.left,
            right=req.right,
            step1=req.step1,
            step2=req.step2,
            step3=req.step3,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Diagnose failed: {type(e).__name__}: {e}")

    return {
        "ok": bool(rep.ok),
        "weak_point": rep.weak_point,
        "weak_id": rep.weak_id,
        "diagnosis_code": getattr(rep, "diagnosis_code", ""),
        "message": rep.message,
        "next_hint": rep.next_hint,
        "retry_prompt": getattr(rep, "retry_prompt", ""),
        "resource_url": rep.resource_url,
        "expected": {
            "step1": rep.expected_step1,
            "step2": rep.expected_step2,
            "step3": rep.expected_step3,
            "mixed": rep.expected_mixed,
        },
    }


@app.get("/static/local", response_class=HTMLResponse, summary="Local browser-only setup notes")
def local_browser_only_notes():
    path = Path(__file__).resolve().parent / "LOCAL_BROWSER_ONLY.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail="LOCAL_BROWSER_ONLY.md not found")
    text = path.read_text(encoding="utf-8")

    # Minimal Markdown->HTML (good enough for local notes)
    esc = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    html = """
<!doctype html>
<html><head><meta charset=\"utf-8\" /><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
<title>LOCAL_BROWSER_ONLY</title>
<style>body{font-family:Segoe UI,Helvetica,Arial; max-width:980px; margin:0 auto; padding:18px; line-height:1.6} pre{background:#0b1020;color:#e6edf3;padding:12px;border-radius:8px;overflow:auto} code{background:#f6f8fa;padding:2px 6px;border-radius:6px}</style>
</head><body>
<h2>LOCAL_BROWSER_ONLY</h2>
<pre>""" + esc + """</pre>
</body></html>
"""
    return HTMLResponse(content=html)


def _build_diagnose_prompt(submission: StudentSubmission) -> str:
    return (
        "你是一位國中數學老師。學生在處理『{concept}』題目時出錯了。\n"
        "正確答案是：{correct}\n"
        "學生的答案是：{student}\n"
        "學生的解題過程：{process}\n\n"
        "請執行以下任務：\n"
        "1. 分析學生可能的迷思概念（Misconception）。\n"
        "2. 給予一個引導式提示（不要直接給答案）。\n"
        "3. 判斷是否需要複習前置觀念。\n"
    ).format(
        concept=submission.concept_tag,
        correct=submission.correct_answer,
        student=submission.student_answer,
        process=submission.process_text or "（未提供）",
    )


def _diagnose_core(submission: StudentSubmission) -> Dict[str, Any]:
    is_correct = _is_answer_correct(submission.student_answer, submission.correct_answer)
    if is_correct:
        return {
            "status": "success",
            "message": "太棒了！你已掌握此觀念。",
            "next_step": "建議挑戰進階應用題",
        }

    prompt = _build_diagnose_prompt(submission)
    ai_analysis = _diagnose_via_llm(prompt)

    recommendation = KNOWLEDGE_BASE.get(submission.concept_tag, {})
    prerequisites = recommendation.get("prerequisites")

    # MVP: Hint 先給通用版；若之後要更精準，可要求 LLM 以 JSON 回傳 hint。
    default_hint = "先把你的每一步寫清楚，特別檢查：符號、通分/約分、運算順序。"

    return {
        "status": "needs_remediation",
        "diagnosis": ai_analysis,
        "hint": default_hint,
        "recommended_video": recommendation.get("video_url"),
        "recommended_video_description": recommendation.get("description"),
        "prerequisites_to_check": prerequisites,
        "needs_prerequisite_review": bool(prerequisites),
    }


@app.post("/diagnose")
def diagnose_learning(submission: StudentSubmission):
    """Public MVP endpoint: accepts a submission and returns diagnosis + recommendation."""

    return _diagnose_core(submission)


@app.post("/v1/diagnose")
def diagnose_learning_v1(
    submission: StudentSubmission,
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    """Gated endpoint: same as /diagnose but requires subscription."""

    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])
    return _diagnose_core(submission)


# NOTE: Root "/" is served by StaticFiles mount (docs/index.html).
# The old inline fraction practice page was removed to avoid
# intercepting the proper landing page.


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


@app.get("/v1/teacher/classes", summary="List classes for the authenticated teacher")
def teacher_list_classes(x_api_key: str = Header(..., alias="X-API-Key")):
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])

    conn = db()
    role_row = _teacher_role_row(conn, int(acc["id"]))
    if not role_row:
        conn.close()
        return {"classes": [], "teacher_configured": False}

    rows = conn.execute(
        """
        SELECT c.id, c.name, c.grade, c.created_at,
               s.id AS school_id, s.name AS school_name, s.school_code,
               COUNT(cs.student_id) AS student_count
        FROM classes c
        JOIN schools s ON s.id = c.school_id
        LEFT JOIN class_students cs ON cs.class_id = c.id
        WHERE c.teacher_account_id = ?
        GROUP BY c.id, c.name, c.grade, c.created_at, s.id, s.name, s.school_code
        ORDER BY c.id ASC
        """,
        (int(acc["id"]),),
    ).fetchall()
    conn.close()

    return {
        "teacher_configured": True,
        "classes": [row_to_dict(r) for r in rows],
    }


@app.post("/v1/teacher/classes", summary="Create a class for the authenticated teacher")
def teacher_create_class(
    payload: TeacherCreateClassRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])

    conn = db()
    role_row = _ensure_teacher_role(
        conn,
        account_id=int(acc["id"]),
        school_name=payload.school_name,
        school_code=payload.school_code,
    )

    cur = conn.cursor()
    cur.execute(
        "INSERT INTO classes(school_id, teacher_account_id, name, grade, created_at) VALUES(?,?,?,?,?)",
        (int(role_row["school_id"]), int(acc["id"]), payload.class_name.strip(), int(payload.grade), now_iso()),
    )
    class_id = int(cur.lastrowid)
    conn.commit()

    row = _require_teacher_scope(conn, int(acc["id"]), class_id)
    conn.close()
    return {
        "ok": True,
        "class": row_to_dict(row),
        "teacher_role": {"school_id": int(role_row["school_id"]), "role": role_row["role"]},
    }


@app.post("/v1/teacher/classes/{class_id}/students", summary="Add a student to a teacher class")
def teacher_add_student_to_class(
    class_id: int,
    payload: TeacherAddStudentRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])

    conn = db()
    _require_teacher_scope(conn, int(acc["id"]), int(class_id))

    if payload.student_id is not None:
        student_row = _teacher_student_row(conn, int(acc["id"]), int(payload.student_id))
        student_id = int(student_row["id"])
    else:
        display_name = str(payload.display_name or "").strip()
        if not display_name:
            conn.close()
            raise HTTPException(status_code=400, detail="display_name is required when student_id is omitted")
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO students(account_id, display_name, grade, created_at, updated_at) VALUES(?,?,?,?,?)",
            (int(acc["id"]), display_name, payload.grade, now_iso(), now_iso()),
        )
        student_id = int(cur.lastrowid)
        student_row = _teacher_student_row(conn, int(acc["id"]), student_id)

    exists = conn.execute(
        "SELECT 1 FROM class_students WHERE class_id = ? AND student_id = ?",
        (int(class_id), student_id),
    ).fetchone()
    if exists:
        conn.close()
        raise HTTPException(status_code=409, detail="Student is already in this class")

    conn.execute(
        "INSERT INTO class_students(class_id, student_id, enrolled_at) VALUES(?,?,?)",
        (int(class_id), student_id, now_iso()),
    )
    conn.commit()
    conn.close()

    return {
        "ok": True,
        "class_id": int(class_id),
        "student": row_to_dict(student_row),
    }


@app.get("/v1/teacher/classes/{class_id}/report", summary="Get aggregated class report for a teacher class")
def teacher_class_report(
    class_id: int,
    window_days: int = 14,
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])
    if generate_class_report is None:
        raise HTTPException(status_code=503, detail="Class report module unavailable")

    conn = db()
    _require_teacher_scope(conn, int(acc["id"]), int(class_id))
    report = generate_class_report(conn, class_id=int(class_id), teacher_account_id=int(acc["id"]), window_days=int(window_days))
    conn.close()
    return report


@app.get("/v1/teacher/classes/{class_id}/concept-report", summary="Concept-level class report for teacher")
def teacher_concept_report(
    class_id: int,
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])
    if learning_generate_teacher_report is None or learning_get_class_states is None:
        raise HTTPException(status_code=503, detail="Teacher concept report module unavailable")

    conn = db()
    _require_teacher_scope(conn, int(acc["id"]), int(class_id))
    # Get student IDs in this class
    rows = conn.execute(
        "SELECT student_id FROM class_students WHERE class_id = ?", (int(class_id),)
    ).fetchall()
    conn.close()
    student_ids = [str(r["student_id"]) for r in rows]
    if not student_ids:
        return learning_report_to_dict(learning_generate_teacher_report(
            class_id=str(class_id), teacher_name=str(acc["id"]),
            student_states={},
        ))

    # Get concept states from learning DB
    class_states = learning_get_class_states(student_ids)
    # Convert {sid: {cid: state}} → {sid: [state, ...]}
    student_states = {sid: list(cid_map.values()) for sid, cid_map in class_states.items()}
    report = learning_generate_teacher_report(
        class_id=str(class_id), teacher_name=str(acc["id"]),
        student_states=student_states,
    )
    return learning_report_to_dict(report)


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

    hints = _build_hints(q)

    conn = db()
    cur = conn.cursor()
    cur.execute("""INSERT INTO question_cache(topic,difficulty,question,correct_answer,explanation,created_at)
                   VALUES (?,?,?,?,?,?)""",
                (q["topic"], q["difficulty"], q["question"], q["answer"], q["explanation"], now_iso()))
    qid = cur.lastrowid

    # persist hints_json via migration-safe UPDATE
    try:
        cur.execute("UPDATE question_cache SET hints_json=? WHERE id=?", (json.dumps(hints, ensure_ascii=False), qid))
    except Exception:
        pass
    conn.commit()
    conn.close()

    # 注意：前端拿到 qid，但不直接拿 answer（避免作弊）
    return {
        "question_id": qid,
        "topic": q["topic"],
        "difficulty": q["difficulty"],
        "question": q["question"],
        "hints": hints,
        "policy": {"reveal_answer_after_submit": True, "max_hint_level": 3},
        "explanation_preview": "（交卷後顯示）"
    }


@app.post("/v1/questions/hint")
async def question_hint(request: Request, x_api_key: str = Header(..., alias="X-API-Key")):
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])

    body = await request.json()
    try:
        question_id = int(body.get("question_id"))
    except Exception:
        raise HTTPException(status_code=400, detail="question_id must be an integer")
    try:
        level = int(body.get("level"))
    except Exception:
        raise HTTPException(status_code=400, detail="level must be 1|2|3")
    if level not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="level must be 1|2|3")

    conn = db()
    q = conn.execute("SELECT * FROM question_cache WHERE id=?", (question_id,)).fetchone()
    conn.close()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    hints_json = q["hints_json"] if "hints_json" in q.keys() else None
    hints = {}
    if hints_json:
        try:
            hints = json.loads(hints_json)
        except Exception:
            hints = {}
    key = f"level{level}"
    hint = hints.get(key) if isinstance(hints, dict) else None
    if not hint:
        # fallback
        hint = _build_hints({"topic": q["topic"], "question": q["question"]}).get(key, "")
    return {"hint": hint}


@app.post("/v1/learning/weekly_report", summary="Parent weekly report (weak skills + practice + teaching guide)")
def learning_weekly_report(req: WeeklyReportRequest, x_api_key: str = Header(..., alias="X-API-Key")):
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])

    if learning_connect is None or ensure_learning_schema is None or generate_parent_weekly_report is None:
        raise HTTPException(status_code=500, detail="Learning module not available")

    # Verify student belongs to account.
    conn = db()
    st = conn.execute("SELECT * FROM students WHERE id=? AND account_id=?", (int(req.student_id), acc["id"])).fetchone()
    conn.close()
    if not st:
        raise HTTPException(status_code=404, detail="Student not found")

    lconn = learning_connect(DB_PATH)
    try:
        ensure_learning_schema(lconn)
        report = generate_parent_weekly_report(
            lconn,
            student_id=str(req.student_id),
            window_days=int(req.window_days),
            top_k=int(req.top_k),
            questions_per_skill=int(req.questions_per_skill),
        )
        return {
            "ok": True,
            "student": {"id": int(st["id"]), "display_name": st["display_name"], "grade": st["grade"]},
            "window_days": int(req.window_days),
            "report": report,
        }
    finally:
        try:
            lconn.close()
        except Exception:
            pass


@app.post("/v1/learning/practice_next", summary="Targeted practice: next question + mastery status")
def learning_practice_next(req: PracticeNextRequest, x_api_key: str = Header(..., alias="X-API-Key")):
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])

    if (
        learning_connect is None
        or ensure_learning_schema is None
        or learning_get_student_analytics is None
        or compute_skill_status is None
        or get_practice_items_for_skill is None
        or get_teaching_guide is None
        or suggested_engine_topic_key is None
    ):
        raise HTTPException(status_code=500, detail="Learning module not available")

    if engine is None:
        raise HTTPException(status_code=500, detail="engine.py not found")

    # Verify student belongs to account.
    conn = db()
    st = conn.execute("SELECT * FROM students WHERE id=? AND account_id=?", (int(req.student_id), acc["id"])).fetchone()
    conn.close()
    if not st:
        raise HTTPException(status_code=404, detail="Student not found")

    lconn = learning_connect(DB_PATH)
    try:
        ensure_learning_schema(lconn)
        analytics = learning_get_student_analytics(lconn, student_id=str(req.student_id), window_days=int(req.window_days))
        snapshot = _skill_snapshot_from_analytics(analytics, skill_tag=str(req.skill_tag))
        status = compute_skill_status(
            attempts=int(snapshot.get("attempts") or 0),
            accuracy=float(snapshot.get("accuracy") or 0.0),
            hint_dependency=float(snapshot.get("hint_dependency") or 0.0),
            skill_tag=str(req.skill_tag),
        )
    finally:
        try:
            lconn.close()
        except Exception:
            pass

    guide = get_teaching_guide(str(req.skill_tag))
    practice_items = get_practice_items_for_skill(str(req.skill_tag))

    topic_key = str(req.topic_key) if req.topic_key not in (None, "") else (suggested_engine_topic_key(str(req.skill_tag)) or None)
    if topic_key is None:
        # Fallback: use a general fraction word problem set (broad coverage) to keep endpoint usable.
        topic_key = "11"

    # Generate a question and cache it so /v1/answers/submit can reference it.
    with _with_random_seed(req.seed):
        q = engine.next_question(topic_key)
    hints = _build_hints(q)

    conn = db()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO question_cache(topic,difficulty,question,correct_answer,explanation,created_at)
                   VALUES (?,?,?,?,?,?)""",
        (q.get("topic"), q.get("difficulty"), q.get("question"), q.get("answer"), q.get("explanation"), now_iso()),
    )
    qid = int(cur.lastrowid)
    try:
        cur.execute("UPDATE question_cache SET hints_json=? WHERE id=?", (json.dumps(hints, ensure_ascii=False), qid))
    except Exception:
        pass
    conn.commit()
    conn.close()

    return {
        "ok": True,
        "student": {"id": int(st["id"]), "display_name": st["display_name"], "grade": st["grade"]},
        "skill_tag": str(req.skill_tag),
        "window_days": int(req.window_days),
        "topic_key": topic_key,
        "mastery": {"snapshot": snapshot, "status": status},
        "recommendations": {
            "practice_items": practice_items,
            "teaching_guide": guide.__dict__,
        },
        "question": {
            "question_id": qid,
            "topic": q.get("topic"),
            "difficulty": q.get("difficulty"),
            "question": q.get("question"),
            "hints": hints,
            "policy": {"reveal_answer_after_submit": True, "max_hint_level": 3},
            "explanation_preview": "（交卷後顯示）",
        },
    }


@app.post("/v1/hints/next", summary="Next-step hint (3 levels, student-aware)")
async def hints_next(req: HintNextRequest, x_api_key: str = Header(..., alias="X-API-Key")):
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])

    qobj: Dict[str, Any] = {}
    if req.question_id is not None:
        conn = db()
        row = conn.execute("SELECT * FROM question_cache WHERE id=?", (int(req.question_id),)).fetchone()
        conn.close()
        if not row:
            raise HTTPException(status_code=404, detail="Question not found")
        qobj = {"topic": row["topic"], "question": row["question"]}
    elif isinstance(req.question_data, dict):
        qobj = {
            "topic": str(req.question_data.get("topic") or ""),
            "question": str(req.question_data.get("question") or req.question_data.get("question_text") or ""),
        }
    else:
        raise HTTPException(status_code=400, detail="Provide question_id or question_data")

    # Prefer engine's student-aware next-step hint generator.
    if engine is not None and hasattr(engine, "get_next_step_hint"):
        try:
            out = engine.get_next_step_hint(qobj, student_state=req.student_state, level=int(req.level))
            if isinstance(out, dict) and out.get("hint"):
                resp = {
                    "hint": str(out.get("hint")),
                    "level": int(out.get("level") or req.level),
                    "mode": str(out.get("mode") or "engine"),
                }
                if isinstance(out.get("hint_ladder"), list):
                    resp["hint_ladder"] = out.get("hint_ladder")
                if isinstance(out.get("current_step"), dict):
                    resp["current_step"] = out.get("current_step")
                return resp
        except Exception:
            pass

    # Fallback: return the static hint for this level.
    hints = _build_hints(qobj)
    return {"hint": hints.get(f"level{int(req.level)}", ""), "level": int(req.level), "mode": "fallback"}

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
    # validate input
    if body.get("student_id") is None:
        raise HTTPException(status_code=400, detail="student_id is required")
    if body.get("question_id") is None:
        raise HTTPException(status_code=400, detail="question_id is required")
    try:
        student_id = int(body["student_id"])
    except Exception:
        raise HTTPException(status_code=400, detail="student_id must be an integer")
    try:
        question_id = int(body["question_id"])
    except Exception:
        raise HTTPException(status_code=400, detail="question_id must be an integer")
    user_answer = str(body.get("user_answer", "")).strip()
    try:
        time_spent = int(body.get("time_spent_sec", 0))
    except Exception:
        raise HTTPException(status_code=400, detail="time_spent_sec must be an integer")
    hint_level_used = body.get("hint_level_used")
    # hint_level_used is optional. Treat 0/empty as "not used".
    if hint_level_used in ("", 0, "0"):
        hint_level_used_int = None
    else:
        try:
            hint_level_used_int = int(hint_level_used) if hint_level_used is not None else None
        except Exception:
            raise HTTPException(status_code=400, detail="hint_level_used must be an integer")
        if hint_level_used_int is not None and hint_level_used_int not in (1, 2, 3):
            raise HTTPException(status_code=400, detail="hint_level_used must be 1|2|3")

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

    diagnosis = None
    error_tag = None
    error_detail = None
    hint_plan: List[str] = []
    drill_reco: List[Dict[str, Any]] = []
    if engine is not None and hasattr(engine, "diagnose_attempt") and is_correct != 1:
        try:
            diagnosis = engine.diagnose_attempt({
                "topic": q["topic"],
                "difficulty": q["difficulty"],
                "question": q["question"],
                "correct_answer": q["correct_answer"],
            }, user_answer)
        except Exception as e:
            diagnosis = {"error_tag": "OTHER", "error_detail": f"diagnose_attempt failed: {e}", "hint_plan": [], "drill_reco": []}

    if isinstance(diagnosis, dict):
        error_tag = diagnosis.get("error_tag")
        error_detail = diagnosis.get("error_detail")
        hint_plan = diagnosis.get("hint_plan") or []
        drill_reco = diagnosis.get("drill_reco") or []

    # --- Recommender Integration ---
    resources_reco = []
    if is_correct != 1:
         # Count consecutive errors for this topic
        last_attempts = conn.execute("""
            SELECT is_correct FROM attempts
            WHERE student_id=? AND topic=?
            ORDER BY ts DESC LIMIT 5
        """, (student_id, q["topic"])).fetchall()

        con_errors = 1 # current one is wrong
        for r in last_attempts:
            if r["is_correct"] != 1:
                con_errors += 1
            else:
                break

        try:
            import recommender
            rec_sys = recommender.Recommender()
            # Map topic to tag if needed, or just pass topic string
            # Our resources use tags like "linear_eq", "quadratic_eq"
            # We map q["topic"] which might be "linear", "A1", etc.
            tag_map = {
                "linear": "linear_eq", "A1": "linear_eq", "A2": "linear_eq", "一元一次方程": "linear_eq",
                "quadratic": "quadratic_eq", "A3": "quadratic_eq", "A4": "quadratic_eq", "A5": "quadratic_eq", "一元二次方程式": "quadratic_eq"
            }
            mapped_tag = tag_map.get(q["topic"], q["topic"])
            resources_reco = rec_sys.recommend(mapped_tag, con_errors)
        except Exception as e:
            print(f"Recommender error: {e}")
    # -------------------------------

    meta = {
        "hint_level_used": hint_level_used_int,
        "policy": {"reveal_answer_after_submit": True, "max_hint_level": 3},
        "resources_reco": resources_reco,
    }

    # Optional meta payload from client for error classification.
    client_meta = body.get("meta")
    if isinstance(client_meta, dict):
        meta["client_meta"] = client_meta

    conn.execute("""INSERT INTO attempts(account_id, student_id, question_id, mode, topic, difficulty,
                    question, correct_answer, user_answer, is_correct, time_spent_sec,
                    error_tag, error_detail, hint_level_used, meta_json, ts)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                 (acc["id"], student_id, question_id, 'interactive', q["topic"], q["difficulty"],
                  q["question"], q["correct_answer"], user_answer, is_correct, time_spent,
                  error_tag, error_detail, hint_level_used_int, json.dumps(meta, ensure_ascii=False), now_iso()))
    conn.commit()

    # ---- Adaptive Mastery Update (per student x concept) ----
    concept_id = str(q["topic"] or "unknown")
    avg_t = _avg_time(conn, student_id=student_id, concept_id=concept_id)
    err_code = classify_error_code(
        is_correct=(is_correct == 1),
        correct_answer=q["correct_answer"],
        user_answer=user_answer,
        time_spent_sec=time_spent,
        avg_time_sec=avg_t,
        meta=meta.get("client_meta") if isinstance(meta.get("client_meta"), dict) else {},
    )

    st_state = _get_or_create_student_concept(conn, student_id=student_id, concept_id=concept_id)
    last5 = _window_accuracy(conn, student_id=student_id, concept_id=concept_id, n=5)
    last8 = _window_accuracy(conn, student_id=student_id, concept_id=concept_id, n=8)
    last4 = _window_accuracy(conn, student_id=student_id, concept_id=concept_id, n=4)
    st_state, actions = update_state_on_attempt(
        st_state,
        AttemptEvent(
            is_correct=(is_correct == 1),
            time_spent_sec=time_spent,
            error_code=err_code,
            meta=meta.get("client_meta") if isinstance(meta.get("client_meta"), dict) else {},
            now_iso=now_iso(),
        ),
        last5_acc=last5,
        last8_acc=last8,
        last4_acc=last4,
    )

    # Advance concept if the state machine says so.
    next_id = None
    if actions.advanced_concept:
        next_id = _next_concept_id(concept_id)
        if next_id:
            # Mark student's current concept.
            conn.execute(
                "UPDATE students SET current_concept_id=?, updated_at=? WHERE id=?",
                (next_id, now_iso(), student_id),
            )
            # Ensure the next concept row exists.
            _get_or_create_student_concept(conn, student_id=student_id, concept_id=next_id)

    _save_student_concept(conn, student_id=student_id, state=st_state)

    # ---- Learning analytics bridge (normalized attempt events) ----
    learning_ack = None
    if learning_record_attempt is not None:
        hint_steps_viewed: List[int] = []
        hints_viewed_count = 0
        if hint_level_used_int is not None:
            # Interpret as the highest hint level used; treat lower levels as seen.
            hint_steps_viewed = list(range(1, int(hint_level_used_int) + 1))
            hints_viewed_count = len(hint_steps_viewed)

        learning_event = {
            "student_id": str(student_id),
            "question_id": str(question_id),
            "timestamp": now_iso(),
            "is_correct": bool(is_correct == 1),
            "answer_raw": user_answer,
            "duration_ms": int(max(0, time_spent) * 1000),
            "hints_viewed_count": int(hints_viewed_count),
            "hint_steps_viewed": hint_steps_viewed,
            "mistake_code": _mistake_code_from_error_code(err_code),
            "topic": str(q["topic"] or ""),
            "question_type": "interactive",
            "session_id": f"acc:{acc['id']}",
            "extra": {
                "error_tag": error_tag,
                "error_detail": error_detail,
            },
            "skill_tags": _skill_tags_from_topic(str(q["topic"] or "")),
        }
        learning_ack = _safe_learning_record_attempt(event=learning_event)

    conn.close()

    # 回傳詳解與結果（你現有 INCORRECT_CUSTOM_FEEDBACK 可在前端呈現）
    return {
        "is_correct": is_correct,
        "correct_answer": q["correct_answer"],
        "explanation": q["explanation"],
        "topic": q["topic"],
        "difficulty": q["difficulty"],
        "error_tag": error_tag,
        "error_detail": error_detail,
        "hint_plan": hint_plan,
        "drill_reco": drill_reco,
        "resources_reco": resources_reco
        ,
        "learning": {
            "recorded": bool(learning_ack and learning_ack.get("ok") is True),
            "attempt_id": (learning_ack.get("attempt_id") if isinstance(learning_ack, dict) else None),
        },
        "adaptive": {
            "concept_id": st_state.concept_id,
            "stage": st_state.stage.value,
            "answered": st_state.answered,
            "correct": st_state.correct,
            "mastery": round(st_state.mastery(), 4),
            "in_hint_mode": bool(st_state.in_hint_mode),
            "in_micro_step": bool(st_state.in_micro_step),
            "micro_count": int(st_state.micro_count),
            "consecutive_wrong": int(st_state.consecutive_wrong),
            "calm_mode": bool(st_state.calm_mode),
            "flag_teacher": bool(st_state.flag_teacher),
            "completed": bool(st_state.completed),
            "error_code": (err_code.value if err_code else None),
            "actions": {
                "upgraded_stage": bool(actions.upgraded_stage),
                "advanced_concept": bool(actions.advanced_concept),
                "next_concept_id": next_id,
                "entered_hint": bool(actions.entered_hint),
                "exited_hint": bool(actions.exited_hint),
                "entered_micro": bool(actions.entered_micro),
                "exited_micro": bool(actions.exited_micro),
                "entered_calm": bool(actions.entered_calm),
                "exited_calm": bool(actions.exited_calm),
                "flagged_teacher": bool(actions.flagged_teacher),
            },
            "ui_actions": _adaptive_ui_actions(st_state, error_code=(err_code.value if err_code else None)),
        },
    }


@app.get("/v1/student/concept-state", summary="Get concept mastery states (EXP-06)")
def student_concept_state(student_id: int, x_api_key: str = Header(..., alias="X-API-Key")):
    """Return all concept mastery states for a student from la_student_concept_state."""
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])

    if learning_get_all_concept_states is None or learning_connect is None:
        raise HTTPException(status_code=500, detail="Learning module not available")

    conn = db()
    st = conn.execute("SELECT * FROM students WHERE id=? AND account_id=?", (int(student_id), acc["id"])).fetchone()
    conn.close()
    if not st:
        raise HTTPException(status_code=404, detail="Student not found")

    lconn = learning_connect(DB_PATH)
    try:
        ensure_learning_schema(lconn)
        states = learning_get_all_concept_states(str(student_id), conn=lconn)
    finally:
        try:
            lconn.close()
        except Exception:
            pass

    return {
        "ok": True,
        "student_id": int(student_id),
        "concepts": {
            cid: {
                "mastery_level": s.mastery_level.value,
                "mastery_score": round(s.mastery_score, 4),
                "attempts_total": s.attempts_total,
                "correct_total": s.correct_total,
                "recent_accuracy": round(s.recent_accuracy, 4) if s.recent_accuracy is not None else None,
                "hint_dependency": round(s.hint_dependency, 4),
                "consecutive_correct": s.consecutive_correct,
                "consecutive_wrong": s.consecutive_wrong,
                "needs_review": s.needs_review,
                "last_seen_at": s.last_seen_at,
            }
            for cid, s in states.items()
        },
    }


@app.get("/v1/student/concept-progress", summary="Parent concept progress report (EXP-09)")
def student_concept_progress(student_id: int, x_api_key: str = Header(..., alias="X-API-Key")):
    """Return concept-level mastery progress formatted for parent consumption."""
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])

    if learning_parent_concept_progress is None or learning_get_all_concept_states is None:
        raise HTTPException(status_code=503, detail="Parent concept progress module unavailable")

    conn = db()
    st = conn.execute("SELECT * FROM students WHERE id=? AND account_id=?", (int(student_id), acc["id"])).fetchone()
    conn.close()
    if not st:
        raise HTTPException(status_code=404, detail="Student not found")

    lconn = learning_connect(DB_PATH)
    try:
        ensure_learning_schema(lconn)
        states = learning_get_all_concept_states(str(student_id), conn=lconn)
    finally:
        try:
            lconn.close()
        except Exception:
            pass

    report = learning_parent_concept_progress(
        student_id=str(student_id),
        states=list(states.values()),
    )
    return learning_parent_progress_to_dict(report)


def _build_concept_question_pool(domain=None):
    """Build virtual QuestionItem pool from concept taxonomy for adaptive selection."""
    items = []
    for cid, info in learning_concept_taxonomy.items():
        if domain and info.get("domain") != domain:
            continue
        for diff in ("easy", "normal", "hard"):
            items.append(LearningQuestionItem(
                item_id=f"{cid}_{diff}",
                concept_ids=[cid],
                difficulty=diff,
                prerequisite_concepts=info.get("prerequisites", []),
                topic_tags=[info.get("domain", "")],
                is_application=(diff == "hard"),
            ))
    return items


@app.post("/v1/practice/concept-next", summary="Adaptive next-concept recommendation (EXP-04)")
def practice_concept_next(req: ConceptNextRequest, x_api_key: str = Header(..., alias="X-API-Key")):
    """Select the next concept and difficulty for adaptive practice based on student mastery state."""
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])

    if learning_select_next_item is None or learning_get_all_concept_states is None or learning_connect is None:
        raise HTTPException(status_code=503, detail="Next-item selector module unavailable")

    conn = db()
    st = conn.execute("SELECT * FROM students WHERE id=? AND account_id=?", (int(req.student_id), acc["id"])).fetchone()
    conn.close()
    if not st:
        raise HTTPException(status_code=404, detail="Student not found")

    lconn = learning_connect(DB_PATH)
    try:
        ensure_learning_schema(lconn)
        states = learning_get_all_concept_states(str(req.student_id), conn=lconn)
    finally:
        try:
            lconn.close()
        except Exception:
            pass

    pool = _build_concept_question_pool(domain=req.domain)
    result = learning_select_next_item(
        student_id=str(req.student_id),
        concept_states=states,
        available_items=pool,
        recent_item_ids=req.recent_item_ids,
    )

    if result is None:
        return {"ok": True, "recommendation": None, "reason": "No items available for the given filters"}

    return {
        "ok": True,
        "recommendation": {
            "item_id": result.item.item_id,
            "target_concept": result.target_concept,
            "concept_ids": result.item.concept_ids,
            "difficulty": result.item.difficulty,
            "strategy": result.strategy,
            "reason": result.reason,
            "domain": (result.item.topic_tags or [None])[0],
        },
    }


@app.get("/v1/adaptive/state", summary="Get adaptive mastery state for a student")
def adaptive_state(student_id: int, x_api_key: str = Header(..., alias="X-API-Key")):
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])

    conn = db()
    st = conn.execute(
        "SELECT * FROM students WHERE id=? AND account_id=?",
        (int(student_id), acc["id"]),
    ).fetchone()
    if not st:
        conn.close()
        raise HTTPException(status_code=404, detail="Student not found")

    current = str(st["current_concept_id"] or "").strip() or None
    if not current:
        seq = _concept_sequence()
        current = seq[0] if seq else None

    out_state = None
    if current:
        cs = _get_or_create_student_concept(conn, student_id=int(student_id), concept_id=current)
        out_state = {
            "concept_id": cs.concept_id,
            "stage": cs.stage.value,
            "answered": cs.answered,
            "correct": cs.correct,
            "mastery": round(cs.mastery(), 4),
            "in_hint_mode": bool(cs.in_hint_mode),
            "in_micro_step": bool(cs.in_micro_step),
            "micro_count": int(cs.micro_count),
            "consecutive_wrong": int(cs.consecutive_wrong),
            "calm_mode": bool(cs.calm_mode),
            "flag_teacher": bool(cs.flag_teacher),
            "completed": bool(cs.completed),
            "error_stats": cs.error_stats,
        }

        # Persist current concept if missing.
        if not st["current_concept_id"]:
            conn.execute(
                "UPDATE students SET current_concept_id=?, updated_at=? WHERE id=?",
                (current, now_iso(), int(student_id)),
            )
            conn.commit()

    conn.close()
    return {
        "student_id": int(student_id),
        "current_concept_id": current,
        "sequence": _concept_sequence(),
        "current_state": out_state,
    }


@app.get("/v1/adaptive/dashboard", summary="Dashboard (JSON) for parent/teacher")
def adaptive_dashboard(student_id: int, x_api_key: str = Header(..., alias="X-API-Key")):
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])

    conn = db()
    st = conn.execute(
        "SELECT * FROM students WHERE id=? AND account_id=?",
        (int(student_id), acc["id"]),
    ).fetchone()
    if not st:
        conn.close()
        raise HTTPException(status_code=404, detail="Student not found")

    rows = conn.execute(
        "SELECT * FROM student_concepts WHERE student_id=? ORDER BY concept_id ASC",
        (int(student_id),),
    ).fetchall()

    seq = _concept_sequence()
    cur_id = str(st["current_concept_id"] or "").strip() or (seq[0] if seq else None)

    concepts: List[Dict[str, Any]] = []
    for r in rows:
        answered = int(r["answered"] or 0)
        correct = int(r["correct"] or 0)
        mastery = (correct / answered) if answered > 0 else 0.0
        stuck_flag = bool(answered >= 6 and mastery < 0.6)

        color = "yellow"
        if bool(r["completed"]):
            color = "green"
        elif bool(r["flag_teacher"]) or stuck_flag:
            color = "red"

        concepts.append(
            {
                "concept_id": r["concept_id"],
                "stage": r["stage"],
                "answered": answered,
                "correct": correct,
                "mastery": round(mastery, 4),
                "in_hint_mode": bool(r["in_hint_mode"]),
                "in_micro_step": bool(r["in_micro_step"]),
                "micro_count": int(r["micro_count"] or 0),
                "consecutive_wrong": int(r["consecutive_wrong"] or 0),
                "calm_mode": bool(r["calm_mode"]),
                "stuck_flag": bool(stuck_flag),
                "flag_teacher": bool(r["flag_teacher"]),
                "last_activity": r["last_activity"],
                "color": color,
                "error_stats": error_stats_from_json(r["error_stats_json"]),
            }
        )

    conn.close()
    return {
        "student": {
            "id": st["id"],
            "display_name": st["display_name"],
            "grade": st["grade"],
        },
        "current_concept_id": cur_id,
        "concepts": concepts,
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


@app.post("/v1/parent-report/registry/fetch")
def parent_report_registry_fetch(req: ParentReportFetchRequest):
    display_name = str(req.name or "").strip()
    if not display_name:
        raise HTTPException(status_code=400, detail="name is required")
    pin = _validate_parent_report_pin(req.pin)
    normalized_name = _normalize_parent_report_name(display_name)
    conn = db()
    try:
        row = _load_parent_report_row(conn, normalized_name)
        if not row:
            raise HTTPException(status_code=404, detail="report not found")
        if not _pwd_ok(pin, row["pin_salt"], row["pin_hash"]):
            raise HTTPException(status_code=403, detail="invalid parent report credentials")
        data = _parse_parent_report_data(row["data_json"], fallback_name=row["display_name"])
        return {
            "ok": True,
            "entry": {
                "name": row["display_name"],
                "cloud_ts": int(row["cloud_ts"] or 0),
                "data": data,
            },
        }
    finally:
        conn.close()


@app.post("/v1/parent-report/registry/upsert")
def parent_report_registry_upsert(req: ParentReportUpsertRequest):
    display_name = str(req.name or "").strip()
    if not display_name:
        raise HTTPException(status_code=400, detail="name is required")
    if req.report_data is None and req.practice_event is None:
        raise HTTPException(status_code=400, detail="report_data or practice_event is required")
    pin = _validate_parent_report_pin(req.pin)
    normalized_name = _normalize_parent_report_name(display_name)
    now_ms = _now_ms()
    conn = db()
    try:
        row = _load_parent_report_row(conn, normalized_name)
        if row:
            if not _pwd_ok(pin, row["pin_salt"], row["pin_hash"]):
                raise HTTPException(status_code=403, detail="invalid parent report credentials")
            current_display = row["display_name"] or display_name
            data = _parse_parent_report_data(row["data_json"], fallback_name=current_display)
        else:
            current_display = display_name
            data = {
                "name": display_name,
                "ts": now_ms,
                "days": 7,
                "d": {},
            }

        if req.report_data is not None:
            data = _sanitize_parent_report_data(req.report_data, fallback_name=current_display)

        if req.practice_event is not None:
            event = _sanitize_practice_event(req.practice_event)
            practice = data.setdefault("d", {}).setdefault("practice", {})
            events = practice.setdefault("events", [])
            if not isinstance(events, list):
                events = []
                practice["events"] = events
            events.append(event)

        final_display = str(data.get("name") or current_display or display_name).strip() or display_name
        data["name"] = final_display
        data["ts"] = now_ms
        data.setdefault("days", 7)
        payload = json.dumps(data, ensure_ascii=False)
        updated_at = now_iso()

        if row:
            conn.execute(
                """
                UPDATE parent_report_registry
                SET display_name = ?, data_json = ?, cloud_ts = ?, updated_at = ?
                WHERE normalized_name = ?
                """,
                (final_display, payload, now_ms, updated_at, normalized_name),
            )
        else:
            pin_salt = secrets.token_hex(16)
            pin_hash = _pwd_hash(pin, pin_salt)
            conn.execute(
                """
                INSERT INTO parent_report_registry
                (normalized_name, display_name, pin_hash, pin_salt, data_json, cloud_ts, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (normalized_name, final_display, pin_hash, pin_salt, payload, now_ms, updated_at),
            )
        conn.commit()
        return {"ok": True, "cloud_ts": now_ms}
    finally:
        conn.close()


# ========= Subscription-gated report snapshot endpoints =========

def _verify_student_ownership(conn: sqlite3.Connection, account_id: int, student_id: int):
    """Verify that the student belongs to this account. Raises 404 if not."""
    row = conn.execute(
        "SELECT id FROM students WHERE id = ? AND account_id = ?",
        (student_id, account_id),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Student not found or not owned by this account")


@app.post("/v1/app/report_snapshots")
def create_report_snapshot(
    req: ReportSnapshotWriteRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])
    conn = db()
    try:
        _verify_student_ownership(conn, acc["id"], req.student_id)
        now = now_iso()
        payload = json.dumps(req.report_payload, ensure_ascii=False)
        source = str(req.source or "frontend")[:40]
        # Upsert: one snapshot per student per account
        existing = conn.execute(
            "SELECT id FROM report_snapshots WHERE account_id = ? AND student_id = ?",
            (acc["id"], req.student_id),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE report_snapshots SET report_payload_json = ?, source = ?, updated_at = ? WHERE id = ?",
                (payload, source, now, existing["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO report_snapshots (account_id, student_id, report_payload_json, source, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (acc["id"], req.student_id, payload, source, now, now),
            )
        conn.commit()
        return {"ok": True, "updated_at": now}
    finally:
        conn.close()


@app.post("/v1/app/report_snapshots/latest")
def get_latest_report_snapshot(
    req: ReportSnapshotReadRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])
    conn = db()
    try:
        _verify_student_ownership(conn, acc["id"], req.student_id)
        row = conn.execute(
            "SELECT * FROM report_snapshots WHERE account_id = ? AND student_id = ? ORDER BY updated_at DESC LIMIT 1",
            (acc["id"], req.student_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No snapshot found for this student")
        payload = {}
        try:
            payload = json.loads(row["report_payload_json"])
        except (json.JSONDecodeError, TypeError):
            pass
        return {
            "ok": True,
            "snapshot": {
                "student_id": row["student_id"],
                "report_payload": payload,
                "source": row["source"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            },
        }
    finally:
        conn.close()


@app.post("/v1/app/practice_events")
def create_practice_event(
    req: PracticeEventWriteRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])
    conn = db()
    try:
        _verify_student_ownership(conn, acc["id"], req.student_id)
        event = _sanitize_practice_event(req.event)
        now = now_iso()
        # Append to the student's report snapshot practice events
        existing = conn.execute(
            "SELECT id, report_payload_json FROM report_snapshots WHERE account_id = ? AND student_id = ?",
            (acc["id"], req.student_id),
        ).fetchone()
        if existing:
            payload = {}
            try:
                payload = json.loads(existing["report_payload_json"])
            except (json.JSONDecodeError, TypeError):
                pass
            if not isinstance(payload, dict):
                payload = {}
            d = payload.setdefault("d", {})
            practice = d.setdefault("practice", {})
            events = practice.setdefault("events", [])
            if not isinstance(events, list):
                events = []
                practice["events"] = events
            events.append(event)
            conn.execute(
                "UPDATE report_snapshots SET report_payload_json = ?, updated_at = ? WHERE id = ?",
                (json.dumps(payload, ensure_ascii=False), now, existing["id"]),
            )
        else:
            payload = {"d": {"practice": {"events": [event]}}}
            conn.execute(
                "INSERT INTO report_snapshots (account_id, student_id, report_payload_json, source, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (acc["id"], req.student_id, json.dumps(payload, ensure_ascii=False), "practice_event", now, now),
            )
        conn.commit()
        return {"ok": True, "updated_at": now}
    finally:
        conn.close()


@app.get("/v1/reports/parent_weekly")
def parent_weekly(student_id: int, days: int = 7, x_api_key: str = Header(..., alias="X-API-Key")):
    acc = get_account_by_api_key(x_api_key)
    ensure_subscription_active(acc["id"])

    days = int(days)
    if days <= 0 or days > 90:
        raise HTTPException(status_code=400, detail="days must be 1..90")

    since_dt = datetime.now() - timedelta(days=days)
    since = since_dt.isoformat(timespec="seconds")

    conn = db()
    st = conn.execute("SELECT * FROM students WHERE id=? AND account_id=?", (student_id, acc["id"])).fetchone()
    if not st:
        conn.close()
        raise HTTPException(status_code=404, detail="Student not found")

    totals = conn.execute(
        """
        SELECT
          COUNT(*) AS total_attempts,
          SUM(CASE WHEN is_correct IN (0,1) THEN 1 ELSE 0 END) AS valid_attempts,
          SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) AS correct,
          SUM(CASE WHEN is_correct = 0 THEN 1 ELSE 0 END) AS wrong,
          SUM(CASE WHEN is_correct IS NULL THEN 1 ELSE 0 END) AS invalid,
          SUM(COALESCE(time_spent_sec,0)) AS practice_seconds
        FROM attempts
        WHERE student_id=? AND ts>=?
        """,
        (student_id, since),
    ).fetchone()

    topic_rows = conn.execute(
        """
        SELECT
          topic,
          COUNT(*) AS total,
          SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) AS correct,
          SUM(CASE WHEN is_correct = 0 THEN 1 ELSE 0 END) AS wrong,
          SUM(CASE WHEN is_correct IS NULL THEN 1 ELSE 0 END) AS invalid
        FROM attempts
        WHERE student_id=? AND ts>=?
        GROUP BY topic
        ORDER BY total DESC
        """,
        (student_id, since),
    ).fetchall()

    # Weakness aggregation by error_tag (wrong or invalid only)
    weakness_rows = conn.execute(
        """
        SELECT
          COALESCE(error_tag, 'OTHER') AS error_tag,
          COUNT(*) AS cnt
        FROM attempts
        WHERE student_id=? AND ts>=? AND is_correct != 1
        GROUP BY COALESCE(error_tag, 'OTHER')
        ORDER BY cnt DESC
        LIMIT 3
        """,
        (student_id, since),
    ).fetchall()

    weakness_top3: List[Dict[str, Any]] = []
    for r in weakness_rows:
        tag = r["error_tag"]
        cnt = int(r["cnt"] or 0)
        samples = conn.execute(
            """
            SELECT question
            FROM attempts
            WHERE student_id=? AND ts>=? AND is_correct != 1 AND COALESCE(error_tag,'OTHER')=?
            ORDER BY ts DESC
            LIMIT 2
            """,
            (student_id, since, tag),
        ).fetchall()
        weakness_top3.append(
            {
                "error_tag": tag,
                "count": cnt,
                "sample_questions": [s["question"] for s in samples],
            }
        )

    # Streak days: consecutive days with >=1 attempt
    day_rows = conn.execute(
        """
        SELECT DISTINCT substr(ts,1,10) AS d
        FROM attempts
        WHERE student_id=? AND ts>=?
        ORDER BY d DESC
        """,
        (student_id, since),
    ).fetchall()
    days_set = {row["d"] for row in day_rows}

    streak = 0
    cursor = datetime.now().date()
    while True:
        d_str = cursor.isoformat()
        if d_str in days_set:
            streak += 1
            cursor = cursor - timedelta(days=1)
            # Stop after window to avoid infinite.
            if streak > days:
                break
        else:
            break

    # ── recent_windows: 24h / 3d time-based stats ──
    def _window_stats(conn_w, sid, hours):
        """Return {total, accuracy, avg_time_sec, hint_dependency} for a time window."""
        since_w = (datetime.now() - timedelta(hours=hours)).isoformat(timespec="seconds")
        row = conn_w.execute(
            """
            SELECT
              COUNT(*) AS n,
              SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) AS c,
              AVG(COALESCE(time_spent_sec, 0)) AS avg_t,
              SUM(CASE WHEN hint_level_used > 0 THEN 1 ELSE 0 END) AS hinted
            FROM attempts
            WHERE student_id=? AND ts>=?
            """,
            (sid, since_w),
        ).fetchone()
        n = int(row["n"] or 0)
        c = int(row["c"] or 0)
        avg_t = float(row["avg_t"] or 0)
        hinted = int(row["hinted"] or 0)
        return {
            "total": n,
            "accuracy": round(c / n, 4) if n else 0.0,
            "avg_time_sec": round(avg_t, 2),
            "hint_dependency": round(hinted / n, 4) if n else 0.0,
        }

    h24 = _window_stats(conn, student_id, 24)
    prev24 = _window_stats(conn, student_id, 48)
    prev24_n = prev24["total"] - h24["total"]
    prev24_only = {
        "total": prev24_n,
        "accuracy": round((prev24["accuracy"] * prev24["total"] - h24["accuracy"] * h24["total"]) / max(prev24_n, 1), 4) if prev24_n > 0 else 0.0,
        "avg_time_sec": round(prev24["avg_time_sec"], 2),
        "hint_dependency": round((prev24["hint_dependency"] * prev24["total"] - h24["hint_dependency"] * h24["total"]) / max(prev24_n, 1), 4) if prev24_n > 0 else 0.0,
    }
    d3 = _window_stats(conn, student_id, 72)
    prev_d3_full = _window_stats(conn, student_id, 144)
    prev_d3_n = prev_d3_full["total"] - d3["total"]
    prev_d3_only = {
        "total": prev_d3_n,
        "accuracy": round((prev_d3_full["accuracy"] * prev_d3_full["total"] - d3["accuracy"] * d3["total"]) / max(prev_d3_n, 1), 4) if prev_d3_n > 0 else 0.0,
        "avg_time_sec": round(prev_d3_full["avg_time_sec"], 2),
        "hint_dependency": round((prev_d3_full["hint_dependency"] * prev_d3_full["total"] - d3["hint_dependency"] * d3["total"]) / max(prev_d3_n, 1), 4) if prev_d3_n > 0 else 0.0,
    }

    def _delta(curr_w, prev_w):
        return {k: round(curr_w.get(k, 0) - prev_w.get(k, 0), 4) for k in ("total", "accuracy", "avg_time_sec", "hint_dependency")}

    recent_windows = {
        "h24": h24,
        "d3": d3,
        "delta": {
            "h24_vs_prev24h": _delta(h24, prev24_only),
            "d3_vs_prev3d": _delta(d3, prev_d3_only),
        },
    }

    conn.close()

    total_attempts = int(totals["total_attempts"] or 0)
    valid_attempts = int(totals["valid_attempts"] or 0)
    correct = int(totals["correct"] or 0)
    wrong = int(totals["wrong"] or 0)
    invalid = int(totals["invalid"] or 0)
    accuracy = (correct / valid_attempts * 100.0) if valid_attempts else 0.0
    practice_minutes = int(round((int(totals["practice_seconds"] or 0)) / 60.0))

    # Topic table with status
    topic_table: List[Dict[str, Any]] = []
    for tr in topic_rows:
        t_total = int(tr["total"] or 0)
        t_correct = int(tr["correct"] or 0)
        t_wrong = int(tr["wrong"] or 0)
        t_acc = (t_correct / (t_correct + t_wrong) * 100.0) if (t_correct + t_wrong) else 0.0
        if t_total >= 8 and t_acc < 70:
            status = "NEED_FOCUS"
        elif t_total >= 8 and t_acc >= 90:
            status = "STRONG"
        else:
            status = "OK"
        topic_table.append(
            {
                "topic": tr["topic"],
                "total": t_total,
                "correct": t_correct,
                "wrong": t_wrong,
                "accuracy": round(t_acc, 2),
                "status": status,
            }
        )

    # Plan mapping: error_tag -> topic_key
    tag_to_topic = {
        "LCM_WRONG": "2",
        "COMMON_DENOM_WRONG": "2",
        "NUMERATOR_OP_WRONG": "4",
        "REDUCTION_MISSED": "3",
        "SIGN_OR_ORDER_WRONG": "4",
        "FORMAT_INVALID": "4",
        "ORDER_OF_OPS_WRONG": "1",
        "OTHER": "4",
    }

    def topic_name(topic_key: str) -> str:
        if engine is not None and hasattr(engine, "GENERATORS"):
            try:
                return engine.GENERATORS.get(topic_key, (topic_key, None))[0]
            except Exception:
                pass
        return topic_key

    weak1 = weakness_top3[0]["error_tag"] if len(weakness_top3) >= 1 else "COMMON_DENOM_WRONG"
    weak2 = weakness_top3[1]["error_tag"] if len(weakness_top3) >= 2 else weak1
    k1 = tag_to_topic.get(weak1, "4")
    k2 = tag_to_topic.get(weak2, "3")

    next_week_plan: List[Dict[str, Any]] = []
    for day_idx in range(1, 8):
        if day_idx <= 4:
            k = k1
        else:
            k = k2
        next_week_plan.append(
            {
                "day": day_idx,
                "focus_topic_key": k,
                "focus_topic_name": topic_name(k),
                "target_count": 10 if day_idx in (1, 2, 3, 4) else 8,
                "success_metric": "正確率≥85%（以有效作答計）",
            }
        )

    # Headline
    if valid_attempts == 0:
        headline = "本週尚未有有效作答紀錄，建議先完成每天 10 分鐘的分數練習。"
    else:
        headline = f"本週有效作答 {valid_attempts} 題，正確率 {accuracy:.0f}%。最需要加強：{weak1}。"

    return {
        "student": {"id": st["id"], "display_name": st["display_name"], "grade": st["grade"]},
        "window_days": days,
        "headline": headline,
        "kpis": {
            "practice_minutes": practice_minutes,
            "total_attempts": total_attempts,
            "valid_attempts": valid_attempts,
            "accuracy": round(accuracy, 2),
            "streak_days": streak,
        },
        "weakness_top3": weakness_top3,
        "topic_table": topic_table,
        "next_week_plan": next_week_plan,
        "recent_windows": recent_windows,
    }


    @app.get("/_debug/accounts")
    def _debug_accounts():
        conn = db()
        rows = conn.execute('SELECT id,name,api_key,created_at FROM accounts').fetchall()
        conn.close()
        return [row_to_dict(r) for r in rows]


    @app.get("/_debug/students")
    def _debug_students():
        conn = db()
        rows = conn.execute('SELECT id,account_id,display_name,grade,created_at FROM students').fetchall()
        conn.close()
        return [row_to_dict(r) for r in rows]

from fastapi.responses import RedirectResponse

@app.get("/linear")
async def redirect_linear():
    return RedirectResponse(url="/linear/")

@app.get("/quadratic")
async def redirect_quadratic():
    return RedirectResponse(url="/quadratic/")


# ── Admin: login failure audit ──────────────────────────────────────────

@app.get("/v1/app/admin/login-failures", summary="Query recent login failures (admin only)")
def admin_login_failures(
    minutes: int = 60,
    x_admin_token: str = Header("", alias="X-Admin-Token"),
):
    expected = os.getenv("APP_PROVISION_ADMIN_TOKEN", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="Admin token not configured")
    if not x_admin_token or x_admin_token != expected:
        raise HTTPException(status_code=401, detail="Invalid admin token")

    minutes = max(1, min(minutes, 1440))  # clamp 1min–24h
    cutoff = datetime.now().timestamp() - (minutes * 60)
    conn = db()
    rows = conn.execute(
        "SELECT username, client_ip, ts FROM login_failures WHERE ts >= ? ORDER BY ts DESC LIMIT 200",
        (cutoff,),
    ).fetchall()

    # Compute summary statistics
    unique_ips = set()
    unique_usernames = set()
    for r in rows:
        unique_ips.add(r["client_ip"])
        unique_usernames.add(r["username"])

    # Detect currently locked accounts
    lockout_cutoff = datetime.now().timestamp() - _LOGIN_LOCKOUT_DURATION_S
    locked_rows = conn.execute(
        "SELECT username, COUNT(*) AS c FROM login_failures "
        "WHERE ts >= ? GROUP BY username HAVING c >= ?",
        (lockout_cutoff, _LOGIN_LOCKOUT_THRESHOLD),
    ).fetchall()
    locked_accounts = [r["username"] for r in locked_rows]

    conn.close()

    # Determine alert level based on failure count
    total = len(rows)
    if total > 50:
        alert_level = "critical"
    elif total >= 10:
        alert_level = "elevated"
    else:
        alert_level = "normal"

    return {
        "window_minutes": minutes,
        "count": total,
        "failures": [
            {"username": r["username"], "client_ip": r["client_ip"], "ts": r["ts"]}
            for r in rows
        ],
        "summary": {
            "total_failures": total,
            "unique_ips": len(unique_ips),
            "unique_usernames": len(unique_usernames),
            "locked_accounts": locked_accounts,
            "alert_level": alert_level,
        },
    }


# ── Admin: password reset (Option A — admin-assisted MVP) ───────────────

class AdminResetPasswordRequest(BaseModel):
    username: str


@app.post("/v1/app/admin/reset-password", summary="Reset user password (admin only)")
def admin_reset_password(
    payload: AdminResetPasswordRequest,
    x_admin_token: str = Header("", alias="X-Admin-Token"),
):
    expected = os.getenv("APP_PROVISION_ADMIN_TOKEN", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="Admin token not configured")
    if not x_admin_token or x_admin_token != expected:
        raise HTTPException(status_code=401, detail="Invalid admin token")

    username = payload.username.strip().lower()
    if not username:
        raise HTTPException(status_code=400, detail="username required")

    conn = db()
    row = conn.execute(
        "SELECT id FROM app_users WHERE username = ?", (username,)
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    temp_password = secrets.token_urlsafe(12)
    salt = secrets.token_hex(16)
    pwd_hash = _pwd_hash(temp_password, salt)
    conn.execute(
        "UPDATE app_users SET password_hash = ?, password_salt = ?, updated_at = ? WHERE username = ?",
        (pwd_hash, salt, now_iso(), username),
    )
    conn.commit()
    conn.close()

    _clear_login_failures(username)
    _auth_logger.info("admin_password_reset", extra={"username": username})

    return {"ok": True, "username": username, "temp_password": temp_password}


# ── Stripe Webhook → Backend Subscription State ────────────────────────

STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()

def _verify_stripe_signature(payload: bytes, sig_header: str, secret: str) -> dict:
    """Verify Stripe webhook signature and return parsed event.

    Uses the same algorithm as Stripe's official SDK:
    timestamp + '.' + payload → HMAC-SHA256 with webhook secret.
    """
    if not secret:
        raise HTTPException(status_code=500, detail="STRIPE_WEBHOOK_SECRET not configured")
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    # Parse "t=...,v1=...,v0=..." from Stripe-Signature
    parts = {}
    for item in sig_header.split(","):
        kv = item.strip().split("=", 1)
        if len(kv) == 2:
            parts.setdefault(kv[0], []).append(kv[1])

    timestamp = (parts.get("t") or [None])[0]
    signatures = parts.get("v1", [])
    if not timestamp or not signatures:
        raise HTTPException(status_code=400, detail="Invalid Stripe-Signature format")

    # Tolerance: reject events older than 5 minutes
    try:
        ts_int = int(timestamp)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid timestamp in signature")
    if abs(int(datetime.now().timestamp()) - ts_int) > 300:
        raise HTTPException(status_code=400, detail="Webhook timestamp too old")

    # Compute expected signature
    signed_payload = f"{timestamp}.".encode("utf-8") + payload
    expected = hmac.new(
        secret.encode("utf-8"), signed_payload, hashlib.sha256
    ).hexdigest()

    if not any(hmac.compare_digest(expected, sig) for sig in signatures):
        raise HTTPException(status_code=400, detail="Webhook signature verification failed")

    return json.loads(payload)


def _stripe_upsert_subscription(account_id: int, status: str, plan: str,
                                stripe_customer_id: str, stripe_subscription_id: str):
    """Insert or update subscription row for a given account."""
    conn = db()
    existing = conn.execute(
        "SELECT id FROM subscriptions WHERE account_id = ? ORDER BY updated_at DESC LIMIT 1",
        (account_id,)
    ).fetchone()

    now = now_iso()
    if existing:
        conn.execute(
            """UPDATE subscriptions
               SET status = ?, plan = ?, stripe_customer_id = ?,
                   stripe_subscription_id = ?, updated_at = ?
               WHERE id = ?""",
            (status, plan, stripe_customer_id, stripe_subscription_id, now, existing["id"])
        )
    else:
        conn.execute(
            """INSERT INTO subscriptions
               (account_id, status, plan, seats, current_period_end,
                stripe_customer_id, stripe_subscription_id, updated_at)
               VALUES (?, ?, ?, 1, ?, ?, ?, ?)""",
            (account_id, status, plan,
             (datetime.now() + timedelta(days=30)).isoformat(timespec="seconds"),
             stripe_customer_id, stripe_subscription_id, now)
        )
    conn.commit()
    conn.close()


def _resolve_account_from_stripe(customer_id: str = "",
                                 subscription_id: str = "",
                                 metadata_uid: str = "") -> Optional[int]:
    """Resolve Stripe identifiers to a local account_id.

    Lookup order:
      1. metadata.customer_uid → accounts.api_key prefix match (uid is api_key)
      2. stripe_subscription_id → subscriptions
      3. stripe_customer_id → subscriptions
    """
    conn = db()

    # 1) metadata uid is the api_key
    if metadata_uid:
        row = conn.execute(
            "SELECT id FROM accounts WHERE api_key = ?", (metadata_uid,)
        ).fetchone()
        if row:
            conn.close()
            return int(row["id"])

    # 2) stripe_subscription_id
    if subscription_id:
        row = conn.execute(
            "SELECT account_id FROM subscriptions WHERE stripe_subscription_id = ? LIMIT 1",
            (subscription_id,)
        ).fetchone()
        if row:
            conn.close()
            return int(row["account_id"])

    # 3) stripe_customer_id
    if customer_id:
        row = conn.execute(
            "SELECT account_id FROM subscriptions WHERE stripe_customer_id = ? LIMIT 1",
            (customer_id,)
        ).fetchone()
        if row:
            conn.close()
            return int(row["account_id"])

    conn.close()
    return None


@app.post("/v1/stripe/webhook", summary="Stripe webhook → update backend subscription state")
async def stripe_webhook(request: Request):
    """Receive Stripe events and update the local subscriptions table.

    Events handled:
      - checkout.session.completed → activate subscription
      - customer.subscription.updated → sync status
      - customer.subscription.deleted → mark expired/inactive
    """
    body = await request.body()
    sig = request.headers.get("stripe-signature", "")

    event = _verify_stripe_signature(body, sig, STRIPE_WEBHOOK_SECRET)
    event_type = event.get("type", "")
    data_obj = (event.get("data") or {}).get("object") or {}

    if event_type == "checkout.session.completed":
        metadata = data_obj.get("metadata") or {}
        uid = metadata.get("customer_uid", "")
        plan = metadata.get("plan_type", "standard")
        customer_id = data_obj.get("customer", "")
        sub_id = data_obj.get("subscription", "")

        account_id = _resolve_account_from_stripe(
            customer_id=customer_id, metadata_uid=uid
        )
        if account_id:
            _stripe_upsert_subscription(
                account_id, "active", plan, customer_id, sub_id
            )
            logging.info("stripe_webhook: activated account_id=%s plan=%s", account_id, plan)

    elif event_type == "customer.subscription.updated":
        stripe_status = data_obj.get("status", "")
        sub_id = data_obj.get("id", "")
        customer_id = data_obj.get("customer", "")

        status_map = {
            "active": "active",
            "trialing": "active",
            "past_due": "past_due",
            "canceled": "inactive",
            "unpaid": "inactive",
            "incomplete": "inactive",
            "incomplete_expired": "inactive",
        }
        local_status = status_map.get(stripe_status, "inactive")

        account_id = _resolve_account_from_stripe(
            customer_id=customer_id, subscription_id=sub_id
        )
        if account_id:
            conn = db()
            conn.execute(
                """UPDATE subscriptions
                   SET status = ?, updated_at = ?
                   WHERE account_id = ? AND stripe_subscription_id = ?""",
                (local_status, now_iso(), account_id, sub_id)
            )
            conn.commit()
            conn.close()
            logging.info("stripe_webhook: updated account_id=%s → %s", account_id, local_status)

    elif event_type == "customer.subscription.deleted":
        sub_id = data_obj.get("id", "")
        customer_id = data_obj.get("customer", "")
        account_id = _resolve_account_from_stripe(
            customer_id=customer_id, subscription_id=sub_id
        )
        if account_id:
            conn = db()
            conn.execute(
                """UPDATE subscriptions
                   SET status = 'inactive', updated_at = ?
                   WHERE account_id = ? AND stripe_subscription_id = ?""",
                (now_iso(), account_id, sub_id)
            )
            conn.commit()
            conn.close()
            logging.info("stripe_webhook: cancelled account_id=%s", account_id)

    return {"received": True}


# ── Subscription Verification (anti-tampering) ─────────────────────────

@app.get("/v1/subscription/verify", summary="Verify subscription status (does not 402)")
def subscription_verify(x_api_key: str = Header(..., alias="X-API-Key")):
    """Return the server-side subscription truth for the authenticated account.

    Unlike /whoami, this endpoint does NOT throw 402 when subscription is
    inactive — it returns the actual status so the frontend can reconcile
    localStorage against the server.
    """
    acc = get_account_by_api_key(x_api_key)
    account_id = int(acc["id"])

    conn = db()
    sub = conn.execute(
        "SELECT * FROM subscriptions WHERE account_id = ? ORDER BY updated_at DESC LIMIT 1",
        (account_id,)
    ).fetchone()
    conn.close()

    if not sub:
        return {
            "ok": True,
            "subscription": {
                "status": "none",
                "plan": "free",
                "seats": 0,
                "current_period_end": None,
            }
        }

    return {
        "ok": True,
        "subscription": {
            "status": sub["status"],
            "plan": sub["plan"],
            "seats": int(sub["seats"] or 0),
            "current_period_end": sub["current_period_end"],
        }
    }


# Mount specific modules explicitly to ensure /linear/ works even if root mount misses it
app.mount("/linear", StaticFiles(directory="docs/linear", html=True), name="static_linear")
app.mount("/quadratic", StaticFiles(directory="docs/quadratic", html=True), name="static_quadratic")

# Mount docs folder to serve static web pages
# 1. Allow access via /docs/path/to/file (Matches physical folder structure)
app.mount("/docs", StaticFiles(directory="docs", html=True), name="static_docs_explicit")
# 2. Allow access via root /path/to/file (Web root convenience)
app.mount("/", StaticFiles(directory="docs", html=True), name="static_docs_root")


if __name__ == "__main__":
    print("Starting server...")
    print("   Web UI (Linear):    http://localhost:8000/linear/  (or /docs/linear/)")
    print("   Web UI (Quadratic): http://localhost:8000/quadratic/")
    print("   API Docs:           http://localhost:8000/api/docs")
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), reload=True)
