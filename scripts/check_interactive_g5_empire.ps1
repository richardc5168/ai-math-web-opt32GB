Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
Set-Location -Path $root

$py = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) {
  throw "Missing venv python: $py (run your setup first)"
}

& $py (Join-Path $root 'scripts\stability_check_interactive_g5_empire.py') --count 20
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $py (Join-Path $root 'scripts\verify_interactive_g5_empire_bank.py')
exit $LASTEXITCODE
