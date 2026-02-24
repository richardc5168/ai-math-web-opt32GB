# GitHub 指令橋接（每 30 分鐘 + 任務完成後）

## 目的

讓系統可從 GitHub 上的 `ops/hourly_commands.json` 讀取指令，並自動執行：
- 每 30 分鐘輪詢一次
- 既有 workflow 成功完成後再輪詢一次

## 實作

- Workflow：`.github/workflows/hourly-command-runner.yml`
- 執行腳本：`npm run commands:poll:once -- --command-file ops/hourly_commands.json`
- 指令來源：`ops/hourly_commands.json`

## 執行方式

1. 在 GitHub 編輯 `ops/hourly_commands.json` 增加/更新 command。
2. 等待排程（30 分鐘）或手動觸發 workflow dispatch。
3. Workflow 會執行輪詢器，依 allow-list 執行對應 npm script。
4. 成功後會在 `artifacts/hourly_command_*.json*` 留下狀態與 log。

## 與 Chat 的關係（重點）

- GitHub 無法直接「喚醒這個 Chat 介面」去執行命令。
- 可行作法是：由 GitHub Actions / 本機常駐輪詢器代為執行命令。
- 這份流程等價達成「在 GitHub 打指令 → 自動抓取 → 自動執行」。

## 安全與治理

- 僅 allow-list 內的 npm script 可被執行（見 `tools/poll_hourly_commands.cjs`）。
- 執行後會跑既有驗證 gate，通過才自動 commit/push。
- 若要新增可執行 script，需先在 allow-list 明確加入。
