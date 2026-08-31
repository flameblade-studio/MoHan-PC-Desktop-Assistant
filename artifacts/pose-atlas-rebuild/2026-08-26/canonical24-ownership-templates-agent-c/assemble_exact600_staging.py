"""Atomically assemble 24 accepted view fragments into an exact-600 staging set."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import uuid
from pathlib import Path

import numpy as np
from PIL import Image


VIEWS = tuple(f"yaw{yaw:+04d}-pitch+00" for yaw in range(-180, 180, 15))
LAYERS = (
    "body", "hair_back", "base", "jaw", "oral_cavity", "teeth_tongue",
    "lip_lower", "lip_upper", "corner_left", "corner_right", "blush_left",
    "blush_right", "iris_left", "iris_right", "eyelid_left", "eyelid_right",
    "eyeliner_left", "eyeliner_right", "brow_left", "brow_right", "hair_left",
    "hair_right", "sleeve_left", "sleeve_right", "ornament",
)
SIZE = (1024, 1536)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verified_asset(record: dict, path_key: str, hash_key: str) -> Path:
    path = Path(record[path_key]).resolve()
    if not path.is_file() or sha256(path).lower() != str(record[hash_key]).lower():
        raise ValueError(f"asset missing or hash drifted: {path}")
    return path


def read_mask(record: dict, hash_key: str = "sha256") -> np.ndarray:
    path = verified_asset(record, "mask", hash_key)
    with Image.open(path) as image:
        if image.size != SIZE:
            raise ValueError(f"invalid ownership mask canvas: {path}")
        return np.asarray(image.convert("L"), dtype=np.uint8) > 0


def validate_fragment(path: Path) -> tuple[dict, list[tuple[str, Path, str]]]:
    fragment = json.loads(path.read_text(encoding="utf-8"))
    view = fragment.get("view_id")
    if fragment.get("schema") != "mohan.pose_atlas.view_fragment":
        raise ValueError(f"invalid fragment schema: {path}")
    if fragment.get("version") != "1.0" or fragment.get("accepted") is not True:
        raise ValueError(f"fragment is not accepted: {path}")
    if view not in VIEWS:
        raise ValueError(f"invalid canonical view: {view}")
    if fragment.get("canvas") != {"width": 1024, "height": 1536}:
        raise ValueError(f"invalid canvas: {path}")
    if (fragment.get("offset_x"), fragment.get("offset_y")) != (0, 0):
        raise ValueError(f"invalid full-canvas registration: {path}")
    if fragment.get("body_center") != [512, 1292]:
        raise ValueError(f"invalid body center: {path}")
    recomposition = fragment.get("recomposition", {})
    if recomposition.get("diff_pixels") != 0 or recomposition.get("max_channel_error") != 0:
        raise ValueError(f"recomposition is not exact: {path}")

    layers = fragment.get("layers")
    if not isinstance(layers, list) or [item.get("id") for item in layers] != list(LAYERS):
        raise ValueError(f"invalid 25-layer order: {path}")
    assets: list[tuple[str, Path, str]] = []
    for item in layers:
        source = verified_asset(item, "path", "sha256")
        with Image.open(source) as image:
            if image.mode != "RGBA" or image.size != SIZE:
                raise ValueError(f"invalid layer image: {source}")
        expected_name = f"{view}_{item['id']}.png"
        if source.name != expected_name:
            raise ValueError(f"noncanonical layer filename: {source}")
        assets.append((expected_name, source, str(item["sha256"]).lower()))

    ownership = fragment.get("ownership", {})
    core = read_mask(ownership["core"])
    outfit = read_mask(ownership["default_outfit"], "mask_sha256")
    ornament = read_mask(ownership["ornament"], "mask_sha256")
    read_mask(ownership["hair"])
    verified_asset(ownership["default_outfit"], "overlay", "overlay_sha256")
    verified_asset(ownership["ornament"], "overlay", "overlay_sha256")
    if np.any(core & outfit) or np.any(core & ornament) or np.any(outfit & ornament):
        raise ValueError(f"ownership masks overlap: {path}")
    return fragment, assets


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fragments-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite exact600 staging: {output}")

    paths = tuple(args.fragments_root.resolve().rglob("*.manifest-fragment.json"))
    by_view: dict[str, tuple[dict, list[tuple[str, Path, str]]]] = {}
    for path in paths:
        fragment, assets = validate_fragment(path)
        view = str(fragment["view_id"])
        if view in by_view:
            raise ValueError(f"duplicate accepted view fragment: {view}")
        by_view[view] = (fragment, assets)
    missing = [view for view in VIEWS if view not in by_view]
    if missing or len(by_view) != 24:
        raise ValueError(f"exact accepted 24 required; accepted={len(by_view)} missing={missing}")

    expected_names = {
        f"{view}_{layer}.png" for view in VIEWS for layer in LAYERS
    }
    transaction = output.with_name(f".{output.name}.{uuid.uuid4().hex}.tmp")
    layers_dir = transaction / "layers"
    try:
        layers_dir.mkdir(parents=True)
        records: list[dict[str, str]] = []
        for view in VIEWS:
            _, assets = by_view[view]
            for name, source, expected_hash in assets:
                target = layers_dir / name
                shutil.copyfile(source, target)
                actual_hash = sha256(target).lower()
                if actual_hash != expected_hash:
                    raise ValueError(f"copy hash mismatch: {target}")
                records.append({"path": f"layers/{name}", "sha256": actual_hash})
        actual_names = {path.name for path in layers_dir.glob("*.png")}
        if actual_names != expected_names or len(actual_names) != 600:
            raise ValueError(
                f"exact600 filename gate failed: actual={len(actual_names)} expected=600"
            )
        manifest = {
            "schema": "mohan.pose_atlas.exact600_staging",
            "version": "1.0",
            "view_ids": list(VIEWS),
            "layer_ids": list(LAYERS),
            "file_count": 600,
            "files": records,
        }
        (transaction / "exact600-staging.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(transaction, output)
    except Exception:
        if transaction.exists():
            shutil.rmtree(transaction)
        raise
    print(f"PASS_EXACT600_ATOMIC_STAGING files=600 output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
