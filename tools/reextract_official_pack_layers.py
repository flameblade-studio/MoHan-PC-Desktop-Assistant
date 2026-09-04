"""Re-extract all 31 official-pack silhouettes from immutable intermediate art."""

from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import sys
lazy from pathlib import Path
lazy from typing import Final

ROOT: Final = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SOURCE_ROOT_LABEL: Final = "<owner-provided-immutable-scratchpad>"

lazy from domain.outfit_pack import official_pose_template
lazy from tools.art_pipeline.extract_layers import extract


HALF_SOURCES: Final = {
    "front-crossed": "halfprod_front_A",
    "cheek-rest": "halfprod_cheek_A",
    "left-neutral": "halfprod_lean_A",
    "front-mock-scold": "halfprod_mock_scold_A",
    "front-mock-hit": "halfprod_mock_hit_front_A",
    "front-eureka": "halfprod_eureka_front_A",
    "front-exasperated": "halfprod_exasperated_front_A",
}
SOURCE_STEPS: Final = ("L1_makeup", "L2_garment", "L3_hair", "L4_headwear")


def _source_prefix(silhouette: str) -> str:
    return HALF_SOURCES.get(silhouette, f"full_{silhouette}")


FRONT_REFERENCE_PREFIX: Final = "full_yaw+000-pitch+00"
# 參考圖抽層的顏色規則以正面五點為座標（臉核心、額頭、右側流蘇欄），只對正面到
# 45 度以內的 yaw 成立；更側面與背面仍用差分抽層（2026-09-05 量測：yaw+075 的五點
# 殘差已達 12.9 px，yaw-105 的比例失真到 0.586）。
REFERENCE_MAX_ABS_YAW: Final = 45


def _reference_prefix(source_prefix: str) -> str:
    """全身 yaw 姿勢用同角度的 v4 對齊參考圖；半身表情姿勢共用正面參考圖。"""
    if source_prefix.startswith("full_"):
        return source_prefix
    return FRONT_REFERENCE_PREFIX


def _reference_eligible(silhouette: str) -> bool:
    if not silhouette.startswith("yaw"):
        return True
    return abs(int(silhouette[3:7])) <= REFERENCE_MAX_ABS_YAW


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reextract(
    source_root: Path,
    output_root: Path,
    model_path: Path,
    safe_regions_path: Path,
) -> dict[str, object]:
    source_root = source_root.resolve()
    output_root = output_root.resolve()
    if output_root == source_root or source_root in output_root.parents:
        raise ValueError("Output must not be inside the immutable source root.")
    generated_root = source_root / "halfbody" / "out"
    extracted_root = source_root / "layers" / "out"
    if output_root.exists() and any(output_root.iterdir()):
        raise FileExistsError(f"Output is not empty: {output_root}")

    silhouettes = official_pose_template()["required_silhouettes"]
    report: dict[str, object] = {
        "source_root": SOURCE_ROOT_LABEL,
        "silhouettes": {},
    }
    entries = report["silhouettes"]
    if not isinstance(entries, dict):
        raise AssertionError("Internal report shape is invalid.")
    for silhouette in silhouettes:
        prefix = _source_prefix(silhouette)
        base = extracted_root / prefix / "base.png"
        inputs = [base, *(generated_root / f"{prefix}.{step}.png" for step in SOURCE_STEPS)]
        for shoe_step in ("L5c_shoes", "L5b_shoes", "L5_shoes"):
            shoe = generated_root / f"{prefix}.{shoe_step}.png"
            if shoe.is_file():
                inputs.append(shoe)
                break
        # 擁有者 2026-09-05 裁決：頭髮與髮飾以 v4 原圖為準。全身 yaw 姿勢用同角度的
        # 對齊參考圖；半身表情姿勢都是正面，共用 yaw+000 的參考圖。
        reference: Path | None = None
        if _reference_eligible(silhouette):
            reference = source_root / "layers" / f"{_reference_prefix(prefix)}.ref.aligned.png"
            inputs.append(reference)
        missing = [str(path) for path in inputs if not path.is_file()]
        if missing:
            raise FileNotFoundError(f"Missing immutable inputs for {silhouette}: {missing}")
        result = extract(
            base,
            prefix,
            source_directory=generated_root,
            output_root=output_root,
            model_path=model_path,
            safe_regions_path=safe_regions_path,
            output_name=silhouette,
            reference_path=reference,
        )
        entries[silhouette] = {
            "source_prefix": prefix,
            "reference_prefix": _reference_prefix(prefix) if reference else None,
            "source_sha256": {path.name: _sha256(path) for path in inputs},
            "result": result,
        }
        print(f"{silhouette}: {prefix} -> {output_root / silhouette}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root", type=Path)
    parser.add_argument("output_root", type=Path)
    parser.add_argument(
        "--model",
        type=Path,
        default=ROOT / "assets/vision-models/face_detection_yunet_2023mar.onnx",
    )
    parser.add_argument(
        "--safe-regions",
        type=Path,
        default=ROOT / "assets/makeup-safe-regions.json",
    )
    parser.add_argument("--report", type=Path, required=True)
    arguments = parser.parse_args()
    report = reextract(
        arguments.source_root,
        arguments.output_root,
        arguments.model,
        arguments.safe_regions,
    )
    arguments.report.parent.mkdir(parents=True, exist_ok=True)
    arguments.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"OFFICIAL_LAYER_REEXTRACT_OK count={len(report['silhouettes'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
