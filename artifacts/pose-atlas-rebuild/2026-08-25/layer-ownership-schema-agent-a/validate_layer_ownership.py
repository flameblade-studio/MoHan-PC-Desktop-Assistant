from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
LAYERS = (
    "body", "hair_back", "base", "jaw", "oral_cavity", "teeth_tongue",
    "lip_lower", "lip_upper", "corner_left", "corner_right", "blush_left",
    "blush_right", "iris_left", "iris_right", "eyelid_left", "eyelid_right",
    "eyeliner_left", "eyeliner_right", "brow_left", "brow_right", "hair_left",
    "hair_right", "sleeve_left", "sleeve_right", "ornament",
)
FACE = frozenset(LAYERS[2:20])
HAIR = frozenset({"hair_back", "hair_left", "hair_right"})
SLEEVES = frozenset({"sleeve_left", "sleeve_right"})
GARMENT_TAGS = frozenset({"garment", "outerwear", "bodice", "sleeve", "skirt", "trousers", "legwear", "swimwear"})


def load_fixture(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if "base_fixture" not in raw:
        return raw
    data = copy.deepcopy(json.loads((FIXTURES / raw["base_fixture"]).read_text(encoding="utf-8")))
    mutation = raw["mutation"]
    target = next(item for item in data["assets"] if item["asset_id"] == mutation["asset_id"])
    target.update({key: value for key, value in mutation.items() if key != "asset_id"})
    return data


def validate(data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("schema") != "mohan.pose-atlas.layer-ownership-manifest.v1": errors.append("schema")
    if data.get("status") != "SYNTHETIC_SCHEMA_FIXTURE_NOT_PRODUCTION_ASSET_EVIDENCE": errors.append("truth_status")
    if data.get("canvas") != {"width": 1024, "height": 1536, "registration": "full-canvas"}: errors.append("canvas")
    if data.get("views_expected") != 24 or data.get("layers_expected") != 25: errors.append("counts")
    if data.get("compose_phases") != ["identity_and_body_core", "selected_appearance"]: errors.append("two_phase_order")
    slots = data.get("layer_slots", [])
    if tuple(item.get("layer") for item in slots) != LAYERS: errors.append("layer_slot_order_or_count")
    if len({item.get("layer") for item in slots}) != 25: errors.append("layer_slot_unique")
    allowed_by_layer = {item["layer"]: set(item.get("allowed_owners", [])) for item in slots if "layer" in item}
    for asset in data.get("assets", []):
        layer, owner = asset.get("layer"), asset.get("owner")
        if asset.get("synthetic") is not True: errors.append("fixture_not_marked_synthetic")
        if layer not in allowed_by_layer or owner not in allowed_by_layer[layer]: errors.append(f"owner_not_allowed:{asset.get('asset_id')}")
        if layer == "body":
            if owner != "body_skin": errors.append("body_owner")
            if GARMENT_TAGS.intersection(asset.get("content_tags", [])): errors.append("body_contains_garment")
            if asset.get("phase") != "identity_and_body_core": errors.append("body_phase")
        if layer in FACE and (owner != "identity_core" or asset.get("phase") != "identity_and_body_core"):
            errors.append(f"face_identity_boundary:{layer}")
        if layer in HAIR and owner not in {"built_in_hair", "dlc_hair"}: errors.append(f"hair_owner:{layer}")
        if layer in SLEEVES and (owner not in {"built_in_garment", "dlc_garment"} or asset.get("phase") != "selected_appearance"):
            errors.append(f"sleeve_boundary:{layer}")
        attachment = asset.get("attachment")
        if layer in HAIR | SLEEVES | {"ornament"}:
            if not isinstance(attachment, dict) or attachment.get("owner") != owner or not attachment.get("point") or attachment.get("physical_side") not in {"left", "right", "center"}:
                errors.append(f"attachment_owner:{layer}")
        if layer == "ornament":
            component_owners = asset.get("component_owners", [owner])
            if len(set(component_owners)) != 1 or set(component_owners) != {owner}:
                errors.append("ornament_mixed_owner")
    return sorted(set(errors))


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_layer_ownership.py FIXTURE", file=sys.stderr)
        return 2
    path = Path(sys.argv[1]).resolve()
    errors = validate(load_fixture(path))
    payload = {"fixture": path.name, "status": "PASS" if not errors else "FAIL", "errors": errors}
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
