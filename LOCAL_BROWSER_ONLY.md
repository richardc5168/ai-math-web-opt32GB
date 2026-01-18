# AIMATH（本機：只用瀏覽器）

你的目標是：**不需要點 .bat、不需要打指令**，使用者只要打開瀏覽器就能用。

## 一次性安裝（自動常駐）

用 Windows 工作排程在「登入時」自動啟動兩個服務：
- FastAPI：`http://127.0.0.1:8001/verify` / `http://127.0.0.1:8001/quadratic`
- Streamlit：`http://127.0.0.1:8501`

請用 PowerShell 執行一次：
- `scripts/windows/install_aimath_autostart.ps1`

執行後會：
- 建立兩個排程任務
- 立刻啟動服務
- 在桌面建立捷徑 `AIMATH Local Hub.url`

## 之後（每天使用）

之後你只要：
- 打開瀏覽器輸入 `http://127.0.0.1:8001/verify`

## 解除安裝

- `scripts/windows/uninstall_aimath_autostart.ps1`

## Troubleshooting

如果瀏覽器顯示 `ERR_CONNECTION_REFUSED`：
- 表示服務沒啟動或埠被占用
- 看 log：
  - `logs/uvicorn_8001.log`
  - `logs/streamlit_8501.log`
