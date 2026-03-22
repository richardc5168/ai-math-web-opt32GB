# IMPLEMENTATION_PLAN.md — 學習效果導向系統最小可行實作計畫

> Generated: 2026-03-22  
> Based on: DESIGN_AUDIT.md  
> Principle: 最小破壞、漸進升級、每階段可測試可交付

---

## 總覽

```
Phase 1 ──→ Phase 2 ──→ Phase 3 ──→ Phase 4 ──→ Phase 5
 資料基礎      引擎層     提示/錯誤     報表        輕遊戲化
```

每個 Phase 完成後必須：
1. 所有既有測試通過
2. 新功能有測試覆蓋
3. 產出 changed files / why / tests / risks / next

---

## Phase 1: 資料基礎建設

### 1A. Concept Taxonomy
**新增:** `learning/concept_taxonomy.py`

標準化概念 ID 體系，對應國小五下數學課綱：
```python
CONCEPT_TAXONOMY = {
    "frac_add_like": {
        "name": "同分母分數加法",
        "display_name_zh": "同分母分數加法",
        "grade": 5,
        "domain": "fraction",
        "prerequisites": [],
        "difficulty_base": "easy"
    },
    "frac_add_unlike": {
        "name": "異分母分數加法",
        "display_name_zh": "異分母分數加法",
        "grade": 5,
        "domain": "fraction",
        "prerequisites": ["frac_add_like", "lcm_basic"],
        "difficulty_base": "normal"
    },
    # ...
}
```

### 1B. Question Metadata Enhancement
**修改:** `data/web_g5s_pack.json` (向後相容)

為每題新增：
```json
{
  "concept_ids": ["percent_of_number"],
  "format": "numeric",
  "prerequisite_concepts": ["multiply_decimal"],
  "variant_group": "percent_basic_001",
  "remediation_target": null,
  "supports_hints": true
}
```

Migration: Python script 自動填入預設值，人工校驗 top-20 題。

### 1C. Enhanced Event Schema
**新增:** `db/migrations/002_enhanced_events.sql`

```sql
ALTER TABLE la_attempt_events ADD COLUMN started_at TEXT;
ALTER TABLE la_attempt_events ADD COLUMN first_answer TEXT;
ALTER TABLE la_attempt_events ADD COLUMN attempts_count INTEGER DEFAULT 1;
ALTER TABLE la_attempt_events ADD COLUMN changed_answer INTEGER DEFAULT 0;
ALTER TABLE la_attempt_events ADD COLUMN selection_reason TEXT;
ALTER TABLE la_attempt_events ADD COLUMN concept_ids_json TEXT DEFAULT '[]';
ALTER TABLE la_attempt_events ADD COLUMN remediation_triggered INTEGER DEFAULT 0;
ALTER TABLE la_attempt_events ADD COLUMN prerequisite_fallback INTEGER DEFAULT 0;
ALTER TABLE la_attempt_events ADD COLUMN error_type TEXT;
```

### 1D. Student Concept State
**新增:** `db/migrations/003_concept_state.sql`

```sql
CREATE TABLE IF NOT EXISTS la_student_concept_state (
  student_id TEXT NOT NULL,
  concept_id TEXT NOT NULL,
  mastery_level TEXT NOT NULL DEFAULT 'unbuilt',
  mastery_score REAL NOT NULL DEFAULT 0.0,
  recent_accuracy REAL,
  hint_dependency REAL DEFAULT 0.0,
  avg_response_time_sec REAL,
  attempts_total INTEGER DEFAULT 0,
  correct_total INTEGER DEFAULT 0,
  correct_no_hint INTEGER DEFAULT 0,
  correct_with_hint INTEGER DEFAULT 0,
  consecutive_correct INTEGER DEFAULT 0,
  consecutive_wrong INTEGER DEFAULT 0,
  transfer_success_count INTEGER DEFAULT 0,
  delayed_review_status TEXT DEFAULT 'none',
  needs_review INTEGER DEFAULT 0,
  last_seen_at TEXT,
  last_mastered_at TEXT,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (student_id, concept_id)
);
```

**新增:** `learning/concept_state.py` — CRUD for student concept state

### 1E. Tests
- `tests/test_concept_taxonomy.py`
- `tests/test_concept_state.py`
- `tests/test_enhanced_events.py`

---

## Phase 2: 引擎層

### 2A. Mastery Config
**新增:** `learning/mastery_config.py`

所有閾值集中管理：
```python
MASTERY_CONFIG = {
    "levels": {
        "unbuilt":              {"min_score": 0.0,  "max_score": 0.19},
        "developing":           {"min_score": 0.20, "max_score": 0.49},
        "approaching_mastery":  {"min_score": 0.50, "max_score": 0.79},
        "mastered":             {"min_score": 0.80, "max_score": 1.00},
        "review_needed":        {"trigger": "mastery_decay"}
    },
    "score_deltas": {
        "correct_no_hint":      +0.15,
        "correct_with_hint":    +0.08,
        "wrong":                -0.10,
        "too_slow":             -0.03,
        "repeated_changes":     -0.05,
        "transfer_success":     +0.12,
        "delayed_review_correct": +0.10,
        "repeated_failure":     -0.15,
    },
    "promotion_rules": {
        "to_developing":     {"min_attempts": 3, "min_recent_acc": 0.30},
        "to_approaching":    {"min_attempts": 5, "min_recent_acc": 0.60, "max_hint_dep": 0.50},
        "to_mastered":       {"min_attempts": 8, "min_recent_acc": 0.85, "max_hint_dep": 0.25},
    },
    "review_trigger": {
        "days_since_mastered": 7,
        "min_delayed_review_attempts": 2,
        "min_delayed_review_acc": 0.75
    },
    "selector": {
        "mastered_spiral_review_prob": 0.15,
        "approaching_variant_prob": 0.3,
        "developing_standard_prob": 0.7,
        "unbuilt_prerequisite_first": True
    }
}
```

### 2B. Mastery Update Engine
**新增:** `learning/mastery_engine.py`

```python
def update_mastery(
    state: StudentConceptState,
    event: AnswerEvent,
    config: dict = MASTERY_CONFIG
) -> Tuple[StudentConceptState, MasteryActions]:
    """Rule-based mastery update. Pure function."""
```

- 讀取 config，不寫死在函式
- 回傳 actions (promoted, demoted, review_triggered, etc.)
- 全部 rule-based，不用 ML

### 2C. Next-Item Selector
**新增:** `learning/next_item_selector.py`

```python
def select_next_item(
    student_id: str,
    concept_states: Dict[str, StudentConceptState],
    available_items: List[QuestionItem],
    config: dict = MASTERY_CONFIG
) -> Tuple[QuestionItem, str]:
    """Returns (next_item, selection_reason)"""
```

選題策略：
- **mastered**: 15% spiral review, 跨概念題, 變式題
- **approaching_mastery**: 同概念不同表徵 + 少量應用題
- **developing**: 標準題 + 簡化題
- **unbuilt**: 前置技能 → 最基礎題
- **應用題失敗但基礎穩**: 降語言複雜度，不全面降級

### 2D. Tests
- `tests/test_mastery_engine.py`
- `tests/test_next_item_selector.py`

---

## Phase 3: 提示與錯誤分類

### 3A. Error Classifier
**新增:** `learning/error_classifier.py`

擴充 ErrorCode enum：
```python
class ErrorType(str, Enum):
    CONCEPT_MISUNDERSTANDING = "concept_misunderstanding"
    CARELESS = "careless"
    CALCULATION_ERROR = "calculation_error"
    UNIT_ERROR = "unit_error"
    READING_COMPREHENSION = "reading_comprehension_issue"
    GUESS_PATTERN = "guess_pattern"
    STUCK_AFTER_HINT = "stuck_after_hint"
```

### 3B. Hint / Remediation Flow Enhancement
**修改:** `docs/shared/hint_engine.js` — 追蹋提示效果
**新增:** `learning/remediation_flow.py`

提示三層：
1. **Concept hint**: 觀念提示 (不涉及具體數字)
2. **Step hint**: 步驟提示 (列式、方法)
3. **Scaffold hint**: 鷹架提示 (完整步驟但留一步讓學生做)

連續卡住 (≥3 同概念錯)：
- 切換到 simpler isomorphic item (同概念、更簡單數字)
- 或 prerequisite item (前置概念基礎題)

所有提示與補救寫入 event log。

### 3C. Hint Effectiveness Tracking
追蹤指標：
- hint → next attempt correct rate
- hint level → effectiveness by concept
- remediation → recovery rate

### 3D. Tests
- `tests/test_error_classifier.py`
- `tests/test_remediation_flow.py`

---

## Phase 4: 報表

### 4A. Teacher Report
**新增:** `learning/teacher_report.py`

```python
def generate_teacher_report(
    class_student_ids: List[str],
    window_days: int = 7,
    db_path: str = None
) -> TeacherReport:
```

報表內容：
1. **Top blocking concepts** — 全班最多人卡住的概念
2. **Top blocking items** — 最多人答錯的題目
3. **Most used hints** — 最常被使用的提示
4. **Hint effectiveness** — 提示後答對率
5. **Students needing remediation** — 需補救學生清單
6. **Concept mastery distribution** — 各概念 mastery 分佈
7. **Repeated failure patterns** — 重複錯誤模式
8. **Class-level insight summary** — 班級觀察摘要

### 4B. Teacher Report UI
**新增:** `docs/teacher-report/index.html`
- 表格式、可列印
- 無花俏動畫
- 純 HTML + vanilla JS

### 4C. Parent Report Enhancement
**修改:** `learning/parent_report.py`, `docs/parent-report/index.html`

新增：
- 本週新學概念 (不只 accuracy)
- 進步的概念 (上週 vs 本週 comparison)
- 哪個提示等級有幫助
- 進步證據 (具體描述而非只有百分比)
- 列印友善 CSS (`@media print`)

### 4D. Tests
- `tests/test_teacher_report.py`
- `tests/test_parent_report_enhanced.py`

---

## Phase 5: 輕量遊戲化

### 前提
Phase 2-4 穩定運作後才開始。

### 5A. Mastery-Based Unlock
**新增:** `learning/gamification.py`

- Concept zone unlock: concept mastery ≥ approaching_mastery
- Boss challenge: mastery = mastered (all concepts in zone)
- Badge: per-concept mastery 達標
- Streak: 連續天數有作答且 accuracy ≥ 50%

### 5B. Constraints
- 必須與 mastery threshold 綁定
- 不做重動畫、不做戰鬥系統
- 不做排行榜 (避免競爭壓力)
- 解鎖狀態透過 concept state 計算，不另建系統

---

## 風險登記

| ID | 風險 | 影響 | 緩解 |
|----|------|------|------|
| R1 | 既有測試因 schema 變更 break | 中 | 新欄位全部 NULLABLE / DEFAULT |
| R2 | 前端未同步新 event 欄位 | 低 | 新欄位 optional，前端漸進更新 |
| R3 | 題庫缺 concept_ids → selector 無法工作 | 高 | Phase 1 先完成 taxonomy + mapping |
| R4 | 教師報表無真實 class 資料 | 中 | 先用 mock data 驗證 |
| R5 | Mastery 升降規則需教師驗證 | 中 | Config-driven，便於調整 |

---

## Definition of Done Checklist

- [ ] 系統可追蹤學生作答過程（first_answer, changed_answer, attempts）
- [ ] 系統可根據掌握狀態自適應出題（next_item_selector + selection_reason）
- [ ] 系統可分辨 unbuilt / developing / approaching / mastered / review
- [ ] 系統可分層提示並在必要時降階補救
- [ ] 老師可看班級卡點與概念分佈
- [ ] 家長可看懂進步證據與建議
- [ ] 遊戲化僅為輔助
- [ ] 所有重要功能有測試覆蓋
- [ ] 既有核心功能未退化
