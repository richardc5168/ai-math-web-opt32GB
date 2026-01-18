param(
  [int]$ApiPort = 8001,
  [int]$StreamlitPort = 8501
)

$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $root

$py = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) {
  $py = 'python'
}

$uvTask = "AIMATH_Uvicorn_$ApiPort"
$stTask = "AIMATH_Streamlit_$StreamlitPort"

$uvCmd = "`"$py`" -m uvicorn server:app --host 127.0.0.1 --port $ApiPort"
$stCmd = "`"$py`" -m streamlit run app.py --server.port $StreamlitPort --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false"

# Create logs folder
$logs = Join-Path $root 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

# Use cmd /c so we can redirect logs
$uvRun = "cmd /c $uvCmd ^> logs\\uvicorn_$ApiPort.log 2^>^&1"
$stRun = "cmd /c $stCmd ^> logs\\streamlit_$StreamlitPort.log 2^>^&1"

Write-Host "Installing scheduled tasks (current user) ..." -ForegroundColor Cyan
Write-Host "- $uvTask" -ForegroundColor Cyan
schtasks /Create /F /SC ONLOGON /TN $uvTask /TR $uvRun | Out-Null
Write-Host "- $stTask" -ForegroundColor Cyan
schtasks /Create /F /SC ONLOGON /TN $stTask /TR $stRun | Out-Null

Write-Host "Starting tasks now ..." -ForegroundColor Cyan
schtasks /Run /TN $uvTask | Out-Null
schtasks /Run /TN $stTask | Out-Null

$hub = "http://127.0.0.1:$ApiPort/verify"
$quad = "http://127.0.0.1:$ApiPort/quadratic"
$st = "http://127.0.0.1:$StreamlitPort/"

Write-Host "\nDone." -ForegroundColor Green
Write-Host "From now on, you can just open these in your browser (no .bat needed):" -ForegroundColor Green
Write-Host "- $hub"
Write-Host "- $quad"
Write-Host "- $st"
Write-Host "\nLogs:" -ForegroundColor Yellow
Write-Host "- logs\\uvicorn_$ApiPort.log"
Write-Host "- logs\\streamlit_$StreamlitPort.log"

# Create a Desktop shortcut (.url) for convenience
try {
  $desktop = [Environment]::GetFolderPath('Desktop')
  if ($desktop) {
    $urlPath = Join-Path $desktop 'AIMATH Local Hub.url'
    $content = "[InternetShortcut]`r`nURL=$hub`r`n"
    Set-Content -Path $urlPath -Value $content -Encoding ASCII
    Write-Host "\nCreated desktop shortcut: $urlPath" -ForegroundColor Green
  }
} catch {
  # ignore
}
