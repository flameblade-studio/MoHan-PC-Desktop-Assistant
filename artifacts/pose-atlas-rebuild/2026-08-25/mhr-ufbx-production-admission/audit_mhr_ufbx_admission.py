from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
MHR_CODE = REPO / "artifacts/third-party-downloads/MHR-e412e12c"
MHR_ASSETS = REPO / "artifacts/third-party-downloads/MHR-v1.0.1-assets"
ASSET_DIR = MHR_ASSETS / "extracted/assets"
UFBX = REPO / "artifacts/third-party-downloads/ufbx-v0.23.0"
CANDIDATE3 = REPO / "artifacts/pose-atlas-rebuild/2026-08-25/ufbx-lod1-extractor-agent-a/body-morph-candidate3"
CONTROLS = REPO / "artifacts/pose-atlas-rebuild/2026-08-25/ufbx-lod1-extractor-agent-a/candidate3-yaw-controls-24"

ALLOW = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "CC0-1.0", "CC-BY"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def record(path: Path) -> dict[str, object]:
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}


def git_value(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def main() -> int:
    required = [
        MHR_CODE / "LICENSE",
        MHR_CODE / "README.md",
        MHR_CODE / "pyproject.toml",
        ASSET_DIR / "LICENSE.txt",
        ASSET_DIR / "lod1.fbx",
        ASSET_DIR / "mhr_model.pt",
        MHR_ASSETS / "assets.zip",
        UFBX / "LICENSE",
        UFBX / "README.md",
        UFBX / "ufbx.c",
        UFBX / "ufbx.h",
        CANDIDATE3 / "candidate3.obj",
        CANDIDATE3 / "candidate3-vertices.bin",
        CONTROLS / "candidate3-camera-anchor-control-manifest.json",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        print(json.dumps({"status": "FAIL_CLOSED_MISSING_EVIDENCE", "missing": missing}))
        return 3

    mhr_license = (MHR_CODE / "LICENSE").read_text(encoding="utf-8", errors="replace")
    asset_license = (ASSET_DIR / "LICENSE.txt").read_text(encoding="utf-8", errors="replace")
    ufbx_license = (UFBX / "LICENSE").read_text(encoding="utf-8", errors="replace")
    license_checks = {
        "mhr_code_apache_2_0": "Apache License" in mhr_license and "Version 2.0" in mhr_license,
        "mhr_assets_apache_2_0": "Apache License" in asset_license and "Version 2.0" in asset_license,
        "ufbx_mit_alternative_a": "ALTERNATIVE A - MIT License" in ufbx_license,
    }

    asset_files = sorted(path for path in ASSET_DIR.iterdir() if path.is_file())
    image_suffixes = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".exr", ".hdr"}
    texture_files = [path for path in asset_files if path.suffix.lower() in image_suffixes]
    material_files = [path for path in asset_files if path.suffix.lower() in {".mtl", ".mat", ".material"}]

    components = [
        {
            "id": "mhr_code",
            "kind": "code",
            "license": "Apache-2.0",
            "decision": "ALLOW_WITH_APACHE_NOTICE_OBLIGATIONS" if license_checks["mhr_code_apache_2_0"] else "BLOCK",
            "upstream": "https://github.com/facebookresearch/MHR",
            "revision": git_value(MHR_CODE, "rev-parse", "HEAD"),
            "remote": git_value(MHR_CODE, "remote", "get-url", "origin"),
            "evidence": record(MHR_CODE / "LICENSE"),
        },
        {
            "id": "mhr_v1_0_1_model_human_assets",
            "kind": "model/human topology/blendshape/rig assets",
            "license": "Apache-2.0",
            "decision": "ALLOW_WITH_APACHE_NOTICE_OBLIGATIONS" if license_checks["mhr_assets_apache_2_0"] else "BLOCK",
            "upstream": "https://github.com/facebookresearch/MHR/releases/tag/v1.0.1",
            "revision": "v1.0.1",
            "evidence": {
                "bundle_license": record(ASSET_DIR / "LICENSE.txt"),
                "archive": record(MHR_ASSETS / "assets.zip"),
                "lod1_fbx": record(ASSET_DIR / "lod1.fbx"),
            },
        },
        {
            "id": "mhr_torchscript_and_corrective_weights",
            "kind": "weights/model parameterization",
            "license": "Apache-2.0",
            "decision": "ALLOW_WITH_APACHE_NOTICE_OBLIGATIONS" if license_checks["mhr_assets_apache_2_0"] else "BLOCK",
            "production_dependency": False,
            "note": "The admitted candidate3 reconstruction is ufbx-only; mhr_model.pt/PyTorch served as an oracle, not the production reconstruction dependency.",
            "evidence": {
                "mhr_model_pt": record(ASSET_DIR / "mhr_model.pt"),
                "compact_model": record(ASSET_DIR / "compact_v6_1.model"),
                "corrective_activation": record(ASSET_DIR / "corrective_activation.npz"),
                "corrective_blendshapes_lod1": record(ASSET_DIR / "corrective_blendshapes_lod1.npz"),
                "bundle_license": record(ASSET_DIR / "LICENSE.txt"),
            },
        },
        {
            "id": "ufbx_code",
            "kind": "code",
            "license": "MIT (Alternative A selected)",
            "decision": "ALLOW_WITH_MIT_NOTICE" if license_checks["ufbx_mit_alternative_a"] else "BLOCK",
            "upstream": "https://github.com/ufbx/ufbx",
            "revision": git_value(UFBX, "rev-parse", "HEAD"),
            "remote": git_value(UFBX, "remote", "get-url", "origin"),
            "evidence": {
                "license": record(UFBX / "LICENSE"),
                "ufbx_c": record(UFBX / "ufbx.c"),
                "ufbx_h": record(UFBX / "ufbx.h"),
            },
        },
    ]

    license_stack_pass = all(item["decision"].startswith("ALLOW") for item in components)
    derived = {
        "candidate3_obj": record(CANDIDATE3 / "candidate3.obj"),
        "candidate3_vertices": record(CANDIDATE3 / "candidate3-vertices.bin"),
        "candidate3_control_manifest": record(CONTROLS / "candidate3-camera-anchor-control-manifest.json"),
    }
    output_admission = {
        "license_only_decision": "ALLOW_AS_APACHE_DERIVATIVE_WITH_NOTICES" if license_stack_pass else "BLOCK",
        "scope": [
            "candidate3.obj and candidate3-vertices.bin geometry",
            "24-view silhouette/depth/normal/part-ID control evidence derived from that geometry",
        ],
        "not_a_quality_or_final_art_approval": True,
        "obligations": [
            "Ship a readable Apache-2.0 license copy for MHR code/assets.",
            "Retain applicable copyright/patent/trademark/attribution notices.",
            "Mark modified/derived MHR files where distributed as source/object derivatives.",
            "Include the selected ufbx MIT copyright and permission notice for substantial copies.",
            "Do not imply Meta/MHR or ufbx endorsement and do not use upstream trademarks as product branding.",
        ],
        "evidence": derived,
    }

    skin_gate = {
        "status": "BLOCKED_NO_LICENSED_SKIN_TEXTURE_OR_MATERIAL",
        "asset_package_file_count": len(asset_files),
        "texture_file_count": len(texture_files),
        "material_sidecar_count": len(material_files),
        "texture_files": [str(path) for path in texture_files],
        "material_files": [str(path) for path in material_files],
        "blocked_outputs": [
            "final realistic body_skin RGBA",
            "textured nude/body render",
            "albedo/normal/roughness-derived formal raster",
            "any final 24/600 art that claims a licensed skin texture from MHR",
        ],
        "reason": "The local MHR asset bundle has no image texture or material sidecar. Geometry admission does not create a license or provenance for realistic skin artwork.",
    }

    result = {
        "schema": "mohan.mhr-ufbx.production-admission.v1",
        "policy": {
            "allowed": sorted(ALLOW),
            "rejected": ["GPL", "AGPL", "LGPL", "CC-BY-SA", "CC-BY-ND", "all NC", "unknown/undocumented"],
            "separate_gates": ["code", "model/human assets", "derived outputs", "textures/materials", "weights"],
        },
        "status": "PARTIAL_ADMISSION_GEOMETRY_ONLY_SKIN_BLOCKED" if license_stack_pass else "FAIL_CLOSED_LICENSE_STACK",
        "license_checks": license_checks,
        "components": components,
        "derived_geometry_outputs": output_admission,
        "textures_and_materials": skin_gate,
        "formal_pipeline_decision": {
            "candidate3_geometry_controls": "ADMIT_LICENSE_ONLY_PENDING_EXISTING_GEOMETRY_QA",
            "candidate3_as_final_body_skin_or_final_art": "BLOCK",
            "reason": "MHR/ufbx licensing is admissible, but no separately licensed realistic skin material exists locally.",
        },
        "prohibitions_observed": ["no network", "no download", "no formal notices edit", "no formal asset edit"],
    }
    json_path = OUT / "mhr-ufbx-production-admission.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    notices = f"""# THIRD-PARTY NOTICES CANDIDATE — NOT FORMAL\n\nThis file is an isolated review candidate and does not modify the project's formal notices.\n\n## Momentum Human Rig (MHR)\n\n- Upstream: https://github.com/facebookresearch/MHR\n- Code revision: `{components[0]['revision']}`\n- Asset release: `v1.0.1`\n- License: Apache License 2.0\n- Use: LOD1 human topology, rig/blendshape data and geometry-control derivatives.\n- Local license evidence: `{MHR_CODE / 'LICENSE'}` and `{ASSET_DIR / 'LICENSE.txt'}`.\n- Modifications/derivatives: local candidate body coefficients, torso morph, reconstructed vertices, OBJ and geometry control renders; these remain candidate evidence, not final art.\n\nA complete Apache-2.0 license copy and applicable upstream notices must accompany distribution. Modified files must carry prominent change notices where required.\n\n## ufbx\n\n- Upstream: https://github.com/ufbx/ufbx\n- Revision: `{components[3]['revision']}` (`v0.23.0`)\n- Selected license: Alternative A, MIT License\n- Copyright: Copyright (c) 2020 Samuli Raivio\n- Use: offline parsing of MHR LOD1 FBX topology, skeleton, skin weights and blendshape offsets.\n\nThe MIT copyright and permission notice in `{UFBX / 'LICENSE'}` must be included in copies or substantial portions.\n"""
    (OUT / "THIRD-PARTY-NOTICES-CANDIDATE.md").write_text(notices, encoding="utf-8")

    report = f"""# MHR / ufbx production-admission audit\n\n## 結論\n\n`{result['status']}`\n\n- MHR 程式碼：Apache-2.0，本機 LICENSE 與 commit 可核對，授權准入。\n- MHR v1.0.1 人體模型／FBX／blendshape／TorchScript 與 corrective weights：同一解壓資產目錄附 Apache-2.0 LICENSE.txt，授權准入。\n- ufbx v0.23.0：明確雙授權；本案固定選 Alternative A MIT，授權准入。\n- candidate3 OBJ／vertices 與 24 視角幾何控制圖：從授權角度可作 Apache-2.0 衍生候選，但必須附 notices；這不等於美術或幾何 QA 最終通過。\n- 真實 body_skin／皮膚貼圖：BLOCKED。MHR 本機資產包沒有任何圖片貼圖或 material sidecar，不能把灰模、normal 或未追溯皮膚圖冒充正式人體皮膚素材。\n\n因此，能進正式產線的是「幾何控制資料」的授權層；不能進正式產線的是任何宣稱已有合法真實皮膚材質的最終 RGBA／貼圖成品。\n"""
    (OUT / "REPORT.md").write_text(report, encoding="utf-8")

    print(json.dumps({
        "status": result["status"],
        "machine_json": str(json_path),
        "notices_candidate": str(OUT / "THIRD-PARTY-NOTICES-CANDIDATE.md"),
        "mhr_commit": components[0]["revision"],
        "ufbx_commit": components[3]["revision"],
        "geometry_license_decision": output_admission["license_only_decision"],
        "skin_status": skin_gate["status"],
    }, ensure_ascii=False, indent=2))
    return 4 if skin_gate["status"].startswith("BLOCKED") else 0


if __name__ == "__main__":
    raise SystemExit(main())
