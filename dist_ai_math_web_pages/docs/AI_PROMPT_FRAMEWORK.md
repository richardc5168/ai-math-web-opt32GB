# AI Prompt Framework (Tagging / Misconception MCQ / Validation)

這份文件提供一套可重用的 Prompt 模板與 JSON schema，支援三件事：

1) 題目自動標籤化（core concept / prerequisites / difficulty / time）
2) 生成「帶迷思診斷」的選擇題（包含誘答項、診斷邏輯、三層提示）
3) 用 Sympy 自動驗證題目（方程式/解答一致性）

## 1) Automated Tagging

- Prompt builder: `ai/prompt_templates.py::build_tagging_prompt`
- Schema: `ai/schemas.py::TaggingResult`
- CLI: `scripts/ai_tag_math_bank.py`

Example:

```powershell
C:/Users/Richard/Documents/RAGWEB/.venv/Scripts/python.exe scripts/ai_tag_math_bank.py `
  --input math_bank/grade5_math.json `
  --output math_bank/grade5_math.tagged.json `
  --knowledge knowledge_points_example.json
```

Environment:
- `OPENAI_API_KEY`
- optional `OPENAI_MODEL` (default: gpt-4o-mini)

## 2) Misconception-aware MCQ Generation

- Prompt builder: `ai/prompt_templates.py::build_misconception_mcq_prompt`
- Schema: `ai/schemas.py::MisconceptionMCQ` (+ `GeneratedMCQSet`)
- CLI: `scripts/ai_generate_misconception_mcq.py`

Example:

```powershell
C:/Users/Richard/Documents/RAGWEB/.venv/Scripts/python.exe scripts/ai_generate_misconception_mcq.py `
  --concept "一元二次方程式-公式解" `
  --output data/mcqs.formula_solve.json
```

If `OPENAI_API_KEY` is missing, the script falls back to an offline stub so that CI/tests can still run.

## 2.1) Quadratic end-to-end pipeline (Generate → Validate → Tag)

目標：針對「一元二次（公式解）」自動生成題目，並用 Sympy 驗證正確性後再做 AI 標籤化，最後輸出 JSONL 方便匯入資料庫。

- 知識點清單：`knowledge_points_quadratic.json`
- Pipeline CLI：`scripts/pipeline_quadratic_generate_validate_tag.py`

Offline example (no API calls):

```powershell
C:/Users/Richard/Documents/RAGWEB/.venv/Scripts/python.exe scripts/pipeline_quadratic_generate_validate_tag.py --count 3 --offline
```

推薦風格（國中常見教學）：先因式分解，再用公式解驗算

```powershell
C:/Users/Richard/Documents/RAGWEB/.venv/Scripts/python.exe scripts/pipeline_quadratic_generate_validate_tag.py --count 20 --style factoring_then_formula
```

根型態與難度可控（品質優先：會在 Sympy 驗證階段硬性檢查根型態與係數範圍，不符合就丟棄重生）

```powershell
# 整數根（最貼近課本因式分解）
C:/Users/Richard/Documents/RAGWEB/.venv/Scripts/python.exe scripts/pipeline_quadratic_generate_validate_tag.py --count 30 --roots integer --difficulty 2

# 有理數根（至少一個非整數）
C:/Users/Richard/Documents/RAGWEB/.venv/Scripts/python.exe scripts/pipeline_quadratic_generate_validate_tag.py --count 30 --roots rational --difficulty 3

# 混合（至少一個整數 + 一個非整數有理數）
C:/Users/Richard/Documents/RAGWEB/.venv/Scripts/python.exe scripts/pipeline_quadratic_generate_validate_tag.py --count 30 --roots mixed --difficulty 3
```

Online example (requires `OPENAI_API_KEY`):

```powershell
$env:OPENAI_API_KEY="..."
C:/Users/Richard/Documents/RAGWEB/.venv/Scripts/python.exe scripts/pipeline_quadratic_generate_validate_tag.py --count 20
```

## 2.2) Textbook-style hints template（四層固定流程，向後相容）

為了讓每題的提示更像課本、且更一致好教學，本專案把 hints 收斂成固定的「四層模板」：

- `hints.level1`（整理）：整理成 `ax^2+bx+c=0`（移項、合併同類項）。
- `hints.level2`（因式分解）：提示因式分解成 `(px+q)(rx+s)=0`（必要時可先提出公因數）。
- `hints.level3`（零乘積）：提示用零乘積性質，把 `(px+q)(rx+s)=0` 拆成兩個一次方程。
- `hints.level4`（公式驗算）：提示用判別式與公式解 *驗算*（給出一般式），但不要寫出最終根。

向後相容：舊資料若只有 `level1..level3` 仍可通過驗證（允許把「零乘積」合併在 level2）。

Pipeline 會做硬性檢查：

- 必須包含上述步驟關鍵詞（整理/因式/零乘積/Δ/2a）。
- 禁止把答案用「解是… / 答案：… / 根為…」這種句型寫進 hints。

如果你想快速看被丟棄的原因：

```powershell
C:/Users/Richard/Documents/RAGWEB/.venv/Scripts/python.exe scripts/pipeline_quadratic_generate_validate_tag.py --count 1 --offline --max-attempts 5 --debug
```

## 3) Sympy Verification

- CLI: `scripts/verify_question_sympy.py`

Example:

```powershell
C:/Users/Richard/Documents/RAGWEB/.venv/Scripts/python.exe scripts/verify_question_sympy.py --expr "x**2 - 5*x + 6" --answer 2
```

Notes:
- `--expr` is interpreted as `expr == 0`.
- For batch validation, we can add a runner that reads a JSON bank and validates each item.
