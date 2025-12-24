#!/bin/bash
# ===========================================
# 🧠 Neo RAG 啟動腳本 (自動掃描文件 + 啟動系統)
# 功能：
# 1️⃣ 啟用 Python 虛擬環境
# 2️⃣ 自動建立/更新 knowledge.db
# 3️⃣ 自動偵測 GPT-4o 或 Llama3.1 模式
# 4️⃣ 啟動 Streamlit 前端
# ===========================================

echo "------------------------------------"
echo "🚀 啟動 Neo RAG 系統中..."
echo "------------------------------------"

# 切換到專案資料夾
cd /mnt/c/Users/Richard/Documents/RAG || exit

# 啟用虛擬環境
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ 虛擬環境已啟用 (.venv)"
else
    echo "⚠️ 找不到 .venv，正在建立虛擬環境..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install streamlit openai requests sentence-transformers pypdf
fi

# 自動建立 neo_docs 資料夾（若不存在）
if [ ! -d "neo_docs" ]; then
    mkdir neo_docs
    echo "📁 已建立 neo_docs/ 資料夾，請放入你的 Neo 文件（PDF / DOCX / TXT）"
fi

# 自動偵測並更新 knowledge.db
if [ "$(find neo_docs -type f \( -iname '*.pdf' -o -iname '*.docx' -o -iname '*.txt' \) | wc -l)" -gt 0 ]; then
    echo "🔍 偵測到新文件，更新 knowledge.db 中..."
    if [ -f "ingest_neo_docs_sections.py" ]; then
        python3 ingest_neo_docs_sections.py
        echo "✅ knowledge.db 已更新完成"
    else
        echo "⚠️ 找不到 ingest_neo_docs_sections.py，請確認檔案存在。"
    fi
else
    echo "⚠️ neo_docs/ 無文件可更新，跳過建庫步驟。"
fi

# 檢查 OpenAI API 金鑰
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️ 未偵測到 OPENAI_API_KEY！"
    echo "👉 請執行： export OPENAI_API_KEY=\"sk-你的金鑰\""
    echo "將自動切換至離線模式（Llama3.1）"
else
    echo "✅ 已偵測到 OPENAI_API_KEY，啟用 GPT-4o 雲端模式"
fi

# 啟動 Streamlit
echo "------------------------------------"
echo "🌐 啟動 Streamlit 前端..."
echo "（稍等幾秒後可於瀏覽器開啟）"
echo "------------------------------------"
streamlit run app.py --server.address 0.0.0.0 --server.port 8503
