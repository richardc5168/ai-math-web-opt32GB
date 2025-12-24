import streamlit as st, os, sqlite3, hashlib, json, requests, pandas as pd, re, numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from rag_backend import Retriever

# === LLM 中文回答函式（使用 GPT / DeepSeek / Ollama 任意模型）===
def qa_answer_zh(question, contexts):
    """
    contexts: list of strings (retrieved chunks)
    回傳：模型輸出的繁體中文回答
    """
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "deepseek-math:7b")

    context_text = "\n\n".join([f"[片段{i+1}]\n{c}" for i, c in enumerate(contexts)])

    prompt = f"""
你是一位技術說明助理。請依據以下文件內容，用繁體中文回答問題。

【文件內容】
{context_text}

【使用者問題】
{question}

回覆要求：
1. 嚴格依據文件內容，不要捏造資訊。
2. 若文件不足以回答，請明確說「文件中未提供足夠資訊」。
3. 回答必須使用繁體中文，條列式分點整理。
"""

    try:
        r = requests.post(
            f"{host}/api/generate",
            json={"model": model, "prompt": prompt},
            timeout=90
        )
        return r.text.strip()
    except Exception as e:
        return f"[回答產生錯誤] {e}"



DB_ANS = "answers.db"

# === 題庫載入與抽題 ===
import random, re, glob

TOPIC_KEYS = {
    "分數": r"(分數|fraction|通分|約分|分母|分子)",
    "小數": r"(小數|decimal|四捨五入|位值|近似)",
    "幾何": r"(角|面積|周長|邊|圖形|三角形|梯形|長方形|geometry)",
    "應用題": r"(速度|時間|工作|濃度|比例|比率|率|應用)"
}

def _classify_topic(text: str) -> str:
    t = text.lower()
    for k, pat in TOPIC_KEYS.items():
        if re.search(pat, t):
            return k
    return "應用題"

def _estimate_difficulty(text: str) -> str:
    L = len(text)
    if L < 40: return "簡單"
    if L < 100: return "中等"
    return "困難"

def load_math_candidates():
    """
    優先使用 math_bank_index.json；若沒有，從 knowledge.db 內挑出 math 來源。
    回傳：list[ {id, question, topic, difficulty, source} ]
    """
    idx_path = "math_bank_index.json"
    if os.path.exists(idx_path):
        with open(idx_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 統一欄位
        rows = []
        for i, item in enumerate(data):
            q = item.get("question") or item.get("題目") or ""
            rows.append({
                "id": f"IDX_{i}",
                "question": q,
                "topic": item.get("topic") or item.get("題型") or _classify_topic(q),
                "difficulty": item.get("difficulty") or item.get("難度") or _estimate_difficulty(q),
                "source": item.get("source") or "math_bank_index.json",
            })
        return rows

    # 從 knowledge.db 抽取含 math 關鍵字的來源
    rows = []
    try:
        conn = sqlite3.connect("knowledge.db")
        cur = conn.cursor()
        # 你題庫常見來源：gradeX_*.json / geometry.txt / algebra.pdf …可擴增
        cur.execute("""
            SELECT id, source, text FROM knowledge
            WHERE lower(source) LIKE '%grade%' OR lower(source) LIKE '%math%' 
               OR lower(source) LIKE '%geometry%' OR lower(source) LIKE '%algebra%'
        """)
        for rid, src, txt in cur.fetchall():
            qtxt = txt.strip()
            rows.append({
                "id": f"DB_{rid}",
                "question": qtxt,
                "topic": _classify_topic(qtxt),
                "difficulty": _estimate_difficulty(qtxt),
                "source": src
            })
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return rows

def sample_questions(candidates, n=3, topics=None, difficulties=None, used=set()):
    """
    依主題/難度過濾並隨機抽 n 題，避免重覆
    """
    pool = []
    for item in candidates:
        if topics and item["topic"] not in topics:
            continue
        if difficulties and item["difficulty"] not in difficulties:
            continue
        if item["id"] in used:
            continue
        pool.append(item)
    random.shuffle(pool)
    return pool[:n]

def generate_questions_by_model(n=3, topic_hint="應用題", difficulty_hint="中等"):
    """
    由本地 deepseek-math:7b 生成新題（純文字），回傳同樣的結構
    """
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "deepseek-math:7b")
    sys_prompt = (
        "你是一位國小數學命題老師。請生成{n}題{topic}，難度{diff}，每題用單行敘述，避免超過60字，"
        "不提供解答與提示，只回題幹，每題獨立成行。"
    ).format(n=n, topic=topic_hint, diff=difficulty_hint)
    try:
        r = requests.post(f"{host}/api/generate", json={"model": model, "prompt": sys_prompt}, timeout=120)
        text = r.text.strip()
    except Exception as e:
        text = f"[模型出題錯誤] {e}"
    # 粗切行
    lines = [ln.strip("-• ").strip() for ln in text.splitlines() if ln.strip()]
    rows = []
    for i, q in enumerate(lines[:n]):
        rows.append({
            "id": f"GEN_{hashlib.md5((q+str(i)).encode()).hexdigest()[:10]}",
            "question": q,
            "topic": _classify_topic(q),
            "difficulty": _estimate_difficulty(q),
            "source": "deepseek-math:7b"
        })
    return rows

def save_answer_to_db(conn, question: str, answer: str):
    qid = hashlib.md5(question.encode()).hexdigest()
    conn.execute("REPLACE INTO answers(id, question, answer) VALUES(?,?,?)", (qid, question, answer))
    conn.commit()



# === 初始化答案資料庫 ===
def init_answers_db():
    conn = sqlite3.connect(DB_ANS)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS answers(
        id TEXT PRIMARY KEY,
        question TEXT,
        answer TEXT
    )""")
    conn.commit()
    return conn

answers_conn = init_answers_db()
retriever = Retriever("knowledge.db")

st.set_page_config(page_title="Neo 文件與數學教師系統", layout="wide")
st.title("🧠 Neo 文件知識庫 + 🎓 AI 數學教師")

tab1, tab2, tab3, tab4 = st.tabs([
    "📚 文件問答", 
    "🧩 題庫管理", 
    "🎓 數學教師模式", 
    "📈 出題統計分析"
])

# ============================================================
# 📚 文件問答區
# ============================================================

with tab1:
    st.subheader("📘 文件問答")
    q = st.text_area("輸入問題", height=100)

    if st.button("查詢文件"):
        if not q:
            st.warning("請輸入問題")
        else:
            hits = retriever.search(q, topk=4)

            if not hits:
                st.info("未找到相關文件內容。")
            else:
                # 顯示文件片段
                contexts = []
                for h in hits:
                    st.markdown(f"**來源：{h['source']}**\n\n{h['text'][:800]}…")
                    contexts.append(h["text"])

                st.success("📄 已取得文件內容（用於回答）")

                # === 加入中文回答 ===
                st.markdown("## 🧠 中文回答（依文件內容）")
                ans_zh = qa_answer_zh(q, contexts)
                st.write(ans_zh)



# ============================================================
# 🎓 AI 數學教師模式
# ============================================================
def get_or_build_solution(q: str) -> dict:
    qid = hashlib.md5(q.encode()).hexdigest()
    c = answers_conn.cursor()
    r = c.execute("SELECT answer FROM answers WHERE id=?", (qid,)).fetchone()
    if r:
        return {"answer": r[0]}

    ctx = "\n".join([x["text"] for x in retriever.search(q, topk=3)])
    prompt = f"請逐步解答下列數學題，並給出清晰步驟：\n題目：{q}\n參考資料：{ctx}"
    model = os.getenv("OLLAMA_MODEL", "deepseek-math:7b")
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    try:
        r = requests.post(f"{host}/api/generate", json={"model": model, "prompt": prompt})
        ans = r.text.strip()
    except Exception as e:
        ans = f"離線模型錯誤：{e}"

    c.execute("REPLACE INTO answers VALUES(?,?,?)", (qid, q, ans))
    answers_conn.commit()
    return {"answer": ans}


def next_step_hint_offline(q: str, state: str) -> str:
    p = f"題目：{q}\n學生目前想法：{state}\n請給下一步提示，不要直接給答案。"
    try:
        r = requests.post("http://localhost:11434/api/generate",
            json={"model": "deepseek-math:7b", "prompt": p}, timeout=60)
        return r.text.strip()
    except Exception as e:
        return f"提示生成錯誤：{e}"

with tab3:
    st.subheader("🎓 AI 數學教師模式")

    # 狀態
    if "used_qids" not in st.session_state:
        st.session_state.used_qids = set()
    if "last_batch" not in st.session_state:
        st.session_state.last_batch = []

    # === 出題來源選擇 ===
    st.markdown("**出題來源**")
    source_mode = st.radio("選擇出題來源", ["題庫抽題", "模型自動出題"], horizontal=True)

    colA, colB, colC = st.columns(3)
    with colA:
        topics = st.multiselect("主題過濾", ["分數", "小數", "幾何", "應用題"], default=[])
    with colB:
        difficulties = st.multiselect("難度過濾", ["簡單", "中等", "困難"], default=[])
    with colC:
        n_pick = st.number_input("出題數量", min_value=1, max_value=20, value=3, step=1)

    st.markdown("—")

    # === 🎲 隨機/自動出題 ===
    if source_mode == "題庫抽題":
        if st.button("🎲 題庫抽題"):
            candidates = load_math_candidates()
            batch = sample_questions(candidates, n=n_pick, topics=topics or None,
                                     difficulties=difficulties or None, used=st.session_state.used_qids)
            st.session_state.last_batch = batch
            for it in batch:
                st.session_state.used_qids.add(it["id"])

    else:  # 模型自動出題
        colM1, colM2 = st.columns(2)
        with colM1:
            topic_hint = st.selectbox("主題提示", ["應用題", "分數", "小數", "幾何"], index=0)
        with colM2:
            diff_hint = st.selectbox("難度提示", ["簡單", "中等", "困難"], index=1)
        if st.button("🤖 模型自動出題（離線）"):
            st.session_state.last_batch = generate_questions_by_model(n=n_pick, topic_hint=topic_hint, difficulty_hint=diff_hint)

    # === 顯示本次出題 ===
    if st.session_state.last_batch:
        st.markdown("### 本次題目")
        for i, item in enumerate(st.session_state.last_batch, 1):
            st.write(f"**Q{i} [{item['topic']}/{item['difficulty']}]** {item['question']}  \n*來源：{item['source']}*")

        # 一鍵全解
        if st.button("🧠 一鍵全解並快取"):
            for item in st.session_state.last_batch:
                sol = get_or_build_solution(item["question"])  # 會自動寫 answers.db
                # 再存一次確保最新答案覆蓋
                save_answer_to_db(answers_conn, item["question"], sol["answer"])
            st.success("✅ 已完成解題並快取（answers.db）")

    st.markdown("---")
    st.subheader("🔎 手動解題 / 提示")
    q = st.text_area("輸入題目", height=100, placeholder="也可手動貼題")
    if st.button("解題 / 教學說明"):
        if not q:
            st.warning("請輸入題目")
        else:
            sol = get_or_build_solution(q)
            st.markdown(sol["answer"])
            save_answer_to_db(answers_conn, q, sol["answer"])

    stu_state = st.text_area("學生目前想法 / 錯誤推理", height=80)
    if st.button("給提示 (離線)"):
        if not q:
            st.warning("請先輸入題目 或 使用上面的出題功能")
        else:
            hint = next_step_hint_offline(q, stu_state)
            st.info(hint or "無提示內容")

  
# ============================================================
# 🧩 題庫管理
# ============================================================
with tab2:
    st.subheader("🧩 題庫管理")
    if st.button("查看快取資料數"):
        c = answers_conn.cursor()
        n = c.execute("SELECT COUNT(*) FROM answers").fetchone()[0]
        st.info(f"📊 當前 answers.db 含有 {n} 筆解題資料")
    if st.button("清除所有快取"):
        answers_conn.execute("DELETE FROM answers")
        answers_conn.commit()
        st.success("✅ 已清除所有快取")

# ============================================================
# 📈 出題統計分析（含題型、難度與熱力圖）
# ============================================================
def classify_topic(q):
    q = q.lower()
    if re.search(r"分數|fraction", q): return "分數"
    if re.search(r"小數|decimal", q): return "小數"
    if re.search(r"角|面積|邊|圖形|geometry", q): return "幾何"
    return "應用題"

def estimate_difficulty(q):
    length = len(q)
    if length < 30: return "簡單"
    elif length < 80: return "中等"
    else: return "困難"

with tab4:
    st.subheader("📈 出題統計分析")
    conn = sqlite3.connect(DB_ANS)
    df = pd.read_sql_query("SELECT question, answer FROM answers", conn)
    conn.close()

    if df.empty:
        st.info("目前沒有題目資料。請先使用 AI 出題或解題。")
    else:
        df["字數"] = df["question"].apply(len)
        df["題型"] = df["question"].apply(classify_topic)
        df["難度"] = df["question"].apply(estimate_difficulty)

        col1, col2, col3 = st.columns(3)
        with col1: st.metric("題目總數", len(df))
        with col2: st.metric("平均題目長度", f"{df['字數'].mean():.1f} 字")
        with col3:
            avg_ans_len = df["answer"].apply(len).mean()
            st.metric("平均解答長度", f"{avg_ans_len:.1f} 字")

        st.markdown("### 題型比例分布")
        st.bar_chart(df["題型"].value_counts())

        st.markdown("### 難度比例分布")
        st.bar_chart(df["難度"].value_counts())

        # === 新增：題型 × 難度 熱力圖 ===
        st.markdown("### 📊 題型 × 難度 熱力圖")
        pivot = pd.crosstab(df["題型"], df["難度"])
        fig, ax = plt.subplots(figsize=(6,4))
        sns.heatmap(pivot, annot=True, fmt="d", cmap="YlGnBu", ax=ax)
        st.pyplot(fig)

        st.markdown("### 題目字數分布")
        st.line_chart(df["字數"])

        st.download_button("📥 下載題庫 JSON",
                           data=df.to_json(orient="records", force_ascii=False, indent=2),
                           file_name="answers_export.json", mime="application/json")
        st.success("✅ 統計分析完成")
