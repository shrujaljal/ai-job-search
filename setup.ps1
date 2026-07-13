# Setup script for the Job Search Assistant.
# Installs Python + scraper dependencies so the app and CLIs are ready to run.
# Usage:  powershell -ExecutionPolicy Bypass -File setup.ps1

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host "=== Job Search Assistant Setup ===" -ForegroundColor Cyan

# --- 1. Virtual environment + Python packages --------------------------------
Write-Host "`n[1/3] Setting up virtual environment (.venv) and Python packages..." -ForegroundColor Yellow

$venvPy = Join-Path $root ".venv\Scripts\python.exe"

# Find a base Python to create the venv. Windows often exposes a fake
# C:\Windows\System32\python app alias, so verify candidates before using them.
$basePy = $null
$candidates = @()

$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($pyLauncher) {
    $candidates += @{ Cmd = "py"; Args = @("-3") }
}

foreach ($p in (where.exe python 2>$null)) {
    if ($p -and ($p -notmatch "\\Windows\\System32\\python(\.exe)?$")) {
        $candidates += @{ Cmd = $p; Args = @() }
    }
}

foreach ($candidate in $candidates) {
    try {
        $versionOutput = & $candidate.Cmd @($candidate.Args + @("--version")) 2>&1
        if ($LASTEXITCODE -eq 0 -and ($versionOutput -match "Python\s+3\.")) {
            $basePy = $candidate
            break
        }
    } catch { }
}

if (-not (Test-Path $venvPy)) {
    if (-not $basePy) {
        Write-Host "  Python not found on PATH. Install Python 3 from python.org, then re-run." -ForegroundColor Red
        exit 1
    }
    Write-Host "  Creating .venv ..." -ForegroundColor DarkGray
    & $basePy.Cmd @($basePy.Args + @("-m", "venv", (Join-Path $root ".venv")))
}

if (Test-Path $venvPy) {
    & $venvPy -m pip install --quiet --upgrade pip
    & $venvPy -m pip install --quiet python-docx streamlit lxml pywin32 Pillow
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Python packages installed into .venv." -ForegroundColor Green
    } else {
        Write-Host "  Python package install failed." -ForegroundColor Red
    }
} else {
    Write-Host "  Could not create .venv." -ForegroundColor Red
    exit 1
}

# --- 2. Scraper CLI dependencies (Bun) ---------------------------------------
Write-Host "`n[2/3] Installing scraper dependencies (bun install)..." -ForegroundColor Yellow

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

# --- 3. Desktop / Start Menu shortcuts (with the J icon) ----------------------
Write-Host "`n[3/3] Creating desktop launcher and shortcuts..." -ForegroundColor Yellow

$icon = Join-Path $root "assets\job_app_agent.ico"
if (-not (Test-Path $icon)) {
    Write-Host "  Generating J icon..." -ForegroundColor DarkGray
    try { & $venvPy (Join-Path $root "assets\make_icon.py") | Out-Null } catch {}
}

$mkShortcuts = Join-Path $root "assets\make_shortcuts.ps1"
if (Test-Path $mkShortcuts) {
    try {
        & $mkShortcuts
    } catch {
        Write-Host "  Shortcut creation failed: $($_.Exception.Message)" -ForegroundColor Red
    }
} else {
    Write-Host "  assets\make_shortcuts.ps1 not found, skipping." -ForegroundColor DarkGray
}

Write-Host "`n=== Setup complete ===" -ForegroundColor Cyan
Write-Host "Launch the app by double-clicking the 'Job application agent' icon on your Desktop," -ForegroundColor White
Write-Host "or run:  python -m streamlit run app.py" -ForegroundColor Green
Write-Host "To pin to the taskbar: right-click the desktop icon -> Show more options -> Pin to taskbar." -ForegroundColor DarkGray
