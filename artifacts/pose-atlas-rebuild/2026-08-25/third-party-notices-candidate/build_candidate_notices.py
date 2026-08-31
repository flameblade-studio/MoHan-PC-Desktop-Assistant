from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO = Path(r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision")
ROOT = REPO / "artifacts" / "pose-atlas-rebuild" / "2026-08-25"
OUT = ROOT / "third-party-notices-candidate"
BIR = ROOT / "birefnet-production-admission" / "birefnet-production-admission.json"
MHR = ROOT / "mhr-ufbx-production-admission" / "mhr-ufbx-production-admission.json"
OPENAI = ROOT / "image-input-production-admission" / "official-openai-output-rights-evidence.json"
SITE = REPO / "tools" / "third_party" / "InstantMesh" / ".conda" / "Lib" / "site-packages"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def ev(path: Path) -> dict:
    item = {"path": str(path), "exists": path.is_file()}
    if path.is_file():
        item.update(bytes=path.stat().st_size, sha256=sha(path))
    return item


def main() -> int:
    bir = json.loads(BIR.read_text(encoding="utf-8"))
    mhr = json.loads(MHR.read_text(encoding="utf-8"))
    openai = json.loads(OPENAI.read_text(encoding="utf-8"))
    m = {x["id"]: x for x in mhr["components"]}
    components = [
        dict(id="birefnet_code", name="BiRefNet code/config", kind="code", upstream=bir["identity"]["source_repo"], revision=bir["identity"]["revision"], license="MIT", commercial="ALLOW", infectious=False, purpose="Offline alpha matting", modified=False, evidence={"audit": ev(BIR), **bir["code"]["license_evidence"]}, admission="ALLOW_PINNED_REVISION_ONLY"),
        dict(id="birefnet_weights", name="BiRefNet_HR-matting weights", kind="weights", upstream=bir["identity"]["upstream"], revision=bir["identity"]["revision"], sha256=bir["weights"]["locked_sha256"], license="MIT", commercial="ALLOW", infectious=False, purpose="Pinned alpha prediction", modified=False, evidence={"audit": ev(BIR), "weight": bir["weights"]["file"]}, admission="ALLOW_PINNED_REVISION_AND_SHA_ONLY"),
        dict(id="mhr_code", name="Meta MHR", kind="code", upstream=m["mhr_code"]["upstream"], revision=m["mhr_code"]["revision"], license="Apache-2.0", commercial="ALLOW_WITH_NOTICE", infectious=False, purpose="Geometry interpretation/oracle", modified=False, evidence={"audit": ev(MHR), "license": m["mhr_code"]["evidence"]}, admission=m["mhr_code"]["decision"]),
        dict(id="mhr_geometry_assets", name="MHR v1.0.1 geometry assets", kind="model/topology/rig/blendshape assets", upstream=m["mhr_v1_0_1_model_human_assets"]["upstream"], revision="v1.0.1", license="Apache-2.0", commercial="ALLOW_WITH_NOTICE", infectious=False, purpose="Depth/normal/silhouette/part controls only; no skin texture", modified=True, evidence={"audit": ev(MHR), **m["mhr_v1_0_1_model_human_assets"]["evidence"]}, admission=m["mhr_v1_0_1_model_human_assets"]["decision"]),
        dict(id="mhr_weights", name="MHR TorchScript/correctives", kind="weights/parameterization", upstream="https://github.com/facebookresearch/MHR/releases/tag/v1.0.1", revision="v1.0.1", license="Apache-2.0", commercial="ALLOW_WITH_NOTICE", infectious=False, purpose="Oracle only; not production ufbx dependency", production_dependency=False, modified=False, evidence={"audit": ev(MHR), **m["mhr_torchscript_and_corrective_weights"]["evidence"]}, admission=m["mhr_torchscript_and_corrective_weights"]["decision"]),
        dict(id="ufbx_code", name="ufbx", kind="code", upstream=m["ufbx_code"]["upstream"], revision=f"v0.23.0/{m['ufbx_code']['revision']}", license="MIT Alternative A", commercial="ALLOW_WITH_NOTICE", infectious=False, purpose="Read MHR lod1.fbx", modified=False, evidence={"audit": ev(MHR), **m["ufbx_code"]["evidence"]}, admission=m["ufbx_code"]["decision"]),
        dict(id="makehuman", name="MakeHuman", kind="code/assets", upstream="NOT_LOCALLY_EVIDENCED", revision="NOT_PRESENT", license="UNKNOWN", commercial="BLOCK", infectious="UNKNOWN", purpose="Not used by current MHR/ufbx path", modified=False, evidence="No local tools/artifact evidence found", admission="BLOCK_NOT_PRESENT_NOT_USED_DO_NOT_INTRODUCE"),
        dict(id="mpfb", name="MPFB", kind="code/assets", upstream="NOT_LOCALLY_EVIDENCED", revision="NOT_PRESENT", license="UNKNOWN", commercial="BLOCK", infectious="UNKNOWN", purpose="Not used by current MHR/ufbx path", modified=False, evidence="No local tools/artifact evidence found", admission="BLOCK_NOT_PRESENT_NOT_USED_DO_NOT_INTRODUCE"),
        dict(id="openai_imagegen_rights", name="OpenAI ImageGen Output rights", kind="service contract", upstream=[s["url"] for s in openai["sources"]], revision="Terms effective 2026-01-01; Service Terms updated 2026-06-12", license="NOT_OPEN_SOURCE_NOT_MIT", commercial="NO_NC_RESTRICTION_FOUND; INPUT_RIGHTS_SEPARATE", infectious=False, purpose="Output ownership evidence as between OpenAI and user", modified=False, evidence=ev(OPENAI), admission="CONTRACTUAL_OUTPUT_RIGHTS_ONLY_NOT_LICENSE_ADMISSION"),
        dict(id="pillow_runtime", name="Pillow", kind="runtime", upstream="https://github.com/python-pillow/Pillow", revision="10.4.0", license="HPND", commercial="PERMISSIVE_GENERALLY_BUT_POLICY_BLOCK", infectious=False, purpose="RGBA/alpha/contact-sheet QA", modified=False, evidence={"metadata": ev(SITE / "pillow-10.4.0.dist-info" / "METADATA"), "license": ev(SITE / "pillow-10.4.0.dist-info" / "LICENSE")}, admission="BLOCK_LICENSE_OUTSIDE_EXPLICIT_ALLOWLIST"),
        dict(id="scipy_runtime", name="SciPy installed binary", kind="runtime", upstream="https://github.com/scipy/scipy", revision="1.15.3", license="SciPy BSD-3-Clause; binary metadata also lists BSD-3-Clause-Attribution and GPL-3.0-with-GCC-exception", commercial="SCIPY_SOURCE_PERMISSIVE; CURRENT_BINARY_POLICY_BLOCK", infectious="GCC exception normally permits proprietary target code, but current policy rejects literal GPL components", purpose="Numerical geometry/interpolation", modified=False, evidence={"metadata": ev(SITE / "scipy-1.15.3.dist-info" / "METADATA"), "license": ev(SITE / "scipy-1.15.3.dist-info" / "LICENSE.txt")}, admission="BLOCK_CURRENT_BINARY_PENDING_CLEAN_ALLOWLIST_BUILD_OR_POLICY"),
    ]
    blocked = sum(x["admission"].startswith("BLOCK") for x in components)
    result = {"schema": "mohan.third_party_notices_candidate.v1", "status": "CANDIDATE_ONLY_FAIL_CLOSED_NOT_FORMAL_NOTICES", "policy": {"allowed": ["MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "CC0-1.0", "CC-BY"], "blocked": ["unknown", "NC", "SA", "ND", "GPL", "AGPL", "LGPL", "outside allowlist"]}, "components": components, "counts": {"components": len(components), "blocked": blocked}, "formal_notice_modified": False}
    jp = OUT / "third-party-notices-candidate.json"
    jp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# 墨寒 24/600 新產線第三方 Notices 候選", "", "> 僅供 artifact 稽核；不是正式 notices，也不改變墨寒 MIT 授權。", "", "| 元件 | 類型 | 授權/權利 | 准入 | 用途 |", "|---|---|---|---|---|"]
    lines += [f"| {x['name']} | {x['kind']} | {x['license']} | {x['admission']} | {x['purpose']} |" for x in components]
    lines += ["", "## Fail-closed 摘要", "", "- BiRefNet 程式與權重分開鎖 revision/SHA；均有 MIT 證據。", "- MHR 程式、幾何資產、權重分開；均為 Apache-2.0。幾何准入不會產生皮膚貼圖權利。", "- ufbx 選 MIT Alternative A。MakeHuman/MPFB 本機無證據且未使用，維持 BLOCK。", "- OpenAI ImageGen 是契約 Output 權利，不是 MIT；Input 權利仍逐張驗證。", "- Pillow 10.4.0 為 HPND，不在白名單；BLOCK。SciPy 原始碼主授權 BSD-3，但目前二進位包的複合授權不符合嚴格白名單；BLOCK runtime bundle。"]
    mp = OUT / "THIRD-PARTY-NOTICES-CANDIDATE.md"
    mp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "counts": result["counts"], "outputs": {str(jp): sha(jp), str(mp): sha(mp)}}, ensure_ascii=False, indent=2))
    return 4 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
