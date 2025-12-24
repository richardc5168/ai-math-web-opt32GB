# app.py
# Neo RAG 離線版：結合本地 Ollama (llama3.1:8b-instruct-q5_K_M)
import os, json, requests, streamlit as st
from rag_backend import Retriever
from neo_rag_prompts import QA_PROMPT, SUMM_PROMPT, COMPARE_PROMPT

# ======== 初始化 ========
st.set_page_config(page_title="Neo RAG 教學助理 (離線版)", layout="wide")
st.title("🧠 Neo 文件知識庫 (RAG + Llama3.1 離線生成)")

retriever = Retriever("knowledge.db")

# Ollama 設定
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b-instruct-q5_K_M")

def run_ollama(prompt: str) -> str:
    """呼叫本地 Ollama API 生成回答"""
    try:
        resp = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=300
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("response", "").strip()
        else:
            return f"[錯誤] Ollama 回傳碼 {resp.status_code}: {resp.text}"
    except Exception as e:
        return f"[無法連線 Ollama] {e}"

# ======== 側邊欄狀態 ========
with st.sidebar:
    st.markdown("### 系統狀態")
    st.write(f"RAG 啟用：{'✅' if retriever else '❌'}")
    # 檢查 Ollama 狀態
    try:
        test = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=3)
        if test.status_code == 200:
            st.write(f"Ollama 模型：✅ {OLLAMA_MODEL}")
            OLLAMA_OK = True
        else:
            st.warning("⚠️ 找不到 Ollama 模型服務")
            OLLAMA_OK = False
    except Exception:
        st.warning("⚠️ 無法連線 Ollama，本系統將僅顯示檢索結果")
        OLLAMA_OK = False
    st.write("知識庫：knowledge.db")
    st.caption("🔒 全程離線運作，資料不會外傳。")

# ======== 主介面 ========
tab1, tab2 = st.tabs(["📚 RAG 問答", "🧩 題庫管理（可略過）"])

# --- Tab1: RAG 問答 ---
with tab1:
    st.subheader("📘 問 Neo 文件內容（RAG + Llama 離線模式）")
    q = st.text_area("輸入你的問題", height=100)
    mode = st.selectbox("選擇回答風格", ["一般問答", "摘要", "版本比較"])
    topk = st.slider("檢索片段數 Top-K", 1, 8, 4)

    if st.button("開始查詢"):
        hits = retriever.search(q, topk=topk)
        if not hits:
            st.error("❌ knowledge.db 無內容，請先執行 ingest_neo_docs_sections.py")
        else:
            # 合併檢索內容
            ctx = "\n\n".join([h["text"] for h in hits])

            # 套用 Prompt 模板
            if mode == "摘要":
                prompt = SUMM_PROMPT.format(question=q, context=ctx)
            elif mode == "版本比較":
                prompt = COMPARE_PROMPT.format(context_a=ctx, context_b=ctx, question=q)
            else:
                prompt = QA_PROMPT.format(question=q, context=ctx)

            st.markdown("#### 🔍 檢索片段來源")
            for h in hits:
                st.markdown(f"- **{h['source']}** (score={h['score']:.2f})")

            # ---- Ollama 離線回答 ----
            st.markdown("#### 🧠 離線 AI 回答")
            if OLLAMA_OK:
                with st.spinner(f"正在使用 {OLLAMA_MODEL} 生成回答..."):
                    answer = run_ollama(prompt)
                    st.markdown(answer)
            else:
                st.warning("⚠️ 無法連線 Ollama，僅顯示檢索內容。")
                st.text_area("檢索內容", ctx, height=200)

# --- Tab2: 題庫管理（可略過） ---
with tab2:
    st.info("此區暫留給題庫功能。RAG 問答與 Ollama 模型已可離線運作。")
