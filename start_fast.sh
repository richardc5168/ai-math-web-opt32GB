#!/usr/bin/env bash
# 一鍵啟動 Neo RAG + 數學教師（優先使用本地 Ollama）

set -e

APP_PORT=8508
VENV_DIR=".venv"
APP_FILE="app.py"
BROWSER_URL="http://127.0.0.1:${APP_PORT}"
OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"

# 1) 切到腳本所在目錄
cd "$(dirname "$0")"

echo "=== Neo RAG 啟動腳本 ==="

# 2) 啟用虛擬環境
if [ ! -d "${VENV_DIR}" ]; then
    echo "ERROR: 找不到虛擬環境目錄 ${VENV_DIR}"
    echo "請先執行：python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

source "${VENV_DIR}/bin/activate"
echo "OK: 已啟用虛擬環境 ${VENV_DIR}"

# 3) 檢查並釋放被佔用的 port
echo "檢查 port ${APP_PORT} 使用狀態..."
PIDS_BY_PORT=$(lsof -ti tcp:${APP_PORT} 2>/dev/null || true)
if [ -n "${PIDS_BY_PORT}" ]; then
    echo "發現使用 port ${APP_PORT} 的行程：${PIDS_BY_PORT}，正在 kill..."
    kill -9 ${PIDS_BY_PORT} || true
fi

# 再補殺殘留的 streamlit run app.py 行程（如果有）
PIDS_STREAMLIT=$(ps aux | grep "streamlit run ${APP_FILE}" | grep -v grep | awk '{print $2}')
if [ -n "${PIDS_STREAMLIT}" ]; then
    echo "發現殘留 streamlit 行程：${PIDS_STREAMLIT}，正在 kill..."
    kill -9 ${PIDS_STREAMLIT} || true
fi

# 4) 檢查 Ollama 狀態（只是提示，不強制）
if curl -s "${OLLAMA_HOST}/api/tags" >/dev/null 2>&1; then
    echo "OK: Ollama 已在運行 (${OLLAMA_HOST})"
else
    echo "WARN: 無法連到 Ollama (${OLLAMA_HOST})，若使用離線模型請確認已執行：ollama serve"
fi

# 5) 啟動 Streamlit
echo "啟動 Streamlit（port=${APP_PORT}）..."
nohup streamlit run "${APP_FILE}" --server.address 0.0.0.0 --server.port ${APP_PORT} > streamlit.log 2>&1 &

# 6) 等待服務起來
echo "等待應用程式啟動..."
for i in $(seq 1 20); do
    if curl -s "http://127.0.0.1:${APP_PORT}/_stcore/health" >/dev/null 2>&1; then
        echo "OK: Streamlit 已啟動"
        break
    fi
    sleep 1
done

echo "啟動完成 → ${BROWSER_URL}"

# 7) 嘗試在 Windows 瀏覽器開啟
if command -v wslview >/dev/null 2>&1; then
    wslview "${BROWSER_URL}" >/dev/null 2>&1 &
else
    echo "請在 Windows 瀏覽器手動開啟：${BROWSER_URL}"
    echo "（可直接貼到 Edge 或 Chrome）"
fi
