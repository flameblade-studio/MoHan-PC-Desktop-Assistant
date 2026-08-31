param()

$ErrorActionPreference = 'Stop'
$outDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceManifestPath = 'D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\artifacts\pose-atlas-rebuild\2026-08-25\candidate3-formal-controls-bundle-agent-a\formal-controls-manifest.json'
$sourceManifest = Get-Content -LiteralPath $sourceManifestPath -Raw | ConvertFrom-Json
$view = $sourceManifest.views | Where-Object { $_.formal_view_id -eq 'yaw+045-pitch+00' }
if ($null -eq $view -or @($view).Count -ne 1) { throw 'formal yaw+045 record must exist exactly once' }
if ($view.formal_yaw_degrees -ne 45 -or $view.source_renderer_yaw_degrees -ne -45 -or $view.source_control_file_id -ne 'yaw-045-pitch+00') { throw 'formal/renderer yaw sign contract mismatch' }

Add-Type -AssemblyName PresentationCore
Add-Type -AssemblyName WindowsBase

function Get-Sha256([string]$path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
}

function Open-Bitmap([string]$path) {
    $stream = [System.IO.File]::OpenRead($path)
    try {
        $decoder = [System.Windows.Media.Imaging.PngBitmapDecoder]::new(
            $stream,
            [System.Windows.Media.Imaging.BitmapCreateOptions]::PreservePixelFormat,
            [System.Windows.Media.Imaging.BitmapCacheOption]::OnLoad)
        $bitmap = $decoder.Frames[0]
        $bitmap.Freeze()
        return $bitmap
    } finally {
        $stream.Dispose()
    }
}

$kinds = @('silhouette', 'depth', 'normal')
$records = @()
$bitmaps = @()
foreach ($kind in $kinds) {
    $source = $view.outputs.$kind.absolute_path
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "missing source: $source" }
    $target = Join-Path $outDir ("yaw+045-pitch+00_{0}.png" -f $kind)
    Copy-Item -LiteralPath $source -Destination $target -Force
    $sourceHash = Get-Sha256 $source
    $targetHash = Get-Sha256 $target
    if ($sourceHash -ne $view.outputs.$kind.output_sha256 -or $targetHash -ne $sourceHash) { throw "hash mismatch: $kind" }
    $bitmap = Open-Bitmap $target
    if ($bitmap.PixelWidth -ne 1024 -or $bitmap.PixelHeight -ne 1536) { throw "dimension mismatch: $kind" }
    $expectedMode = if ($kind -eq 'normal') { 'RGB' } else { 'L' }
    $records += [ordered]@{
        kind = $kind
        file = [System.IO.Path]::GetFileName($target)
        absolute_path = $target
        source_path = $source
        source_sha256 = $sourceHash
        output_sha256 = $targetHash
        width = $bitmap.PixelWidth
        height = $bitmap.PixelHeight
        expected_mode = $expectedMode
        wic_pixel_format = $bitmap.Format.ToString()
    }
    $bitmaps += $bitmap
}

$sheetWidth = 900
$sheetHeight = 560
$visual = [System.Windows.Media.DrawingVisual]::new()
$dc = $visual.RenderOpen()
try {
    $dc.DrawRectangle([System.Windows.Media.Brushes]::White, $null, [System.Windows.Rect]::new(0, 0, $sheetWidth, $sheetHeight))
    $typeface = [System.Windows.Media.Typeface]::new('Segoe UI')
    $title = [System.Windows.Media.FormattedText]::new('GEOMETRY CONTROL ONLY - NOT FINAL ART', [System.Globalization.CultureInfo]::InvariantCulture, [System.Windows.FlowDirection]::LeftToRight, $typeface, 24, [System.Windows.Media.Brushes]::DarkRed, 1.0)
    $subtitle = [System.Windows.Media.FormattedText]::new('formal yaw +045  <-  source renderer yaw -045 | MHR candidate3 | clothing_baked=false', [System.Globalization.CultureInfo]::InvariantCulture, [System.Windows.FlowDirection]::LeftToRight, $typeface, 15, [System.Windows.Media.Brushes]::Black, 1.0)
    $dc.DrawText($title, [System.Windows.Point]::new(18, 12))
    $dc.DrawText($subtitle, [System.Windows.Point]::new(18, 48))
    for ($i = 0; $i -lt 3; $i++) {
        $x = 20 + $i * 294
        $label = [System.Windows.Media.FormattedText]::new($kinds[$i].ToUpperInvariant(), [System.Globalization.CultureInfo]::InvariantCulture, [System.Windows.FlowDirection]::LeftToRight, $typeface, 18, [System.Windows.Media.Brushes]::Black, 1.0)
        $dc.DrawText($label, [System.Windows.Point]::new($x, 78))
        $dc.DrawRectangle([System.Windows.Media.Brushes]::LightGray, [System.Windows.Media.Pen]::new([System.Windows.Media.Brushes]::Black, 1), [System.Windows.Rect]::new($x, 108, 270, 405))
        $dc.DrawImage($bitmaps[$i], [System.Windows.Rect]::new($x, 108, 270, 405))
    }
} finally {
    $dc.Close()
}

$render = [System.Windows.Media.Imaging.RenderTargetBitmap]::new($sheetWidth, $sheetHeight, 96, 96, [System.Windows.Media.PixelFormats]::Pbgra32)
$render.Render($visual)
$encoder = [System.Windows.Media.Imaging.PngBitmapEncoder]::new()
$encoder.Frames.Add([System.Windows.Media.Imaging.BitmapFrame]::Create($render))
$contactPath = Join-Path $outDir 'yaw+045-formal-controls-contact.png'
$outputStream = [System.IO.File]::Create($contactPath)
try { $encoder.Save($outputStream) } finally { $outputStream.Dispose() }

$candidate3Manifest = 'D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\artifacts\pose-atlas-rebuild\2026-08-25\ufbx-lod1-extractor-agent-a\candidate3-yaw-controls-24\candidate3-camera-anchor-control-manifest.json'
$bundle = [ordered]@{
    schema = 'mohan.poseatlas.generator-control-input-bundle/v1'
    status = 'PASS_STAGING_GEOMETRY_CONTROLS_ONLY'
    formal_art_status = 'NOT_FINAL_ART'
    formal_view_id = 'yaw+045-pitch+00'
    formal_yaw_degrees = 45
    source_renderer_yaw_degrees = -45
    sign_mapping = 'source_renderer_yaw=-formal_yaw'
    dimensions = @(1024, 1536)
    camera = 'fixed orthographic, Y-up, pitch 0'
    candidate3_mesh_sha256 = '23c5ecb3e943089954459f9f16e5551f0413571f5bacf85e3c3a6dcf155318a4'
    clothing_baked_into_body_mesh = $false
    clothing_statement = 'MHR body topology plus deterministic torso X/Z morph only; no outfit geometry introduced.'
    records = $records
    contact_sheet = [ordered]@{ path = $contactPath; sha256 = (Get-Sha256 $contactPath); width = $sheetWidth; height = $sheetHeight }
    provenance = [ordered]@{
        formal_controls_manifest = [ordered]@{ path = $sourceManifestPath; sha256 = (Get-Sha256 $sourceManifestPath) }
        candidate3_camera_anchor_manifest = [ordered]@{ path = $candidate3Manifest; sha256 = (Get-Sha256 $candidate3Manifest) }
        mhr_assets_license = 'Apache-2.0'
        ufbx_license = 'MIT Alternative A'
    }
    forbidden_claims = @('formal MoHan art complete', 'body_skin complete', 'clothing segmentation present')
}
$manifestPath = Join-Path $outDir 'input-bundle-manifest.json'
$bundle | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $manifestPath -Encoding utf8
$parsed = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($parsed.records.Count -ne 3 -or $parsed.clothing_baked_into_body_mesh -ne $false) { throw 'manifest validation failed' }
[ordered]@{ status = $bundle.status; files = 3; formal_yaw = 45; source_renderer_yaw = -45; contact_sheet = $contactPath; manifest = $manifestPath } | ConvertTo-Json -Compress
exit 0
