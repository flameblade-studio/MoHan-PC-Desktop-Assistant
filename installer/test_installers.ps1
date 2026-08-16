param(
    [Parameter(Mandatory = $true)][string]$ArtifactsDir,
    [Parameter(Mandatory = $true)][string]$Version,
    [Parameter(Mandatory = $true)][string]$Python,
    [Parameter(Mandatory = $true)][string]$NativeEvidenceDir
)

$ErrorActionPreference = "Stop"
if (
    $env:GITHUB_ACTIONS -ne "true" -and
    $env:MOHAN_ALLOW_INSTALLER_MUTATION -ne "1"
) {
    throw (
        "Installer integration tests modify per-user installation state. " +
        "Run them on GitHub Actions or set MOHAN_ALLOW_INSTALLER_MUTATION=1 " +
        "only inside a disposable Windows account or virtual machine."
    )
}
$ResolvedArtifacts = (Resolve-Path $ArtifactsDir).Path
$ResolvedNativeEvidence = [IO.Path]::GetFullPath($NativeEvidenceDir)
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$NativeVerifier = Join-Path $ProjectRoot (
    "tools\verify_packaged_native_acceleration.py"
)
New-Item -ItemType Directory -Force $ResolvedNativeEvidence | Out-Null
$ExeInstaller = Get-Item (Join-Path $ResolvedArtifacts "*Setup.exe")
$MsiInstaller = Get-Item (Join-Path $ResolvedArtifacts "*.msi")
$MsiTransforms = Get-ChildItem (Join-Path $ResolvedArtifacts "*.mst") |
    Sort-Object Name
$ExpectedTransformLocales = @("en-US", "ja-JP", "zh-CN")
$ProgramsFolder = [Environment]::GetFolderPath("Programs")
$ExpectedNativeLabels = @(
    "exe",
    "msi-zh-TW",
    "msi-en-US",
    "msi-zh-CN",
    "msi-ja-JP"
)

function Invoke-NativeVerification {
    param(
        [Parameter(Mandatory = $true)][string]$PackageRoot,
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][array]$Artifacts
    )
    if ($Label -notin $ExpectedNativeLabels) {
        throw "Unexpected native installer verification label: $Label"
    }
    $Arguments = @(
        $NativeVerifier,
        $PackageRoot,
        "--label", $Label,
        "--output", (Join-Path $ResolvedNativeEvidence "$Label.json")
    )
    foreach ($Artifact in $Artifacts) {
        $Arguments += @("--artifact", $Artifact)
    }
    & $Python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Label strict native acceleration verification failed"
    }
}

foreach ($Locale in $ExpectedTransformLocales) {
    if (-not ($MsiTransforms.Name -match "-$Locale\.mst$")) {
        throw "Missing MSI language transform: $Locale"
    }
}
if ($MsiTransforms.Count -ne $ExpectedTransformLocales.Count) {
    throw "Unexpected MSI language-transform count: $($MsiTransforms.Count)"
}
$ExeInstallDir = Join-Path $env:RUNNER_TEMP "mohan-exe-install"
$env:MOHAN_DATA_DIR = Join-Path $env:RUNNER_TEMP "mohan-installer-profile"
New-Item -ItemType Directory -Force $env:MOHAN_DATA_DIR | Out-Null

$Process = Start-Process $ExeInstaller.FullName -ArgumentList @(
    "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
    "/MERGETASKS=!desktopicon", "/DIR=$ExeInstallDir"
) -Wait -PassThru
if ($Process.ExitCode -ne 0) { throw "EXE installer failed" }
$InstalledExe = Join-Path $ExeInstallDir "MoHan-Desktop-Assistant-$Version.exe"
foreach ($Notice in @("LICENSE", "THIRD_PARTY_NOTICES.md")) {
    if (-not (Test-Path (Join-Path $ExeInstallDir "_internal\$Notice"))) {
        throw "EXE installer omitted required distribution notice: $Notice"
    }
}
$SelfTest = Join-Path $env:RUNNER_TEMP "mohan-exe-installer-selftest.txt"
$Process = Start-Process $InstalledExe -ArgumentList @(
    "--self-test", "--self-test-output=$SelfTest"
) -Wait -PassThru
if (
    $Process.ExitCode -ne 0 -or
    (Get-Content -Raw $SelfTest) -ne "PACKAGED_SELFTEST_OK"
) {
    throw "EXE-installed application self-test failed"
}
Invoke-NativeVerification `
    -PackageRoot $ExeInstallDir `
    -Label "exe" `
    -Artifacts @($ExeInstaller.FullName)
$ExeShortcutPath = Join-Path $ProgramsFolder "MoHan Desktop Assistant.lnk"
if (-not (Test-Path -LiteralPath $ExeShortcutPath)) {
    throw "EXE installer did not create the Start menu shortcut"
}
$ExeShortcut = (New-Object -ComObject WScript.Shell).CreateShortcut(
    $ExeShortcutPath
)
$ExpectedIconLocation = $InstalledExe + ",0"
if (-not [string]::Equals(
    $ExeShortcut.TargetPath,
    $InstalledExe,
    [StringComparison]::OrdinalIgnoreCase
)) {
    throw "EXE shortcut target escaped the installed application directory"
}
if (-not [string]::Equals(
    $ExeShortcut.IconLocation,
    $ExpectedIconLocation,
    [StringComparison]::OrdinalIgnoreCase
)) {
    throw "EXE shortcut icon does not use the installed MoHan half-body icon"
}
$Uninstaller = Join-Path $ExeInstallDir "unins000.exe"
$Process = Start-Process $Uninstaller -ArgumentList @(
    "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"
) -Wait -PassThru
if ($Process.ExitCode -ne 0) { throw "EXE uninstall verification failed" }
if (Test-Path -LiteralPath $ExeShortcutPath) {
    throw "EXE uninstaller left the Start menu shortcut behind"
}

$MsiVariants = @($null) + @($MsiTransforms)
foreach ($Transform in $MsiVariants) {
    $Variant = if ($null -eq $Transform) {
        "zh-TW"
    }
    else {
        $ExpectedTransformLocales |
            Where-Object { $Transform.Name -match "-$_\.mst$" } |
            Select-Object -First 1
    }
    if (-not $Variant) { throw "Could not identify MSI transform locale" }
    $MsiInstallDir = Join-Path $env:RUNNER_TEMP "mohan-msi-install-$Variant"
    $InstallArguments = @(
        "/i", $MsiInstaller.FullName, "/qn", "/norestart",
        "INSTALLFOLDER=$MsiInstallDir"
    )
    if ($null -ne $Transform) {
        $InstallArguments += "TRANSFORMS=$($Transform.FullName)"
    }
    $Process = Start-Process msiexec.exe -ArgumentList $InstallArguments `
        -Wait -PassThru
    if ($Process.ExitCode -ne 0) {
        throw "MSI $Variant installer failed: $($Process.ExitCode)"
    }
    $InstalledMsiExe = Join-Path $MsiInstallDir (
        "MoHan-Desktop-Assistant-$Version.exe"
    )
    if (-not (Test-Path $InstalledMsiExe)) {
        throw "MSI $Variant did not install the application"
    }
    foreach ($Notice in @("LICENSE", "THIRD_PARTY_NOTICES.md")) {
        if (-not (Test-Path (Join-Path $MsiInstallDir "_internal\$Notice"))) {
            throw "MSI $Variant omitted required distribution notice: $Notice"
        }
    }
    $SelfTest = Join-Path $env:RUNNER_TEMP "mohan-msi-$Variant-selftest.txt"
    $Process = Start-Process $InstalledMsiExe -ArgumentList @(
        "--self-test", "--self-test-output=$SelfTest"
    ) -Wait -PassThru
    if (
        $Process.ExitCode -ne 0 -or
        (Get-Content -Raw $SelfTest) -ne "PACKAGED_SELFTEST_OK"
    ) {
        throw "MSI $Variant application self-test failed"
    }
    $NativeArtifacts = @($MsiInstaller.FullName)
    if ($null -ne $Transform) {
        $NativeArtifacts += $Transform.FullName
    }
    Invoke-NativeVerification `
        -PackageRoot $MsiInstallDir `
        -Label "msi-$Variant" `
        -Artifacts $NativeArtifacts
    $MsiShortcutPath = Join-Path $ProgramsFolder (
        "MoHan Desktop Assistant\MoHan Desktop Assistant.lnk"
    )
    if (-not (Test-Path -LiteralPath $MsiShortcutPath)) {
        throw "MSI $Variant did not create the Start menu shortcut"
    }
    $MsiShortcut = (New-Object -ComObject WScript.Shell).CreateShortcut(
        $MsiShortcutPath
    )
    $ExpectedMsiIconLocation = $InstalledMsiExe + ",0"
    if (-not [string]::Equals(
        $MsiShortcut.TargetPath,
        $InstalledMsiExe,
        [StringComparison]::OrdinalIgnoreCase
    )) {
        throw "MSI $Variant shortcut target escaped the install directory"
    }
    $ShortcutBytes = [IO.File]::ReadAllBytes($MsiShortcutPath)
    [uint32]$ShellLinkHeaderSize = 0x0000004C
    if (
        $ShortcutBytes.Length -lt $ShellLinkHeaderSize -or
        [BitConverter]::ToUInt32($ShortcutBytes, 0) -ne $ShellLinkHeaderSize
    ) {
        throw "MSI $Variant shortcut has an invalid Shell Link header"
    }
    [uint32]$LinkFlags = [BitConverter]::ToUInt32($ShortcutBytes, 20)
    [uint32]$HasIconLocationFlag = 0x00000040
    if (($LinkFlags -band $HasIconLocationFlag) -ne 0) {
        throw "MSI $Variant shortcut contains an independent icon location"
    }
    $ReportedIconLocation = ([string]$MsiShortcut.IconLocation).Trim()
    $IconLocationIsAllowed = (
        [string]::IsNullOrEmpty($ReportedIconLocation) -or
        [string]::Equals(
            $ReportedIconLocation,
            ",0",
            [StringComparison]::Ordinal
        ) -or
        [string]::Equals(
            $ReportedIconLocation,
            $ExpectedMsiIconLocation,
            [StringComparison]::OrdinalIgnoreCase
        )
    )
    if (-not $IconLocationIsAllowed) {
        throw "MSI $Variant shortcut icon escaped the installed MoHan executable"
    }
    $UninstallArguments = @(
        "/x", $MsiInstaller.FullName, "/qn", "/norestart"
    )
    if ($null -ne $Transform) {
        $UninstallArguments += "TRANSFORMS=$($Transform.FullName)"
    }
    $Process = Start-Process msiexec.exe -ArgumentList $UninstallArguments `
        -Wait -PassThru
    if ($Process.ExitCode -ne 0) {
        throw "MSI $Variant uninstall verification failed"
    }
    if (Test-Path -LiteralPath $MsiShortcutPath) {
        throw "MSI $Variant uninstaller left the Start menu shortcut behind"
    }
}

"INSTALLER_EXE_AND_4_LANGUAGE_MSI_OK"
