"""Atomically merge exactly 24 accepted per-view fragments."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import uuid
from pathlib import Path

from PIL import Image


VIEWS = tuple(f"yaw{yaw:+04d}-pitch+00" for yaw in range(-180, 180, 15))
LAYERS = (
    "body", "hair_back", "base", "jaw", "oral_cavity", "teeth_tongue",
    "lip_lower", "lip_upper", "corner_left", "corner_right", "blush_left",
    "blush_right", "iris_left", "iris_right", "eyelid_left", "eyelid_right",
    "eyeliner_left", "eyeliner_right", "brow_left", "brow_right", "hair_left",
    "hair_right", "sleeve_left", "sleeve_right", "ornament",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_fragment(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema") != "mohan.pose_atlas.view_fragment" or value.get("version") != "1.0":
        raise ValueError(f"invalid fragment schema: {path}")
    if value.get("accepted") is not True:
        raise ValueError(f"fragment is not accepted: {path}")
    if value.get("canvas") != {"width": 1024, "height": 1536}:
        raise ValueError(f"invalid canvas: {path}")
    if value.get("offset_x") != 0 or value.get("offset_y") != 0:
        raise ValueError(f"invalid full-canvas offset: {path}")
    if value.get("body_center") != [512, 1292]:
        raise ValueError(f"invalid body center: {path}")
    layers = value.get("layers")
    if not isinstance(layers, list) or [item.get("id") for item in layers] != list(LAYERS):
        raise ValueError(f"invalid 25-layer order: {path}")
    for item in layers:
        asset = Path(item["path"])
        if not asset.is_file() or sha256(asset) != item.get("sha256"):
            raise ValueError(f"layer missing or hash drifted: {asset}")
        with Image.open(asset) as image:
            if image.mode != "RGBA" or image.size != (1024, 1536):
                raise ValueError(f"invalid layer image: {asset}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fragments-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite: {args.output}")
    paths = tuple(args.fragments_root.rglob("*.manifest-fragment.json"))
    fragments = [validate_fragment(path) for path in paths]
    by_view: dict[str, dict] = {}
    for fragment in fragments:
        view = fragment.get("view_id")
        if view not in VIEWS or view in by_view:
            raise ValueError(f"invalid or duplicate view fragment: {view}")
        by_view[view] = fragment
    missing = [view for view in VIEWS if view not in by_view]
    if missing or len(by_view) != 24:
        raise ValueError(f"exact accepted 24 required; accepted={len(by_view)} missing={missing}")

    manifest = {
        "schema": "mohan.pose_atlas.layer_manifest",
        "version": "1.0",
        "canvas": {"width": 1024, "height": 1536},
        "view_ids": list(VIEWS),
        "layer_ids": list(LAYERS),
        "z_order": list(LAYERS),
        "offset_policy": {"offset_x": 0, "offset_y": 0, "full_canvas_registered": True},
        "body_center": [512, 1292],
        "views": [by_view[view] for view in VIEWS],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(f".{args.output.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, args.output)
    print(f"PASS_LAYER_MANIFEST_EXACT24 output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
