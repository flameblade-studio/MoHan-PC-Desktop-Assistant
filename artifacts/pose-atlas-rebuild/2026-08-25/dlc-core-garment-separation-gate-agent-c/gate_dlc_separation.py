from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


REQUIRED_NEW_SLOTS = (
    "core_skin", "body_geometry", "outfit_outer", "outfit_inner",
    "sleeve_left", "sleeve_right", "hand_left", "hand_right",
    "shoe_left", "shoe_right", "ornament_core_fixed_hairpin",
    "ornament_replaceable_headwear", "ornament_replaceable_jewelry",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def bbox(alpha: np.ndarray):
    ys, xs = np.nonzero(alpha > 0)
    if not len(xs):
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)]


def inspect(path: Path) -> dict:
    image = Image.open(path).convert("RGBA")
    rgba = np.asarray(image)
    rgb = rgba[:, :, :3].astype(np.int16)
    alpha = rgba[:, :, 3]
    visible = alpha > 0
    blue = visible & (rgb[:, :, 2] >= rgb[:, :, 0] + 12) & (rgb[:, :, 2] >= rgb[:, :, 1] + 4)
    skin = visible & (rgb[:, :, 0] >= 95) & (rgb[:, :, 0] >= rgb[:, :, 1] + 6) & (rgb[:, :, 1] >= rgb[:, :, 2] - 5)
    yy = np.indices(alpha.shape)[0]
    return {
        "path": str(path), "sha256": sha256(path), "size": list(image.size), "mode": image.mode,
        "alpha_bbox": bbox(alpha), "visible_pixels": int(visible.sum()),
        "blue_garment_proxy_pixels": int(blue.sum()), "skin_proxy_pixels": int(skin.sum()),
        "visible_below_y900": int((visible & (yy >= 900)).sum()),
    }


def contact(view_records: list[dict], out: Path) -> None:
    names = ("body", "base", "sleeve_left", "sleeve_right", "ornament")
    tile_w, tile_h = 245, 400
    canvas = Image.new("RGB", (tile_w * len(names), (tile_h + 36) * len(view_records)), (16, 18, 20))
    draw = ImageDraw.Draw(canvas)
    for row, record in enumerate(view_records):
        for col, name in enumerate(names):
            image = Image.open(record["layers"][name]["path"]).convert("RGBA")
            bg = Image.new("RGBA", image.size, (12, 12, 12, 255)); bg.alpha_composite(image)
            bg.thumbnail((tile_w, tile_h), Image.Resampling.LANCZOS)
            x = col * tile_w + (tile_w - bg.width) // 2
            y = row * (tile_h + 36) + 30
            canvas.paste(bg.convert("RGB"), (x, y))
            draw.text((col * tile_w + 5, row * (tile_h + 36) + 8), f'{record["view_id"]} / {name}', fill=(240, 240, 240))
    canvas.save(out)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-layer-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--views", nargs="+", default=["yaw+000-pitch+00", "yaw+045-pitch+00"])
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    records = []
    for view in args.views:
        legacy = {name: inspect(args.legacy_layer_dir / f"{view}_{name}.png") for name in ("body", "base", "sleeve_left", "sleeve_right", "ornament")}
        expected_paths = {slot: args.legacy_layer_dir / f"{view}_{slot}.png" for slot in REQUIRED_NEW_SLOTS}
        missing = [slot for slot, path in expected_paths.items() if not path.is_file()]
        failures = []
        if legacy["body"]["blue_garment_proxy_pixels"]:
            failures.append("LEGACY_BODY_CONTAINS_GARMENT_PIXELS")
        if legacy["body"]["visible_below_y900"]:
            failures.append("LEGACY_BODY_CONTAINS_LOWER_GARMENT_OR_SHOE_PIXELS")
        if legacy["sleeve_left"]["skin_proxy_pixels"] or legacy["sleeve_right"]["skin_proxy_pixels"]:
            failures.append("LEGACY_SLEEVE_CONTAINS_HAND_OR_SKIN_PIXELS")
        failures.extend(f"MISSING_REQUIRED_SLOT:{slot}" for slot in missing)
        failures.extend([
            "MISSING_EXCLUSIVE_OWNERSHIP_MANIFEST",
            "MISSING_PROTECTED_CORE_MASK",
            "MISSING_TYPED_ORNAMENT_OWNERSHIP",
        ])
        records.append({"view_id": view, "status": "FAIL", "exit_code": 4, "layers": legacy, "failures": failures})

    report = {
        "schema": "mohan.pose-atlas.dlc-separation-audit.v1",
        "contract": "../dlc-layer-contract.json",
        "audit_scope": "legacy formal layers; read-only negative fixture",
        "views": records,
        "overall_status": "FAIL",
        "exit_code": 4,
        "promotion_allowed": False,
        "interpretation": "The legacy files are evidence of migration debt, not a valid naked/core-body source.",
    }
    report_path = args.output_dir / "legacy-negative-audit.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    contact(records, args.output_dir / "yaw000-yaw045-layer-ownership-contact.png")
    print(json.dumps({"report": str(report_path), "views": len(records), "status": "FAIL", "exit_code": 4}))
    return 4


if __name__ == "__main__":
    raise SystemExit(main())
