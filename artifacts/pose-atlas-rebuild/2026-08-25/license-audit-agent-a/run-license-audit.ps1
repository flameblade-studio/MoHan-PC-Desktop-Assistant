$ErrorActionPreference = "Stop"
$project = "D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision"
$instantMesh = "$project\tools\third_party\InstantMesh"
$mhr = "$project\artifacts\third-party-downloads\MHR-e412e12c"
$biRef = "$env:USERPROFILE\.cache\huggingface\hub\models--ZhengPeng7--BiRefNet_HR-matting\snapshots\5d6b6f8adcb5b417c871b1d84ceaae9871355b7f"
$imModel = "$env:USERPROFILE\.cache\huggingface\hub\models--TencentARC--InstantMesh\snapshots\b785b4ecfb6636ef34a08c748f96f6a5686244d0"
$nvdLicense = "$instantMesh\.conda\Lib\site-packages\nvdiffrast-0.3.3.dist-info\licenses\LICENSE.txt"

function Evidence([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return [ordered]@{ path=$Path; exists=$false; bytes=$null; sha256=$null }
    }
    $item = Get-Item -LiteralPath $Path
    $hash = Get-FileHash -Algorithm SHA256 -LiteralPath $Path
    [ordered]@{ path=$Path; exists=$true; bytes=$item.Length; sha256=$hash.Hash }
}

$imHead = git -c "safe.directory=$instantMesh" -C $instantMesh rev-parse HEAD
if ($LASTEXITCODE -ne 0) { throw "InstantMesh rev-parse failed: $LASTEXITCODE" }
$imStatus = @(git -c "safe.directory=$instantMesh" -C $instantMesh status --short)
if ($LASTEXITCODE -ne 0) { throw "InstantMesh status failed: $LASTEXITCODE" }
$mhrHead = git -c "safe.directory=$mhr" -C $mhr rev-parse HEAD
if ($LASTEXITCODE -ne 0) { throw "MHR rev-parse failed: $LASTEXITCODE" }
$mhrStatus = @(git -c "safe.directory=$mhr" -C $mhr status --short)
if ($LASTEXITCODE -ne 0) { throw "MHR status failed: $LASTEXITCODE" }

[ordered]@{
    generated_at=(Get-Date).ToString("o")
    policy="Only MIT or Apache-2.0 accepted; code and weights/assets assessed separately."
    instantmesh=[ordered]@{
        upstream="https://github.com/TencentARC/InstantMesh"; commit=$imHead.Trim(); git_status=$imStatus
        code_license=Evidence "$instantMesh\LICENSE"; code_decision="PASS_APACHE_2_0"
        model_upstream="https://huggingface.co/TencentARC/InstantMesh"; model_revision="b785b4ecfb6636ef34a08c748f96f6a5686244d0"
        reconstruction_checkpoint=Evidence "$imModel\instant_mesh_base.ckpt"
        white_background_unet=Evidence "$imModel\diffusion_pytorch_model.bin"
        local_model_license_path=$null; model_decision="BLOCKED_LOCAL_LICENSE_COPY_MISSING_UPSTREAM_TAG_APACHE_2_0"
    }
    nvdiffrast=[ordered]@{
        upstream="https://github.com/NVlabs/nvdiffrast"; release="0.3.3"; code_license=Evidence $nvdLicense
        detected_license="NVIDIA Source Code License (1-Way Commercial)"; decision="EXCLUDE_NOT_MIT_OR_APACHE_2_0"
    }
    birefnet=[ordered]@{
        code_upstream="https://github.com/ZhengPeng7/BiRefNet"; model_upstream="https://huggingface.co/ZhengPeng7/BiRefNet_HR-matting"
        revision="5d6b6f8adcb5b417c871b1d84ceaae9871355b7f"; cached_remote_code=Evidence "$biRef\birefnet.py"
        model_weights=Evidence "$biRef\model.safetensors"; local_license_path=$null; upstream_license_tag="MIT"
        decision="BLOCKED_LOCAL_LICENSE_COPY_MISSING"
    }
    mhr=[ordered]@{
        upstream="https://github.com/facebookresearch/MHR"; commit=$mhrHead.Trim(); git_status=$mhrStatus
        code_license=Evidence "$mhr\LICENSE"; code_decision="PASS_APACHE_2_0"
        assets_directory_exists=(Test-Path -LiteralPath "$mhr\assets" -PathType Container)
        asset_decision="NOT_AUDITED_ASSETS_NOT_PRESENT"
    }
} | ConvertTo-Json -Depth 8
