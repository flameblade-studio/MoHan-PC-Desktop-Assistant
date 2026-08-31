from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageStat


PROJECT = Path(r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision")
ARTIFACT_ROOT = PROJECT / "artifacts" / "pose-atlas-rebuild" / "2026-08-25"
EVIDENCE_ROOT = ARTIFACT_ROOT / "yunchangge-vnext-three-domain-compat-agent-c"
SOURCE = (
    ARTIFACT_ROOT
    / "yaw-105-candidate-v2-shoe-local-edit-main"
    / "yaw-105-pitch+00.candidate-v3.deterministic-shoe-roi-composite.png"
)
EXPECTED_SOURCE_SHA256 = "10F705A4CA4F2B5FC4FB7D96C2BB69E7EC18AA25209841CBB76979BA0F47C86C"
MODEL_REVISION = "5d6b6f8adcb5b417c871b1d84ceaae9871355b7f"
MODEL_SNAPSHOT = (
    Path(r"D:\FlamebladeStudio\CodexProjects\.third-party-cache\huggingface\hub")
    / "models--ZhengPeng7--BiRefNet_HR-matting"
    / "snapshots"
    / MODEL_REVISION
)
MODEL_WEIGHT = MODEL_SNAPSHOT / "model.safetensors"
EXPECTED_WEIGHT_BYTES = 444_473_596
EXPECTED_WEIGHT_SHA256 = "A5A4DE698739EA5E0E8BBAB28E1B293DDE95092B87A442D566CBC585C53CEF55"
STAGED_RGBA = EVIDENCE_ROOT / "yaw-105-pitch+00.candidate-v3.birefnet-rgba-staging.png"
REPORT_PATH = EVIDENCE_ROOT / "yaw-105-v3-alpha-preflight-result.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def main() -> int:
    errors: list[str] = []
    if not SOURCE.is_file():
        errors.append(f"missing source: {SOURCE}")
        image_facts: dict[str, object] = {}
        source_sha = None
    else:
        source_sha = sha256(SOURCE)
        if source_sha != EXPECTED_SOURCE_SHA256:
            errors.append("source SHA256 drift")
        with Image.open(SOURCE) as image:
            rgb = image.convert("RGB")
            corners = [
                list(rgb.getpixel((0, 0))),
                list(rgb.getpixel((rgb.width - 1, 0))),
                list(rgb.getpixel((0, rgb.height - 1))),
                list(rgb.getpixel((rgb.width - 1, rgb.height - 1))),
            ]
            statistics = ImageStat.Stat(rgb)
            image_facts = {
                "size": [image.width, image.height],
                "mode": image.mode,
                "has_alpha": "A" in image.getbands(),
                "bands": list(image.getbands()),
                "corner_rgb": corners,
                "rgb_extrema": [list(values) for values in rgb.getextrema()],
                "rgb_mean": [round(value, 4) for value in statistics.mean],
            }
            if image.size != (1024, 1536):
                errors.append("source dimensions are not 1024x1536")
            if image.mode != "RGB":
                errors.append("source mode is not RGB")

    required_model_files = [
        MODEL_SNAPSHOT / "config.json",
        MODEL_SNAPSHOT / "birefnet.py",
        MODEL_SNAPSHOT / "BiRefNet_config.py",
        MODEL_WEIGHT,
    ]
    missing_model_files = [str(path) for path in required_model_files if not path.is_file()]
    if missing_model_files:
        errors.extend(f"missing pinned model file: {path}" for path in missing_model_files)

    weight_sha = None
    weight_bytes = None
    if MODEL_WEIGHT.is_file():
        weight_bytes = MODEL_WEIGHT.stat().st_size
        if weight_bytes != EXPECTED_WEIGHT_BYTES:
            errors.append("model weight byte size drift")
        weight_sha = sha256(MODEL_WEIGHT)
        if weight_sha != EXPECTED_WEIGHT_SHA256:
            errors.append("model weight SHA256 drift")

    if SOURCE.resolve() == STAGED_RGBA.resolve():
        errors.append("staged output aliases source")
    if STAGED_RGBA.exists():
        errors.append("staged output already exists; refuse overwrite")

    report = {
        "schema": "mohan.yaw105.v3.alpha-preflight/v1",
        "technical_preflight_status": "PASS" if not errors else "BLOCK",
        "inference_run": False,
        "alpha_output_exists": STAGED_RGBA.is_file(),
        "promotion_allowed": False,
        "identity_gate": "NOT_ACCEPTED",
        "angle_gate": "NOT_ACCEPTED",
        "art_gate": "OWNER_REVIEW_UNANSWERED",
        "source": {
            "path": str(SOURCE),
            "expected_sha256": EXPECTED_SOURCE_SHA256,
            "actual_sha256": source_sha,
            **image_facts,
            "interpretation": "RGB gray-background mother candidate; no transparency exists yet",
        },
        "pinned_birefnet": {
            "model_id": "ZhengPeng7/BiRefNet_HR-matting",
            "revision": MODEL_REVISION,
            "snapshot": str(MODEL_SNAPSHOT),
            "weight_path": str(MODEL_WEIGHT),
            "weight_bytes": weight_bytes,
            "weight_sha256": weight_sha,
            "offline_only": True,
            "files_present": not missing_model_files,
        },
        "staged_output": {
            "path": str(STAGED_RGBA),
            "must_not_overwrite": True,
            "expected_mode": "RGBA",
            "expected_size": [1024, 1536],
        },
        "qa_contract": {
            "corner_alpha": [0, 0, 0, 0],
            "transparent_rgb_nonzero_pixels": 0,
            "foreground_must_not_touch_canvas": True,
            "foreground_bbox_min_bottom": 1460,
            "shoe_roi": [385, 1380, 650, 1475],
            "shoe_left_roi": [385, 1380, 515, 1475],
            "shoe_right_roi": [500, 1380, 650, 1475],
            "shoe_min_nonzero_alpha_each": 500,
            "hem_roi": [290, 1220, 710, 1455],
            "hem_min_nonzero_alpha": 20000,
            "manual_required": [
                "both low white shoes retained without sole erosion",
                "semi-transparent skirt hem retained without rectangular cut or hard saw edge",
                "hair strands and fixed ornament retained",
            ],
        },
        "errors": errors,
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 4


if __name__ == "__main__":
    raise SystemExit(main())
