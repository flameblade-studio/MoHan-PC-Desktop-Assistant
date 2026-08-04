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

$PythonVersion = (& $Python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')").Trim()
if ($LASTEXITCODE -ne 0 -or $PythonVersion -notmatch '^3\.14(?:\.|$)') {
    throw "MoHan RC4 packages must be built with Python 3.14.x; found $PythonVersion."
}

$BuildInfo = Join-Path $ProjectRoot "build-info.json"
@{
    version = $Version
    repository = "hitoshic1982/MoHan-PC-Desktop-Assistant"
    python = $PythonVersion
} | ConvertTo-Json | Set-Content -Encoding utf8 $BuildInfo

try {
    & $Python -m PyInstaller `
        --noconfirm `
        --clean `
        --windowed `
        --name "$AppName-$Version" `
        --icon "assets\mohan-halfbody.ico" `
        --add-data "assets;assets" `
        --add-data "voice_listener.ps1;." `
        --add-data "build-info.json;." `
        app.py
}
finally {
    Remove-Item -LiteralPath $BuildInfo -Force -ErrorAction SilentlyContinue
}

Write-Host "Build complete: dist\$AppName-$Version\"
