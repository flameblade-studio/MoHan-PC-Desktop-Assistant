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

# The studio-maintained PySide6 6.11.1 build is installed in a dedicated
# Python 3.15 compatibility environment.  The packaging interpreter owns all
# other dependencies; prepend only the rebuilt Qt site-packages when the
# selected interpreter cannot import it directly.
$QtCompatSitePackages = Join-Path $ProjectRoot ".qt315-compat-full\Lib\site-packages"
& $Python -c "import PySide6" 2>$null
if ($LASTEXITCODE -ne 0) {
    if (-not (Test-Path -LiteralPath (Join-Path $QtCompatSitePackages "PySide6"))) {
        throw "MoHan $Version packaging requires the rebuilt PySide6 6.11.1 Python 3.15 runtime; expected $QtCompatSitePackages."
    }
    $env:PYTHONPATH = if ($env:PYTHONPATH) {
        "$QtCompatSitePackages;$env:PYTHONPATH"
    } else {
        $QtCompatSitePackages
    }
}

# CPython 3.15's JIT is selected before interpreter initialization.  `-X jit`
# only records an xoption and does not enable sys._jit, so every build-time
# child must inherit the real startup switch.  The installed public launcher
# applies the same contract to the frozen runtime below.
$env:PYTHON_JIT = "1"

$PythonVersion = (& $Python -c "import platform; print(platform.python_version())").Trim()
if ($LASTEXITCODE -ne 0 -or $PythonVersion -ne "3.15.0rc1") {
    throw "MoHan $Version packages must be built with Python 3.15.0rc1; found $PythonVersion."
}
$JitContract = (& $Python -c "import sys; print(f'{sys._jit.is_available()}:{sys._jit.is_enabled()}')").Trim()
if ($LASTEXITCODE -ne 0 -or $JitContract -ne "True:True") {
    throw "MoHan $Version packages require a Python 3.15.0rc1 runtime built with JIT enabled by default; found $JitContract."
}

& $Python -c "import azure.cognitiveservices.speech, cryptography, cv2, numpy, opencc, sounddevice, websocket; import PySide6.QtCore, PySide6.QtGui, PySide6.QtMultimedia, PySide6.QtWidgets"
if ($LASTEXITCODE -ne 0) {
    throw "MoHan $Version packaging dependencies are incomplete; install requirements.txt and the rebuilt Python 3.15-compatible PySide6 runtime."
}
& $Python -c "import importlib.metadata as m; v=m.version('PySide6'); assert v.startswith('6.11.1+mohan.py315.'), v"
if ($LASTEXITCODE -ne 0) {
    throw "MoHan $Version packaging requires the studio-rebuilt PySide6 6.11.1+mohan.py315 runtime."
}

# Exercise the provider-neutral local speech path before packaging: synthetic
# non-empty TTS bytes must start the PCM sink, enter SPEAKING, and produce a
# non-zero mouth parameter.  The same audit also fails closed when sounddevice
# cannot resolve its bundled PortAudio binary.
& $Python -m tools.audit_speech_runtime_chain
if ($LASTEXITCODE -ne 0) {
    throw "MoHan $Version speech runtime chain or PortAudio dependency is incomplete."
}

# The 600 registered PoseAtlas layers must be semantically correct before any
# bootloader, native wheel, or PyInstaller work starts.  Geometry-only checks
# cannot detect a complete face stored in `ornament`, duplicated lips, empty
# teeth/tongue layers, or a detached mouth.  Preserve the deterministic JSON
# evidence even on failure, then stop the package build fail-closed.
$LayeredSemanticEvidenceDir = Join-Path `
    $ProjectRoot "docs\release-evidence\layered-full-body-semantic-audit"
$LayeredSemanticEvidence = Join-Path `
    $LayeredSemanticEvidenceDir "layered-full-body-semantic-audit.json"
New-Item -ItemType Directory -Force $LayeredSemanticEvidenceDir | Out-Null
& $Python -m tools.audit_layered_full_body_semantics `
    --json-output $LayeredSemanticEvidence
$LayeredSemanticAuditExitCode = $LASTEXITCODE
if ($LayeredSemanticAuditExitCode -ne 0) {
    throw "MoHan $Version layered full-body semantic audit blocked packaging with exit code $LayeredSemanticAuditExitCode. Evidence: $LayeredSemanticEvidence"
}

# Independently gate the 24 authoritative static views.  This catches identity
# and raster defects that layer naming cannot reveal: profile-forehead spikes,
# mirror/aspect drift, adjacent-yaw registration jumps, and green/cyan mouth
# pixels.  The report is retained for visual release evidence on every run.
$StaticIdentityEvidenceDir = Join-Path `
    $ProjectRoot "docs\release-evidence\pose-atlas-static-identity-audit"
$StaticIdentityEvidence = Join-Path `
    $StaticIdentityEvidenceDir "pose-atlas-static-identity-audit.json"
New-Item -ItemType Directory -Force $StaticIdentityEvidenceDir | Out-Null
& $Python -m tools.audit_pose_atlas_identity `
    --json-output $StaticIdentityEvidence
$StaticIdentityAuditExitCode = $LASTEXITCODE
if ($StaticIdentityAuditExitCode -ne 0) {
    throw "MoHan $Version static PoseAtlas identity audit blocked packaging with exit code $StaticIdentityAuditExitCode. Evidence: $StaticIdentityEvidence"
}

# Paired face controls must preserve the small, deterministic differences in
# the authored left/right eyelids, liners, irises, brows, mouth corners, and
# blush. Exact copies or exact mirrors produce an uncanny mechanical face even
# when every individual PNG is otherwise valid.
$FaceAsymmetryEvidenceDir = Join-Path `
    $ProjectRoot "docs\release-evidence\face-layer-asymmetry-audit"
$FaceAsymmetryEvidence = Join-Path `
    $FaceAsymmetryEvidenceDir "face-layer-asymmetry-audit.json"
New-Item -ItemType Directory -Force $FaceAsymmetryEvidenceDir | Out-Null
& $Python -m tools.audit_face_layer_asymmetry --json $FaceAsymmetryEvidence
$FaceAsymmetryAuditExitCode = $LASTEXITCODE
if ($FaceAsymmetryAuditExitCode -ne 0) {
    throw "MoHan $Version face-layer asymmetry audit blocked packaging with exit code $FaceAsymmetryAuditExitCode. Evidence: $FaceAsymmetryEvidence"
}

# Python 3.15 uses PyInitConfig (PEP 741).  The stock PyInstaller bootloader
# forces isolated mode and therefore discards PYTHON_JIT before CPython starts.
# Rebuild the pinned bootloader with the narrowly scoped MoHan environment
# contract; the public launcher removes every inherited PYTHON* variable and
# then supplies PYTHON_JIT=1 as the only Python startup setting.
& $Python tools/build_pyinstaller_jit_bootloader.py
if ($LASTEXITCODE -ne 0) {
    throw "MoHan $Version could not build the Python 3.15 JIT-aware PyInstaller bootloader."
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
    repository = "flameblade-studio/MoHan-PC-Desktop-Assistant"
    python = $PythonVersion
    jit_supported = $true
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
        --add-data "ASSETS-LICENSE.md;." `
        --add-data "THIRD_PARTY_NOTICES.md;." `
        --add-data "third_party_licenses;third_party_licenses" `
        --add-data "build-info.json;." `
        --add-data "$NativeEvidence;." `
        --add-binary "$Abi3tCompatibilityDll;." `
        --hidden-import "_mohan_accel" `
        --hidden-import "PySide6.QtCore" `
        --hidden-import "PySide6.QtGui" `
        --hidden-import "PySide6.QtMultimedia" `
        --hidden-import "PySide6.QtWidgets" `
        --hidden-import "azure.cognitiveservices.speech" `
        --hidden-import "cryptography" `
        --hidden-import "cv2" `
        --hidden-import "numpy" `
        --hidden-import "sounddevice" `
        --hidden-import "websocket" `
        --collect-all "azure.cognitiveservices.speech" `
        --collect-all "opencc" `
        --collect-all "sounddevice" `
        app.py
}
finally {
    Remove-Item -LiteralPath $BuildInfo -Force -ErrorAction SilentlyContinue
}
if ($LASTEXITCODE -ne 0) {
    throw "MoHan $Version main application PyInstaller build failed with exit code $LASTEXITCODE."
}

$PackageRoot = Join-Path $ProjectRoot "dist\$AppName-$Version"
$PublicExecutable = Join-Path $PackageRoot "$AppName-$Version.exe"
$RuntimeExecutable = Join-Path $PackageRoot "$AppName-$Version-runtime.exe"
Move-Item -LiteralPath $PublicExecutable -Destination $RuntimeExecutable -Force

# A separate non-JIT public launcher is required because the embedded runtime
# must see PYTHON_JIT=1 before CPython initializes.  The child runtime owns Qt;
# after Qt shutdown it terminates at finalize_process_exit(), avoiding the
# Python 3.15rc1 JIT/Qt interpreter-finalization heap corruption.
$LauncherBuild = Join-Path $ProjectRoot "build\jit-launcher-$Version"
$LauncherDist = Join-Path $ProjectRoot "dist\jit-launcher-$Version"
Remove-Item -LiteralPath $LauncherBuild, $LauncherDist -Recurse -Force -ErrorAction SilentlyContinue
$env:PYTHON_JIT = "0"
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
$env:PYTHON_JIT = "1"

& $Python tools/verify_packaged_native_acceleration.py `
    "dist\$AppName-$Version"
if ($LASTEXITCODE -ne 0) {
    throw "MoHan $Version packaged native verification failed."
}

Write-Host "Build complete: dist\$AppName-$Version\"
