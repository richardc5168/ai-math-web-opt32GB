# Question Pipeline Report
- Generated: 2026-02-18T15:11:55
- Output dir: `20260218_test`
- per_template: 50
- base_seed: 12345

## 1. Export Summary
- Templates: 15
- Total items: 750
- answer_ok_fail: 100
- hint_ladder_ok_fail: 24

## 2. Schema Validation
- Status: ✅ PASS
- 750/750 passed

## 3. Math Correctness (SymPy)
- Status: ⚠ WARN
- 207/750 passed
- Failures (first 10):
  - template=1, seed=41221394: ['step result 18 != answer 17']
  - template=1, seed=577440704: ['step result 1 != answer 2']
  - template=1, seed=108283298: ['step result 20 != answer 11']
  - template=1, seed=942107839: ['step result 25 != answer 35']
  - template=1, seed=811043241: ['negative answer: -11', 'step result -10 != answer -11']
  - template=1, seed=317038957: ['step result 18 != answer 20']
  - template=1, seed=908848086: ['negative answer: -1', 'step result 2 != answer -1']
  - template=1, seed=243707564: ['step result 120 != answer 119']
  - template=1, seed=801821977: ['step result 46 != answer 52']
  - template=1, seed=72504298: ['step result -3 != answer 2']

## 4. Hint Ladder Rules
- Status: ⚠ WARN
- 559/750 passed
- Failures (first 10):
  - template=10, seed=159372559: ['hint1 longer than hint3 (should be progressive)']
  - template=10, seed=12672997: ['hint1 longer than hint3 (should be progressive)']
  - template=10, seed=319587859: ['hint1 longer than hint3 (should be progressive)']
  - template=10, seed=473709958: ['hint1 longer than hint3 (should be progressive)']
  - template=10, seed=18320308: ['hint1 longer than hint3 (should be progressive)']
  - template=10, seed=551358022: ['hint1 longer than hint3 (should be progressive)']
  - template=10, seed=995927089: ['hint1 longer than hint3 (should be progressive)']
  - template=10, seed=915493359: ['hint1 longer than hint3 (should be progressive)']
  - template=10, seed=812540331: ['hint1 longer than hint3 (should be progressive)']
  - template=10, seed=769064144: ['hint1 longer than hint3 (should be progressive)']

## 5. Next Steps

### 外部模型 QA（Gemini / GPT-5.3）
1. 把 `20260218_test/questions_dump.jsonl` 丟給外部模型
2. 使用 `20260218_test/llm_review_prompt.md` 中的 prompt
3. 收到 review JSONL 存成 `20260218_test/question_reviews.jsonl`
4. 跑驗證：`python scripts/validate_question_reviews.py --in_jsonl <reviews>`
5. 跑回填：`python scripts/apply_question_reviews.py --reviews_jsonl <reviews>`

### 回歸測試
```bash
python -m pytest tests/ -q
python scripts/check_hint_overrides_regression.py --only_approved --per_template 5
```

## Overall: ⚠ ISSUES FOUND — review above
