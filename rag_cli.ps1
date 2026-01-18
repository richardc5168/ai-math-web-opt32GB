<# PowerShell launcher for rag_cli.py #>
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPy = Join-Path $scriptDir '.venv\Scripts\python.exe'
$cliPy = Join-Path $scriptDir 'rag_cli.py'
$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

if (Test-Path $venvPy) {
    & $venvPy $cliPy @args
} else {
    # Prefer Windows py launcher when venv is not available
    if (Get-Command py -ErrorAction SilentlyContinue) {
        py $cliPy @args
    } else {
        python $cliPy @args
    }
}
