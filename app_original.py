# app.py
# 離線題庫 + Neo RAG 問答介面
import os, sqlite3, json, streamlit as st
from rag_backend import Retriever
from neo_rag_prompts import QA_PROMPT, SUMM_PROMPT, COMPARE_PROMPT

st.set_page_config(page_title="Neo RAG 教學助理", layout="wide")
st.title("🧠 Neo 文件知識庫 (RAG) + 題庫系統")

# 初始化 RAG
retriever = Retriever("knowledge.db")

# Sidebar 狀態
with st.sidebar:
    st.markdown("### 系統狀態")
    st.write(f"RAG 啟用：{'✅' if retriever else '❌'}")
    st.write(f"知識庫路徑：knowledge.db")
    st.markdown("---")
    st.caption("離線運作時不會外傳任何資料")

# Tabs
tab1, tab2 = st.tabs(["📚 RAG 問答", "🧩 題庫管理（可略過）"])

# --- Tab1: RAG 問答 ---
with tab1:
    st.subheader("📘 問 Neo 文件內容（RAG 模式）")
    q = st.text_area("輸入你的問題", height=100)
    mode = st.selectbox("選擇回答風格", ["一般問答", "摘要", "版本比較"])
    topk = st.slider("檢索片段數 Top-K", 1, 8, 4)

    if st.button("開始查詢"):
        hits = retriever.search(q, topk=topk)
        if not hits:
            st.error("knowledge.db 無內容，請先執行 ingest_neo_docs_sections.py")
        else:
            ctx = "\n\n".join([h["text"] for h in hits])
            if mode == "摘要":
                prompt = SUMM_PROMPT.format(question=q, context=ctx)
            elif mode == "版本比較":
                prompt = COMPARE_PROMPT.format(context_a=ctx, context_b=ctx, question=q)
            else:
                prompt = QA_PROMPT.format(question=q, context=ctx)

            st.markdown("#### 🔍 檢索片段來源")
            for h in hits:
                st.markdown(f"- **{h['source']}** (score={h['score']:.2f})")

            # 使用 OpenAI 或 Ollama（可選）
            if os.getenv("OPENAI_API_KEY"):
                from openai import OpenAI
                client = OpenAI()
                resp = client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    messages=[{"role":"user","content":prompt}],
                )
                st.markdown("#### 🧠 AI 回答")
                st.write(resp.choices[0].message.content)
            else:
                st.warning("未設定 OPENAI_API_KEY，無法生成回答，但已顯示檢索片段。")

# --- Tab2: 題庫管理（可略過） ---
with tab2:
    st.info("此區僅供題庫用途，可略過。RAG 模式不依賴 questions.db。")
