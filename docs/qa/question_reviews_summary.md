# QA 匯出自檢摘要（ALL_SUMMARY_MAX）

- 產生時間：2026-02-16T01:27:00
- 匯出檔案：
  - `./ALL_SUMMARY_MAX.jsonl`
  - `./ALL_SUMMARY_MAX.md`
- 題型數：15
- 每題型抽樣：500
- 題目總數：7500
- base_seed：12345
- answer_ok_fail：1000
- hint_ladder_ok_fail：273

## 下一步（外部模型回饋）
- 這份摘要是『程式自檢』結果（不是外部模型 review）。
- 若要顯示外部模型回饋摘要：請把 review JSONL 放到 `artifacts/question_reviews.jsonl`，再跑：
  - `./.venv/Scripts/python.exe scripts/summarize_question_reviews.py --in_jsonl artifacts/question_reviews.jsonl --out_md artifacts/question_reviews_summary.md`

## Release Note
- 2026-02-21：`commercial-pack1-fraction-sprint` 上線四層圖解提示系統（commit `3cdee61`），包含資料模型路由、SVG 圖解渲染、提示 UI 逐層遞進與可複用 Prompt Spec；遠端 `cross_validate_remote` 結果為 17 passed / 0 failed。
