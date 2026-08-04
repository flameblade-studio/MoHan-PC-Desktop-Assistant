param(
    [Parameter(Mandatory = $true)][string]$ArtifactsDir,
    [Parameter(Mandatory = $true)][string]$Version
)

$ErrorActionPreference = "Stop"
$ResolvedArtifacts = (Resolve-Path $ArtifactsDir).Path
$ExeInstaller = Get-Item (Join-Path $ResolvedArtifacts "*Setup.exe")
$MsiInstaller = Get-Item (Join-Path $ResolvedArtifacts "*.msi")
$MsiTransforms = Get-ChildItem (Join-Path $ResolvedArtifacts "*.mst") |
    Sort-Object Name
$ExpectedTransformLocales = @("en-US", "ja-JP", "zh-CN")
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
    "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/DIR=$ExeInstallDir"
) -Wait -PassThru
if ($Process.ExitCode -ne 0) { throw "EXE installer failed" }
$InstalledExe = Join-Path $ExeInstallDir "MoHan-Desktop-Assistant-$Version.exe"
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
$Uninstaller = Join-Path $ExeInstallDir "unins000.exe"
$Process = Start-Process $Uninstaller -ArgumentList @(
    "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"
) -Wait -PassThru
if ($Process.ExitCode -ne 0) { throw "EXE uninstall verification failed" }

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
}

"INSTALLER_EXE_AND_4_LANGUAGE_MSI_OK"
