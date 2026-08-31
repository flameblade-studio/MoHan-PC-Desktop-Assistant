$ErrorActionPreference = "Stop"

$target = [System.IO.Path]::GetFullPath("C:\Program")
$expected = [System.IO.Path]::GetFullPath("C:\Program")
$protectedProgramFiles = [System.IO.Path]::GetFullPath("C:\Program Files")
$protectedVisualStudio = [System.IO.Path]::GetFullPath(
    "C:\Program Files\Microsoft Visual Studio\18\Community"
)
$resultPath = Join-Path $PSScriptRoot "remove-c-program-result.json"

if (-not $target.Equals($expected, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "DELETE_TARGET_MISMATCH"
}
if ($target.Equals($protectedProgramFiles, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "PROTECTED_PATH_COLLISION"
}

$allowedNames = @(
    "VC", "Common7", "MSBuild", "Team Tools", "Xml", "DIA SDK",
    "Licenses", "VB", "VC#", "ImportProjects", "SDK"
)
$unexpected = @(
    Get-ChildItem -LiteralPath $target -Force |
        Where-Object { $_.Name -notin $allowedNames }
)
if ($unexpected.Count -gt 0) {
    throw "UNEXPECTED_TOP_LEVEL_CONTENT: $($unexpected.Name -join ',')"
}

$before = Get-ChildItem -LiteralPath $target -Recurse -File -Force |
    Measure-Object Length -Sum
& takeown.exe /F $target /R /D Y | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "TAKEOWN_FAILED_EXIT_$LASTEXITCODE"
}

$administratorsSid = "*S-1-5-32-544:(OI)(CI)F"
& icacls.exe $target /grant:r $administratorsSid /T /C /Q | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "ICACLS_FAILED_EXIT_$LASTEXITCODE"
}

Get-ChildItem -LiteralPath $target -Recurse -Force | ForEach-Object {
    if ($_.Attributes -band [System.IO.FileAttributes]::ReadOnly) {
        $_.Attributes = $_.Attributes -bxor [System.IO.FileAttributes]::ReadOnly
    }
}
Remove-Item -LiteralPath $target -Recurse -Force

$result = [ordered]@{
    deleted_path = $target
    deleted_bytes = [int64]$before.Sum
    deleted_files = $before.Count
    target_exists_after_delete = Test-Path -LiteralPath $target
    program_files_preserved = Test-Path -LiteralPath $protectedProgramFiles
    visual_studio_preserved = Test-Path -LiteralPath $protectedVisualStudio
}
$result | ConvertTo-Json | Set-Content -LiteralPath $resultPath -Encoding UTF8

if (
    $result.target_exists_after_delete -or
    -not $result.program_files_preserved -or
    -not $result.visual_studio_preserved
) {
    throw "POST_DELETE_VERIFICATION_FAILED"
}
