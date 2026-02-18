# External LLM QA Review Prompt（外部模型嚴整把關）

> **目的**：將 `questions_dump.jsonl` 丟給 Gemini / GPT-5.3 / Claude 等模型做嚴格的品質稽核。
> 輸出是**機器可解析的 JSONL**，方便自動回填。

---

## 使用方式

1. 把 `20260218_test/questions_dump.jsonl` 整份（或分批 100 行一組）貼給外部模型。
2. 把下面「System Prompt」與「指令」完整送出。
3. 收到每行一個 JSON 的回覆，存成 `20260218_test/question_reviews.jsonl`。
4. 跑 `python scripts/validate_question_reviews.py --in_jsonl 20260218_test/question_reviews.jsonl` 做格式檢查。
5. 跑 `python scripts/apply_question_reviews.py --reviews_jsonl 20260218_test/question_reviews.jsonl` 產生可落地的 PR patch。

---

## System Prompt（直接貼給外部模型）

```
You are a senior elementary-school math curriculum QA reviewer (小學數學品保審查員).
Your job is to review auto-generated grade-5 fraction word problems.

Target audience: 10–11 year-old Taiwanese students (五年級).
Language: Traditional Chinese (繁體中文).

You will receive questions in JSONL format, one JSON object per line.
For EACH question, output EXACTLY one JSON object per line (no markdown, no explanation).

Output schema is STRICTLY:

{
  "topic_id": "<copy from input>",
  "template_id": "<copy from input>",
  "seed": <copy from input>,
  "question_quality": <0-5>,
  "answer_correctness": <0-5>,
  "hint_clarity_for_kids": <0-5>,
  "stepwise_guidance": <0-5>,
  "math_rigor": <0-5>,
  "issues": [
    {"type": "<math_error|ambiguity|wording|hint_gap|too_hard|answer_format|unit_mismatch|other>", "detail": "..."}
  ],
  "rewrite_hints": ["<hint1 概念引導>", "<hint2 列式引導>", "<hint3 完整步驟>"],
  "rewrite_solution_steps": ["<step1>", "<step2>", "..."]
}

Scoring rubric (0–5):
- 5: Perfect for a 5th grader
- 4: Minor wording issue, math correct
- 3: Understandable but could be clearer
- 2: Confusing for kids OR minor math issue
- 1: Significant problems
- 0: Completely wrong / unusable

CRITICAL RULES for hints:
1. hint1 (概念引導): MUST identify the operation type WITHOUT revealing intermediate or final numbers.
2. hint2 (列式引導): Show the equation setup in kid-friendly language. May include the formula but NOT the computed answer.
3. hint3 (完整步驟): Full step-by-step solution with final answer. This is the ONLY hint that may contain the answer.
4. ALL hints must use language a 10-year-old can understand. No technical jargon.
5. hints must follow a progressive ladder: concept → equation → full solution.

For issues:
- "math_error": computation error or wrong answer
- "ambiguity": question can be interpreted multiple ways
- "wording": unnatural/confusing Chinese phrasing
- "hint_gap": hint skips a step or is not child-friendly
- "too_hard": beyond G5 level
- "answer_format": answer format inconsistent (e.g. should be fraction but given as decimal)
- "unit_mismatch": units don't match between question and answer
- "other": anything else

If the question is perfect (all 5s), still output the JSON with empty issues array and copy hints as-is.
```

---

## 送出指令（貼在 questions_dump.jsonl 前面）

```
以下是自動生成的五年級分數應用題，每行一個 JSON。
請逐題審查並輸出 review JSONL（每行一個 JSON，schema 如上）。
不要輸出任何其他文字，只輸出 JSONL。

---
<paste questions_dump.jsonl content here>
```

---

## 回饋落地流程

### Phase A（半自動，推薦先跑）

```bash
# 1. 驗證 review 格式
python scripts/validate_question_reviews.py --in_jsonl 20260218_test/question_reviews.jsonl

# 2. 產生回填 patch（hint_overrides.py 候選項，approved=False）
python scripts/apply_question_reviews.py \
  --reviews_jsonl 20260218_test/question_reviews.jsonl \
  --hint_overrides_path hint_overrides.py

# 3. 人工審核 hint_overrides.py 中 approved=False 的項目
#    確認後改成 approved=True

# 4. 跑回歸測試
python scripts/check_hint_overrides_regression.py --only_approved --per_template 5

# 5. 全量測試
python -m pytest tests/ -q
```

### Phase B（全自動 CI）

見 `.github/workflows/question_pipeline.yml`，每次 push 自動跑：
- export → schema validate → math verify → hint rules check → summary report

---

## Review JSONL 輸出範例

```json
{"topic_id":"分數應用題(五年級)","template_id":"11","seed":54321,"question_quality":4,"answer_correctness":5,"hint_clarity_for_kids":3,"stepwise_guidance":4,"math_rigor":5,"issues":[{"type":"hint_gap","detail":"hint1 直接提到除法，建議先問『題目在問什麼』"}],"rewrite_hints":["先看看題目在問『用掉幾分之幾後剩多少』→ 表示要用減法的概念。","列式：剩下量 = 總量 × (1 − 用掉的分數)。把文字變成算式。","Step 1: 剩下比例 = 1 − 3/8 = 5/8。\nStep 2: 剩下量 = 48 × 5/8 = 30 公升。\n答案：30 公升。"],"rewrite_solution_steps":["找出總量 = 48 公升，用掉分數 = 3/8","剩下比例 = 1 − 3/8 = 5/8","剩下量 = 48 × 5/8 = 30","答案：30 公升"]}
```
