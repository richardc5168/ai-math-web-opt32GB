# AI MATH WEB（GitHub Pages 發佈流程）

你要的「獨立 AI MATH WEB 連結路徑」最穩定的做法，是做一個**只放純前端 pages** 的獨立 repo，直接用 GitHub Pages 發佈（參考 `math-offline`）。

## 1) 你要發佈的內容（本專案已準備好）
- `docs/index.html`：Hub（入口頁）
- `docs/catalog.json`：題型清單（之後新增題型只要改這裡）
- `docs/quadratic/index.html`：一元二次方程式（練習 + 驗證）
- `docs/.nojekyll`

## 2) 方案 A：不用安裝 Git（直接用 GitHub 網頁上傳）
1. 到 `https://github.com/richardc5168` 建立新 repo，例如：`ai-math-web`（Public）
2. 進 repo → Add file → Upload files
3. 把本機的 `docs/` 整個資料夾上傳（包含 `index.html` 與 `quadratic/`）
4. 到 Settings → Pages
   - Source: Deploy from a branch
   - Branch: `main`
   - Folder: `/docs`
5. 等 1~3 分鐘，Pages 會提供網址：
   - Hub：`https://richardc5168.github.io/ai-math-web/`
   - 題型：`https://richardc5168.github.io/ai-math-web/quadratic/`

## 3) 方案 B：使用 GitHub Desktop（推薦，比裝 Git 更簡單）
1. 安裝 GitHub Desktop
2. Clone 新 repo 到本機
3. 把 `docs/` 複製進去
4. Commit + Push
5. 到 Settings → Pages 同上

## 4) 方案 C：安裝 Git（CLI）
你目前系統看起來沒有 `git` 指令，因此無法在這台機器上用 CLI 直接 commit/push。
- 你可以安裝 Git for Windows 後，再在新 repo 內：`git init` → `git add` → `git commit` → `git push`

## 5) 發佈驗證（你要的「路徑驗證」）
發佈後請檢查兩個網址：
- `.../ai-math-web/`（Hub 是否能打開）
- `.../ai-math-web/quadratic/`（題型是否能出題與驗證）

## 6) 產生「可上傳包」（可選）
若你不想把整個專案搬去 GitHub，可以用這個腳本產生乾淨的發布包（只含 pages 必要檔）：

- `powershell -ExecutionPolicy Bypass -File scripts/windows/export_ai_math_web_pages.ps1`

會輸出到：`dist_ai_math_web_pages/`，把裡面的 `docs/` 上傳到 GitHub repo 即可。

如果你希望我也把「Hub 上顯示更多題型」做成可擴展清單，我可以再加一個 `docs/catalog.json` 讓新增題型不用改 HTML。
