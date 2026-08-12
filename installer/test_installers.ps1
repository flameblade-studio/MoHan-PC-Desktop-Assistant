param(
    [Parameter(Mandatory = $true)][string]$ArtifactsDir,
    [Parameter(Mandatory = $true)][string]$Version
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
$ExeInstaller = Get-Item (Join-Path $ResolvedArtifacts "*Setup.exe")
$MsiInstaller = Get-Item (Join-Path $ResolvedArtifacts "*.msi")
$MsiTransforms = Get-ChildItem (Join-Path $ResolvedArtifacts "*.mst") |
    Sort-Object Name
$ExpectedTransformLocales = @("en-US", "ja-JP", "zh-CN")
$ProgramsFolder = [Environment]::GetFolderPath("Programs")
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
    $Variant = if ($null -eq $Transform) { "zh-TW" } else { $Transform.BaseName }
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
    if (-not [string]::Equals(
        $MsiShortcut.IconLocation,
        $ExpectedMsiIconLocation,
        [StringComparison]::OrdinalIgnoreCase
    )) {
        throw "MSI $Variant shortcut icon is not the installed MoHan icon"
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
