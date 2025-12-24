#!/bin/bash
# ===========================================================
# 🚀 Neo 文件知識庫一鍵啟動腳本（含自動版本修正與模型管理）
# ===========================================================

APP_PORT=8508
APP_FILE="app.py"
VENV_PATH=".venv"
BROWSER_URL="http://127.0.0.1:${APP_PORT}"
OLLAMA_DEFAULT="/usr/bin/ollama"
OLLAMA_LOCAL="/usr/local/bin/ollama"
MODEL_MAIN="llama3.1:8b-instruct-q5_K_M"
MODEL_MATH="deepseek-math:7b"
OLLAMA_HOST="http://localhost:11434"

echo "==========================================="
echo "🧠 啟動 Neo 文件知識庫（自動檢測環境）"
echo "==========================================="

# 1️⃣ 啟用虛擬環境
if [ -d "${VENV_PATH}" ]; then
    source "${VENV_PATH}/bin/activate"
    echo "✅ 已啟用虛擬環境 ${VENV_PATH}"
else
    echo "❌ 找不到虛擬環境，請先執行：python3 -m venv .venv"
    exit 1
fi

# 2️⃣ 偵測 Ollama 版本並修正
OLLAMA_CMD="ollama"
if ! which ollama >/dev/null 2>&1; then
    echo "⚠️ 找不到 Ollama 可執行檔，嘗試使用 ${OLLAMA_LOCAL}"
    OLLAMA_CMD="${OLLAMA_LOCAL}"
else
    ver=$($(which ollama) --version | grep -oE '[0-9]+\.[0-9]+' | head -1)
    if [[ "$ver" == "0.12" || "$ver" == "0.12."* ]]; then
        echo "⚠️ 偵測到舊版 Ollama ($ver)，切換至新版 ${OLLAMA_LOCAL}"
        sudo ln -sf "${OLLAMA_LOCAL}" /usr/bin/ollama
        OLLAMA_CMD="${OLLAMA_LOCAL}"
    fi
fi
echo "✅ 使用 Ollama 執行檔：${OLLAMA_CMD}"

# 3️⃣ 釋放被佔用的 port
pid=$(lsof -ti tcp:${APP_PORT})
if [ ! -z "$pid" ]; then
    echo "⚠️  釋放被佔用的 port ${APP_PORT} (PID: $pid)"
    kill -9 $pid
fi

# 4️⃣ 啟動 Ollama（如未執行）
if ! curl -s "${OLLAMA_HOST}/api/tags" >/dev/null; then
    echo "⚙️ 啟動 Ollama..."
    nohup "${OLLAMA_CMD}" serve >/dev/null 2>&1 &
    sleep 6
    if curl -s "${OLLAMA_HOST}/api/tags" >/dev/null; then
        echo "✅ Ollama 啟動成功"
    else
        echo "❌ Ollama 啟動失敗，請手動檢查"
    fi
else
    echo "✅ Ollama 已啟動"
fi

# 5️⃣ 檢查離線模型是否存在
check_model() {
    local model="$1"
    if curl -s "${OLLAMA_HOST}/api/tags" | grep -q "${model%%:*}"; then
        echo "✅ 模型 ${model} 已存在"
    else
        echo "⚙️ 下載模型 ${model}..."
        "${OLLAMA_CMD}" pull "${model}" || echo "⚠️ 模型 ${model} 下載失敗"
    fi
}

check_model "${MODEL_MAIN}"
check_model "${MODEL_MATH}"

# 6️⃣ 啟動 Streamlit
echo "🚀 啟動 Streamlit (port=${APP_PORT})..."
nohup streamlit run "${APP_FILE}" --server.port=${APP_PORT} >/tmp/streamlit.log 2>&1 &

echo "⏳ 等待應用程式啟動中..."
sleep 5

# 7️⃣ 開啟瀏覽器
if which wslview &>/dev/null; then
    wslview "${BROWSER_URL}" &
elif which xdg-open &>/dev/null; then
    xdg-open "${BROWSER_URL}" &
else
    echo "💡 請在 Windows 開啟以下連結：${BROWSER_URL}"
fi

echo "✅ 啟動完成 → ${BROWSER_URL}"
