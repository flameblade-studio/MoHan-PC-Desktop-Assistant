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
        (Join-Path $ProjectRoot ".venv315\Scripts\python.exe")
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

$PythonVersion = (& $Python -c "import platform; print(platform.python_version())").Trim()
if ($LASTEXITCODE -ne 0 -or $PythonVersion -ne "3.15.0rc1") {
    throw "MoHan $Version packages must be built with Python 3.15.0rc1; found $PythonVersion."
}
$JitContract = (& $Python -c "import sys; print(f'{sys._jit.is_available()}:{sys._jit.is_enabled()}')").Trim()
if ($LASTEXITCODE -ne 0 -or $JitContract -ne "True:True") {
    throw "MoHan $Version packages require a Python 3.15.0rc1 runtime built with JIT enabled by default; found $JitContract."
}

$BuildInfo = Join-Path $ProjectRoot "build-info.json"
@{
    version = $Version
    repository = "hitoshic1982/MoHan-PC-Desktop-Assistant"
    python = $PythonVersion
    jit_default = $true
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
        --add-data "LICENSE;." `
        --add-data "THIRD_PARTY_NOTICES.md;." `
        --add-data "build-info.json;." `
        app.py
}
finally {
    Remove-Item -LiteralPath $BuildInfo -Force -ErrorAction SilentlyContinue
}

Write-Host "Build complete: dist\$AppName-$Version\"
