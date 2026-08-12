param(
    [string]$InnoVersion = "7.0.2",
    [string]$WixVersion = "7.0.0"
)

$ErrorActionPreference = "Stop"

if (-not $env:RUNNER_TEMP) {
    throw "RUNNER_TEMP is required so packaging tools stay isolated."
}
if ($env:GITHUB_ACTIONS -eq "true" -and -not $env:GH_TOKEN) {
    throw "GH_TOKEN is required for release attestation verification in Actions."
}

$InnoTag = "is-" + ($InnoVersion -replace '\.', '_')
$InnoAsset = "innosetup-$InnoVersion-x64.exe"
$InnoDownload = Join-Path $env:RUNNER_TEMP $InnoAsset
$InnoInstallDir = Join-Path $env:RUNNER_TEMP "inno-setup-$InnoVersion"

gh release download $InnoTag `
    --repo jrsoftware/issrc `
    --pattern $InnoAsset `
    --dir $env:RUNNER_TEMP `
    --clobber
if ($LASTEXITCODE -ne 0) { throw "Official Inno Setup download failed" }

gh release verify-asset $InnoTag $InnoDownload --repo jrsoftware/issrc
if ($LASTEXITCODE -ne 0) {
    throw "Official Inno Setup release attestation verification failed"
}

$Signature = Get-AuthenticodeSignature -FilePath $InnoDownload
if (
    $Signature.Status -ne "Valid" -or
    $Signature.SignerCertificate.Subject -notmatch 'Pyrsys B\.V\.'
) {
    throw "Official Inno Setup Authenticode verification failed"
}

$Install = Start-Process -FilePath $InnoDownload -ArgumentList @(
    "/VERYSILENT",
    "/SUPPRESSMSGBOXES",
    "/NORESTART",
    "/CURRENTUSER",
    "/DIR=$InnoInstallDir"
) -WindowStyle Hidden -Wait -PassThru
if ($Install.ExitCode -ne 0) {
    throw "Inno Setup $InnoVersion installation failed"
}
$Iscc = Join-Path $InnoInstallDir "ISCC.exe"
if (-not (Test-Path -LiteralPath $Iscc)) {
    throw "Inno Setup compiler was not installed at $Iscc"
}
$InnoVersionProbe = Join-Path $InnoInstallDir "unins000.exe"
if (-not (Test-Path -LiteralPath $InnoVersionProbe)) {
    throw "Inno Setup version probe was not installed at $InnoVersionProbe"
}
$InstalledInnoVersion = (
    Get-Item -LiteralPath $InnoVersionProbe
).VersionInfo.ProductVersion.Trim()
if ($InstalledInnoVersion -notmatch ('^' + [regex]::Escape($InnoVersion) + '(?:\.|$)')) {
    throw "Inno Setup version mismatch: $InstalledInnoVersion"
}

$Wix = Join-Path $env:USERPROFILE ".dotnet\tools\wix.exe"
if (Test-Path -LiteralPath $Wix) {
    dotnet tool update --global wix --version $WixVersion
} else {
    dotnet tool install --global wix --version $WixVersion
}
if ($LASTEXITCODE -ne 0) { throw "WiX Toolset installation failed" }
$InstalledWixVersion = (& $Wix --version).Trim()
if ($InstalledWixVersion -notmatch ('^' + [regex]::Escape($WixVersion) + '(?:\+|$)')) {
    throw "WiX Toolset version mismatch: $InstalledWixVersion"
}

$env:MOHAN_ISCC_PATH = $Iscc
$env:MOHAN_WIX_PATH = $Wix
if ($env:GITHUB_ENV) {
    "MOHAN_ISCC_PATH=$Iscc" | Out-File `
        -FilePath $env:GITHUB_ENV -Encoding utf8 -Append
    "MOHAN_WIX_PATH=$Wix" | Out-File `
        -FilePath $env:GITHUB_ENV -Encoding utf8 -Append
}
if ($env:GITHUB_PATH) {
    (Split-Path -Parent $Wix) | Out-File `
        -FilePath $env:GITHUB_PATH -Encoding utf8 -Append
}

Write-Host "WINDOWS_PACKAGING_TOOLS_OK Inno=$InstalledInnoVersion WiX=$InstalledWixVersion"
