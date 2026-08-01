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
$Harvest = Join-Path $WixWork "harvest.wxs"
& $Heat dir $ResolvedAppDir -cg AppFiles -dr INSTALLFOLDER -gg -sfrag -sreg -srd `
    -var var.SourceDir -out $Harvest
if ($LASTEXITCODE -ne 0) { throw "WiX harvesting failed" }
& $Candle -nologo `
    "-dSourceDir=$ResolvedAppDir" `
    "-dProductVersion=$NumericVersion" `
    "-dExecutableName=$ExecutableName" `
    "-dIconPath=$IconPath" `
    -out "$WixWork\" `
    (Join-Path $ProjectRoot "installer\Product.wxs") `
    $Harvest
if ($LASTEXITCODE -ne 0) { throw "WiX compilation failed" }
$Msi = Join-Path $ResolvedOutput "MoHan-Desktop-Assistant-$Tag-Windows-x64.msi"
& $Light -nologo -sice:ICE38 -sice:ICE64 `
    -out $Msi `
    (Join-Path $WixWork "Product.wixobj") `
    (Join-Path $WixWork "harvest.wixobj")
if ($LASTEXITCODE -ne 0) { throw "WiX linking failed" }

Get-Item (Join-Path $ResolvedOutput "*Setup.exe"), $Msi
