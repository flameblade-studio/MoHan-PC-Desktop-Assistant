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
if (-not (Test-Path (Join-Path $ResolvedAppDir $ExecutableName))) {
    throw "Packaged executable was not found in $ResolvedAppDir"
}
New-Item -ItemType Directory -Force $ResolvedOutput | Out-Null

$Iscc = Get-ChildItem "C:\Program Files*\Inno Setup *\ISCC.exe" |
    Sort-Object FullName -Descending |
    Select-Object -First 1
if (-not $Iscc) { throw "Inno Setup compiler was not found" }
& $Iscc.FullName (Join-Path $ProjectRoot "installer\mohan.iss") `
    "/DMyVersion=$Version" `
    "/DSourceDir=$ResolvedAppDir" `
    "/DExecutableName=$ExecutableName" `
    "/DOutputDir=$ResolvedOutput" `
    "/DIconPath=$IconPath"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup build failed" }

$NumericVersion = (($Version -split '-', 2)[0] -split '\.')[0..2] -join '.'
$WixBin = Get-ChildItem "C:\Program Files (x86)\WiX Toolset v3*\bin" -Directory |
    Sort-Object FullName -Descending |
    Select-Object -First 1
if (-not $WixBin) { throw "WiX Toolset v3 was not found" }
$WixWork = Join-Path $env:RUNNER_TEMP "mohan-wix-$Version"
New-Item -ItemType Directory -Force $WixWork | Out-Null
$Heat = Join-Path $WixBin.FullName "heat.exe"
$Candle = Join-Path $WixBin.FullName "candle.exe"
$Light = Join-Path $WixBin.FullName "light.exe"
$Torch = Join-Path $WixBin.FullName "torch.exe"
$Harvest = Join-Path $WixWork "harvest.wxs"
& $Heat dir $ResolvedAppDir -cg AppFiles -dr INSTALLFOLDER -gg -sfrag -sreg -srd `
    -var var.SourceDir -out $Harvest
if ($LASTEXITCODE -ne 0) { throw "WiX harvesting failed" }
& $Candle -nologo "-dSourceDir=$ResolvedAppDir" `
    -out (Join-Path $WixWork "harvest.wixobj") $Harvest
if ($LASTEXITCODE -ne 0) { throw "WiX harvesting compilation failed" }

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
    & $Candle -nologo `
        "-dSourceDir=$ResolvedAppDir" `
        "-dProductVersion=$NumericVersion" `
        "-dExecutableName=$ExecutableName" `
        "-dIconPath=$IconPath" `
        "-dProductCode=$ProductCode" `
        "-dProductLanguage=$($Locale.Language)" `
        "-dProductCodepage=$($Locale.Codepage)" `
        -out "$LocaleWork\" `
        (Join-Path $ProjectRoot "installer\Product.wxs")
    if ($LASTEXITCODE -ne 0) {
        throw "WiX $($Locale.Name) product compilation failed"
    }
    $LocaleMsi = Join-Path $LocaleWork "MoHan-$($Locale.Name).msi"
    & $Light -nologo -sice:ICE38 -sice:ICE64 `
        -loc (Join-Path $ProjectRoot "installer\localization\$($Locale.Name).wxl") `
        -out $LocaleMsi `
        (Join-Path $LocaleWork "Product.wixobj") `
        (Join-Path $WixWork "harvest.wixobj")
    if ($LASTEXITCODE -ne 0) {
        throw "WiX $($Locale.Name) linking failed"
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
    & $Torch -nologo -p -t language `
        $LocalizedMsi["zh-TW"] `
        $LocalizedMsi[$Locale.Name] `
        -out $Transform
    if ($LASTEXITCODE -ne 0) {
        throw "WiX $($Locale.Name) transform generation failed"
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
