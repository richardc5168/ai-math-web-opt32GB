import streamlit as st
import os, sqlite3, hashlib, json, requests, pandas as pd, re, numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

from rag_backend import Retriever

DB_ANS = "answers.db"
DB_CONV = "conversation.db"

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

answers_conn = init_answers_db()
conv_conn = init_conversation_db()
retriever = Retriever("knowledge.db")

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
