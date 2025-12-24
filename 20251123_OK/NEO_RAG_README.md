
# Neo 專用 RAG 建置說明

## 1. 準備資料
把你的 Neo 公司文件（UG、NW/NW-SW、Adapter、AXI/DDR 規格、客戶簡報等）複製到專案根目錄下的 `neo_docs/`。支援 PDF/TXT/MD。

## 2. 將文件寫入 knowledge.db
```bash
pip install pypdf
python ingest_neo_docs.py
```
執行完成後，將會在 `knowledge.db` 內建立可檢索的片段。

## 3. 啟動前端（參考你的主專案 app.py）
```bash
streamlit run app.py
```
前端的「知識庫問答（RAG）」頁籤會只用 `knowledge.db` 的片段來回答。

## 4. 推薦做法（Neo 文件）
- 每份 PDF 名稱加上版本號，如 `Neo210_UG_v1.3.pdf`，方便追蹤。
- 重要章節可先另存 TXT 直接放入 `neo_docs/`（如「AXI_Config_Guide.txt」）。
- 對於極長章節，維持分塊長度 1200 字，重疊 160 字（在 `ingest_neo_docs.py` 可調）。

## 5. 問答提示（Prompt）
使用 `neo_rag_prompts.py` 中的 `QA_PROMPT`/`SUMM_PROMPT`/`COMPARE_PROMPT`，把檢索到的片段代入 `{context}` 再送給模型。

## 6. 安全
- 全流程可離線運作；建議放在內網隔離的工作站上。
- knowledge.db 內只存文字片段與來源檔名，不上傳雲端。
