from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageChops


VIEWS = (
    "yaw-180-pitch+00", "yaw-165-pitch+00", "yaw-150-pitch+00", "yaw-135-pitch+00",
    "yaw-120-pitch+00", "yaw-105-pitch+00", "yaw-090-pitch+00", "yaw-075-pitch+00",
    "yaw-060-pitch+00", "yaw-045-pitch+00", "yaw-030-pitch+00", "yaw-015-pitch+00",
    "yaw+000-pitch+00", "yaw+015-pitch+00", "yaw+030-pitch+00", "yaw+045-pitch+00",
    "yaw+060-pitch+00", "yaw+075-pitch+00", "yaw+090-pitch+00", "yaw+105-pitch+00",
    "yaw+120-pitch+00", "yaw+135-pitch+00", "yaw+150-pitch+00", "yaw+165-pitch+00",
)
LAYERS = (
    "body", "hair_back", "base", "jaw", "oral_cavity", "teeth_tongue",
    "lip_lower", "lip_upper", "corner_left", "corner_right", "blush_left",
    "blush_right", "iris_left", "iris_right", "eyelid_left", "eyelid_right",
    "eyeliner_left", "eyeliner_right", "brow_left", "brow_right", "hair_left",
    "hair_right", "sleeve_left", "sleeve_right", "ornament",
)
CORE_LAYERS = frozenset(LAYERS) - {"body", "sleeve_left", "sleeve_right", "ornament"}
EXPECTED_SIZE = (1024, 1536)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _transparent_rgb_contamination(image: Image.Image, alpha: Image.Image) -> int:
    red, green, blue = image.split()[:3]
    rgb_max = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    rgb_nonzero = rgb_max.point(lambda value: 255 if value else 0)
    transparent = alpha.point(lambda value: 255 if value == 0 else 0)
    contaminated = ImageChops.multiply(rgb_nonzero, transparent)
    return contaminated.histogram()[255]


def _domain(layer: str) -> str:
    if layer == "body" or layer == "ornament":
        return "blocked_mixed"
    if layer in {"sleeve_left", "sleeve_right"}:
        return "garment"
    if layer in CORE_LAYERS:
        return "core_anatomy"
    raise AssertionError(layer)


def _decision(layer: str, technical_ok: bool, visible_pixels: int) -> tuple[str, str]:
    if layer == "body":
        return "BLOCK_REBUILD_MIXED", "body mixes anatomy, clothing base, arms and hands"
    if layer == "ornament":
        return "BLOCK_REBUILD_SPLIT", "ornament does not separate fixed hairpin from swappable accessory"
    if not technical_ok:
        return "BLOCK_TECHNICAL", "RGBA/canvas/corner-alpha/transparent-RGB gate failed"
    if visible_pixels == 0:
        return "HOLD_EMPTY_REQUIRES_OCCLUSION_EVIDENCE", "empty legacy layer needs per-view occlusion evidence"
    if layer in {"sleeve_left", "sleeve_right"}:
        return "PRESERVE_GARMENT_CANDIDATE", "legacy sleeve is technically reusable only after cuff/hand ownership QA"
    return "PRESERVE_CORE_CANDIDATE", "technically reusable legacy core pixels; not promoted"


def _record(root: Path, view_id: str, layer: str) -> dict[str, object]:
    path = root / f"{view_id}_{layer}.png"
    if not path.is_file():
        return {
            "view_id": view_id,
            "legacy_layer": layer,
            "relative_path": path.name,
            "exists": False,
            "ownership_domain": _domain(layer),
            "decision": "BLOCK_MISSING_FILE",
            "reason": "formal PNG is missing",
        }
    with Image.open(path) as opened:
        opened.load()
        mode = opened.mode
        size = opened.size
        if mode == "RGBA":
            rgba = opened
            alpha = rgba.getchannel("A")
            histogram = alpha.histogram()
            visible_pixels = size[0] * size[1] - histogram[0]
            soft_alpha_pixels = sum(histogram[1:255])
            alpha_bbox = list(alpha.getbbox()) if alpha.getbbox() is not None else None
            corners = [
                alpha.getpixel((0, 0)),
                alpha.getpixel((size[0] - 1, 0)),
                alpha.getpixel((0, size[1] - 1)),
                alpha.getpixel((size[0] - 1, size[1] - 1)),
            ]
            transparent_rgb = _transparent_rgb_contamination(rgba, alpha)
        else:
            visible_pixels = 0
            soft_alpha_pixels = 0
            alpha_bbox = None
            corners = None
            transparent_rgb = None
    technical_ok = (
        mode == "RGBA"
        and size == EXPECTED_SIZE
        and corners == [0, 0, 0, 0]
        and transparent_rgb == 0
    )
    decision, reason = _decision(layer, technical_ok, visible_pixels)
    return {
        "view_id": view_id,
        "legacy_layer": layer,
        "relative_path": path.name,
        "exists": True,
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
        "mode": mode,
        "width": size[0],
        "height": size[1],
        "corner_alpha": corners,
        "transparent_rgb_contamination_pixels": transparent_rgb,
        "visible_alpha_pixels": visible_pixels,
        "soft_alpha_pixels": soft_alpha_pixels,
        "alpha_bbox": alpha_bbox,
        "technical_ok": technical_ok,
        "ownership_domain": _domain(layer),
        "decision": decision,
        "reason": reason,
        "promotion_allowed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--production-candidate", type=Path, required=True)
    parser.add_argument("--fixture-template", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    records = [_record(source, view, layer) for view in VIEWS for layer in LAYERS]
    decisions = Counter(record["decision"] for record in records)
    by_layer: dict[str, Counter[str]] = defaultdict(Counter)
    for record in records:
        by_layer[str(record["legacy_layer"])][str(record["decision"])] += 1
    missing = [record["relative_path"] for record in records if not record["exists"]]
    report = {
        "schema": "mohan.poseatlas.v4-layered-to-vnext-ownership-audit/v1",
        "source": str(source),
        "source_files_modified": False,
        "source_files_copied": False,
        "formal_600_complete": False,
        "promotion_allowed": False,
        "status": "BLOCKED_MIGRATION",
        "facts": {
            "expected_files": 600,
            "observed_files": sum(1 for record in records if record["exists"]),
            "missing_files": len(missing),
            "decision_counts": dict(sorted(decisions.items())),
            "blocked_body_files": sum(1 for record in records if record["legacy_layer"] == "body"),
            "blocked_ornament_files": sum(1 for record in records if record["legacy_layer"] == "ornament"),
        },
        "by_layer": {layer: dict(sorted(counts.items())) for layer, counts in sorted(by_layer.items())},
        "missing": missing,
        "records": records,
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    candidate = json.loads(args.fixture_template.read_text(encoding="utf-8"))
    candidate["manifest_kind"] = "PRODUCTION"
    candidate["fixture_only"] = False
    candidate["asset_records"] = []
    candidate["mask_records"] = []
    candidate["formal_600_complete"] = False
    candidate["promotion_allowed"] = False
    args.production_candidate.write_text(
        json.dumps(candidate, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["facts"], ensure_ascii=False, indent=2))
    return 4


if __name__ == "__main__":
    raise SystemExit(main())
