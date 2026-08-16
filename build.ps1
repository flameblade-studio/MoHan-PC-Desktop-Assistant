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

& $Python tools/verify_multimodal_model_assets.py
if ($LASTEXITCODE -ne 0) {
    throw "MoHan $Version bundled multimodal model verification failed."
}

$NativeBuildId = [guid]::NewGuid().ToString("N")
$NativeWheels = Join-Path $ProjectRoot "native-wheels-$NativeBuildId"
$NativeEvidence = Join-Path $NativeWheels "mohan-native-build-evidence.json"
& $Python tools/build_native_acceleration.py `
    --output-dir $NativeWheels `
    --evidence $NativeEvidence `
    --install
if ($LASTEXITCODE -ne 0) {
    throw "MoHan $Version native acceleration build failed with exit code $LASTEXITCODE."
}
& $Python -c "import _mohan_accel; assert _mohan_accel.__version__ == '0.1.0'; assert _mohan_accel.__rgba_parallel_pixel_threshold__ == 262_144; assert _mohan_accel.scale_pcm16(bytes.fromhex('e80318fc'), 0.5) == bytes.fromhex('f4010cfe'); assert _mohan_accel.alpha_over_rgba(bytes((20, 40, 60, 80)), bytes((200, 100, 50, 128))) == bytes((110, 70, 54, 167))"
if ($LASTEXITCODE -ne 0) {
    throw "MoHan $Version native acceleration import or operation verification failed."
}
$Abi3tCompatibilityDll = Join-Path $NativeWheels "python3t.dll"
if (-not (Test-Path -LiteralPath $Abi3tCompatibilityDll)) {
    throw "MoHan $Version requires Python 3.15's abi3t compatibility DLL for native packaging."
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
        --add-data "$NativeEvidence;." `
        --add-binary "$Abi3tCompatibilityDll;." `
        --hidden-import "_mohan_accel" `
        --collect-all "azure.cognitiveservices.speech" `
        --python-option "X jit" `
        app.py
}
finally {
    Remove-Item -LiteralPath $BuildInfo -Force -ErrorAction SilentlyContinue
}

$PackageRoot = Join-Path $ProjectRoot "dist\$AppName-$Version"
$PublicExecutable = Join-Path $PackageRoot "$AppName-$Version.exe"
$RuntimeExecutable = Join-Path $PackageRoot "$AppName-$Version-runtime.exe"
Move-Item -LiteralPath $PublicExecutable -Destination $RuntimeExecutable -Force

$LauncherBuild = Join-Path $ProjectRoot "build\jit-launcher-$Version"
$LauncherDist = Join-Path $ProjectRoot "dist\jit-launcher-$Version"
Remove-Item -LiteralPath $LauncherBuild, $LauncherDist -Recurse -Force -ErrorAction SilentlyContinue
& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name "$AppName-$Version" `
    --icon (Join-Path $ProjectRoot "assets\mohan-halfbody.ico") `
    --distpath $LauncherDist `
    --workpath $LauncherBuild `
    --specpath $LauncherBuild `
    tools\jit_launcher.py
if ($LASTEXITCODE -ne 0) {
    throw "MoHan $Version JIT launcher build failed with exit code $LASTEXITCODE."
}
Copy-Item -LiteralPath (Join-Path $LauncherDist "$AppName-$Version.exe") `
    -Destination $PublicExecutable `
    -Force

& $Python tools/verify_packaged_native_acceleration.py `
    "dist\$AppName-$Version"
if ($LASTEXITCODE -ne 0) {
    throw "MoHan $Version packaged native verification failed."
}

Write-Host "Build complete: dist\$AppName-$Version\"
