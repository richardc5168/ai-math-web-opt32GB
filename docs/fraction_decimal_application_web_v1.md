# fraction_decimal_application_web_v1

新增題型 `fraction_decimal_application_web_v1`，採 plugin/registry 增量註冊，不覆蓋既有題型邏輯。

## Feature Flag

- 設定：`EXTERNAL_WEB_FRACTION_DECIMAL=1`
- 預設關閉，未開啟時不會註冊到 `engine.GENERATORS`。

## 目標題型範圍

- 購物折扣
- 平均分配
- 單位換算
- 路程時間

每題包含：
- 4 階提示（策略→列式→計算→檢查/反思）
- 至少 5 種常見錯誤診斷

## 外網資料流

- 來源清單：`data/external_web_notes/fraction_decimal_sources.yaml`
- 摘要輸出：`data/external_web_notes/fraction_decimal_notes.jsonl`
- 題庫輸出：`data/fraction_decimal_application_web_v1_pack.json`

## 指令

```bash
npm run fraction-decimal:web:ingest
npm run fraction-decimal:web:build
npm run fraction-decimal:web:validate
npm run test:fraction-decimal:web
```

## Idle 觸發流程

```bash
npm run idle:web:fraction-decimal:expand
```

行為：
- 僅在任務完成 / 無任務 / 卡住時觸發。
- 預設 idle 判斷門檻 20 分鐘，stuck 門檻 30 分鐘。
- 可透過參數調整：
  - `--idle-minutes <N>`
  - `--stuck-minutes <N>`
- 觸發後會先執行 hourly commands 輪詢，再跑 ingest/build/validate/test/verify。
- 只有驗證通過才可搭配 `--auto-commit` 提交。
