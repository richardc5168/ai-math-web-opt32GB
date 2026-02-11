$ErrorActionPreference = "Stop"

$python = Join-Path (Split-Path $PSScriptRoot -Parent) ".venv\Scripts\python.exe"
if (!(Test-Path $python)) {
  $python = "python"
}

Write-Host "[verify_before_commit] Running verify_all..." -ForegroundColor Cyan
& $python "$PSScriptRoot\verify_all.py"
if ($LASTEXITCODE -ne 0) {
  Write-Error "verify_all failed."
  exit 1
}

Write-Host "[verify_before_commit] Running question bank tests..." -ForegroundColor Cyan
& $python -m pytest -q tests\test_question_bank_validation.py
if ($LASTEXITCODE -ne 0) {
  Write-Error "Question bank tests failed."
  exit 1
}

Write-Host "[verify_before_commit] Checking git status..." -ForegroundColor Cyan
# Unstaged changes
$unstaged = git diff --name-only
# Untracked files
$untracked = git status --porcelain | Where-Object { $_ -match "^\?\?" }

if ($unstaged) {
  Write-Error "Unstaged changes detected. Please stage all intended files before commit."
  Write-Host $unstaged
  exit 1
}

if ($untracked) {
  Write-Error "Untracked files detected. Please add or ignore them before commit."
  Write-Host $untracked
  exit 1
}

Write-Host "[verify_before_commit] OK. Safe to commit." -ForegroundColor Green
exit 0
