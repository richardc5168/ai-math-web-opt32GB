# Question Pipeline Report
- Generated: 2026-02-18T15:46:14
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
- 495/750 passed
- Failures (first 10):
  - template=2, seed=242392322: ['cannot parse answer: 20 4 5']
  - template=2, seed=296591804: ['cannot parse answer: 10 1 5']
  - template=2, seed=978871023: ['cannot parse answer: 24 3 2']
  - template=2, seed=516700906: ['cannot parse answer: 24 21 8']
  - template=2, seed=430331144: ['cannot parse answer: 36 32 9']
  - template=2, seed=943090652: ['cannot parse answer: 8 2 4']
  - template=2, seed=606405295: ['cannot parse answer: 20 10 15']
  - template=2, seed=575792062: ['cannot parse answer: 24 16 12']
  - template=2, seed=303290946: ['cannot parse answer: 12 6 4']
  - template=2, seed=336446099: ['cannot parse answer: 12 1 3']

## 4. Hint Ladder Rules
- Status: ⚠ WARN
- 736/750 passed
- Soft warnings: 191
- Failures (first 10):
  - template=g5s_web_concepts_v1, seed=564624146: ['hint3 too short (6 chars)']
  - template=g5s_web_concepts_v1, seed=60668392: ['hint3 too short (7 chars)']
  - template=g5s_web_concepts_v1, seed=587059068: ['hint3 too short (6 chars)']
  - template=g5s_web_concepts_v1, seed=419427574: ['hint3 too short (6 chars)']
  - template=g5s_web_concepts_v1, seed=813874789: ['hint3 too short (7 chars)']
  - template=g5s_web_concepts_v1, seed=100793654: ['hint3 too short (7 chars)']
  - template=g5s_web_concepts_v1, seed=554352200: ['hint3 too short (7 chars)']
  - template=g5s_web_concepts_v1, seed=828094769: ['hint3 too short (7 chars)']
  - template=g5s_web_concepts_v1, seed=562868682: ['hint3 too short (7 chars)']
  - template=g5s_web_concepts_v1, seed=940641036: ['hint3 too short (7 chars)']

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
