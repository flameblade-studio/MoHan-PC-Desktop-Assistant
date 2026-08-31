param()

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..\..\..')).Path
$python = Join-Path $projectRoot 'tools\third_party\InstantMesh\.conda\python.exe'
$validator = Join-Path $projectRoot 'tools\validate_third_party_denylist.py'
$policy = Join-Path $projectRoot 'THIRD_PARTY_DENYLIST.json'
$badFixture = Join-Path $projectRoot 'artifacts\pose-atlas-rebuild\2026-08-25\layer-manifest-schema-draft\fixtures\bad-permanently-denied-nvdiffrast.json'

$residuePaths = @(
    (Join-Path $projectRoot 'tools\third_party\InstantMesh\.conda\Lib\site-packages\nvdiffrast'),
    (Join-Path $projectRoot 'tools\third_party\InstantMesh\.conda\Lib\site-packages\nvdiffrast-0.3.3.dist-info'),
    (Join-Path $projectRoot 'tools\third_party\InstantMesh\.torch_extensions'),
    'C:\Users\hitos\AppData\Local\torch_extensions\torch_extensions\Cache\py310_cu121\nvdiffrast_plugin',
    'C:\Users\hitos\.cache\huggingface\hub\models--sudo-ai--zero123plus-v1.2'
)

$absenceStdout = Join-Path $PSScriptRoot 'local-absence.stdout.txt'
$absenceStderr = Join-Path $PSScriptRoot 'local-absence.stderr.txt'
$absenceProcess = Start-Process -FilePath $python -ArgumentList @($validator, '--verify-local-absence') -Wait -PassThru -NoNewWindow -RedirectStandardOutput $absenceStdout -RedirectStandardError $absenceStderr
$absenceExit = $absenceProcess.ExitCode

$fixtureStdout = Join-Path $PSScriptRoot 'deny-fixture.stdout.txt'
$fixtureStderr = Join-Path $PSScriptRoot 'deny-fixture.stderr.txt'
$fixtureProcess = Start-Process -FilePath $python -ArgumentList @($validator, '--candidate', $badFixture) -Wait -PassThru -NoNewWindow -RedirectStandardOutput $fixtureStdout -RedirectStandardError $fixtureStderr
$fixtureExit = $fixtureProcess.ExitCode

$result = [ordered]@{
    schema = 'mohan.third-party-removal-evidence.v1'
    generated_at = (Get-Date).ToString('o')
    policy_sha256 = (Get-FileHash -LiteralPath $policy -Algorithm SHA256).Hash
    validator_sha256 = (Get-FileHash -LiteralPath $validator -Algorithm SHA256).Hash
    checked_residue = @($residuePaths | ForEach-Object {
        [ordered]@{ path = $_; exists = [bool](Test-Path -LiteralPath $_) }
    })
    nvdiffrast_importable_in_instantmesh_env = (& $python -c "import importlib.util; print('true' if importlib.util.find_spec('nvdiffrast') else 'false')") -eq 'true'
    local_absence_exit_code = $absenceExit
    deny_fixture_exit_code = $fixtureExit
    expected = [ordered]@{
        local_absence_exit_code = 0
        deny_fixture_exit_code = 2
    }
    retained_evidence_only = @(
        'InstantMesh Apache-2.0 source tree',
        'negative denylist fixtures and their results'
    )
}

$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'removal-audit.json') -Encoding utf8

if ($absenceExit -ne 0) { exit 10 }
if ($fixtureExit -ne 2) { exit 11 }
if ($result.nvdiffrast_importable_in_instantmesh_env) { exit 12 }
if (@($result.checked_residue | Where-Object { $_.exists }).Count -ne 0) { exit 13 }
exit 0
