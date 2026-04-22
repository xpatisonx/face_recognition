$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExe = Join-Path $scriptDir ".venv\Scripts\python.exe"
$mainPy = Join-Path $scriptDir "main.py"

if (-not (Test-Path $pythonExe)) {
    Write-Error "Virtual environment not found. Create it first with: py -3.9 -m venv .venv"
}

& $pythonExe $mainPy
