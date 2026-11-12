$ErrorActionPreference = "Stop"

$source = Join-Path $PSScriptRoot "intelligence\gemini_live.py"
$destination = Join-Path (Get-Location) "intelligence\gemini_live.py"
$backupDir = Join-Path (Get-Location) "backup_before_phase3"

if (-not (Test-Path $source)) {
    throw "The ZIP's intelligence\gemini_live.py was not found. Extract the ZIP first."
}

if (-not (Test-Path $destination)) {
    throw "Run this script from the ZORIN project root."
}

New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
Copy-Item $destination (Join-Path $backupDir "gemini_live.py") -Force
Copy-Item $source $destination -Force

Write-Host "Phase 3 conversation update installed."
Write-Host "Backup saved in: $backupDir"
Write-Host "Next run:"
Write-Host ".\.venv\Scripts\python.exe -m compileall intelligence\gemini_live.py"
