# Golden Set (Grade 5 Life Applications)

- 檔案：`grade5_pack_v1.jsonl`
- 目的：鎖定 30 題核心題，避免提示與解題流程隨迭代漂移。
- 每題包含：題目、正解、常見錯答、4 階提示、家長報告關聯標籤。

## 使用方式

1. `node tools/validate_questions.cjs`
2. `node tools/judge_hint_quality.cjs golden/grade5_pack_v1.jsonl --out artifacts/hint_judge.json`
3. `node tools/run_golden_correctness.cjs`

## 規格保證

- `schemas/question.schema.json` 驗證每行 JSON。
- `tools/judge_hint_quality.cjs` 以規則式 Rubric 產生 0~10 分。
