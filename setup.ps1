# Windows setup for Job Application Agent V2.
# Usage: powershell -ExecutionPolicy Bypass -File setup.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== Job Application Agent V2 Setup ===" -ForegroundColor Cyan

$python = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $python = @("py", "-3")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $python = @("python")
}

if (-not $python) {
    Write-Host "Python 3.10+ was not found. Install it from https://python.org and rerun setup." -ForegroundColor Red
    exit 1
}

if ($python.Count -eq 2) {
    & $python[0] $python[1] run.py --install
} else {
    & $python[0] run.py --install
}
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
Write-Host "`nRunning diagnostics..." -ForegroundColor Yellow
& $venvPython run.py --doctor

$shortcutScript = Join-Path $PSScriptRoot "assets\make_shortcuts.ps1"
if (Test-Path $shortcutScript) {
    try { & $shortcutScript } catch {
        Write-Host "Desktop shortcut was not created: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

Write-Host "`nSetup complete. Double-click 'Job Application Agent.bat' or run:" -ForegroundColor Green
Write-Host "  .venv\Scripts\python.exe run.py"
