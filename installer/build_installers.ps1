param(
    [Parameter(Mandatory = $true)][string]$AppDir,
    [Parameter(Mandatory = $true)][string]$Version,
    [Parameter(Mandatory = $true)][string]$Tag,
    [Parameter(Mandatory = $true)][string]$OutputDir
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ResolvedAppDir = (Resolve-Path $AppDir).Path
$ResolvedOutput = [IO.Path]::GetFullPath($OutputDir)
$IconPath = Join-Path $ProjectRoot "assets\mohan-halfbody.ico"
$ExecutableName = "MoHan-Desktop-Assistant-$Version.exe"
# PyInstaller 6.21 places onedir support files under _internal.
$BundledFonts = Join-Path $ResolvedAppDir "_internal\assets\fonts"
$RequiredFontFiles = @(
    (Join-Path $BundledFonts "LXGW-WenKai-TC\LXGWWenKaiTC-Regular.ttf"),
    (Join-Path $BundledFonts "LXGW-WenKai-TC\OFL.txt"),
    (Join-Path $BundledFonts "Cinzel\Cinzel[wght].ttf"),
    (Join-Path $BundledFonts "Cinzel\OFL.txt")
)
foreach ($RequiredFontFile in $RequiredFontFiles) {
    if (-not (Test-Path -LiteralPath $RequiredFontFile -PathType Leaf)) {
        throw "Bundled font file is missing from the installer source: $RequiredFontFile"
    }
}
if (-not (Test-Path (Join-Path $ResolvedAppDir $ExecutableName))) {
    throw "Packaged executable was not found in $ResolvedAppDir"
}
New-Item -ItemType Directory -Force $ResolvedOutput | Out-Null

$Iscc = $null
if ($env:MOHAN_ISCC_PATH -and (Test-Path -LiteralPath $env:MOHAN_ISCC_PATH)) {
    $Iscc = Get-Item -LiteralPath $env:MOHAN_ISCC_PATH
}
if (-not $Iscc) {
    $Iscc = Get-ChildItem "C:\Program Files*\Inno Setup *\ISCC.exe" |
        Sort-Object FullName -Descending |
        Select-Object -First 1
}
if (-not $Iscc) { throw "Inno Setup 7.0.2 compiler was not found" }
$InnoVersionProbe = Join-Path $Iscc.DirectoryName "unins000.exe"
if (-not (Test-Path -LiteralPath $InnoVersionProbe)) {
    throw "Inno Setup version probe was not found at $InnoVersionProbe"
}
$IsccVersion = (
    Get-Item -LiteralPath $InnoVersionProbe
).VersionInfo.ProductVersion.Trim()
if ($IsccVersion -notmatch '^7\.0\.2(?:\.|$)') {
    throw "MoHan installers require Inno Setup 7.0.2; found $IsccVersion"
}
& $Iscc.FullName (Join-Path $ProjectRoot "installer\mohan.iss") `
    "/DMyVersion=$Version" `
    "/DSourceDir=$ResolvedAppDir" `
    "/DExecutableName=$ExecutableName" `
    "/DOutputDir=$ResolvedOutput" `
    "/DIconPath=$IconPath"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup build failed" }

$NumericVersion = (($Version -split '-', 2)[0] -split '\.')[0..2] -join '.'
$WixCommand = $null
if ($env:MOHAN_WIX_PATH -and (Test-Path -LiteralPath $env:MOHAN_WIX_PATH)) {
    $WixCommand = Get-Item -LiteralPath $env:MOHAN_WIX_PATH
}
if (-not $WixCommand) {
    $WixCommand = Get-Command wix.exe -ErrorAction SilentlyContinue
}
if (-not $WixCommand) {
    $DotnetWix = Join-Path $env:USERPROFILE ".dotnet\tools\wix.exe"
    if (Test-Path -LiteralPath $DotnetWix) {
        $WixCommand = Get-Item -LiteralPath $DotnetWix
    }
}
if (-not $WixCommand) {
    throw "WiX Toolset v7.0.0 was not found. Install it with: dotnet tool install --global wix --version 7.0.0"
}
$Wix = $WixCommand.Source
if (-not $Wix) { $Wix = $WixCommand.FullName }
$WixVersion = (& $Wix --version).Trim()
if ($LASTEXITCODE -ne 0 -or $WixVersion -notmatch '^7\.0\.0(?:\+|$)') {
    throw "MoHan installers require WiX Toolset v7.0.0; found $WixVersion"
}
$WixWork = Join-Path $env:RUNNER_TEMP "mohan-wix-$Version"
New-Item -ItemType Directory -Force $WixWork | Out-Null

$ProductCode = "{" + ([guid]::NewGuid()).ToString().ToUpperInvariant() + "}"
$Locales = @(
    @{
        Name = "zh-TW"
        Language = "1028"
        Codepage = "950"
        Base = $true
    },
    @{
        Name = "en-US"
        Language = "1033"
        Codepage = "1252"
        Base = $false
    },
    @{
        Name = "zh-CN"
        Language = "2052"
        Codepage = "936"
        Base = $false
    },
    @{
        Name = "ja-JP"
        Language = "1041"
        Codepage = "932"
        Base = $false
    }
)
$LocalizedMsi = @{}
foreach ($Locale in $Locales) {
    $LocaleWork = Join-Path $WixWork $Locale.Name
    New-Item -ItemType Directory -Force $LocaleWork | Out-Null
    $LocaleMsi = Join-Path $LocaleWork "MoHan-$($Locale.Name).msi"
    & $Wix build `
        -acceptEula wix7 `
        -nologo `
        -arch x64 `
        -d "SourceDir=$ResolvedAppDir" `
        -d "ProductVersion=$NumericVersion" `
        -d "ExecutableName=$ExecutableName" `
        -d "IconPath=$IconPath" `
        -d "ProductCode=$ProductCode" `
        -d "ProductLanguage=$($Locale.Language)" `
        -d "ProductCodepage=$($Locale.Codepage)" `
        -loc (Join-Path $ProjectRoot "installer\localization\$($Locale.Name).wxl") `
        -intermediateFolder $LocaleWork `
        -out $LocaleMsi `
        (Join-Path $ProjectRoot "installer\Product.wxs")
    if ($LASTEXITCODE -ne 0) {
        throw "WiX v7 $($Locale.Name) build failed"
    }
    & $Wix msi validate `
        -acceptEula wix7 `
        -sice ICE38 `
        -sice ICE64 `
        -sice ICE91 `
        $LocaleMsi
    if ($LASTEXITCODE -ne 0) {
        throw "WiX v7 $($Locale.Name) validation failed"
    }
    $LocalizedMsi[$Locale.Name] = $LocaleMsi
}

$Msi = Join-Path $ResolvedOutput "MoHan-Desktop-Assistant-$Tag-Windows-x64.msi"
Copy-Item $LocalizedMsi["zh-TW"] $Msi -Force
$Transforms = @()
foreach ($Locale in $Locales | Where-Object { -not $_.Base }) {
    $Transform = Join-Path $ResolvedOutput (
        "MoHan-Desktop-Assistant-$Tag-$($Locale.Name).mst"
    )
    & $Wix msi transform `
        -acceptEula wix7 `
        -p `
        -t language `
        $LocalizedMsi["zh-TW"] `
        $LocalizedMsi[$Locale.Name] `
        -out $Transform
    if ($LASTEXITCODE -ne 0) {
        throw "WiX v7 $($Locale.Name) transform generation failed"
    }
    $Transforms += $Transform
}

$BuiltArtifacts = @(
    Get-Item (Join-Path $ResolvedOutput "*Setup.exe")
    Get-Item $Msi
    foreach ($Transform in $Transforms) {
        Get-Item $Transform
    }
)
$BuiltArtifacts
