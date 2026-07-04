# Creates a "Job application agent" shortcut on the Desktop (with the J icon)
# and attempts to pin it to the taskbar.

$ErrorActionPreference = "Stop"
$root    = Split-Path $PSScriptRoot -Parent
$bat     = Join-Path $root "Job Application Agent.bat"
$icon    = Join-Path $root "assets\job_app_agent.ico"
$desktop = [Environment]::GetFolderPath("Desktop")
$lnkPath = Join-Path $desktop "Job application agent.lnk"

# --- Desktop shortcut ---------------------------------------------------------
# Target cmd.exe (not the .bat directly) so Windows offers "Pin to taskbar".
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut($lnkPath)
$sc.TargetPath       = "$env:SystemRoot\System32\cmd.exe"
$sc.Arguments        = "/c `"$bat`""
$sc.WorkingDirectory = $root
$sc.IconLocation     = "$icon,0"
$sc.Description       = "Launch the Job Search Assistant"
$sc.WindowStyle      = 1
$sc.Save()
Write-Host "Desktop shortcut created: $lnkPath" -ForegroundColor Green

# --- Start Menu copy (makes it searchable / pinnable to Start) ----------------
$startDir = Join-Path ([Environment]::GetFolderPath("Programs")) "Job Application Agent"
New-Item -ItemType Directory -Force -Path $startDir | Out-Null
Copy-Item $lnkPath (Join-Path $startDir "Job application agent.lnk") -Force
Write-Host "Start Menu shortcut created." -ForegroundColor Green

# --- Attempt to pin to the taskbar --------------------------------------------
$pinned = $false
try {
    $shell  = New-Object -ComObject Shell.Application
    $folder = $shell.Namespace((Split-Path $lnkPath))
    $item   = $folder.ParseName((Split-Path $lnkPath -Leaf))
    foreach ($verb in $item.Verbs()) {
        $name = ($verb.Name -replace '&', '')
        if ($name -match 'Pin to tas?kbar') { $verb.DoIt(); $pinned = $true; break }
    }
} catch { }

if ($pinned) {
    Write-Host "Pinned to taskbar." -ForegroundColor Green
} else {
    Write-Host "Could not pin to taskbar automatically (Windows 11 blocks this)." -ForegroundColor Yellow
    Write-Host "To pin manually: right-click the desktop icon -> Show more options -> Pin to taskbar." -ForegroundColor Yellow
}
