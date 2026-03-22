# DESIGN_AUDIT.md — 學習效果導向系統升級盤點

> Generated: 2026-03-22  
> Scope: ai-math-web 專案全面盤點，為「教育效果導向」升級做準備  
> Principle: 先盤點、再設計、最後實作；不破壞既有穩定功能

---

## 1. 現有能力

### 1.1 題庫系統
| 能力 | 狀態 | 核心檔案 |
|------|------|----------|
| JSON 題庫 (160+ 題) | ✅ 穩定 | `data/web_g5s_pack.json`, `data/fraction_word_g5_teaching_playbook.json` |
| 題目 schema 驗證 | ✅ 穩定 | `schemas/problem.schema.json`, `schemas/question.schema.json` |
| 題目欄位：id, difficulty, topic_tags, concept_points, hints (L1-L3), steps, answer, validator | ✅ 穩定 | 各 JSON pack |
| 配方數學產生器 | ✅ 穩定 | `question_types/g5s_web_concepts/` |
| 題目品質門檻 (confidence, similarity_score, license) | ✅ 穩定 | `quality_gate.md`, `schemas/problem.schema.json` |

### 1.2 提示系統
| 能力 | 狀態 | 核心檔案 |
|------|------|----------|
| 4 層提示 (L1 策略 → L2 列式 → L3 計算 → L4 完整解) | ✅ 穩定 | `hint_overrides.py`, `docs/shared/hint_engine.js` |
| 提示人工審核閘門 | ✅ 穩定 | `hint_overrides.py` |
| 分數專用診斷 DAG (5 skills) | ✅ 穩定 | `fraction_logic.py` |
| 一次方程 hint ladder (5 levels) | ✅ 穩定 | `linear_engine.py` |
| 二次方程 hint ladder (3 methods) | ✅ 穩定 | `quadratic_engine.py` |

### 1.3 自適應狀態機
| 能力 | 狀態 | 核心檔案 |
|------|------|----------|
| ConceptState (BASIC → LITERACY) | ✅ 穩定 | `adaptive_mastery.py` |
| 錯誤分類 (CAL/CON/READ/CARE/TIME) | ✅ 基本 | `adaptive_mastery.py: classify_error_code()` |
| Calm mode (≥3 連錯) | ✅ 穩定 | `adaptive_mastery.py` |
| Hint mode (≥6 題 + mastery<0.6) | ✅ 穩定 | `adaptive_mastery.py` |
| Micro-step mode | ✅ 穩定 | `adaptive_mastery.py` |
| Teacher flag (micro≥2 or 7天未完) | ✅ 穩定 | `adaptive_mastery.py` |
| 前端同步 (calm/micro/hint UI) | ✅ 穩定 | `docs/shared/adaptive_mastery_frontend.js` |

### 1.4 事件紀錄
| 能力 | 狀態 | 核心檔案 |
|------|------|----------|
| 前端 analytics (localStorage, 15+ event types) | ✅ 穩定 | `docs/shared/analytics.js` |
| Attempt telemetry (per-question detail) | ✅ 穩定 | `docs/shared/attempt_telemetry.js` |
| Coach event log | ✅ 穩定 | `docs/shared/coach_event_log.js` |
| 後端 SQLite 寫入 (la_attempt_events) | ✅ 穩定 | `learning/service.py`, `db/migrations/001_learning_analytics.sql` |
| Skill tag 多對多 | ✅ 穩定 | `la_attempt_skill_tags` table |

### 1.5 報表系統
| 能力 | 狀態 | 核心檔案 |
|------|------|----------|
| 家長週報 (概念雷達、弱點、補救建議) | ✅ 穩定 | `learning/parent_report.py`, `docs/parent-report/` |
| Coach report (ABCD 象限分類) | ✅ 穩定 | `coach_report.py` |
| 補救計畫產生 (top-3 弱技能) | ✅ 穩定 | `learning/remediation.py` |
| 學生分析 (skill trend, hint dependency) | ✅ 穩定 | `learning/analytics.py` |

### 1.6 測試覆蓋
| 能力 | 狀態 | 核心檔案 |
|------|------|----------|
| Adaptive mastery 狀態轉換 | ✅ 穩定 | `tests/test_adaptive_mastery.py` |
| 報表聚合與 KPI | ✅ 穩定 | `tests/test_report_aggregate_mvp.py` |
| 學習分析 | ✅ 穩定 | `tests/test_learning_analytics.py` |
| 補救計畫 golden test | ✅ 穩定 | `tests/test_learning_remediation_golden.py` |
| 題庫 schema 驗證 | ✅ 穩定 | `tests/test_question_bank_validation.py` |
| 分數邏輯與 SymPy | ✅ 穩定 | `tests/test_fraction_logic.py`, `tests/test_engine_check_sympy.py` |

---

## 2. 缺口分析

### 2.1 題目 metadata 缺口
| 需要的欄位 | 現況 | 缺口等級 |
|-----------|------|---------|
| `item_id` | ✅ 有 (`id` field) | — |
| `concept_ids` (標準化概念 ID) | ⚠️ 有 `concept_points` (自由文本) 和 `topic_tags`，但不是標準 concept_id | **P0** |
| `difficulty` | ✅ 有 (easy/normal/hard) | — |
| `format` | ❌ 缺 (integer/fraction/word_problem/... 的格式欄位) | **P1** |
| `prerequisite_concepts` | ❌ 缺 (題目層級的前置概念) | **P0** |
| `variant_group` | ❌ 缺 (同概念不同表徵的分組) | **P1** |
| `supports_hints` | ⚠️ 隱含有 (有 hints 就支援)，但無顯式 flag | **P2** |
| `remediation_target` | ❌ 缺 (這題作為補救題的目標概念) | **P1** |

### 2.2 作答事件紀錄缺口
| 需要的欄位 | 現況 | 缺口等級 |
|-----------|------|---------|
| `student_id` | ✅ 有 | — |
| `item_id` | ✅ 有 (`question_id`) | — |
| `session_id` | ✅ 有 | — |
| `started_at` | ❌ 缺 (只有 `ts` 一個時間點) | **P0** |
| `submitted_at` | ⚠️ `ts` 可視為 submitted_at | **P2** |
| `attempts` (同題重答次數) | ❌ 缺 | **P0** |
| `first_answer` | ❌ 缺 (只存 `answer_raw` 最終答案) | **P0** |
| `final_answer` | ✅ 有 (`answer_raw`) | — |
| `changed_answer` | ❌ 缺 | **P0** |
| `used_hints` | ✅ 有 (`hints_viewed_count`, `hint_steps_viewed_json`) | — |
| `response_time_sec` | ⚠️ 有 `duration_ms` (需轉換) | **P2** |
| `is_correct` | ✅ 有 | — |
| `error_type` | ⚠️ 有 `mistake_code` (free text) | **P1** |
| `selection_reason` | ❌ 缺 (為什麼選這題) | **P0** |
| `concept_ids` | ⚠️ 有 `skill_tags` (非標準 concept_id) | **P1** |
| `remediation_triggered` | ❌ 缺 | **P1** |
| `prerequisite_fallback_triggered` | ❌ 缺 | **P1** |

### 2.3 學生概念狀態缺口
| 需要的欄位 | 現況 | 缺口等級 |
|-----------|------|---------|
| `mastery_score` | ⚠️ 有 `ConceptState.mastery()` (answered/correct 比) 但無獨立持久化 | **P0** |
| `state` (5 level) | ⚠️ 只有 BASIC/LITERACY (2 level)，需擴充到 unbuilt/developing/approaching/mastered/review | **P0** |
| `recent_accuracy` | ❌ 缺 (需最近 N 題正確率) | **P0** |
| `hint_dependency` | ⚠️ 分析層有計算，但非 per-concept 持久化 | **P1** |
| `avg_response_time` | ❌ 缺 | **P1** |
| `transfer_success` | ❌ 缺 | **P2** |
| `delayed_review_status` | ❌ 缺 | **P1** |
| `last_seen_at` | ⚠️ 有 `last_activity` | — |
| `last_mastered_at` | ❌ 缺 | **P1** |
| `needs_review` | ❌ 缺 | **P1** |

### 2.4 Mastery 判定缺口
| 需要 | 現況 | 缺口等級 |
|------|------|---------|
| Rule-based mastery engine | ⚠️ 有 BASIC→LITERACY 但只有 2 段，需 5 段 | **P0** |
| Config-driven rules (不寫死 UI) | ⚠️ 部分閾值硬編碼在 `update_state_on_attempt` | **P0** |
| correct_no_hint / correct_with_hint 區分 | ❌ 缺 | **P0** |
| too_slow 判定 | ⚠️ 有 (classify_error_code: TIME/READ) 但未影響 mastery | **P1** |
| transfer_success 判定 | ❌ 缺 | **P2** |
| delayed_review_correct 判定 | ❌ 缺 | **P1** |
| repeated_failure 閾值 | ⚠️ 有 consecutive_wrong 但未用於 mastery downgrade | **P1** |

### 2.5 出題選擇器缺口
| 需要 | 現況 | 缺口等級 |
|------|------|---------|
| 依 mastery state 出題策略 | ❌ 缺 (目前依 topic/difficulty 隨機或順序) | **P0** |
| selection_reason 回傳 | ❌ 缺 | **P0** |
| 同概念不同表徵 | ❌ 缺 (無 variant_group) | **P1** |
| Spiral review 機制 | ❌ 缺 | **P1** |
| 應用題失敗 → 降語言複雜度 (非全面降級) | ❌ 缺 | **P1** |

### 2.6 提示與補救缺口
| 需要 | 現況 | 缺口等級 |
|------|------|---------|
| 3 層提示 (concept/step/scaffold) | ⚠️ 有 L1-L3 但語義未嚴格對應 | **P1** |
| 連續卡住 → simpler isomorphic item | ❌ 缺 (micro-step 存在但未連接到題庫) | **P0** |
| 連續卡住 → prerequisite item | ❌ 缺 (知識圖存在但未連接到出題) | **P0** |
| 提示效果統計 | ❌ 缺 | **P1** |

### 2.7 錯誤分類缺口
| 需要 | 現況 | 缺口等級 |
|------|------|---------|
| 標準化分類 enum | ⚠️ 有 ErrorCode enum (5 類) 但需擴充 | **P1** |
| 缺少: unit_error, guess_pattern, stuck_after_hint | ❌ 缺 | **P1** |
| 可擴充設計 | ⚠️ ErrorCode 是 Enum，可擴充 | — |

### 2.8 教師報表缺口
| 需要 | 現況 | 缺口等級 |
|------|------|---------|
| 班級概念分佈 | ❌ 缺 | **P0** |
| 卡點概念排名 | ❌ 缺 | **P0** |
| 需補救學生清單 | ❌ 缺 | **P0** |
| 提示使用與效果 | ❌ 缺 | **P1** |
| 重複錯誤模式 | ❌ 缺 | **P1** |
| 班級層觀察摘要 | ❌ 缺 | **P1** |

### 2.9 家長報表缺口（相對於目標）
| 需要 | 現況 | 缺口等級 |
|------|------|---------|
| 本週學了什麼概念 | ⚠️ 有 skill_tag 但缺乏人類可讀概念名 | **P1** |
| 進步的概念 | ❌ 缺 (有 trend 但無 diff 對比) | **P1** |
| 卡住的地方 | ⚠️ 有 (weak_skills) | — |
| 哪個提示等級有幫助 | ❌ 缺 | **P1** |
| 建議下一步 | ⚠️ 有 remediation | — |
| 進步證據 (不只分數) | ❌ 缺 (報表仍以 accuracy % 為主) | **P1** |
| 可列印格式 | ❌ 缺 | **P1** |

---

## 3. 與本次目標最相關的檔案清單

### 核心改動檔案
| 檔案 | 改動類型 | 風險 |
|------|---------|------|
| `adaptive_mastery.py` | **擴充** — 5-level mastery state, config-driven rules | 中 (已有測試) |
| `learning/service.py` | **擴充** — 新欄位、concept state CRUD | 低 |
| `learning/analytics.py` | **擴充** — concept-level aggregation | 低 |
| `learning/parent_report.py` | **擴充** — 進步證據、提示效果 | 低 |
| `docs/shared/analytics.js` | **擴充** — 新 event 欄位 | 低 |
| `docs/shared/attempt_telemetry.js` | **擴充** — first_answer, changed_answer, selection_reason | 低 |
| `docs/shared/hint_engine.js` | **擴充** — 提示效果追蹤 | 低 |

### 新增檔案
| 檔案 | 目的 |
|------|------|
| `learning/concept_state.py` | 學生 per-concept 狀態持久化 |
| `learning/mastery_engine.py` | Rule-based mastery update engine (config-driven) |
| `learning/next_item_selector.py` | 自適應出題選擇器 |
| `learning/error_classifier.py` | 標準化錯誤分類 |
| `learning/teacher_report.py` | 教師報表引擎 |
| `learning/mastery_config.py` | Mastery rules 設定檔 |
| `db/migrations/002_concept_state.sql` | 新 table: concept states |
| `db/migrations/003_enhanced_events.sql` | 新欄位: started_at, first_answer, etc. |
| `docs/teacher-report/index.html` | 教師報表 UI |
| `tests/test_mastery_engine.py` | Mastery engine 測試 |
| `tests/test_next_item_selector.py` | 出題選擇器測試 |
| `tests/test_error_classifier.py` | 錯誤分類測試 |
| `tests/test_teacher_report.py` | 教師報表測試 |

### 不應觸碰的檔案
| 檔案 | 原因 |
|------|------|
| `server.py` | 已修復且穩定，僅在最後整合 API endpoint |
| `engine.py` | 核心答案驗證邏輯，穩定不動 |
| `fraction_logic.py` | 分數 DAG 穩定 |
| `schemas/problem.schema.json` | 品質閘門已依賴，只做向後相容擴充 |
| `docs/shared/subscription.js` | 付費流程無關 |

---

## 4. 高風險改動點

### 風險 1: ConceptState 結構變更 (中風險)
- **現況**: `adaptive_mastery.py` 的 `ConceptState` 已有測試覆蓋
- **改動**: 從 2-stage (BASIC/LITERACY) 擴充到 5-level (unbuilt→mastered→review)
- **風險**: 既有測試 break、前端 adaptive_mastery_frontend.js 依賴 stage 名稱
- **緩解**: 保留 BASIC/LITERACY 向後相容，新 engine 使用新 schema；漸進遷移

### 風險 2: 作答事件 schema 變更 (低-中風險)
- **現況**: `la_attempt_events` table 已有資料
- **改動**: 新增欄位 (started_at, first_answer, attempts_count, etc.)
- **風險**: 既有匯入程式、前端 telemetry 需同步更新
- **緩解**: 新欄位全部 NULLABLE 或有 DEFAULT，不影響既有 INSERT

### 風險 3: 出題選擇器與既有 UI 整合 (中風險)
- **現況**: 各 module 頁面自行決定出題順序
- **改動**: 統一由 next_item_selector 決定
- **風險**: 各頁面出題邏輯不一致，覆蓋不完全
- **緩解**: Selector 先以 API / library 形式提供，各頁面逐步接入

### 風險 4: 前端 localStorage 結構變更 (低風險)
- **現況**: `ai_math_attempts_v1::${user_id}` 格式固定
- **改動**: 需新增欄位到 attempt event
- **風險**: 既有資料遺失或 parse 失敗
- **緩解**: 新欄位 optional，讀取時 fallback 到空值

---

## 5. 建議分階段實作計畫

### Phase 0: 盤點與設計 (本文件)
- ✅ DESIGN_AUDIT.md (本文件)
- → IMPLEMENTATION_PLAN.md (接下來)

### Phase 1: 資料基礎建設
**目標:** 讓系統能記錄完整作答過程，而非只有最終對錯
1. 建立標準化 concept taxonomy (`learning/concept_taxonomy.py`)
2. 擴充題目 metadata (concept_ids, prerequisite_concepts, variant_group, format)
3. 擴充事件 schema (started_at, first_answer, attempts_count, changed_answer, selection_reason)
4. 建立 student concept state table + CRUD
5. 測試覆蓋

### Phase 2: 引擎層
**目標:** 系統可根據掌握狀態自適應出題
1. Config-driven mastery rules (`learning/mastery_config.py`)
2. 5-level mastery update engine (`learning/mastery_engine.py`)
3. Next-item selector with selection_reason (`learning/next_item_selector.py`)
4. 測試覆蓋

### Phase 3: 提示與錯誤分類
**目標:** 系統可分層提示並在必要時降階補救
1. 標準化 error type enum (`learning/error_classifier.py`)
2. 3 層提示流程 (concept → step → scaffold)
3. 連續卡住時切換到前置/簡化題
4. 提示效果追蹤
5. 測試覆蓋

### Phase 4: 報表
**目標:** 老師可看班級卡點、家長可看懂進步證據
1. Teacher report engine (`learning/teacher_report.py`)
2. Teacher report UI (`docs/teacher-report/`)
3. 家長報表升級 — 進步證據、提示效果、可列印
4. 測試覆蓋

### Phase 5: 輕量遊戲化
**目標:** 以 mastery threshold 為基礎的解鎖式激勵
1. Concept zone unlock (綁定 mastery ≥ approaching)
2. Boss unlock (綁定 mastery = mastered)
3. Badge / streak (僅做最簡版)
4. 不做重動畫、不做戰鬥系統

---

## 6. 現有測試執行狀態

需在開始改動前確認所有既有測試通過。執行：
```bash
pytest tests/ -v --tb=short
```

---

## 7. 現有 logs / iteration reports

| 報告 | 路徑 | 內容 |
|------|------|------|
| Latest iteration | `reports/latest_iteration_report.md` | 最近一次迭代報告 |
| School-first | `reports/school_first_iteration_report.md` | 學校試行報告 |
| Quality gate | `quality_gate.md` | 4 段品質門檻 |
| 12 週路線圖 | `ROADMAP_12_WEEKS.md` | 12 週強化計畫 |
| MVP 缺口 | `MVP_GAP_LIST.md` | P0-P2 缺口清單 |

本次升級應延續並更新這些文件，避免重複犯錯。
