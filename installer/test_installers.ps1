param(
    [Parameter(Mandatory = $true)][string]$ArtifactsDir,
    [Parameter(Mandatory = $true)][string]$Version
)

$ErrorActionPreference = "Stop"
$ResolvedArtifacts = (Resolve-Path $ArtifactsDir).Path
$ExeInstaller = Get-Item (Join-Path $ResolvedArtifacts "*Setup.exe")
$MsiInstaller = Get-Item (Join-Path $ResolvedArtifacts "*.msi")
$ExeInstallDir = Join-Path $env:RUNNER_TEMP "mohan-exe-install"
$MsiInstallDir = Join-Path $env:RUNNER_TEMP "mohan-msi-install"
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

$Process = Start-Process msiexec.exe -ArgumentList @(
    "/i", $MsiInstaller.FullName, "/qn", "/norestart", "INSTALLFOLDER=$MsiInstallDir"
) -Wait -PassThru
if ($Process.ExitCode -ne 0) {
    throw "MSI installer failed: $($Process.ExitCode)"
}
$InstalledMsiExe = Join-Path $MsiInstallDir "MoHan-Desktop-Assistant-$Version.exe"
if (-not (Test-Path $InstalledMsiExe)) {
    throw "MSI did not install the application"
}
$Process = Start-Process msiexec.exe -ArgumentList @(
    "/x", $MsiInstaller.FullName, "/qn", "/norestart"
) -Wait -PassThru
if ($Process.ExitCode -ne 0) { throw "MSI uninstall verification failed" }

"INSTALLER_EXE_AND_MSI_OK"
