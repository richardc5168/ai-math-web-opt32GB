# One-key terminal flow: activate venv and run in-process TestClient flow
# Usage (PowerShell, run from repo root):
# .\scripts\run_terminal_flow.ps1

try {
    # Allow script to run in case ExecutionPolicy blocks
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
} catch {
    # ignore
}

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Locate venv python and activation script
$venvActivate = Join-Path -Path $PSScriptRoot -ChildPath "..\.venv\Scripts\Activate.ps1"
$venvPython = Join-Path -Path $PSScriptRoot -ChildPath "..\.venv\Scripts\python.exe"

Write-Output "Running terminal flow (bootstrap -> next -> submit -> custom -> report)"

# Prefer to run with venv python directly to avoid activation side-effects
if (Test-Path $venvPython) {
    & $venvPython (Join-Path $PSScriptRoot "..\runner_temp.py")
} else {
    # Fallback: try to activate then run
    if (Test-Path $venvActivate) {
        try {
            . $venvActivate
            python (Join-Path $PSScriptRoot "..\runner_temp.py")
        } catch {
            Write-Error "Failed to activate venv and run runner_temp.py: $_"
        }
    } else {
        Write-Error "No venv python or activate script found; please create .venv and install dependencies."
    }
}

Write-Host "\nTerminal flow finished. Press Enter to exit."
Read-Host | Out-Null
