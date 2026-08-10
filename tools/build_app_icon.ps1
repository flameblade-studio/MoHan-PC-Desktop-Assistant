param(
    [string]$Magick = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Source = Join-Path $ProjectRoot "assets\expressions\idle_front.png"
$PngOutput = Join-Path $ProjectRoot "assets\mohan-taskbar-icon.png"
$IcoOutput = Join-Path $ProjectRoot "assets\mohan-halfbody.ico"

if (-not (Test-Path -LiteralPath $Source)) {
    throw "Canonical MoHan half-body source was not found: $Source"
}
if (-not $Magick) {
    $Command = Get-Command magick.exe -ErrorAction SilentlyContinue
    if (-not $Command) {
        $Command = Get-Command magick -ErrorAction SilentlyContinue
    }
    if ($Command) {
        $Magick = $Command.Source
    }
}
if (-not $Magick -or -not (Test-Path -LiteralPath $Magick)) {
    throw "ImageMagick 7 was not found. Pass its magick executable with -Magick."
}

$TemporaryRoot = Join-Path (
    [IO.Path]::GetTempPath()
) ("mohan-app-icon-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $TemporaryRoot | Out-Null
$Background = Join-Path $TemporaryRoot "background.png"
$Character = Join-Path $TemporaryRoot "character.png"

try {
    & $Magick -size 1024x1024 xc:none `
        -fill "#E8F1F8" -stroke "#6F88A5" -strokewidth 24 `
        -draw "roundrectangle 24,24 1000,1000 180,180" `
        $Background
    if ($LASTEXITCODE -ne 0) { throw "Could not render the app-icon background" }

    & $Magick $Source -trim +repage -resize 920x920 $Character
    if ($LASTEXITCODE -ne 0) { throw "Could not prepare the canonical half-body source" }

    & $Magick $Background $Character -gravity south -geometry +0+20 `
        -compose over -composite -strip $PngOutput
    if ($LASTEXITCODE -ne 0) { throw "Could not render the app-icon PNG" }

    & $Magick $PngOutput -strip `
        -define icon:auto-resize=256,128,96,64,48,40,32,24,20,16 `
        $IcoOutput
    if ($LASTEXITCODE -ne 0) { throw "Could not render the multi-size Windows ICO" }
}
finally {
    Remove-Item -LiteralPath $TemporaryRoot -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Output "APP_ICON_OK source=$Source png=$PngOutput ico=$IcoOutput"
