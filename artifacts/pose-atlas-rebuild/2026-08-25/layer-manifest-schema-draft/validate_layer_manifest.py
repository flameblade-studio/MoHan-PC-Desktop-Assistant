from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from PIL import Image

VIEW_IDS = [f"yaw{yaw:+04d}-pitch+00" for yaw in range(-180, 180, 15)]
LAYER_IDS = [
    "base", "jaw", "oral_cavity", "teeth_tongue", "lip_lower", "lip_upper",
    "corner_left", "corner_right", "blush_left", "blush_right", "iris_left",
    "iris_right", "eyelid_left", "eyelid_right", "eyeliner_left",
    "eyeliner_right", "brow_left", "brow_right", "body", "hair_back",
    "hair_left", "hair_right", "sleeve_left", "sleeve_right", "ornament",
]
Z_ORDER = [
    "body", "hair_back", "base", "jaw", "oral_cavity", "teeth_tongue",
    "lip_lower", "lip_upper", "corner_left", "corner_right", "blush_left",
    "blush_right", "iris_left", "iris_right", "eyelid_left", "eyelid_right",
    "eyeliner_left", "eyeliner_right", "brow_left", "brow_right", "hair_left",
    "hair_right", "sleeve_left", "sleeve_right", "ornament",
]
ALLOWED_LICENSES = {
    "MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "CC0-1.0", "CC-BY",
}
PERMANENT_DENY = ["nvdiffrast", "zero123plus-weights"]
DENIED_SOURCE_TOKENS = (
    "nvdiffrast",
    "nvlabs/nvdiffrast",
    "zero123++",
    "zero123plus-v1.2",
    "sudo-ai/zero123plus-v1.2",
)
SHA256_RE = re.compile(r"^[0-9A-Fa-f]{64}$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate_png(path: Path, expected_hash: str, errors: list[str]) -> None:
    try:
        with Image.open(path) as image:
            image.load()
            require(image.format == "PNG", f"{path}: format must be PNG", errors)
            require(image.mode == "RGBA", f"{path}: mode must be RGBA, got {image.mode}", errors)
            require(image.size == (1024, 1536), f"{path}: size must be 1024x1536, got {image.size}", errors)
            if image.mode == "RGBA" and image.size == (1024, 1536):
                corners = [image.getpixel(point)[3] for point in ((0, 0), (1023, 0), (0, 1535), (1023, 1535))]
                require(corners == [0, 0, 0, 0], f"{path}: four corner alpha values must all be 0, got {corners}", errors)
    except Exception as exc:  # Pillow reports malformed or unsupported image data.
        errors.append(f"{path}: unreadable image: {exc}")
        return
    require(sha256(path) == expected_hash.upper(), f"{path}: SHA256 mismatch", errors)


def validate_manifest(path: Path, allow_missing_assets: bool) -> list[str]:
    errors: list[str] = []
    try:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"manifest unreadable: {exc}"]

    require(data.get("schema") == "mohan.pose_atlas.layer_manifest.v4-draft", "wrong schema", errors)
    require(data.get("status") == "DRAFT_NOT_FORMAL_ASSET_MANIFEST", "draft status marker missing", errors)
    require(data.get("permanent_deny") == {
        "components": PERMANENT_DENY,
        "download_forbidden": True,
        "use_forbidden": True,
        "instantmesh_source_code": "retained_apache_2_0_history",
        "instantmesh_e2e_pipeline": "disabled_due_to_denied_dependencies",
    }, "permanent deny contract mismatch", errors)
    require(data.get("canvas") == {"width": 1024, "height": 1536, "mode": "RGBA", "format": "PNG"}, "canvas contract mismatch", errors)
    require(data.get("view_ids") == VIEW_IDS, "view_ids must be the exact ordered 24-view list", errors)
    require(data.get("layer_ids") == LAYER_IDS, "layer_ids must be the exact ordered 25-layer list", errors)
    require(data.get("z_order") == Z_ORDER, "z_order mismatch", errors)
    require(data.get("body_center_constant") == [512, 1292], "BODY_CENTER_CONSTANT mismatch", errors)
    require(data.get("offset_policy") == {"type": "full-canvas-registered", "offset_x": 0, "offset_y": 0}, "offset policy mismatch", errors)
    require(data.get("transition_contract") == {"tick_hz": 50, "tick_ms": 20, "yaw_step_degrees": 15, "wrap_from": "yaw+165-pitch+00", "wrap_to": "yaw-180-pitch+00", "bounded_weights": True}, "transition contract mismatch", errors)
    alpha = data.get("alpha_policy", {})
    require(alpha.get("required_mode") == "RGBA" and alpha.get("corner_alpha") == 0 and alpha.get("transparent_rgb") == [0, 0, 0], "alpha policy mismatch", errors)
    require(isinstance(data.get("anchors"), dict) and isinstance(data.get("mask_references"), dict), "anchors/mask references missing", errors)
    require(isinstance(data.get("source_license_provenance"), list) and data["source_license_provenance"], "source/license provenance missing", errors)
    for source in data.get("source_license_provenance", []):
        require(source.get("license") in ALLOWED_LICENSES, f"forbidden or unknown source license: {source.get('license')}", errors)
        searchable = " ".join(str(source.get(field, "")) for field in ("name", "source", "upstream", "url")).casefold()
        for denied in DENIED_SOURCE_TOKENS:
            require(denied not in searchable, f"permanently denied source/component referenced: {denied}", errors)

    assets = data.get("assets")
    require(isinstance(assets, dict), "assets must be an object", errors)
    if not isinstance(assets, dict):
        return errors
    expected_names = {f"{view}_{layer}.png" for view in VIEW_IDS for layer in LAYER_IDS}
    require(set(assets) == expected_names, f"asset key set mismatch: expected 600, got {len(assets)}", errors)
    require(len(assets) == 600, f"asset count must be 600, got {len(assets)}", errors)

    root = path.parent
    for name, asset in assets.items():
        if name not in expected_names or not isinstance(asset, dict):
            continue
        expected_view, expected_layer = next(
            (view, layer) for view in VIEW_IDS for layer in LAYER_IDS if name == f"{view}_{layer}.png"
        )
        require(asset.get("view_id") == expected_view, f"{name}: wrong view_id", errors)
        require(asset.get("layer_id") == expected_layer, f"{name}: wrong layer_id", errors)
        require(asset.get("file") == name, f"{name}: file must equal key", errors)
        require(asset.get("offset_x") == 0 and asset.get("offset_y") == 0, f"{name}: offsets must be zero", errors)
        require(asset.get("qa_status") in {"pending", "pass", "fail", "quarantined"}, f"{name}: invalid qa_status", errors)
        require(bool(SHA256_RE.fullmatch(str(asset.get("sha256", "")))), f"{name}: invalid SHA256 field", errors)
        license_id = asset.get("license")
        require(license_id in ALLOWED_LICENSES, f"{name}: forbidden or unknown license: {license_id}", errors)
        searchable = " ".join(str(asset.get(field, "")) for field in ("source", "source_name", "upstream", "url")).casefold()
        for denied in DENIED_SOURCE_TOKENS:
            require(denied not in searchable, f"{name}: permanently denied source/component referenced: {denied}", errors)
        asset_path = root / name
        if asset_path.is_file():
            validate_png(asset_path, str(asset.get("sha256", "")), errors)
        elif not allow_missing_assets:
            errors.append(f"{name}: asset file missing")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--allow-missing-assets", action="store_true", help="Fixture/schema test only; forbidden for formal asset acceptance.")
    args = parser.parse_args()
    errors = validate_manifest(args.manifest.resolve(), args.allow_missing_assets)
    result = {"manifest": str(args.manifest.resolve()), "allow_missing_assets": args.allow_missing_assets, "ok": not errors, "error_count": len(errors), "errors": errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    sys.exit(main())
