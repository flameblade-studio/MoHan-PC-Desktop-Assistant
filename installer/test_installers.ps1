param(
    [Parameter(Mandatory = $true)][string]$ArtifactsDir,
    [Parameter(Mandatory = $true)][string]$Version,
    [Parameter(Mandatory = $true)][string]$Python,
    [Parameter(Mandatory = $true)][string]$NativeEvidenceDir,
    [string]$PreviousVersion,
    [string]$PreviousExeUrl,
    [string]$PreviousExeSha256,
    [string]$PreviousMsiUrl,
    [string]$PreviousMsiSha256,
    [switch]$RequirePoseAtlas
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
$PreviousUpgradeArguments = @(
    $PreviousVersion,
    $PreviousExeUrl,
    $PreviousExeSha256,
    $PreviousMsiUrl,
    $PreviousMsiSha256
)
$HasPreviousUpgrade = @($PreviousUpgradeArguments | Where-Object {
    -not [string]::IsNullOrWhiteSpace($_)
}).Count -gt 0
if ($HasPreviousUpgrade -and @($PreviousUpgradeArguments | Where-Object {
    [string]::IsNullOrWhiteSpace($_)
}).Count -gt 0) {
    throw "Previous-version upgrade verification requires every version, URL, and SHA-256 argument"
}

function Get-VerifiedPreviousInstaller {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][string]$Sha256,
        [Parameter(Mandatory = $true)][string]$Destination
    )
    Invoke-WebRequest -Uri $Url -OutFile $Destination
    $Actual = (Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash
    if (-not [string]::Equals($Actual, $Sha256, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Previous installer SHA-256 mismatch: $Destination"
    }
    return $Destination
}

$UpgradeEvidence = [ordered]@{
    schema = "mohan.installer-upgrade-evidence.v1"
    passed = $false
    previous_version = $PreviousVersion
    target_version = $Version
    exe = $false
    msi = $false
}
if ($HasPreviousUpgrade) {
    $PreviousRoot = Join-Path $env:RUNNER_TEMP "mohan-previous-$PreviousVersion"
    New-Item -ItemType Directory -Force $PreviousRoot | Out-Null
    $PreviousExeInstaller = Get-VerifiedPreviousInstaller `
        -Url $PreviousExeUrl `
        -Sha256 $PreviousExeSha256 `
        -Destination (Join-Path $PreviousRoot "MoHan-$PreviousVersion-Setup.exe")
    $PreviousMsiInstaller = Get-VerifiedPreviousInstaller `
        -Url $PreviousMsiUrl `
        -Sha256 $PreviousMsiSha256 `
        -Destination (Join-Path $PreviousRoot "MoHan-$PreviousVersion.msi")
}

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

function Assert-PackagedPoseAtlas {
    param([Parameter(Mandatory = $true)][string]$PackageRoot)
    if (-not $RequirePoseAtlas) { return }
    $Audit = Join-Path $PackageRoot "_internal\assets\pose-atlas\v4\release-audits.json"
    if (-not (Test-Path -LiteralPath $Audit)) {
        throw "Installer omitted audited PoseAtlas v4 assets"
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

$PreviousExePath = $null
if ($HasPreviousUpgrade) {
    $Process = Start-Process $PreviousExeInstaller -ArgumentList @(
        "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
        "/MERGETASKS=!desktopicon", "/DIR=$ExeInstallDir"
    ) -Wait -PassThru
    if ($Process.ExitCode -ne 0) { throw "Previous EXE installer failed" }
    $PreviousExePath = Join-Path $ExeInstallDir (
        "MoHan-Desktop-Assistant-$PreviousVersion.exe"
    )
    if (-not (Test-Path -LiteralPath $PreviousExePath)) {
        throw "Previous EXE installer did not install the expected application"
    }
}
$Process = Start-Process $ExeInstaller.FullName -ArgumentList @(
    "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
    "/MERGETASKS=!desktopicon", "/DIR=$ExeInstallDir"
) -Wait -PassThru
if ($Process.ExitCode -ne 0) { throw "EXE installer failed" }
$InstalledExe = Join-Path $ExeInstallDir "MoHan-Desktop-Assistant-$Version.exe"
if ($HasPreviousUpgrade) {
    if (-not (Test-Path -LiteralPath $InstalledExe)) {
        throw "EXE in-place upgrade did not install the target application"
    }
    if (Test-Path -LiteralPath $PreviousExePath) {
        throw "EXE in-place upgrade left the previous application executable behind"
    }
    $UpgradeEvidence.exe = $true
}
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
Assert-PackagedPoseAtlas -PackageRoot $ExeInstallDir
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
    $PreviousMsiPath = $null
    if ($HasPreviousUpgrade -and $Variant -eq "zh-TW") {
        $PreviousMsiArguments = @(
            "/i", $PreviousMsiInstaller, "/qn", "/norestart",
            "INSTALLFOLDER=$MsiInstallDir"
        )
        $Process = Start-Process msiexec.exe -ArgumentList $PreviousMsiArguments `
            -Wait -PassThru
        if ($Process.ExitCode -ne 0) {
            throw "Previous MSI installer failed: $($Process.ExitCode)"
        }
        $PreviousMsiPath = Join-Path $MsiInstallDir (
            "MoHan-Desktop-Assistant-$PreviousVersion.exe"
        )
        if (-not (Test-Path -LiteralPath $PreviousMsiPath)) {
            throw "Previous MSI installer did not install the expected application"
        }
    }
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
    if ($HasPreviousUpgrade -and $Variant -eq "zh-TW") {
        if (Test-Path -LiteralPath $PreviousMsiPath) {
            throw "MSI in-place upgrade left the previous application executable behind"
        }
        $UpgradeEvidence.msi = $true
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
    Assert-PackagedPoseAtlas -PackageRoot $MsiInstallDir
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

if ($HasPreviousUpgrade) {
    if (-not ($UpgradeEvidence.exe -and $UpgradeEvidence.msi)) {
        throw "Installer upgrade evidence is incomplete"
    }
    $UpgradeEvidence.passed = $true
    $UpgradeEvidence | ConvertTo-Json | Set-Content `
        -LiteralPath (Join-Path $ResolvedNativeEvidence "installer-upgrade.json") `
        -Encoding utf8
}

"INSTALLER_EXE_AND_4_LANGUAGE_MSI_OK"
