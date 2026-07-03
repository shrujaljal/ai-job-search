# Setup script for the Job Search Assistant.
# Installs Python + scraper dependencies so the app and CLIs are ready to run.
# Usage:  powershell -ExecutionPolicy Bypass -File setup.ps1

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host "=== Job Search Assistant Setup ===" -ForegroundColor Cyan

# --- 1. Python packages ------------------------------------------------------
Write-Host "`n[1/2] Installing Python packages (streamlit, python-docx, lxml)..." -ForegroundColor Yellow
python -m pip install --quiet python-docx streamlit lxml
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Python packages installed." -ForegroundColor Green
} else {
    Write-Host "  Python package install failed." -ForegroundColor Red
}

# --- 2. Scraper CLI dependencies (Bun) ---------------------------------------
Write-Host "`n[2/2] Installing scraper dependencies (bun install)..." -ForegroundColor Yellow

$bun = Get-Command bun -ErrorAction SilentlyContinue
if (-not $bun) {
    Write-Host "  Bun is not installed. Install it from https://bun.sh then re-run." -ForegroundColor Red
    Write-Host "  (Scrapers need Bun; the resume generator and UI work without it.)" -ForegroundColor DarkGray
} else {
    $scrapers = @("linkedin-search", "indeed-search", "glassdoor-search")
    foreach ($s in $scrapers) {
        $dir = Join-Path $root ".agents\skills\$s\cli"
        if (Test-Path $dir) {
            Write-Host "  Installing $s..." -ForegroundColor DarkGray
            Push-Location $dir
            bun install | Out-Null
            Pop-Location
            if ($LASTEXITCODE -eq 0) {
                Write-Host "    $s ready." -ForegroundColor Green
            } else {
                Write-Host "    $s install failed." -ForegroundColor Red
            }
        } else {
            Write-Host "  $s directory not found, skipping." -ForegroundColor DarkGray
        }
    }
}

Write-Host "`n=== Setup complete ===" -ForegroundColor Cyan
Write-Host "Launch the app with:" -ForegroundColor White
Write-Host "  python -m streamlit run app.py" -ForegroundColor Green
