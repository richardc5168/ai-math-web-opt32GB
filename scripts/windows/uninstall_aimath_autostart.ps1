param(
  [int]$ApiPort = 8001,
  [int]$StreamlitPort = 8501
)

$ErrorActionPreference = 'Stop'

$uvTask = "AIMATH_Uvicorn_$ApiPort"
$stTask = "AIMATH_Streamlit_$StreamlitPort"

Write-Host "Removing scheduled tasks (if exist) ..." -ForegroundColor Cyan

schtasks /Delete /F /TN $uvTask 2>$null | Out-Null
schtasks /Delete /F /TN $stTask 2>$null | Out-Null

Write-Host "Done." -ForegroundColor Green
Write-Host "Note: running processes won't be killed automatically." -ForegroundColor Yellow
Write-Host "If you want to stop them now, close the python processes or reboot." -ForegroundColor Yellow
