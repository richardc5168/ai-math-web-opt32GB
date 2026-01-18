import streamlit as st
import os, sqlite3, hashlib, json, requests, pandas as pd, re, numpy as np

# Optional plotting deps (keep app runnable even if not installed)
try:
    import seaborn as sns  # type: ignore
except Exception:
    sns = None

try:
    import matplotlib.pyplot as plt  # type: ignore
except Exception:
    plt = None
from datetime import datetime, timedelta

import sympy as sp

from rag_backend import Retriever

DB_ANS = "answers.db"
DB_CONV = "conversation.db"


@st.cache_resource(show_spinner=False)
def get_answers_conn() -> sqlite3.Connection:
    return init_answers_db()


@st.cache_resource(show_spinner=False)
def get_conversation_conn() -> sqlite3.Connection:
    return init_conversation_db()


@st.cache_resource(show_spinner=False)
def get_retriever() -> Retriever:
    return Retriever("knowledge.db")

# ============================================
# 答案快取資料庫初始化 (answers.db)
# ============================================
def init_answers_db():
    conn = sqlite3.connect(DB_ANS, check_same_thread=False)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS answers(
        id TEXT PRIMARY KEY,
        question TEXT,
        answer TEXT
    )
    """)
    conn.commit()
    return conn

# ============================================
# 學習歷程資料庫初始化 (conversation.db)
# ============================================
def init_conversation_db():
    conn = sqlite3.connect(DB_CONV, check_same_thread=False)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS conversation_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT,
        subject TEXT,
        topic TEXT,
        difficulty TEXT,
        mode TEXT,              -- auto_question / teacher_solution / hint 等
        question TEXT,
        answer TEXT,
        correct INTEGER,        -- 1=對, 0=錯, NULL=未知
        meta_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    return conn

answers_conn = get_answers_conn()
conv_conn = get_conversation_conn()
retriever = get_retriever()

# 初始化 session_state（自動出題相關）
if "auto_q" not in st.session_state:
    st.session_state["auto_q"] = ""
if "auto_steps" not in st.session_state:
    st.session_state["auto_steps"] = []
if "auto_answer" not in st.session_state:
    st.session_state["auto_answer"] = ""
if "auto_step_idx" not in st.session_state:
    st.session_state["auto_step_idx"] = 0
if "student_id" not in st.session_state:
    st.session_state["student_id"] = "demo_student"

st.set_page_config(page_title="Neo 文件與數學教師系統", layout="wide")
st.title("Neo 文件知識庫 + AI 數學教師 + 學習大腦")


tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📚 文件問答",
    "🧩 題庫管理",
    "🎓 數學教師模式",
    "📈 出題統計分析",
    "🧠 學習報表 / 學習大腦"
])

# ============================================================
# 工具函式：題型 / 難度分類
# ============================================================
def classify_topic(q_text: str) -> str:
    q_lower = q_text.lower()
    if re.search(r"分數|fraction", q_lower):
        return "分數"
    if re.search(r"小數|decimal", q_lower):
        return "小數"
    if re.search(r"角|面積|邊|圖形|geometry", q_lower):
        return "幾何"
    return "應用題"

def estimate_difficulty(q_text: str) -> str:
    length = len(q_text)
    if length < 30:
        return "簡單"
    elif length < 80:
        return "中等"
    else:
        return "困難"


# ============================================================
# 🧭 Knowledge Navigator: 弱點追蹤 + 開源資源推薦（可擴展）
# ============================================================
OPEN_RESOURCES = {
    # Khan Academy
    "因式分解": "https://www.khanacademy.org/math/algebra/x2f8bb11595b61c86:quadratics-multiplying-factoring",
    "分配律": "https://www.khanacademy.org/math/arithmetic/arith-review-multiply-divide/arith-review-distributive-property",
    "判別式": "https://www.khanacademy.org/math/algebra2/x2ec2f6f830c9fb89:poly-arithmetic/x2ec2f6f830c9fb89:discriminant",
    "公式解": "https://www.khanacademy.org/math/algebra/x2f8bb11595b61c86:quadratics-solving/quadratic-formula-a1",
    # Junyi / YouTube (use search URLs to keep it stable & key-free)
    "均一-判別式": "https://www.junyiacademy.org/search?q=%E5%88%A4%E5%88%A5%E5%BC%8F",
    "均一-因式分解": "https://www.junyiacademy.org/search?q=%E5%9B%A0%E5%BC%8F%E5%88%86%E8%A7%A3",
    "YouTube-一元二次": "https://www.youtube.com/results?search_query=%E4%B8%80%E5%85%83%E4%BA%8C%E6%AC%A1%E6%96%B9%E7%A8%8B%E5%BC%8F+%E6%95%99%E5%AD%B8",
    "YouTube-公式解": "https://www.youtube.com/results?search_query=%E4%B8%80%E5%85%83%E4%BA%8C%E6%AC%A1%E6%96%B9%E7%A8%8B%E5%BC%8F+%E5%85%AC%E5%BC%8F%E8%A7%A3+%E6%95%99%E5%AD%B8",
}


# ------------------------------------------------------------
# Knowledge Graph (DAG)
# ------------------------------------------------------------
# Keep the existing compact graph for the current prototype UX.
KNOWLEDGE_GRAPH = {
    "一元二次方程式": {
        "prerequisites": ["分配律", "因式分解"],
        "skills": ["判別式", "公式解"],
    },
    "判別式": {"prerequisites": ["分配律"], "skills": []},
    "公式解": {"prerequisites": ["判別式"], "skills": []},
    "因式分解": {"prerequisites": ["分配律"], "skills": []},
}

# A more explicit DAG (ids + prereqs) aligned with你的 prompt 範例。
# This powers “動態路徑導航”：答錯 A5 時會向上回溯 A1~A4，並以歷史正確率決定優先補救。
KNOWLEDGE_GRAPH_V2 = {
    "一元一次方程式": {"id": "A1", "prereqs": []},
    "因式分解-提公因式": {"id": "A2", "prereqs": ["A1"]},
    "一元二次方程式-因式分解法": {"id": "A3", "prereqs": ["A2"]},
    "一元二次方程式-配方法": {"id": "A4", "prereqs": ["A3"]},
    "一元二次方程式-公式解": {"id": "A5", "prereqs": ["A4"]},
    # Bridge nodes to our current UI labels
    "分配律": {"id": "P1", "prereqs": []},
    "判別式": {"id": "Q1", "prereqs": ["P1"]},
    "公式解": {"id": "Q2", "prereqs": ["Q1"]},
    "因式分解": {"id": "P2", "prereqs": ["P1"]},
}


def math_level_label(level: int) -> str:
    level = int(level)
    if level < 1:
        level = 1
    if level > 5:
        level = 5
    return f"MATH Level {level}"


class KnowledgeNavigator:
    """Track student weaknesses and recommend open resources.

    UX: only push resources after consecutive mistakes.
    Extensible: add new concepts/topics by extending maps.
    Stable: uses search URLs (no API keys required).
    """

    def __init__(self, knowledge_graph: dict | None = None, resources: dict | None = None):
        self.knowledge_graph = knowledge_graph or KNOWLEDGE_GRAPH
        self.resources = resources or OPEN_RESOURCES
        self.stats: dict[str, dict[str, int]] = {}

    def record_attempt(self, concept: str, correct: bool):
        key = str(concept or "").strip() or "（未分類）"
        s = self.stats.get(key) or {"attempts": 0, "wrong": 0, "wrong_streak": 0}
        s["attempts"] += 1
        if correct:
            s["wrong_streak"] = 0
        else:
            s["wrong"] += 1
            s["wrong_streak"] += 1
        self.stats[key] = s

    def wrong_streak(self, concept: str) -> int:
        return int((self.stats.get(str(concept)) or {}).get("wrong_streak", 0))

    def should_push_resources(self, concept: str, threshold: int = 2) -> bool:
        return self.wrong_streak(concept) >= int(threshold)

    def prerequisites_for(self, concept: str) -> list[str]:
        meta = self.knowledge_graph.get(str(concept), {})
        prereqs = meta.get("prerequisites") or []
        return [str(x) for x in prereqs if str(x).strip()]

    def get_resource_links(self, concept: str) -> list[tuple[str, str]]:
        c = str(concept)
        links: list[tuple[str, str]] = []

        if c in self.resources:
            links.append((f"Khan / 參考：{c}", self.resources[c]))

        if c == "判別式":
            links.append(("均一：判別式", self.resources.get("均一-判別式", "")))
        if c == "因式分解":
            links.append(("均一：因式分解", self.resources.get("均一-因式分解", "")))
        if c in ("一元二次方程式", "公式解"):
            links.append(("YouTube：公式解", self.resources.get("YouTube-公式解", "")))
            links.append(("YouTube：一元二次", self.resources.get("YouTube-一元二次", "")))

        links.append((f"Google：數學 {c}", "https://www.google.com/search?q=" + requests.utils.quote("數學 " + c)))
        return [(t, u) for (t, u) in links if u]

    def render_remedy_markdown(self, concept: str) -> str:
        prereqs = self.prerequisites_for(concept)
        prereq_text = "、".join(prereqs) if prereqs else "（無）"
        links = self.get_resource_links(concept)
        bullets = "\n".join([f"- [{t}]({u})" for (t, u) in links])
        return (
            f"偵測到你在 **{concept}** 可能有觀念斷層（連續錯誤）。\n\n"
            f"建議回溯前置：**{prereq_text}**\n\n"
            f"可用的開源補救資源：\n{bullets}"
        )


# Session-scoped navigator (per browser session). If you want cross-device persistence,
# we can store this summary into conversation.db as meta_json.
if "knowledge_nav" not in st.session_state:
    st.session_state["knowledge_nav"] = KnowledgeNavigator()


# ============================================================
# 🧠 Dynamic Path Navigation (history-aware remediation)
# ============================================================
def _kg_build_index(kg: dict) -> tuple[dict[str, str], dict[str, str], dict[str, list[str]]]:
    """Build (name->id, id->name, id->prereq_ids) indices.

    Supports prereqs expressed as ids ("A2") or names ("因式分解").
    """

    name_to_id: dict[str, str] = {}
    id_to_name: dict[str, str] = {}

    for name, meta in (kg or {}).items():
        node_id = str((meta or {}).get("id") or name).strip()
        name_to_id[str(name)] = node_id
        id_to_name[node_id] = str(name)

    prereq_ids: dict[str, list[str]] = {}
    for name, meta in (kg or {}).items():
        node_id = name_to_id.get(str(name), str(name))
        prereqs = list((meta or {}).get("prereqs") or [])
        resolved: list[str] = []
        for p in prereqs:
            p_str = str(p).strip()
            if not p_str:
                continue
            # allow referencing by name
            resolved.append(name_to_id.get(p_str, p_str))
        prereq_ids[node_id] = resolved

    return name_to_id, id_to_name, prereq_ids


def _kg_prereq_closure(target: str, kg: dict, include_self: bool = False) -> list[str]:
    """Return prereq chain (unique, topological-ish order), as concept names."""

    name_to_id, id_to_name, prereq_ids = _kg_build_index(kg)
    start_id = name_to_id.get(str(target), str(target))

    visited: set[str] = set()
    ordered: list[str] = []

    def dfs(node_id: str):
        if node_id in visited:
            return
        visited.add(node_id)
        for p in prereq_ids.get(node_id, []):
            dfs(p)
        if include_self or node_id != start_id:
            ordered.append(id_to_name.get(node_id, node_id))

    dfs(start_id)
    return ordered


def _history_accuracy_by_concept(
    conn: sqlite3.Connection,
    student_id: str,
    concepts: list[str],
    lookback_days: int = 180,
):
    """Return per-concept accuracy from conversation_log.

    We primarily read meta_json['concept'] (or legacy mode fallbacks).
    """

    if not concepts:
        return {}

    since = (datetime.utcnow() - timedelta(days=int(lookback_days))).strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT correct, mode, meta_json, topic
        FROM conversation_log
        WHERE student_id=? AND subject='math' AND created_at >= ?
        """,
        (student_id, since),
    ).fetchall()

    wanted = {str(c) for c in concepts}
    stats: dict[str, dict[str, int]] = {str(c): {"attempts": 0, "correct": 0} for c in wanted}

    for correct, mode, meta_json, topic in rows:
        concept = None

        # meta_json concept first
        try:
            meta = json.loads(meta_json) if meta_json else {}
            concept = meta.get("concept") or meta.get("concept_label")
        except Exception:
            concept = None

        # fallback: infer from mode
        if not concept:
            if str(mode) == "quadratic_discriminant":
                concept = "判別式"
            elif str(mode) == "quadratic_roots":
                concept = "公式解"

        # final fallback: topic if it matches a concept label
        if not concept and topic in wanted:
            concept = topic

        if concept not in wanted:
            continue
        if correct is None:
            continue

        stats[concept]["attempts"] += 1
        stats[concept]["correct"] += 1 if int(correct) == 1 else 0

    # convert to accuracy floats
    out: dict[str, dict[str, float | int]] = {}
    for c, s in stats.items():
        attempts = int(s["attempts"])
        correct_n = int(s["correct"])
        acc = (correct_n / attempts) if attempts else 1.0
        out[c] = {"attempts": attempts, "correct": correct_n, "accuracy": float(acc)}
    return out


@st.cache_data(ttl=5, show_spinner=False)
def history_accuracy_by_concept_cached(
    student_id: str,
    concepts: tuple[str, ...],
    lookback_days: int = 180,
):
    with sqlite3.connect(DB_CONV, check_same_thread=False) as conn:
        return _history_accuracy_by_concept(conn, student_id, list(concepts), lookback_days=int(lookback_days))


def dynamic_remediation_targets(
    conn: sqlite3.Connection,
    student_id: str,
    failed_concept: str,
    threshold: float = 0.7,
    min_attempts: int = 3,
    lookback_days: int = 180,
) -> list[dict[str, object]]:
    """When a student fails a concept, backtrack prereqs and pick weak links."""

    chain = _kg_prereq_closure(failed_concept, KNOWLEDGE_GRAPH_V2, include_self=True)
    acc = _history_accuracy_by_concept(conn, student_id, chain, lookback_days=lookback_days)

    targets: list[dict[str, object]] = []
    for label in chain:
        m = acc.get(label) or {"attempts": 0, "accuracy": 1.0}
        attempts = int(m.get("attempts", 0))
        accuracy = float(m.get("accuracy", 1.0))
        if attempts >= int(min_attempts) and accuracy < float(threshold):
            targets.append({"label": label, "attempts": attempts, "accuracy": accuracy})

    # If no strong signal from history yet, default to immediate prereqs.
    if not targets:
        prereqs = _kg_prereq_closure(failed_concept, KNOWLEDGE_GRAPH_V2, include_self=False)
        for p in prereqs[-2:]:
            targets.append({"label": p, "attempts": int((acc.get(p) or {}).get("attempts", 0)), "accuracy": float((acc.get(p) or {}).get("accuracy", 1.0))})

    return targets


def _parse_math_level_label(difficulty: str | None) -> int | None:
    if not difficulty:
        return None
    m = re.search(r"(\d+)", str(difficulty))
    if not m:
        return None
    try:
        v = int(m.group(1))
        if 1 <= v <= 5:
            return v
    except Exception:
        return None
    return None


def quadratic_level_stats(
    conn: sqlite3.Connection,
    student_id: str,
    lookback_days: int = 60,
) -> dict[int, dict[str, float | int]]:
    """Return per-level accuracy for quadratic roots step (final check)."""

    since = (datetime.utcnow() - timedelta(days=int(lookback_days))).strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT correct, difficulty, meta_json
        FROM conversation_log
        WHERE student_id=? AND subject='math'
          AND mode='quadratic_roots'
          AND created_at >= ?
        ORDER BY id DESC
        """,
        (student_id, since),
    ).fetchall()

    stats: dict[int, dict[str, int]] = {i: {"attempts": 0, "correct": 0} for i in range(1, 6)}

    for correct, difficulty, meta_json in rows:
        # Prefer meta level when present, else parse difficulty label
        level = None
        try:
            meta = json.loads(meta_json) if meta_json else {}
            level = meta.get("level")
        except Exception:
            level = None
        if level is None:
            level = _parse_math_level_label(difficulty)
        try:
            level_i = int(level)
        except Exception:
            continue
        if level_i < 1 or level_i > 5:
            continue
        if correct is None:
            continue
        stats[level_i]["attempts"] += 1
        stats[level_i]["correct"] += 1 if int(correct) == 1 else 0

    out: dict[int, dict[str, float | int]] = {}
    for lvl in range(1, 6):
        a = int(stats[lvl]["attempts"])
        c = int(stats[lvl]["correct"])
        acc = (c / a) if a else 1.0
        out[lvl] = {"attempts": a, "correct": c, "accuracy": float(acc)}
    return out


@st.cache_data(ttl=5, show_spinner=False)
def quadratic_level_stats_cached(student_id: str, lookback_days: int = 60):
    with sqlite3.connect(DB_CONV, check_same_thread=False) as conn:
        return quadratic_level_stats(conn, student_id, lookback_days=int(lookback_days))


def recommend_quadratic_level(
    conn: sqlite3.Connection,
    student_id: str,
    current_level: int,
    lookback_days: int = 60,
    promote_acc: float = 0.8,
    promote_min_attempts: int = 5,
    demote_acc: float = 0.5,
    demote_min_attempts: int = 3,
) -> tuple[int, str]:
    """Adaptive rule-of-thumb based on recent final-step correctness (roots).

    - If current level is stable & high accuracy => promote
    - If struggling => demote
    - Else keep
    """

    cur_lvl = int(current_level)
    cur_lvl = max(1, min(5, cur_lvl))

    # Use cached, read-only aggregation to keep Streamlit UI responsive.
    stats = quadratic_level_stats_cached(student_id, lookback_days=int(lookback_days))
    cur = stats.get(cur_lvl) or {"attempts": 0, "accuracy": 1.0}
    attempts = int(cur.get("attempts", 0))
    acc = float(cur.get("accuracy", 1.0))

    if attempts >= int(promote_min_attempts) and acc >= float(promote_acc) and cur_lvl < 5:
        return cur_lvl + 1, f"近 {attempts} 次 Level {cur_lvl} 正確率 {acc:.0%} → 升級"
    if attempts >= int(demote_min_attempts) and acc <= float(demote_acc) and cur_lvl > 1:
        return cur_lvl - 1, f"近 {attempts} 次 Level {cur_lvl} 正確率 {acc:.0%} → 降級"
    if attempts == 0:
        return cur_lvl, "尚無該 Level 作答紀錄 → 維持"
    return cur_lvl, f"近 {attempts} 次 Level {cur_lvl} 正確率 {acc:.0%} → 維持"

# ============================================================
# 工具函式：學習歷程紀錄
# ============================================================
def log_conversation(
    student_id: str,
    subject: str,
    question: str,
    answer: str,
    topic: str = None,
    difficulty: str = None,
    mode: str = "teacher_solution",
    correct: int | None = None,
    meta: dict | None = None,
):
    if not question:
        return
    if topic is None:
        topic = classify_topic(question)
    if difficulty is None:
        difficulty = estimate_difficulty(question)
    meta_json = json.dumps(meta, ensure_ascii=False) if meta else None

    cur = conv_conn.cursor()
    cur.execute(
        """
        INSERT INTO conversation_log
        (student_id, subject, topic, difficulty, mode, question, answer, correct, meta_json)
        VALUES (?,?,?,?,?,?,?,?,?)
        """,
        (student_id, subject, topic, difficulty, mode, question, answer, correct, meta_json),
    )
    conv_conn.commit()

# ============================================================
# 📚 文件問答區
# ============================================================
with tab1:
    st.subheader("📘 文件問答")

    q_doc = st.text_area("輸入問題", height=100)
    if st.button("查詢文件"):
        if not q_doc:
            st.warning("請輸入問題")
        else:
            hits = retriever.search(q_doc, topk=4)
            if not hits:
                st.info("未找到相關文件內容。")
            else:
                for h in hits:
                    st.markdown(f"**來源：{h['source']}**\n\n{h['text'][:800]}…")
                st.success("文件檢索完成")

# ============================================================
# 🎓 AI 數學教師：核心函式
# ============================================================
def get_or_build_solution(q: str, student_id: str) -> dict:
    """
    若 answers.db 已有該題，直接回傳快取。
    否則呼叫本機 Ollama 產生逐步解題說明並寫入快取與 conversation_log。
    """
    qid = hashlib.md5(q.encode()).hexdigest()
    c = answers_conn.cursor()
    r = c.execute("SELECT answer FROM answers WHERE id=?", (qid,)).fetchone()
    if r:
        ans_text = r[0]
        # 把快取的題目也寫進學習歷程（避免沒紀錄）
        log_conversation(
            student_id=student_id,
            subject="math",
            question=q,
            answer=ans_text,
            mode="teacher_solution_cached",
        )
        return {"answer": ans_text}

    ctx = "\n".join([x["text"] for x in retriever.search(q, topk=3)])
    prompt = (
        "你是一位國小與國中數學老師，請用清楚的步驟解題。\n"
        "要求：\n"
        "1. 先幫學生整理題目條件\n"
        "2. 再逐步推理，每一步說明原因\n"
        "3. 最後給出明確答案\n"
        "題目：\n"
        f"{q}\n"
        "（若有參考資料可用）參考資料：\n"
        f"{ctx}\n"
    )

    model = os.getenv("OLLAMA_MODEL", "deepseek-math:7b")
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    try:
        resp = requests.post(
            f"{host}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        ans_text = ""
        for line in resp.text.splitlines():
            try:
                data = json.loads(line)
                ans_text += data.get("response", "")
            except Exception:
                ans_text += line
        ans = ans_text.strip()
    except Exception as e:
        ans = f"離線模型錯誤：{e}"

    c.execute("REPLACE INTO answers VALUES(?,?,?)", (qid, q, ans))
    answers_conn.commit()

    # 寫入學習歷程
    log_conversation(
        student_id=student_id,
        subject="math",
        question=q,
        answer=ans,
        mode="teacher_solution",
    )
    return {"answer": ans}


def next_step_hint_offline(q: str, state: str, student_id: str) -> str:
    """
    給學生「下一步提示」，不直接給完整答案。
    也會記錄在 conversation_log 中（mode=hint）。
    """
    prompt = (
        "你是一位國小與國中數學老師，請只給「下一步提示」。\n"
        "規則：\n"
        "1. 不要直接給出最後答案\n"
        "2. 只提醒學生下一個應該做的動作\n"
        "3. 用 1-2 句話說明\n"
        f"題目：{q}\n"
        f"學生目前想法：{state}\n"
    )
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL_HINT", "deepseek-math:7b")

    try:
        resp = requests.post(
            f"{host}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=60,
        )
        text = ""
        for line in resp.text.splitlines():
            try:
                data = json.loads(line)
                text += data.get("response", "")
            except Exception:
                text += line
        hint = text.strip()
    except Exception as e:
        hint = f"提示生成錯誤：{e}"

    # 記錄提示對話
    log_conversation(
        student_id=student_id,
        subject="math",
        question=q,
        answer=hint,
        mode="hint",
        meta={"student_state": state},
    )
    return hint

def generate_math_problem_ollama(topic: str, difficulty: str, student_id: str) -> dict:
    """
    透過 Ollama 自動出題。
    期望輸出格式：
    題目：...
    解題步驟：
    1. ...
    2. ...
    答案：...
    """
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL_QUESTION", "deepseek-math:7b")

    prompt = (
        "你是一位國小高年級數學老師，請依照指定主題與難度設計一題計算或應用題。\n"
        "請使用以下格式輸出（中文）：\n"
        "題目：...\n"
        "解題步驟：\n"
        "1. ...\n"
        "2. ...\n"
        "3. ...（可視需要有多步）\n"
        "答案：...\n\n"
        f"主題：{topic}\n"
        f"難度：{difficulty}\n"
        "不要加入多餘說明文字，只要依照上述格式輸出。"
    )

    try:
        resp = requests.post(
            f"{host}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=60,
        )
        # 1) HTTP 失敗
        if resp.status_code != 200:
            return {
                "question": "",
                "solution_steps": [],
                "answer": "",
                "error": f"Ollama HTTP {resp.status_code}: {resp.text[:200]}",
            }

        # 2) 非 streaming 模式，直接是單一 JSON
        try:
            data = resp.json()
        except Exception:
            # 若不是標準 JSON，就當純文字
            text = resp.text.strip()
        else:
            # 有 error field（例如 model not found）
            if isinstance(data, dict) and "error" in data:
                return {
                    "question": "",
                    "solution_steps": [],
                    "answer": "",
                    "error": f"Ollama 回傳錯誤: {data['error']}",
                }
            text = data.get("response", "").strip()

        if not text:
            return {
                "question": "",
                "solution_steps": [],
                "answer": "",
                "error": "Ollama 回傳空內容，請檢查模型是否正確。",
            }

    except Exception as e:
        return {
            "question": "",
            "solution_steps": [],
            "answer": "",
            "error": f"自動出題錯誤：{e}",
        }

    # 解析題目 / 步驟 / 答案
    q_match = re.search(r"題目[:：]\s*(.+?)(?:解題步驟[:：]|答案[:：]|$)", text, re.S)
    steps_match = re.search(r"解題步驟[:：]\s*(.+?)(?:答案[:：]|$)", text, re.S)
    ans_match = re.search(r"答案[:：]\s*(.+)$", text, re.S)

    question = q_match.group(1).strip() if q_match else text
    steps_raw = steps_match.group(1).strip() if steps_match else ""
    answer = ans_match.group(1).strip() if ans_match else ""

    steps = []
    if steps_raw:
        parts = re.split(r"^\s*\d+[\.\u3001、]\s*", steps_raw, flags=re.M)
        for p in parts:
            p = p.strip()
            if p:
                steps.append(p)

    # 出題本身也記錄一筆（mode=auto_question）
    log_conversation(
        student_id=student_id,
        subject="math",
        question=question,
        answer=answer,
        mode="auto_question",
        meta={"raw": text, "topic": topic, "difficulty": difficulty, "model": model},
    )

    return {
        "question": question,
        "solution_steps": steps,
        "answer": answer,
        "error": "",
    }

# ============================================================
# 🎓 AI 數學教師模式（含自動出題 + 逐步引導）
# ============================================================
with tab3:
    st.subheader("🎓 AI 數學教師模式")

    student_id = st.text_input(
        "學生 ID 或姓名（用於學習歷程追蹤）",
        value=st.session_state.get("student_id", "demo_student"),
        key="student_id_input",
    )
    st.session_state["student_id"] = student_id

    st.markdown("#### 自動出題（離線 Ollama）")
    col_topic, col_diff, col_btn = st.columns([2, 2, 1])
    with col_topic:
        topic = st.selectbox("主題", ["分數", "小數", "幾何", "應用題"], index=0)
    with col_diff:
        difficulty = st.selectbox("難度", ["簡單", "中等", "困難"], index=1)
    with col_btn:
        if st.button("自動產生一題"):
            data = generate_math_problem_ollama(topic, difficulty, student_id)
            if data.get("error"):
                st.error(data["error"])
            else:
                st.session_state["auto_q"] = data["question"]
                st.session_state["auto_steps"] = data["solution_steps"]
                st.session_state["auto_answer"] = data["answer"]
                st.session_state["auto_step_idx"] = 0
                st.success("已自動產生一題，請見下方題目與步驟提示。")

    if st.session_state["auto_q"]:
        st.markdown("##### 目前自動產生的題目：")
        st.write(st.session_state["auto_q"])

        if st.session_state["auto_steps"]:
            st.markdown("##### 逐步提示")
            if st.button("顯示下一步解題提示"):
                if st.session_state["auto_step_idx"] < len(st.session_state["auto_steps"]):
                    st.session_state["auto_step_idx"] += 1

            max_idx = st.session_state["auto_step_idx"]
            for i, step in enumerate(st.session_state["auto_steps"][:max_idx], start=1):
                st.markdown(f"步驟 {i}：{step}")

            if max_idx >= len(st.session_state["auto_steps"]) and st.session_state["auto_answer"]:
                st.markdown("---")
                st.markdown(f"最終答案：{st.session_state['auto_answer']}")

        st.markdown("---")

    st.markdown("#### 手動輸入題目解題")
    q = st.text_area(
        "輸入題目",
        height=100,
        value=st.session_state.get("auto_q", ""),
        placeholder="例如：一條長 8 公尺的繩子剪成 4 段，每段長多少？",
    )

    if st.button("解題 / 教學說明"):
        if not q:
            st.warning("請輸入題目")
        else:
            sol = get_or_build_solution(q, student_id)
            st.markdown("##### 解題說明：")
            st.markdown(sol["answer"])

    st.markdown("---")

    # ============================================================
    # 🧪 一元二次方程式：Sympy 驗證 + 連錯才推資源（UX 優先）
    # ============================================================
    st.subheader("🧪 一元二次方程式（穩定可控原型）")
    st.caption(
        "流程：先判別式 D → 再求根；採 Sympy 驗證；連續錯誤才推 Khan/均一/YouTube 連結。"
    )

    nav: KnowledgeNavigator = st.session_state["knowledge_nav"]

    def _parse_roots_input(text: str) -> list[sp.Rational]:
        s = (text or "").strip()
        if not s:
            return []
        parts = [p.strip() for p in re.split(r"[\s,;]+", s) if p.strip()]
        out: list[sp.Rational] = []
        for p in parts:
            if "/" in p:
                a, b = p.split("/", 1)
                out.append(sp.Rational(int(a), int(b)))
            else:
                out.append(sp.Rational(int(p), 1))
        return out

    def _gen_quadratic(level: int = 2) -> dict:
        # Controlled difficulty mapping (inspired by MATH Level 1-5 idea)
        level = int(level)
        root_abs = {1: 3, 2: 5, 3: 7, 4: 10, 5: 14}.get(level, 5)
        # integer roots for stability in the MVP
        r1 = np.random.randint(-root_abs, root_abs + 1)
        r2 = np.random.randint(-root_abs, root_abs + 1)
        while r1 == 0:
            r1 = np.random.randint(-root_abs, root_abs + 1)
        while r2 == 0 or r2 == r1:
            r2 = np.random.randint(-root_abs, root_abs + 1)

        x = sp.Symbol("x")
        expr = (x - r1) * (x - r2)
        a = int(sp.expand(expr).coeff(x, 2))
        b = int(sp.expand(expr).coeff(x, 1))
        c = int(sp.expand(expr).coeff(x, 0))
        D = b * b - 4 * a * c
        roots = sorted([sp.Rational(r1, 1), sp.Rational(r2, 1)])
        eq_latex = sp.latex(sp.Eq(a * x**2 + b * x + c, 0))
        return {"a": a, "b": b, "c": c, "D": int(D), "roots": roots, "eq_latex": eq_latex}

    if "quad_state" not in st.session_state:
        st.session_state["quad_state"] = {
            "level": 2,
            "q": _gen_quadratic(2),
            "d_attempts": 0,
            "r_attempts": 0,
            "adaptive": True,
            "last_level_reason": "",
        }

    qs = st.session_state["quad_state"]
    colA, colB, colC, colD = st.columns([1.05, 1.2, 0.95, 0.9])
    with colA:
        level = st.selectbox(
            "難度（MATH Dataset Level 概念）",
            [1, 2, 3, 4, 5],
            index=int(qs.get("level", 2)) - 1,
            format_func=lambda x: f"{math_level_label(x)}",
        )
    with colB:
        concept_mode = st.selectbox(
            "解題路徑",
            ["先判別式 D", "直接求根"],
            index=0,
            help="UX 先用教科書流程，之後可擴展到因式分解優先。",
        )
    with colC:
        adaptive = st.checkbox(
            "自適應 Level",
            value=bool(qs.get("adaptive", True)),
            help="根據最近作答正確率自動升/降難度（以最後求根結果為準）。",
        )
        qs["adaptive"] = bool(adaptive)
        if qs.get("last_level_reason"):
            st.caption("自適應：" + str(qs.get("last_level_reason")))
    with colD:
        if st.button("出新題（Quadratic）"):
            prev_level = int(qs.get("level", int(level)))
            selected_level = int(level)
            reason = "手動指定"
            if qs.get("adaptive"):
                selected_level, reason = recommend_quadratic_level(
                    conv_conn,
                    student_id=student_id,
                    current_level=prev_level,
                    lookback_days=60,
                )
            qs["level"] = int(selected_level)
            qs["last_level_reason"] = str(reason)
            qs["q"] = _gen_quadratic(int(selected_level))
            qs["d_attempts"] = 0
            qs["r_attempts"] = 0
            log_conversation(
                student_id=student_id,
                subject="math",
                question="Adaptive select level for quadratic",
                answer=str(selected_level),
                topic="一元二次",
                difficulty=math_level_label(int(selected_level)),
                mode="quadratic_adaptive_select",
                correct=None,
                meta={
                    "adaptive": bool(qs.get("adaptive")),
                    "prev_level": int(prev_level),
                    "selected_level": int(selected_level),
                    "reason": str(reason),
                    "policy": {
                        "lookback_days": 60,
                        "promote_acc": 0.8,
                        "promote_min_attempts": 5,
                        "demote_acc": 0.5,
                        "demote_min_attempts": 3,
                    },
                },
            )
            st.success(f"已產生新題（{math_level_label(int(selected_level))}）")

    q = qs["q"]
    active_level = int(qs.get("level", int(level)))
    st.markdown("### 題目")
    st.markdown(f"求解：$${q['eq_latex']}$$")
    st.caption("答案格式：例如 2, 3（兩個根用逗號或空白分隔）。")

    # Step 1: Discriminant
    if concept_mode == "先判別式 D":
        st.markdown("#### Step 1：請先計算判別式 $D=b^2-4ac$")
        with st.form("quad_form_discriminant"):
            d_in = st.text_input("輸入 D", key="quad_D_input")
            submitted_d = st.form_submit_button("檢查 D")
        if submitted_d:
            try:
                d_user = int(str(d_in).strip())
                ok = (d_user == int(q["D"]))
                nav.record_attempt("判別式", ok)
                log_conversation(
                    student_id=student_id,
                    subject="math",
                    question=f"Discriminant for {q['eq_latex']}",
                    answer=str(d_user),
                    topic="一元二次",
                    difficulty=math_level_label(int(active_level)),
                    mode="quadratic_discriminant",
                    correct=1 if ok else 0,
                    meta={"concept": "判別式", "level": int(active_level), "a": q["a"], "b": q["b"], "c": q["c"], "D": q["D"]},
                )
                if ok:
                    st.success("正確！下一步求根。")
                else:
                    qs["d_attempts"] += 1
                    st.error("D 計算不正確。先不要急著看答案，檢查 b 的正負號與 4ac。")
                    if nav.should_push_resources("判別式", threshold=2):
                        st.warning(nav.render_remedy_markdown("判別式"))
                        with st.expander("🧭 動態路徑導航（回溯前置 + 看歷史正確率）"):
                            targets = dynamic_remediation_targets(
                                conv_conn,
                                student_id=student_id,
                                failed_concept="判別式",
                                threshold=0.7,
                                min_attempts=3,
                            )
                            if targets:
                                for t in targets:
                                    label = str(t.get("label"))
                                    acc = float(t.get("accuracy", 1.0))
                                    attempts = int(t.get("attempts", 0))
                                    st.markdown(f"- 優先補救：**{label}**（近 {attempts} 次正確率：{acc:.0%}）")
                                    for (title, url) in nav.get_resource_links(label):
                                        st.markdown(f"  - [{title}]({url})")
                            else:
                                st.info("目前尚無足夠歷史資料判定弱點；先回看前置概念即可。")
                        st.info("提示：D 的公式是 $b^2-4ac$，先把 a,b,c 代入再算。")
            except Exception as e:
                st.error(f"格式錯誤：{e}")

    st.markdown("#### Step 2：請輸入兩個根")
    with st.form("quad_form_roots"):
        r_in = st.text_input("輸入根（例如：2, 3 或 -1 4）", key="quad_roots_input")
        submitted_r = st.form_submit_button("檢查根")
    if submitted_r:
        try:
            roots_user = _parse_roots_input(r_in)
            if len(roots_user) != 2:
                st.warning("請輸入兩個根，例如：2, 3")
            else:
                roots_true = q["roots"]
                roots_user_sorted = sorted(roots_user)
                ok = (roots_user_sorted[0] == roots_true[0] and roots_user_sorted[1] == roots_true[1])
                nav.record_attempt("公式解", ok)
                log_conversation(
                    student_id=student_id,
                    subject="math",
                    question=f"Roots for {q['eq_latex']}",
                    answer=str(roots_user_sorted),
                    topic="一元二次",
                    difficulty=math_level_label(int(active_level)),
                    mode="quadratic_roots",
                    correct=1 if ok else 0,
                    meta={"concept": "公式解", "level": int(active_level), "a": q["a"], "b": q["b"], "c": q["c"], "roots": [str(x) for x in roots_true]},
                )
                if ok:
                    st.success("正確 ✅")
                else:
                    qs["r_attempts"] += 1
                    st.error("不正確 ❌ 先檢查：(-b ± √D) / (2a) 的分母與 ±。")
                    if nav.should_push_resources("公式解", threshold=2):
                        st.warning(nav.render_remedy_markdown("公式解"))
                        with st.expander("🧭 動態路徑導航（回溯前置 + 看歷史正確率）"):
                            targets = dynamic_remediation_targets(
                                conv_conn,
                                student_id=student_id,
                                failed_concept="公式解",
                                threshold=0.7,
                                min_attempts=3,
                            )
                            if targets:
                                for t in targets:
                                    label = str(t.get("label"))
                                    acc = float(t.get("accuracy", 1.0))
                                    attempts = int(t.get("attempts", 0))
                                    st.markdown(f"- 優先補救：**{label}**（近 {attempts} 次正確率：{acc:.0%}）")
                                    for (title, url) in nav.get_resource_links(label):
                                        st.markdown(f"  - [{title}]({url})")
                            else:
                                st.info("目前尚無足夠歷史資料判定弱點；先回看前置概念即可。")
                        st.info("提示：先算 D，再算 √D，最後帶入公式。")
        except Exception as e:
            st.error(f"格式錯誤：{e}")

    with st.expander("（可選）顯示教科書式解答（用於自我校正）"):
        x = sp.Symbol("x")
        a, b, c = q["a"], q["b"], q["c"]
        D = q["D"]
        st.markdown(f"$a={a},\; b={b},\; c={c}$")
        st.markdown(f"$$D=b^2-4ac={b}^2-4\cdot {a}\cdot {c}={D}$$")
        st.markdown(
            "$$x=\frac{-b\pm\sqrt{D}}{2a}$$"
        )
        st.markdown(
            "正確根：" + ", ".join([f"$${sp.latex(r)}$$" for r in q["roots"]])
        )
    st.subheader("學生提示模式（不直接給答案）")
    stu_state = st.text_area("學生目前想法 / 錯誤推理", height=80)
    if st.button("給提示 (離線)"):
        if not q:
            st.warning("請先輸入題目（可用上方自動出題或自行輸入）")
        else:
            hint = next_step_hint_offline(q, stu_state, student_id)
            st.info(hint or "無提示內容")

# ============================================================
# 🧩 題庫管理
# ============================================================
with tab2:
    st.subheader("題庫 / 解題快取管理 (answers.db)")
    if st.button("查看快取資料數"):
        c = answers_conn.cursor()
        n = c.execute("SELECT COUNT(*) FROM answers").fetchone()[0]
        st.info(f"當前 answers.db 含有 {n} 筆解題資料")
    if st.button("清除所有快取"):
        answers_conn.execute("DELETE FROM answers")
        answers_conn.commit()
        st.success("已清除所有快取")

# ============================================================
# 📈 出題統計分析（answers.db）
# ============================================================
with tab4:
    st.subheader("出題統計分析 (answers.db)")
    conn = sqlite3.connect(DB_ANS)
    df = pd.read_sql_query("SELECT question, answer FROM answers", conn)
    conn.close()

    if df.empty:
        st.info("目前沒有答案快取資料。請先使用 AI 解題或自動出題。")
    else:
        df["字數"] = df["question"].apply(len)
        df["題型"] = df["question"].apply(classify_topic)
        df["難度"] = df["question"].apply(estimate_difficulty)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("題目總數", len(df))
        with col2:
            st.metric("平均題目長度", f"{df['字數'].mean():.1f} 字")
        with col3:
            avg_ans_len = df["answer"].apply(len).mean()
            st.metric("平均解答長度", f"{avg_ans_len:.1f} 字")

        st.markdown("### 題型比例分布")
        st.bar_chart(df["題型"].value_counts())

        st.markdown("### 難度比例分布")
        st.bar_chart(df["難度"].value_counts())

        st.markdown("### 題目字數分布")
        st.line_chart(df["字數"])

        st.download_button(
            "下載題庫 JSON",
            data=df.to_json(orient="records", force_ascii=False, indent=2),
            file_name="answers_export.json",
            mime="application/json",
        )
        st.success("統計分析完成")

# ============================================================
# 🧠 學習報表 / 學習大腦（conversation.db + GPT/DeepSeek 摘要）
# ============================================================

def build_learning_summary_text(student_id: str, days: int = 7):
    cur = conv_conn.cursor()
    cur.execute(
        """
        SELECT subject, topic, difficulty, mode, question, answer, correct, created_at
        FROM conversation_log
        WHERE student_id = ?
          AND created_at >= datetime('now', ?)
        ORDER BY created_at DESC
        LIMIT 200
        """,
        (student_id, f"-{days} day"),
    )
    rows = cur.fetchall()
    if not rows:
        return "", "", 0

    lines = []
    for subj, topic, diff, mode, q, a, correct, ts in rows:
        status = "未知"
        if correct == 1:
            status = "答對"
        elif correct == 0:
            status = "答錯"
        lines.append(
            f"[{ts}] 科目={subj}, 題型={topic}, 難度={diff}, 模式={mode}, 狀態={status}, 題目={q[:40]}..."
        )
    log_text = "\n".join(lines)

    # 統計摘要
    df = pd.DataFrame(
        rows,
        columns=["subject", "topic", "difficulty", "mode", "question", "answer", "correct", "created_at"],
    )
    by_topic = df.groupby("topic").size().to_dict()
    by_diff = df.groupby("difficulty").size().to_dict()
    stats_lines = [
        f"總筆數: {len(df)}",
        f"題型分布: {by_topic}",
        f"難度分布: {by_diff}",
        f"模式分布: {df.groupby('mode').size().to_dict()}",
    ]
    stats_text = "\n".join(stats_lines)
    return log_text, stats_text, len(df)


def summarize_learning_with_gpt(log_text: str, stats_text: str) -> str:
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "未設定 OPENAI_API_KEY，無法使用 GPT。"

    client = OpenAI(api_key=api_key)
    prompt = (
        "你是一位會做學習診斷的數學老師。請根據學生最近的作答紀錄與統計，"
        "產出學習摘要與下週練習計畫。\n\n"
        "輸出格式固定為：\n"
        "一、整體表現概述（3~5 句）\n"
        "二、明顯弱點（條列 3 點，以「概念/技能」描述）\n"
        "三、接下來 1 週建議練習計畫（用 Day1~Day7 列點）\n\n"
        f"【作答紀錄】\n{log_text}\n\n"
        f"【統計摘要】\n{stats_text}\n"
    )
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "你是一位嚴謹但鼓勵學生的數學老師。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    return resp.choices[0].message.content.strip()


def summarize_learning_with_ollama(log_text: str, stats_text: str) -> str:
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL_SUMMARY", "llama3.1:8b-instruct-q5_K_M")
    prompt = (
        "你是一位數學老師，請根據學生最近的作答紀錄與統計，"
        "用簡體或繁體中文生成學習摘要與建議。"
        "請遵守以下格式：\n"
        "一、整體表現概述\n"
        "二、主要弱點\n"
        "三、下週練習建議\n\n"
        f"【作答紀錄】\n{log_text}\n\n"
        f"【統計摘要】\n{stats_text}\n"
    )
    try:
        resp = requests.post(
            f"{host}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        text = ""
        for line in resp.text.splitlines():
            try:
                data = json.loads(line)
                text += data.get("response", "")
            except Exception:
                text += line
        return text.strip()
    except Exception as e:
        return f"離線摘要模型錯誤：{e}"


with tab5:
    st.subheader("學習報表 / 學習大腦")

    stu_id = st.text_input(
        "學生 ID 或姓名（與數學教師模式相同）",
        value=st.session_state.get("student_id", "demo_student"),
        key="report_student_id",
    )
    days = st.slider("統計最近天數", min_value=3, max_value=30, value=7, step=1)

    mode_summary = st.selectbox(
        "摘要模型選擇",
        ["自動選擇", "優先使用 GPT-4o-mini（需 API）", "只用離線 Ollama"],
        index=0,
    )

    st.markdown("---")
    st.markdown("### 即時診斷儀表板（不依賴 LLM）")

    col1, col2 = st.columns([1.2, 1])
    with col1:
        lookback = st.slider("統計回溯天數（自適應/儀表板）", min_value=7, max_value=180, value=60, step=1)
        concepts = ["分配律", "因式分解", "判別式", "公式解"]
        concept_acc = history_accuracy_by_concept_cached(stu_id, tuple(concepts), lookback_days=int(lookback))
        concept_rows = []
        for c in concepts:
            m = concept_acc.get(c) or {"attempts": 0, "correct": 0, "accuracy": 1.0}
            concept_rows.append(
                {
                    "Concept": c,
                    "Attempts": int(m.get("attempts", 0)),
                    "Correct": int(m.get("correct", 0)),
                    "Accuracy": float(m.get("accuracy", 1.0)),
                }
            )
        st.dataframe(pd.DataFrame(concept_rows), width="stretch")

        st.caption("說明：Accuracy 來自 conversation.db（meta_json['concept']）。")

    with col2:
        qs = st.session_state.get("quad_state") or {"level": 2, "adaptive": True}
        cur_level = int(qs.get("level", 2))
        rec_level, rec_reason = recommend_quadratic_level(
            conv_conn,
            student_id=stu_id,
            current_level=cur_level,
            lookback_days=int(lookback),
        )
        st.markdown(f"**目前一元二次 Level**：{math_level_label(cur_level)}")
        st.markdown(f"**建議下一題 Level**：{math_level_label(rec_level)}")
        st.caption(rec_reason)

        lvl_stats = quadratic_level_stats_cached(stu_id, lookback_days=int(lookback))
        lvl_rows = []
        for lvl in range(1, 6):
            m = lvl_stats.get(lvl) or {"attempts": 0, "correct": 0, "accuracy": 1.0}
            lvl_rows.append(
                {
                    "Level": lvl,
                    "Attempts": int(m.get("attempts", 0)),
                    "Correct": int(m.get("correct", 0)),
                    "Accuracy": float(m.get("accuracy", 1.0)),
                }
            )
        st.dataframe(pd.DataFrame(lvl_rows), width="stretch")

        if st.button("套用建議（設為自適應 + 更新 Level）"):
            if "quad_state" not in st.session_state:
                st.session_state["quad_state"] = {}
            st.session_state["quad_state"]["adaptive"] = True
            st.session_state["quad_state"]["level"] = int(rec_level)
            st.session_state["quad_state"]["last_level_reason"] = f"報表套用：{rec_reason}"
            st.success("已套用。請切到『🎓 數學教師模式』按『出新題（Quadratic）』。");

    st.markdown("### 優先補救清單（動態路徑導航）")
    failed_pick = st.selectbox("假設學生卡關點", ["公式解", "判別式", "因式分解", "分配律"], index=0)
    threshold = st.slider("補救門檻（正確率 < x）", min_value=0.3, max_value=0.95, value=0.7, step=0.05)
    min_attempts = st.slider("至少嘗試次數", min_value=1, max_value=10, value=3, step=1)
    targets = dynamic_remediation_targets(
        conv_conn,
        student_id=stu_id,
        failed_concept=str(failed_pick),
        threshold=float(threshold),
        min_attempts=int(min_attempts),
        lookback_days=int(lookback),
    )
    if targets:
        for t in targets:
            label = str(t.get("label"))
            acc = float(t.get("accuracy", 1.0))
            attempts = int(t.get("attempts", 0))
            st.markdown(f"- **{label}**（近 {attempts} 次正確率：{acc:.0%}）")
            for (title, url) in st.session_state["knowledge_nav"].get_resource_links(label):
                st.markdown(f"  - [{title}]({url})")
    else:
        st.info("目前未偵測到明確弱點（或資料不足）。")

    if st.button("生成學習摘要報告"):
        log_text, stats_text, count = build_learning_summary_text(stu_id, days=days)
        if count == 0:
            st.info("此學生在指定期間內沒有紀錄。")
        else:
            st.markdown("### 原始紀錄摘要（供模型參考）")
            st.text(log_text)
            st.markdown("### 統計摘要")
            st.text(stats_text)

            use_gpt = False
            if mode_summary == "只用離線 Ollama":
                use_gpt = False
            elif mode_summary == "優先使用 GPT-4o-mini（需 API）":
                use_gpt = True
            else:  # 自動選擇
                use_gpt = bool(os.getenv("OPENAI_API_KEY"))

            if use_gpt:
                try:
                    summary = summarize_learning_with_gpt(log_text, stats_text)
                    st.markdown("### GPT-4o-mini 學習摘要")
                    st.markdown(summary)
                except Exception as e:
                    st.error(f"GPT 摘要失敗：{e}，改用離線模式。")
                    summary = summarize_learning_with_ollama(log_text, stats_text)
                    st.markdown("### 離線 Ollama 學習摘要")
                    st.markdown(summary)
            else:
                summary = summarize_learning_with_ollama(log_text, stats_text)
                st.markdown("### 離線 Ollama 學習摘要")
                st.markdown(summary)
