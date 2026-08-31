from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parent.parent / "yaw075-v3-local-roi-packs-agent-b"
sys.path.insert(0, str(PACK_ROOT))
from face_neck_safe_compositor import read_rgba, write_rgb

PROJECT = Path(r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision")
PYPNG_ROOT = PROJECT / r"artifacts\pose-atlas-rebuild\2026-08-25\third-party-notices-candidate\pypng-wheel\extracted"
sys.path.insert(0, str(PYPNG_ROOT))
import png  # type: ignore

BBOX = [270, 1320, 790, 1530]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_rgba(path: Path, width: int, height: int, rows: list[bytearray]) -> None:
    with path.open("wb") as output:
        png.Writer(width, height, greyscale=False, alpha=True, bitdepth=8).write(output, rows)


def crop_rgba(rows: list[bytearray]) -> list[bytearray]:
    left, top, right, bottom = BBOX
    return [bytearray(row[left * 4 : right * 4]) for row in rows[top:bottom]]


def composite_gray(rows: list[bytearray], background: int = 128) -> list[bytearray]:
    result = []
    for row in rows:
        target = bytearray(len(row) // 4 * 3)
        for x in range(len(row) // 4):
            r, g, b, a = row[x * 4 : x * 4 + 4]
            inverse = 255 - a
            target[x * 3] = (r * a + background * inverse + 127) // 255
            target[x * 3 + 1] = (g * a + background * inverse + 127) // 255
            target[x * 3 + 2] = (b * a + background * inverse + 127) // 255
        result.append(target)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    width, height, rows = read_rgba(args.source)
    if (width, height) != (1024, 1536):
        raise SystemExit("expected 1024x1536 RGBA source")
    crop = crop_rgba(rows)
    crop_width, crop_height = BBOX[2] - BBOX[0], BBOX[3] - BBOX[1]
    crop_path = args.output_dir / "source-shoe-roi-unmodified.png"
    preview_path = args.output_dir / "source-shoe-roi-gray-preview.png"
    write_rgba(crop_path, crop_width, crop_height, crop)
    write_rgb(preview_path, crop_width, crop_height, composite_gray(crop))
    record = {
        "schema": "mohan.pose_atlas.yaw030_shoe_roi.v1",
        "status": "PASS_ROI_EXTRACTION_ONLY",
        "source": {"path": str(args.source.resolve()), "sha256": sha256(args.source), "size": [width, height], "mode": "RGBA"},
        "bbox_xyxy_exclusive": BBOX,
        "paste_origin_xy": BBOX[:2],
        "crop": {"path": str(crop_path.resolve()), "sha256": sha256(crop_path), "size": [crop_width, crop_height], "mode": "RGBA"},
        "preview": {"path": str(preview_path.resolve()), "sha256": sha256(preview_path)},
        "formal_assets_modified": False
    }
    (args.output_dir / "roi-sidecar.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
