# Quality Gate — AI Math Web 品質閘門規範

## 業務目標

在第三學習階段（國小 5–6 年級）範圍內，持續產出可用於練習/測驗的數學題目與可教學的解題步驟，
且在不降低正確性與合規的前提下，最大化自動化驗證比例與 CI/CD 自動部署頻率。

## 課綱能力邊界

| 學習表現 | 分年內容（範例） |
|----------|-----------------|
| n-III-*  | N-5-10 百分率、N-5-11 概數、N-6-3 分數除法、N-6-7 速度 |
| s-III-*  | S-6-2 地圖比例尺 |
| r-III-*  | 比例關係、等式推導 |
| d-III-*  | D-5-1 折線圖 |

---

## KPI / SLO 指標

| 指標 | 定義 | MVP 門檻 | 穩定目標 | 自動蒐集方式 |
|------|------|---------|---------|-------------|
| 題目正確率 | 答案與主判解一致 | 95% | 99% | CI pipeline.verify deterministic gate |
| 步驟完整性 | 步驟數 ≥ 最小門檻、每步可驗證 | 80% | 95% | step lint + step-by-step check |
| 步驟一致性 | 相鄰步驟等值/推導通過 | 85% | 97% | 轉換規則檢查（含數值流檢查） |
| 驗證自動化率 | 免人工覆核即可進 main 比例 | 50% | 85% | score ≥ 門檻自動合格 |
| 回歸測試覆蓋率 | topic_code 覆蓋 + 測試案例覆蓋 | 60% | 90% | CI topic coverage report |
| CI/CD 部署頻率 | main 成功部署次/週 | ≥1/週 | ≥1/日 | GitHub Actions run 統計 |
| 合規命中率 | 來源授權可追溯、未觸犯重製 | **100%（硬門檻）** | 100% | source metadata + allowlist + 教科書重製偵測 |
| 每次迭代人工時 | 人工審題/修規則/合規確認總工時 | 8h/週 | 2h/週 | issue/PR 標籤統計 |

---

## 四道驗證閘門 (Four Gates)

任何題目進入 main 前須通過全部四道 gate，缺一不可：

### Gate 1: Schema 格式
- 輸出必須符合 `schemas/problem.schema.json`
- 必填欄位：id, grade, stage, topic_codes, question, solution, source
- topic_codes 須包含至少一個 n-III/s-III/r-III/d-III 或 N-5-/N-6-/S-6-/D-5- 編碼
- 新增欄位：`expected_steps_min`, `grading_exempt`, `similarity_score`, `generation_metadata`, `human_review`

### Gate 2: Correctness 正確性
- 答案必須通過 deterministic 計算或等值規則
- N-5-10 百分率答案 ≤ 100%（僅 answer_type=percent 時檢查）
- 答案非負（距離/價格/百分率）
- confidence < 0.7 → 進人工佇列

### Gate 3: Steps 步驟
- 步驟數 ≥ topic-specific 最小門檻
- N-5-11：禁用「誤差」「近似值」
- N-6-7：必須包含距離=速度×時間（或等價公式）
- N-6-3：不出現「餘數」（除非 grading_exempt=true）
- S-6-2：必須涉及比例尺相關概念（比例尺/分母/放大/縮小）
- D-5-1：題目需包含 ≥5 個資料點
- 每步單位一致、無非法跳步

### Gate 4: License + Anti-cheat 合規
- license_type 必須在 allowlist（CC BY/CC0/public-domain 等）
- all-rights-reserved / unknown / proprietary → 阻斷
- Prompt injection 偵測：掃描題目與步驟中的注入語句
- **教科書重製偵測**：掃描翰林/南一/康軒/課本/習作/教科書/出版社等模式
- 文本相似度未命中黑名單/重複題

---

## 評分卡 (Scorecard: 0-100)

Gate 通過後的軟排序，用於優先選題（由 `pipeline/scorecard.py` 計算）：

| 權重 | 維度 | 說明 | 計算方式 |
|------|------|------|---------|
| 40 | 單題正確性 | 答案完全一致/允許誤差 | 值存在且合理=1.0；非數值=0.8；負值/超限=0.0 |
| 25 | 步驟一致性 | 相鄰步驟推導檢查通過率 | 必要公式檢查 + 數值流連貫性 |
| 15 | 步驟完整性 | 步驟數與必要中介量齊全 | 步驟數/最小門檻比例 |
| 10 | 答案合理性 | 數值範圍、單位、情境合理 | 非負 + 單位存在 + 範圍合理 |
| 10 | 反作弊/去重 | 與既有題庫相似度低 | 教科書重製偵測 + 相似度檢查 |

---

## 四層架構

```
來源層 (Source)     → pipeline/source_governance.py
  ↓
生成層 (Generate)   → pipeline/generate.py (Self-Refine + 多角色 Agent)
  ↓
驗證層 (Verify)     → pipeline/verify.py (4-gate + scorecard)
  ↓
發佈層 (Publish)    → CI/CD auto-merge / auto-PR
```

---

## 來源治理 (`pipeline/source_governance.py`)

### 優先來源（按優先順序）
1. **行政院公報資訊網**（gazette.nat.gov.tw）— 課綱原文，public-domain
2. **教育大市集**（market.cloud.edu.tw）— CC 授權、TW LOM、API
3. **國家教育研究院**（www.naer.edu.tw）— 結構性資訊，需授權評估
4. **教育部**（www.edu.tw）— 素養導向紙筆測驗範例
5. **政府出版品資訊網**（gpi.culture.tw）— 教師手冊結構性資訊

### 授權判定引擎
- `decide_license(license_type, url)` → allow / deny / needs_review
- Allowlist: CC BY/BY-SA/BY-NC/BY-NC-SA (3.0/4.0), CC0, public-domain
- Deny: all-rights-reserved, unknown, proprietary
- 其他 → needs_review

### 合規規則
- Allowlist-only：僅接受 CC/OER/公共領域可確認來源
- 強制保存 license_type + 證據 URL + 時間戳 + evidence_snapshot hash
- 「保留所有著作權利」或無法判定 → 不得進入自動發布管線
- 內容相似度檢測（SequenceMatcher, threshold=0.85），避免直接重製教科書
- 教科書出版商偵測（翰林/南一/康軒/課本/習作/教科書/出版社）

### 標註策略（薄人工＋弱監督）
- **第一層**：規格化後設資料（必填）— grade, stage, topic_code, answer_type, source
- **第二層**：弱監督/主動式學習 — 規則標註函數先大量標註，低信心進人工佇列

---

## 反作弊與 Prompt Injection 防護

- 檢索內容加 delimiter，不可被模型當指令執行
- 掃描注入模式：「忽略以上指示」「ignore previous instructions」等
- Gate 4 自動偵測並阻斷含注入語句的題目
- 教科書重製偵測作為 Gate 4 的一部分
- Signed-Prompt 機制（可擴展）區分可信/不可信來源

---

## 多角色 Agent 架構 (`pipeline/generate.py`)

| 角色 | 職責 | System Prompt |
|------|------|--------------|
| Retriever | 檢索 topic code + 來源教材 | 根據 topic_code 找出課綱能力敘述 |
| Generator | 產出題目 + 步驟 JSON | 國小五六年級出題代理（含 5 條規則） |
| Verifier | 四道閘門檢查 | pipeline.verify 硬門檻 |
| Refiner | 根據失敗回饋修正 | 修正不改變題目核心邏輯 |

### Self-Refine 迴路
1. Generator 產出 JSON
2. Verifier 執行 4-gate 驗證
3. 若失敗 → Refiner 收到結構化失敗原因，重新產出
4. 最多 3 次迭代
5. 仍失敗 → confidence < 0.7，進人工佇列

### 六種情境 Prompt
| 情境 | Topic Code | 驗證條件 |
|------|-----------|---------|
| 百分率與折扣 | N-5-10 | 答案 ≤ 100%，含 n-III-9 |
| 小數取概數 | N-5-11 | 禁「誤差」「近似值」 |
| 速度與單位換算 | N-6-7 | 距離=速度×時間，單位一致 |
| 分數除法 | N-6-3 | 無餘數（或 grading_exempt） |
| 地圖比例尺 | S-6-2 | 含比例尺概念 + 常見錯誤提醒 |
| 折線圖 | D-5-1 | ≥ 5 資料點，趨勢推論 |

---

## 測試矩陣

| 層級 | 檔案 | 覆蓋 | 判定標準 |
|------|------|------|---------|
| 單元 | `test_pipeline_schema.py` | Schema gate 13 cases | 欄位齊全、型態正確 |
| 單元 | `test_pipeline_steps.py` | Steps gate 11 cases | 單位一致、無跳步、公式存在 |
| 單元 | `test_pipeline_license.py` | License gate + injection + textbook | 授權/注入/重製偵測 |
| 單元 | `test_pipeline_correctness.py` | Correctness gate 9 cases | 值域、負值、百分率 |
| 單元 | `test_pipeline_scorecard.py` | 5 維度評分 20+ cases | 各維度分數範圍 |
| 單元 | `test_pipeline_source_governance.py` | 來源治理 25+ cases | 授權/相似度/教科書偵測 |
| 單元 | `test_pipeline_generate.py` | 生成模組 20+ cases | Agent 角色/Prompt/Self-Refine |
| 單元 | `test_pipeline_solver.py` | 確定性解題器 55+ cases | 分數/小數/百分率/速度/比例尺/資料 |
| 單元 | `test_pipeline_oer_fetcher.py` | OER 內容抓取 24 cases | 課綱結構/種子生成/正規化/覆蓋率 |
| 單元 | `test_pipeline_agent_loop.py` | 自主循環控制器 23 cases | 錯誤記憶/指令解析/意圖辨識/閒置偵測 |
| 單元 | `test_pipeline_auto_pipeline.py` | 端對端管線 18 cases | 抓取/解題/驗證/路由/Self-Refine |
| 整合 | `test_pipeline_verify.py` | smoke data → 4 gates | 全 gate 通過、score ≥ 90 |
| 端對端 | `test_pipeline_e2e.py` | CLI → report artifact | topic 覆蓋率 ≥ 5 |
| 安全 | (in license test) | 含注入 + 教科書重製 | gate fail |
| 合規 | (in license test) | 授權不明/deny | license gate fail |

---

## 測試目錄結構

```
tests/
  unit/
    test_pipeline_schema.py            # Schema gate 單元測試
    test_pipeline_steps.py             # Steps gate 單元測試
    test_pipeline_license.py           # License gate + injection + textbook 測試
    test_pipeline_correctness.py       # Correctness gate 單元測試
    test_pipeline_scorecard.py         # 五維度評分卡單元測試
    test_pipeline_source_governance.py # 來源治理單元測試
    test_pipeline_generate.py          # 生成模組單元測試
    test_pipeline_solver.py            # 確定性數學解題器測試
    test_pipeline_oer_fetcher.py       # OER 抓取/正規化/覆蓋率測試
    test_pipeline_agent_loop.py        # 自主循環控制器測試
    test_pipeline_auto_pipeline.py     # 端對端管線測試
  integration/
    test_pipeline_verify.py            # 整合測試（smoke data → 4 gates）
  e2e/
    test_pipeline_e2e.py               # 端對端 CLI 執行 + report 驗證
```

---

## Pipeline 模組結構

```
pipeline/
  __init__.py
  verify.py              # 四道閘門 + scorecard 整合
  scorecard.py            # 五維度評分引擎
  source_governance.py    # 來源治理 + 授權判定 + 教科書偵測
  generate.py             # 多角色 Agent + Self-Refine + 六情境 prompt
  deterministic_solver.py # 確定性數學解題器（主判/雙軌主審）
  oer_fetcher.py          # OER 內容抓取 + 課綱對齊 + 種子生成
  agent_loop.py           # 自主循環控制器 + 錯誤記憶 + 指令執行
  auto_pipeline.py        # 端對端管線：抓取→解題→驗證→路由→發布
```

---

## 自主循環架構 (`pipeline/agent_loop.py`)

### 五大功能
1. **錯誤記憶**：讀取 `golden/error_memory.jsonl`，避免重複已知錯誤
2. **指令執行**：語法容錯解析 `ops/hourly_commands.json`，支援中文關鍵字模糊匹配
3. **閒置偵測**：檢查最近 commit/artifact/hourly-state 判斷是否閒置
4. **品質閘門整合**：commit 前必須通過 validate_all_elementary_banks
5. **README 合規**：每次循環讀取 README 確認規則

### 雙軌裁判（Dual-Track Adjudication）
- **主判**：`deterministic_solver.py` — 確定性精確計算（Fraction 避免浮點誤差）
- **副判**：LLM-as-a-judge — 隔離、沙盒化、可重播，輸出視為不可信輸入
- 覆蓋六大題型：分數、小數、百分率/折扣、速度距離時間、比例尺、資料分析

### 端對端管線流程
```
OER 抓取 (oer_fetcher) → 解題 (deterministic_solver) → 驗證 (verify 4-gate)
  → 路由：
    score ≥ 90 → auto_publish (data/generated/)
    70 ≤ score < 90 → human_review (data/human_queue/)
    score < 70 → rejected
```

### 人工角色轉變
- 從：逐題檢查（每題人工確認）
- 到：抽樣審核 + 規則/測試演進（抽 10%、優化驗證規則）

---

## CI/CD 流程

```
PR → paths filter (pipeline/data/tests/schemas)
  → verify:all (existing)
  → pipeline quality gate (smoke data)
  → pipeline unit/integration/e2e tests (含 scorecard/governance/generate)
  → scorecard gate → auto-merge

push to main
  → full pipeline verify
  → upload pipeline report artifact
  → (optional) auto-PR for batch generation
  → self-heal + auto-merge for fix PRs
```

---

## 執行方式

```bash
# 本機驗證
python -m pipeline.verify --dataset data/smoke/problems.sample.jsonl --report artifacts/report.json

# 執行所有 pipeline 測試
python -m pytest tests/unit/ tests/integration/ tests/e2e/ -q

# 生成模組（stub 模式，需配置 API key 後啟用）
python -m pipeline.generate --out data/problems.jsonl --topics N-5-10,N-6-7

# 端對端自動管線（離線種子模式）
python -m pipeline.auto_pipeline --topic N-5-10 --count 5 --dry-run
python -m pipeline.auto_pipeline --all-topics --count 3
python -m pipeline.auto_pipeline --coverage

# 自主循環（單次/持續/閒置觸發）
python -m pipeline.agent_loop --once
python -m pipeline.agent_loop --watch --interval-min 30
python -m pipeline.agent_loop --idle-timeout 60

# 既有驗證（必須通過）
python tools/validate_all_elementary_banks.py
```

---

## 變更記錄與回滾

- 題庫與驗證報告一起版本化（每次更新保存 report artifact）
- 回滾：revert PR 或 `git revert <commit>`
- 來源證據（URL + license_type + evidence_snapshot hash）隨版本保存
- 發版前建議打 tag：`rollback/pipeline-before-<change>-YYYYMMDD`
