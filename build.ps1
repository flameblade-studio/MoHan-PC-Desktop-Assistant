param(
    [string]$AppName = "MoHan-Desktop-Assistant",
    [string]$Version = "dev",
    [string]$Python = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

if (-not $Python) {
    $localCandidates = @(
        (Join-Path $ProjectRoot ".venv\Scripts\python.exe"),
        (Join-Path $ProjectRoot "venv\Scripts\python.exe")
    )
    $Python = $localCandidates |
        Where-Object { Test-Path $_ } |
        Select-Object -First 1
}
if (-not $Python) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        $Python = $pythonCommand.Source
    }
}
if (-not $Python) {
    throw "Python was not found. Activate a virtual environment or pass -Python."
}

& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name "$AppName-$Version" `
    --icon "assets\mohan-halfbody.ico" `
    --add-data "assets;assets" `
    --add-data "voice_listener.ps1;." `
    app.py

Write-Host "Build complete: dist\$AppName-$Version\"
