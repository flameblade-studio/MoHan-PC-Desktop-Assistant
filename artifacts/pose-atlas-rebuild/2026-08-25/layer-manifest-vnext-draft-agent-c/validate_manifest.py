from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


VIEWS = [f"yaw{yaw:+04d}-pitch+00" for yaw in range(-180, 180, 15)]
CHARACTER = [
    "body", "hair_back", "base", "jaw", "oral_cavity", "teeth_tongue", "lip_lower", "lip_upper",
    "corner_left", "corner_right", "blush_left", "blush_right", "iris_left", "iris_right",
    "eyelid_left", "eyelid_right", "eyeliner_left", "eyeliner_right", "brow_left", "brow_right",
    "hair_left", "hair_right", "sleeve_left", "sleeve_right", "ornament",
]
OUTFITS = ["innerwear", "skirt", "outerwear", "sleeve-left", "sleeve-right", "shoe-left", "shoe-right"]


def fail(message: str) -> int:
    print(f"FAIL: {message}")
    return 4


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--production", action="store_true")
    args = parser.parse_args()
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    if data.get("canvas") != {"width": 1024, "height": 1536, "mode": "RGBA", "registration": "full-canvas"}:
        return fail("canvas contract")
    if data.get("body_center_constant") != [512, 1292]:
        return fail("body center")
    if data.get("promotion_allowed") is not False:
        return fail("draft promotion must be false")
    if data.get("ownership_policy") != {
        "body_may_contain_garment": False, "body_may_contain_shoes": False,
        "hands_may_contain_fabric": False, "garments_may_contain_identity_or_hand_skin": False,
        "fixed_hairpin_side": "character_right", "mirroring_allowed": False,
        "one_authoritative_owner_per_pixel": True,
    }:
        return fail("ownership policy")
    views = data.get("views", [])
    if [item.get("view_id") for item in views] != VIEWS:
        return fail("exact 24 view IDs/order")
    for view in views:
        if view.get("body_center") != [512, 1292]:
            return fail(f"body center {view.get('view_id')}")
        layers = view.get("character_layers", [])
        outfits = view.get("outfit_slots", [])
        if [item.get("layer_id") for item in layers] != CHARACTER:
            return fail(f"character 25 {view.get('view_id')}")
        if [item.get("layer_id") for item in outfits] != OUTFITS:
            return fail(f"outfit 7 {view.get('view_id')}")
        for asset in layers + outfits:
            if asset.get("offset_x") != 0 or asset.get("offset_y") != 0:
                return fail(f"full-canvas offset {view.get('view_id')} {asset.get('layer_id')}")
            for field in ("path", "asset_sha256", "alpha_mask_sha256", "source_provenance", "license_provenance", "qa"):
                if field not in asset:
                    return fail(f"missing {field}")
            if asset["qa"].get("status") == "PASS":
                path = asset.get("path")
                expected = asset.get("asset_sha256")
                if not path or not expected or not Path(path).is_file():
                    return fail("PASS points to missing file")
                actual = hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()
                if actual != expected.upper():
                    return fail("PASS hash mismatch")
        body = next(item for item in layers if item["layer_id"] == "body")
        if body.get("semantics") != "core_skin_only_no_garment_no_shoes_no_hands":
            return fail("body welded semantics")
        for alias in ("sleeve_left", "sleeve_right"):
            item = next(entry for entry in layers if entry["layer_id"] == alias)
            if "no_fabric" not in item.get("semantics", ""):
                return fail("hand alias contains fabric")
    if args.production:
        unresolved = sum(
            asset["qa"].get("status") != "PASS"
            for view in views for asset in view["character_layers"] + view["outfit_slots"]
        )
        if unresolved:
            return fail(f"production unresolved assets={unresolved}")
    print("PASS: vNext draft structure valid; no asset completion implied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
