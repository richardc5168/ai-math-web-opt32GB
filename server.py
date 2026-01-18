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
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, Field

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


def _build_hints(q: Dict[str, Any]) -> Dict[str, str]:
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

# ========= 5) API =========
@app.get("/health")
def health():
    return {"ok": True, "ts": now_iso()}


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


@app.get("/", response_class=HTMLResponse)
def index():
    html = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
        <title>分數練習（學生端）</title>
        <style>
            body{font-family:Segoe UI,Helvetica,Arial; padding:18px; line-height:1.5}
            button{margin:6px}
            .row{margin:10px 0}
            .card{background:#f6f8fa;padding:12px;border:1px solid #ddd;border-radius:6px;max-width:880px}
            .muted{color:#666}
            input{padding:6px}
            .label{display:inline-block; min-width:110px}
            .ok{color:#0a7f2e}
            .bad{color:#b42318}
        </style>
  </head>
  <body>
        <h2>分數練習（學生端）</h2>

        <div class="card" id="app"></div>

        <script>
            function nowMs(){ return Date.now(); }
            function escapeHtml(s){
                return String(s || '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
            }

            const appEl = document.getElementById('app');

            const state = {
                step: 0,            // 0 intro, 1 task, 2 question, 3 summary
                total: 5,           // fixed mission length (簡單可控)
                q_index: 0,
                questions: [],      // {question_id, topic, difficulty, question}
                history: [],        // {question_id, question, topic, difficulty, user_answer, is_correct, error_tag, error_detail, ts}
                started_at_ms: null,
                current_input: '',
                last_short_feedback: '',
                retry_mode: 'all',  // 'all' or 'wrong'
            };

            function init_state(){
                // Restore saved setup.
                state.api_key = localStorage.getItem('rag_api_key') || '';
                state.student_id = localStorage.getItem('rag_student_id') || '';
                state.topic_key = localStorage.getItem('rag_topic_key') || '2';
            }

            function save_setup(apiKey, studentId, topicKey){
                localStorage.setItem('rag_api_key', String(apiKey || '').trim());
                localStorage.setItem('rag_student_id', String(studentId || '').trim());
                localStorage.setItem('rag_topic_key', String(topicKey || '').trim());
            }

            async function apiFetch(path, opts){
                const key = (state.api_key || '').trim();
                const headers = Object.assign({}, (opts && opts.headers) || {});
                if (key) headers['X-API-Key'] = key;
                return fetch(path, Object.assign({}, opts || {}, { headers }));
            }

            function mustGetSetupFromUI(){
                const apiKey = (document.getElementById('apiKey')?.value || '').trim();
                const studentId = (document.getElementById('studentId')?.value || '').trim();
                const topicKey = (document.getElementById('topicKey')?.value || '').trim();
                state.api_key = apiKey;
                state.student_id = studentId;
                state.topic_key = topicKey;
                save_setup(apiKey, studentId, topicKey);
            }

            function reset_run(){
                state.q_index = 0;
                state.questions = [];
                state.history = [];
                state.started_at_ms = null;
                state.current_input = '';
                state.last_short_feedback = '';
                state.retry_mode = 'all';
            }

            function restart_from_summary(mode){
                // mode: 'all' or 'wrong'
                state.retry_mode = mode;
                state.q_index = 0;
                state.current_input = '';
                state.last_short_feedback = '';
                state.started_at_ms = nowMs();

                if(mode === 'wrong'){
                    const wrong = state.history.filter(x => x.is_correct !== 1);
                    state.questions = wrong.map(x => ({
                        question_id: x.question_id,
                        topic: x.topic,
                        difficulty: x.difficulty,
                        question: x.question,
                    }));
                    state.total = state.questions.length || 1;
                    state.history = [];
                }else{
                    state.total = 5;
                    state.questions = [];
                    state.history = [];
                }
                state.step = 2;
                render();
            }

            function render_intro(){
                const apiKey = escapeHtml(state.api_key);
                const studentId = escapeHtml(state.student_id);
                const topicKey = escapeHtml(state.topic_key);
                return `
                    <div class="row"><b>Step 0｜提醒說明</b></div>
                    <div class="row muted">
                        <div>1) 這是一個「練習頁」，一次只做一題。</div>
                        <div>2) 先想一想再輸入答案，輸入後按 Enter 就會進下一題。</div>
                        <div>3) 題目頁不會顯示歷史訊息，避免分心。</div>
                    </div>

                    <div class="row"><b>基本設定</b></div>
                    <div class="row">
                        <span class="label">註冊碼（Key）</span>
                        <input id="apiKey" style="width:520px" value="${apiKey}" placeholder="請貼上註冊碼，或點右邊『取得註冊碼』" />
                        <button id="btnBootstrap">取得註冊碼</button>
                    </div>
                    <div class="row">
                        <span class="label">學生編號</span>
                        <input id="studentId" style="width:120px" value="${studentId}" placeholder="例如 1" />
                        <button id="btnLoadStudents">自動讀取</button>
                        <span id="studentName" class="muted"></span>
                    </div>
                    <div class="row">
                        <span class="label">題型（可空）</span>
                        <input id="topicKey" style="width:120px" value="${topicKey}" />
                        <span class="muted">（例如：2＝分數通分/加減；空白＝隨機）</span>
                    </div>

                    <div class="row">
                        <button id="btnGoTask">開始</button>
                        <span id="introError" class="bad"></span>
                    </div>
                `;
            }

            function render_task(){
                return `
                    <div class="row"><b>Step 1｜任務說明</b></div>
                    <div class="row">
                        <div><b>任務目標：</b>完成 ${state.total} 題練習。</div>
                        <div class="muted">規則：題目頁一次只顯示 1 題；按 Enter 送出後會直接進下一題。</div>
                        <div class="muted">提醒：如果卡住，先把題目分成小步驟（先算括號/先通分/先把一部分算完）。</div>
                    </div>
                    <div class="row">
                        <button id="btnStartAnswer">開始作答</button>
                        <button id="btnBackIntro">回到提醒頁</button>
                    </div>
                `;
            }

            function render_question(){
                const q = state.questions[state.q_index];
                const idx = state.q_index + 1;
                const total = state.total;
                const qText = q ? escapeHtml(q.question) : '';
                const placeholder = '例如：3/5 或 -4 或 1 1/2';

                return `
                    <div class="row"><b>Step 2｜題目頁</b></div>
                    <div class="row"><b>進度：</b>第 ${idx}/${total} 題</div>
                    <div class="row" style="font-size:20px; margin:8px 0"><b>題幹：</b> ${qText}</div>

                    <div class="row">
                        <span class="label">你的答案</span>
                        <input id="userAnswer" style="width:260px" placeholder="${escapeHtml(placeholder)}" value="" autofocus />
                        <button id="btnSubmit">送出 / 下一題</button>
                    </div>

                    <div class="row"><div id="shortFeedback"></div></div>
                    <div class="row"><button id="btnQuitToTask">回到任務說明</button></div>
                `;
            }

            function render_summary(){
                const ms = (state.started_at_ms ? (nowMs() - state.started_at_ms) : 0);
                const sec = Math.max(0, Math.round(ms / 1000));
                const total = state.total;
                const correct = state.history.filter(x => x.is_correct === 1).length;
                const wrong = state.history.filter(x => x.is_correct !== 1);

                const wrongHtml = wrong.length
                    ? wrong.map((x, i) => {
                            const title = escapeHtml(x.question);
                            const detail = escapeHtml([x.error_tag ? ('錯因：' + x.error_tag) : '', x.error_detail || ''].filter(Boolean).join('｜'));
                            return `
                                <details style="margin:6px 0">
                                    <summary>錯題 ${i+1}：${title}</summary>
                                    <div class="muted" style="margin-top:6px">${detail || '（未提供更多錯因）'}</div>
                                </details>
                            `;
                        }).join('')
                    : `<div class="ok">本次沒有錯題，超棒！</div>`;

                return `
                    <div class="row"><b>Step 3｜總結頁</b></div>
                    <div class="row">
                        <div><b>得分：</b>${correct}/${total}</div>
                        <div><b>用時：</b>${sec} 秒</div>
                    </div>
                    <div class="row">
                        <div><b>錯題清單（可展開）</b></div>
                        ${wrongHtml}
                    </div>
                    <div class="row">
                        <button id="btnRetryAll">再練一次</button>
                        <button id="btnRetryWrong" ${wrong.length ? '' : 'disabled'}>只練錯題</button>
                        <button id="btnBackIntro2">回到提醒頁</button>
                    </div>
                `;
            }

            function render(){
                if(state.step === 0){
                    appEl.innerHTML = render_intro();

                    // Bind intro events
                    document.getElementById('btnGoTask').addEventListener('click', () => {
                        mustGetSetupFromUI();
                        const sid = String(state.student_id || '').trim();
                        if(!sid){
                            document.getElementById('introError').textContent = '請先填學生編號（可按「自動讀取」）';
                            return;
                        }
                        state.step = 1;
                        render();
                    });

                    document.getElementById('btnBootstrap').addEventListener('click', async () => {
                        document.getElementById('introError').textContent = '';
                        try{
                            const res = await fetch('/admin/bootstrap?name=Web-Student', { method:'POST' });
                            const j = await res.json();
                            if(!res.ok){
                                document.getElementById('introError').textContent = '取得註冊碼失敗：' + (j && j.detail ? j.detail : ('HTTP ' + res.status));
                                return;
                            }
                            const apiKeyEl = document.getElementById('apiKey');
                            apiKeyEl.value = j.api_key || '';
                            mustGetSetupFromUI();
                            document.getElementById('introError').textContent = '已取得註冊碼（請按「自動讀取」取得學生編號）';
                        }catch(e){
                            document.getElementById('introError').textContent = '取得註冊碼失敗：' + String(e);
                        }
                    });

                    document.getElementById('btnLoadStudents').addEventListener('click', async () => {
                        document.getElementById('introError').textContent = '';
                        mustGetSetupFromUI();
                        try{
                            const res = await apiFetch('/v1/students', { method:'GET' });
                            const j = await res.json();
                            if(!res.ok){
                                document.getElementById('introError').textContent = '讀取學生失敗：' + (j && j.detail ? j.detail : ('HTTP ' + res.status));
                                return;
                            }
                            const list = (j.students || []);
                            if(list.length === 0){
                                document.getElementById('introError').textContent = '讀取學生失敗：找不到學生';
                                return;
                            }
                            document.getElementById('studentId').value = String(list[0].id);
                            document.getElementById('studentName').textContent = `（${list[0].display_name || ''} ${list[0].grade || ''}）`;
                            mustGetSetupFromUI();
                            document.getElementById('introError').textContent = '已載入學生';
                        }catch(e){
                            document.getElementById('introError').textContent = '讀取學生失敗：' + String(e);
                        }
                    });

                    return;
                }

                if(state.step === 1){
                    appEl.innerHTML = render_task();
                    document.getElementById('btnBackIntro').addEventListener('click', () => {
                        state.step = 0;
                        render();
                    });
                    document.getElementById('btnStartAnswer').addEventListener('click', async () => {
                        // Start run
                        mustGetSetupFromUI();
                        state.started_at_ms = nowMs();
                        state.q_index = 0;
                        state.questions = [];
                        state.history = [];
                        state.step = 2;
                        render();
                    });
                    return;
                }

                if(state.step === 2){
                    // Ensure current question exists.
                    (async () => {
                        mustGetSetupFromUI();
                        const sid = String(state.student_id || '').trim();
                        if(!sid){
                            state.step = 0;
                            render();
                            return;
                        }

                        if(state.questions[state.q_index] == null){
                            const topic = String(state.topic_key || '').trim();
                            const qs = new URLSearchParams({ student_id: sid });
                            if(topic) qs.set('topic_key', topic);
                            try{
                                const res = await apiFetch('/v1/questions/next?' + qs.toString(), { method:'POST' });
                                const j = await res.json();
                                if(!res.ok){
                                    state.step = 0;
                                    render();
                                    return;
                                }
                                state.questions.push({
                                    question_id: j.question_id,
                                    topic: j.topic || '',
                                    difficulty: j.difficulty || '',
                                    question: j.question || '',
                                });
                            }catch(e){
                                state.step = 0;
                                render();
                                return;
                            }
                        }

                        // Render question page (clean — only current question)
                        appEl.innerHTML = render_question();
                        const ansInput = document.getElementById('userAnswer');
                        const btnSubmit = document.getElementById('btnSubmit');
                        const btnQuit = document.getElementById('btnQuitToTask');
                        const feedbackEl = document.getElementById('shortFeedback');

                        function setShortFeedback(isOk){
                            feedbackEl.innerHTML = isOk
                                ? `<span class="ok">答對</span>`
                                : `<span class="bad">答錯</span>`;
                        }

                        async function submitAndNext(){
                            const q = state.questions[state.q_index];
                            const sidNum = Number(String(state.student_id || '').trim());
                            const ans = (ansInput.value || '').trim();
                            if(!ans) return;

                            btnSubmit.disabled = true;
                            ansInput.disabled = true;

                            const body = { student_id: sidNum, question_id: Number(q.question_id), user_answer: ans, time_spent_sec: 12 };
                            try{
                                const res = await apiFetch('/v1/answers/submit', {
                                    method:'POST',
                                    headers:{ 'Content-Type':'application/json' },
                                    body: JSON.stringify(body)
                                });
                                const j = await res.json();
                                if(!res.ok){
                                    // Stay on question but only show a short line.
                                    feedbackEl.innerHTML = `<span class="bad">送出失敗</span>`;
                                    btnSubmit.disabled = false;
                                    ansInput.disabled = false;
                                    return;
                                }

                                const ok = (j.is_correct === 1);
                                setShortFeedback(ok);
                                state.history.push({
                                    question_id: q.question_id,
                                    topic: q.topic,
                                    difficulty: q.difficulty,
                                    question: q.question,
                                    user_answer: ans,
                                    is_correct: j.is_correct,
                                    error_tag: j.error_tag || '',
                                    error_detail: j.error_detail || '',
                                    ts: nowMs(),
                                });

                                // Next question
                                state.q_index += 1;
                                state.current_input = '';

                                // Finish
                                if(state.q_index >= state.total){
                                    state.step = 3;
                                    render();
                                    return;
                                }

                                // Small delay so the child can see "答對/答錯" one line, then refresh.
                                setTimeout(() => { render(); }, 300);
                            }catch(e){
                                feedbackEl.innerHTML = `<span class="bad">送出失敗</span>`;
                                btnSubmit.disabled = false;
                                ansInput.disabled = false;
                            }
                        }

                        btnSubmit.addEventListener('click', submitAndNext);
                        ansInput.addEventListener('keydown', (ev) => {
                            if(ev.key === 'Enter'){
                                ev.preventDefault();
                                submitAndNext();
                            }
                        });
                        btnQuit.addEventListener('click', () => {
                            state.step = 1;
                            render();
                        });

                        // Focus input for quick Enter flow
                        try{ ansInput.focus(); }catch(e){}
                    })();
                    return;
                }

                if(state.step === 3){
                    appEl.innerHTML = render_summary();
                    document.getElementById('btnRetryAll').addEventListener('click', () => restart_from_summary('all'));
                    const retryWrongBtn = document.getElementById('btnRetryWrong');
                    if(retryWrongBtn){
                        retryWrongBtn.addEventListener('click', () => restart_from_summary('wrong'));
                    }
                    document.getElementById('btnBackIntro2').addEventListener('click', () => {
                        reset_run();
                        state.step = 0;
                        render();
                    });
                    return;
                }
            }

            init_state();
            render();
        </script>
  </body>
</html>
"""
    return HTMLResponse(content=html)

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

    meta = {
        "hint_level_used": hint_level_used_int,
        "policy": {"reveal_answer_after_submit": True, "max_hint_level": 3},
    }

    conn.execute("""INSERT INTO attempts(account_id, student_id, question_id, mode, topic, difficulty,
                    question, correct_answer, user_answer, is_correct, time_spent_sec,
                    error_tag, error_detail, hint_level_used, meta_json, ts)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                 (acc["id"], student_id, question_id, 'interactive', q["topic"], q["difficulty"],
                  q["question"], q["correct_answer"], user_answer, is_correct, time_spent,
                  error_tag, error_detail, hint_level_used_int, json.dumps(meta, ensure_ascii=False), now_iso()))
    conn.commit()
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), reload=True)
