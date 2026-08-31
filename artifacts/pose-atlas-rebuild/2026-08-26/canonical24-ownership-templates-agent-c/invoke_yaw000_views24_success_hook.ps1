param(
    [Parameter(Mandatory = $true)]
    [string]$RunnerOutputDir,
    [Parameter(Mandatory = $true)]
    [string]$LayerOutputRoot,
    [Parameter(Mandatory = $true)]
    [string]$UpstreamExitCodeFile
)

$Repo = 'D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision'
$Python = Join-Path $Repo '.venv315\Scripts\python.exe'
$Hook = Join-Path $Repo 'artifacts\pose-atlas-rebuild\2026-08-26\canonical24-ownership-templates-agent-c\postprocess_views24_master_success.py'
$Bundles = Join-Path $Repo 'artifacts\pose-atlas-rebuild\2026-08-26\canonical24-control-bundles-agent-b\bundles'

& $Python -B $Hook `
    --view-id 'yaw+000-pitch+00' `
    --runner-output-dir $RunnerOutputDir `
    --layer-output-root $LayerOutputRoot `
    --control-bundles-root $Bundles `
    --repo $Repo `
    --upstream-exit-code-file $UpstreamExitCodeFile
exit $LASTEXITCODE
