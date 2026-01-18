param(
  [int]$Port = 8000,
  [int]$TopicKey = 2,
  [int]$MaxPortTries = 10,
  [int]$HealthWaitSeconds = 15
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Test-PortInUse {
  param([int]$P)
  try {
    $x = Get-NetTCPConnection -LocalPort $P -State Listen -ErrorAction Stop
    return ($null -ne $x)
  } catch {
    return $false
  }
}

# Pick python executable: prefer venv if present
$python = "python"
if (Test-Path -LiteralPath "$PSScriptRoot\..\.venv\Scripts\python.exe") {
  $python = (Resolve-Path "$PSScriptRoot\..\.venv\Scripts\python.exe").Path
}

$chosenPort = $Port
for ($i = 0; $i -lt $MaxPortTries; $i++) {
  if (-not (Test-PortInUse -P $chosenPort)) { break }
  $chosenPort++
}

if (Test-PortInUse -P $chosenPort) {
  throw "No free port found starting from $Port (tried $MaxPortTries ports)."
}

$baseUrl = "http://127.0.0.1:$chosenPort"
Write-Host "== RunSmoke: starting uvicorn on $baseUrl ==" -ForegroundColor Cyan

$uvicorn = Start-Process -FilePath $python -PassThru -WorkingDirectory (Resolve-Path "$PSScriptRoot\..") -ArgumentList @(
  "-m","uvicorn","server:app","--host","127.0.0.1","--port",$chosenPort
)

try {
  $deadline = (Get-Date).AddSeconds($HealthWaitSeconds)
  $healthy = $false
  while ((Get-Date) -lt $deadline) {
    try {
      $h = Invoke-RestMethod -Method Get "$baseUrl/health" -TimeoutSec 2
      if ($h.ok -eq $true) { $healthy = $true; break }
    } catch {
      Start-Sleep -Milliseconds 300
    }
  }

  if (-not $healthy) {
    throw "Server did not become healthy within ${HealthWaitSeconds}s at $baseUrl/health"
  }

  Write-Host "== RunSmoke: server healthy, running smoke.ps1 ==" -ForegroundColor Cyan
  & "$PSScriptRoot\smoke.ps1" -BaseUrl $baseUrl -TopicKey $TopicKey

  Write-Host "== RunSmoke: OK ==" -ForegroundColor Green
}
finally {
  if ($uvicorn -and -not $uvicorn.HasExited) {
    Write-Host "== RunSmoke: stopping uvicorn PID $($uvicorn.Id) ==" -ForegroundColor DarkGray
    Stop-Process -Id $uvicorn.Id -Force -ErrorAction SilentlyContinue
  }
}
