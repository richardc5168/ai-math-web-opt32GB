# 四層圖解提示系統 Prompt Spec（fraction-word-g5 可複用版）

用途：把 `fraction-word-g5` 的「資料模型 + SVG 渲染器 + 題型路由 + CSS + UI 控制器」完整複製到其他分數應用題模組（例如 commercial pack）。

---

## 1) 架構概觀

系統分三層：

1. **資料模型層**：`buildFractionBarModel(q)`
   - 依 `q.kind`（必要時 `q.sub`）回傳統一 model。
   - model 內含 4 個 level（L1~L4）供 UI 逐層呈現。

2. **SVG 渲染層**：
   - `renderBarSVG(parts, cells, brackets, opts)`：1D 橫條。
   - `renderGridSVG(nCols, nRows, grid, opts)`：2D 網格（area / remain-then-fraction）。
   - 可選：`renderCompareBarsSVG()`（雙條比較）。

3. **UI 控制層**：
   - 按 `看提示` 每次顯示下一層（L1→L2→L3→L4）。
   - L4 前不直接爆答案；需符合頁面 gate 規則（例如先交卷）。

---

## 2) 資料模型格式

```js
{
  parts: number,           // 1D bar 切分份數
  cols?: number,           // 2D grid 欄數
  rows?: number,           // 2D grid 列數
  unit_label?: string,
  levels: [
    {
      title: '🔍 Level 1：判斷題型',
      text: '...',
      cells?: ['empty'|'red'|'orange'|'green'|'blue'...],
      brackets?: [{ start:number, count:number, label:string, color:string }],
      cellLabels?: string[] | Object,
      grid?: string[],
      gridCols?: number,
      gridRows?: number,
      hLineScope?: 'none'|'remaining'|'all',
      remainColStart?: number,
      gridLabels?: [{ startCol:number, endCol:number, text:string, color:string }],
      compareBars?: Object
    },
    // Level 2, 3, 4 ...
  ]
}
```

---

## 3) 顏色對照（cell 狀態 → 色碼）

```js
{
  red:   '#f85149',
  orange:'#d29922',
  blue:  '#58a6ff',
  green: '#2ea043',
  eaten1:'#f85149',
  eaten2:'#d29922',
  left:  '#58a6ff',
  white: 'rgba(255,255,255,0.7)',
  empty: 'rgba(255,255,255,0.06)'
}
```

---

## 4) SVG 渲染器

### 4a. `renderBarSVG(parts, cells, brackets, opts)`
- 逐格 `<rect>` 畫橫條。
- 需要時畫 `cellLabels`。
- 底部 bracket 顯示區段語意（例如「用掉」「剩下」「答案」）。

### 4b. `renderGridSVG(nCols, nRows, grid, opts)`
- 逐格繪製 2D model。
- 可控制橫線範圍：`none` / `remaining` / `all`。
- `gridLabels` 顯示欄區塊語意（第1次、剩下、答案）。

---

## 5) 題型路由對應（fraction-word-g5 原版）

| q.kind | builder | 模式 |
|---|---|---|
| `remaining_after_fraction` + sub A/B/C | `buildBarModel_RAF_A/B/C` | 1D |
| `remain_then_fraction` | `buildBarModel_RTF` | 2D |
| `average_division` | `buildBarModel_AVG` | 1D |
| `fraction_of_quantity` | `buildBarModel_FOQ` | 1D |
| `fraction_of_fraction` | `buildBarModel_FOF` | 2D |
| `reverse_fraction` | `buildBarModel_REV` | 1D |
| `generic_fraction_word` | `buildBarModel_GEN` | 1D |
| fallback | `buildBarModel_FALLBACK` | 1D |

商用包（commercial-pack1-fraction-sprint）對應：
- `remain` → `buildBarModel_REMAIN` 或 `buildBarModel_TWO_STEP`
- `remain_multi` → `buildBarModel_MULTI_REMAIN`
- `original` → `buildBarModel_ORIGINAL`
- `part_to_total` → `buildBarModel_PART`
- `compare` → `buildBarModel_COMPARE`

---

## 6) 四層內容模板

- **Level 1（🔍）判斷題型**：辨識基準量與運算型態。
- **Level 2（📊）畫圖切分**：切幾等份、哪幾格上色。
- **Level 3（✏️）算式/讀圖**：由圖回算式。
- **Level 4（🎯）合理性檢查**：驗算與答案收斂。

規則：L1~L3 只引導，不直接給最終答案字串。

---

## 7) CSS（暗底主題）

至少保留：
- `.hint-visual`
- `.hint-visual .hv-title`
- `.hint-visual .hv-text`
- `.hint-visual .hv-key`
- `.hint-visual .hv-warn`
- `.hint-visual .hv-ok`

可選：bar-row / bar-track / bar-used / bar-remain 類。

---

## 8) UI 控制器（逐層遞進）

必備狀態：
- `state.hintLevelUsed`
- `state.allowFull`（是否允許 L4 / 完整解題）

核心行為：

```js
btnHint.onclick = () => {
  const nextLevel = Math.min(4, Math.max(1, state.hintLevelUsed + 1));
  showHint(nextLevel);
};
```

`showHint(level)`：
1. 更新 `hintLevelUsed`。
2. Gate：若 `level===4 && !allowFull` 則顯示提醒，不渲染答案層。
3. 呼叫 `renderAllLevelsHtml(item, level, shortMode)`。

---

## 9) 套用到新模組的步驟

1. 題庫至少提供：`{ id, question, answer, kind, hints[], steps[] }`。
2. 寫 `buildBarModel_YOUR_KIND()` 回傳統一 model。
3. 在 `buildFractionBarModel()` 路由新增 `kind -> builder`。
4. 複製 `renderBarSVG` + `renderGridSVG` + `renderBarHintLevel`。
5. 複製 `.hint-visual` CSS 區塊。
6. 接上 UI：`btnHint.click` 逐層顯示。
7. 加入 L4 gate，避免未交卷提前爆答案。

---

## 10) 給 Claude Opus 4.6 的 Action Prompt（可直接貼）

你現在要在目標模組中實作「四層圖解提示系統」，完全對齊 fraction-word-g5 架構：

- 實作 `buildFractionBarModel(item)` 路由與各 kind builder，回傳統一 model（levels 1~4）。
- 實作 `renderBarSVG`（1D）與 `renderGridSVG`（2D）inline SVG 渲染。
- 實作 `renderBarHintLevel` / `renderAllLevelsHtml`。
- 套用 `.hint-visual` 暗底主題 CSS。
- 實作 UI 控制：`看提示` 每按一次只前進一層，`state.hintLevelUsed` 持續累積。
- 在 Level 4 前不直接顯示最終答案；若未達條件（例如未交卷）要提示而非爆答案。
- 保留 fallback（模型建不出時使用 text-only hints）。
- 任何新增 kind 都必須在路由可達並能渲染。

完成後請做：
1. 功能自測（各 kind 至少 1 題）。
2. 不洩答檢查（L1~L3 不出現最終答案字串）。
3. 輸出修改檔案清單與關鍵差異。
