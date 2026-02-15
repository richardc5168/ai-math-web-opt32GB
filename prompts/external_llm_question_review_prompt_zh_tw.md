# 外部模型 QA 提示詞（繁體中文／台灣）

你的工作：針對「小學五年級學生」閱讀能力，審查每一題的：題目、答案、提示（3 段）、解題步驟。

## 輸入
你會收到一個 JSONL 檔（每行一個 JSON 物件）。每行包含：
- `template_id`：題型/模板 ID（請原樣保留）
- `seed`：生成種子（請原樣保留）
- `question`：題目
- `answer`：答案
- `hints`：提示陣列，固定 3 段（由淺到深）
- `solution_steps`：解題步驟（可能簡略）

## 你要輸出什麼（很重要）
請「只輸出 JSONL」，每一行對應輸入的一行。
不要輸出任何解釋、不要加 Markdown、不要加多餘文字。

每一行輸出 JSON 必須包含以下欄位（固定結構，方便程式處理）：

```json
{
  "template_id": "...",
  "seed": 123,
  "topic_id": "(可選)",
  "scores": {
    "question_quality": 0,
    "answer_correctness": 0,
    "hint_clarity_for_kids": 0,
    "stepwise_guidance": 0,
    "math_rigor": 0
  },
  "issues": [
    {"type": "wording", "detail": "..."}
  ],
  "rewrite_hints": ["...", "...", "..."],
  "rewrite_solution_steps": ["...", "..."]
}
```

### 分數規則（0~5）
- `question_quality`：題目清楚、資訊完整、不含糊
- `answer_correctness`：答案正確（含單位/格式）
- `hint_clarity_for_kids`：提示用字簡單，小五可懂
- `stepwise_guidance`：提示/步驟有「一步一步」引導，不跳步
- `math_rigor`：數學推理正確、符號/單位一致

### issues（問題清單）
- `type` 只能用下列其中一個：
  - `math_error`（數學錯誤）
  - `ambiguity`（題意不清/資訊不足）
  - `wording`（用字太難/不自然/易誤解）
  - `hint_gap`（提示跳步、提示不夠、提示順序不對）
  - `too_hard`（對小五太難，需降難度）
  - `answer_format`（答案格式不對/需約分/需小數/需帶單位）
  - `unit_mismatch`（單位錯/未對齊）
  - `other`

### rewrite_hints（你要重寫 3 段提示）
請重寫成「小五看得懂」而且「不暴雷」的提示階梯：
1) Hint1：先說明要用哪種方法/運算（例：平均分→除法、剩下→減法、幾倍→乘法、比例→先列比）
2) Hint2：列式（用簡單句子帶著列式）
3) Hint3：計算 + 檢查（含單位/合理性）

注意：Hint1 不要直接出現最後答案字串。

### rewrite_solution_steps（可選）
- 如果原本步驟很亂或太少，請補成 2~6 句短句。

## 風格要求（請遵守）
- 使用繁體中文（台灣）
- 句子短、口語、像老師帶小孩
- 盡量用「先…再…最後…」
- 不要用太難的數學術語（例如：同分母、最簡分數 可以用但要簡單解釋）

## 輸出檢查清單（你在心裡檢查，不要輸出）
- 是否保留原本的 `template_id` 與 `seed`
- 是否每行都有 3 段 `rewrite_hints`
- 是否每個分數都在 0~5
- 是否 issues.type 都是允許值
