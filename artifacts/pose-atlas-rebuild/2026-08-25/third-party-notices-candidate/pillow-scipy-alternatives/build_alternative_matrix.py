from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SITE = Path(r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\tools\third_party\InstantMesh\.conda\Lib\site-packages")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def evidence(path: Path) -> dict[str, object]:
    return {
        "path": str(path),
        "exists": path.is_file(),
        "sha256": sha256(path) if path.is_file() else None,
    }


def main() -> int:
    cv2_metadata = SITE / "opencv_python_headless-4.11.0.86.dist-info" / "METADATA"
    cv2_license = SITE / "cv2" / "LICENSE.txt"
    cv2_third_party = SITE / "cv2" / "LICENSE-3RD-PARTY.txt"
    cv2_binary = SITE / "cv2" / "cv2.pyd"
    numpy_metadata = SITE / "numpy-1.26.4.dist-info" / "METADATA"
    numpy_license = SITE / "numpy-1.26.4.dist-info" / "LICENSE.txt"
    imageio_metadata = SITE / "imageio-2.37.4.dist-info" / "METADATA"
    skimage_metadata = SITE / "scikit_image-0.25.2.dist-info" / "METADATA"
    smoke = ROOT / "cv2-functional-smoke.json"

    components = [
        {
            "name": "opencv-python-headless",
            "version": importlib.metadata.version("opencv-python-headless"),
            "code_or_wrapper_license": "MIT / Apache-2.0 metadata",
            "binary_third_party_finding": "Bundled FFmpeg is explicitly LGPL-2.1; build reports FFMPEG=YES.",
            "functions": ["RGBA PNG read", "RGBA PNG write", "distanceTransform"],
            "functional_status": "PASS",
            "production_admission": "BLOCK",
            "reason": "The installed wheel contains an LGPL component, which is outside the owner's literal allowlist.",
            "evidence": [evidence(cv2_metadata), evidence(cv2_license), evidence(cv2_third_party), evidence(cv2_binary), evidence(smoke)],
        },
        {
            "name": "NumPy",
            "version": importlib.metadata.version("numpy"),
            "code_or_wrapper_license": "BSD-3-Clause",
            "binary_third_party_finding": "Wheel metadata lists GPL-3.0-with-GCC-exception and LGPL-2.1-or-later material in bundled OpenBLAS/runtime notices.",
            "functions": ["pixel arrays", "numeric kernels"],
            "functional_status": "PASS",
            "production_admission": "BLOCK",
            "reason": "The installed binary wheel's complete license set is outside the owner's literal allowlist.",
            "evidence": [evidence(numpy_metadata), evidence(numpy_license)],
        },
        {
            "name": "imageio",
            "version": importlib.metadata.version("imageio"),
            "code_or_wrapper_license": "BSD-2-Clause",
            "binary_third_party_finding": "Core metadata requires NumPy and Pillow.",
            "functions": ["image read", "image write"],
            "functional_status": "NOT_SMOKED",
            "production_admission": "BLOCK",
            "reason": "It does not remove the blocked Pillow/NumPy dependency chain.",
            "evidence": [evidence(imageio_metadata)],
        },
        {
            "name": "scikit-image",
            "version": importlib.metadata.version("scikit-image"),
            "code_or_wrapper_license": "BSD-3-Clause project metadata",
            "binary_third_party_finding": "Runtime metadata depends on NumPy, SciPy, Pillow, imageio and other packages.",
            "functions": ["image processing", "distance utilities"],
            "functional_status": "NOT_SMOKED",
            "production_admission": "BLOCK",
            "reason": "It preserves rather than removes the blocked dependency chain.",
            "evidence": [evidence(skimage_metadata)],
        },
        {
            "name": "Windows Imaging Component / System.Drawing",
            "version": "OS supplied",
            "code_or_wrapper_license": "Not evidenced as one of the owner's admitted open-source licenses in this local audit",
            "binary_third_party_finding": "No distributable local license package was identified; no distance transform API.",
            "functions": ["PNG read/write only"],
            "functional_status": "INSUFFICIENT",
            "production_admission": "BLOCK",
            "reason": "Does not satisfy the complete PNG plus distance-transform requirement, and redistribution terms were not locally evidenced.",
            "evidence": [],
        },
    ]

    payload = {
        "schema": "mohan.pillow-scipy-alternative-admission.v1",
        "policy_allowlist": ["MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "CC0", "CC-BY"],
        "policy_deny": ["GPL", "AGPL", "LGPL", "NC", "SA", "ND", "unknown"],
        "scope": "Local installed alternatives for formal RGBA/PNG QA and distance transform; no download; artifact-only smoke.",
        "overall_production_admission": "BLOCK",
        "conclusion": "No locally installed candidate provides both required functions with a fully allowlisted binary dependency chain.",
        "components": components,
    }
    json_path = ROOT / "pillow-scipy-alternative-matrix.json"
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Pillow / SciPy 正式產線替代稽核",
        "",
        "結論：**BLOCK**。本機 OpenCV 的 RGBA PNG 讀寫與距離轉換已實跑成功，但其 wheel 明載並啟用 LGPL FFmpeg；依工作室的字面准入政策，不能進正式 MIT 產線。",
        "",
        "| 候選 | 功能 | 完整 binary / 相依授權 | 正式准入 |",
        "|---|---|---|---|",
    ]
    for item in components:
        lines.append(f"| {item['name']} {item['version']} | {item['functional_status']} | {item['binary_third_party_finding']} | **{item['production_admission']}** |")
    lines.extend([
        "",
        "## 實證邊界",
        "",
        "- `cv2-functional-smoke.json` 只證明現有隔離環境的功能，不構成授權准入。",
        "- 沒有下載或安裝任何新套件，也沒有修改正式程式、正式 notices、manifest 或 assets。",
        "- 若要解除 BLOCK，必須取得不含 LGPL/GPL runtime 的可重現 PNG + distance-transform 實作與完整 binary notices；本報告不以推測代替證據。",
        "",
    ])
    md_path = ROOT / "REPORT.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({
        "overall_production_admission": payload["overall_production_admission"],
        "json": {"path": str(json_path), "sha256": sha256(json_path)},
        "report": {"path": str(md_path), "sha256": sha256(md_path)},
        "blocked_components": [item["name"] for item in components if item["production_admission"] == "BLOCK"],
    }, indent=2))
    return 4


if __name__ == "__main__":
    raise SystemExit(main())
