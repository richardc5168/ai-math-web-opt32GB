# Star Pack Spec

目的：把 MVP 主打場景收斂為家長一眼懂、學生可直接開始的四大主題入口。

## 1. 產品定位

- 對象：台灣國小五六年級數學補弱
- 主打主題：分數、小數、百分率、生活應用題
- 商業目標：作為付費升級最強賣點之一

## 2. 目前實作

- 頁面：`docs/star-pack/index.html`
- 入口：首頁導流至 `star-pack/`
- 精選成交入口：`fraction -> decimal -> percent -> life` 四步明星路線
- 方案 gating：
  - 免費版：僅開放部分分數入口
  - 付費版：解鎖全部 pack

## 3. 四大主題包

| Pack | 模組 | 題數 |
|------|------|------|
| 分數 | `fraction-g5`, `fraction-word-g5`, `commercial-pack1-fraction-sprint` | 483 |
| 小數 | `interactive-decimal-g5`, `decimal-unit4` | 334 |
| 百分率 | `ratio-percent-g5` | 179 |
| 生活應用 | `life-applications-g5` | 300 |

總計：1296 題

## 4. 題型資料結構設計

目前主題包頁使用模組層 metadata；後續每題建議補齊以下欄位：

```json
{
  "id": "fraction_word_001",
  "grade": 5,
  "topic": "fraction",
  "difficulty": "medium",
  "question_type": "word_problem",
  "concept_tags": ["通分", "剩餘量", "分量應用"],
  "hint_levels": 3,
  "common_error_tags": ["對象搞混", "乘除方向錯誤"],
  "module": "fraction-word-g5"
}
```

## 5. 學生完成狀態建議模型

依既有 telemetry，可對單題完成結果映射成：

- 直接答對
- 看提示後答對
- 看提示仍答錯
- 重做後答對

建議對應規則：

- `ok=true && max_hint=0` -> 直接答對
- `ok=true && max_hint>0` -> 看提示後答對
- `ok=false && max_hint>0` -> 看提示仍答錯
- `retry_start` 後 `ok=true` -> 重做後答對

## 6. 家長端應看到的摘要

主題包至少應提供：

- 正確率
- 提示依賴度
- 容易錯的概念
- 下週建議補強模組

目前新增的明星路線摘要會把學生在四步主線中的結果濃縮成：

- 直接答對
- 看提示後答對
- 看提示仍答錯
- 重做後答對

目前這些摘要主要透過 `parent-report/` 的弱點分析與補救建議呈現。

## 7. 事件需求

- `star_pack_view`
- `star_pack_featured_view`
- `star_pack_featured_start`
- `star_pack_module_click`
- `star_pack_progress_summary_view`
- 後續可補：`star_pack_complete`

## 8. 驗收標準

- 首頁能明確看到明星題組入口
- 學生可從題組頁直接進入模組練習
- 明星題組頁能直接說明「適合誰、會補什麼、家長可看到什麼結果」
- 免費與付費差異清楚
- 家長可把這組功能理解為付費主打，而非隱藏功能
