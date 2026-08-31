from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


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
DOMAINS = (
    "core_anatomy", "garment", "ornament_fixed", "ornament_swappable", "blocked_mixed",
)
SLOTS = {
    "core_anatomy": ("core_skin", "hand_left", "hand_right", "foot_left", "foot_right"),
    "garment": ("innerwear", "outerwear", "skirt", "sleeve_left", "sleeve_right", "shoe_left", "shoe_right"),
    "ornament_fixed": ("fixed_hairpin",),
    "ornament_swappable": ("headwear", "jewelry"),
}
MASK_FIELDS = (
    "core_mask", "hand_left_mask", "hand_right_mask", "foot_left_mask", "foot_right_mask",
    "garment_mask", "ornament_fixed_mask", "ornament_swappable_mask",
)
SHA256 = re.compile(r"[0-9A-F]{64}\Z")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _record_errors(record: object, *, mask: bool) -> list[str]:
    if not isinstance(record, dict):
        return ["record must be an object"]
    required = (
        {"view_id", "field", "path", "sha256", "width", "height", "mode", "qa_status"}
        if mask
        else {
            "view_id", "slot", "domain", "path", "sha256", "width", "height", "mode",
            "offset_x", "offset_y", "source_provenance", "license_provenance", "qa_status",
        }
    )
    if set(record) != required:
        return ["record fields disagree with production contract"]
    errors: list[str] = []
    if record["view_id"] not in VIEWS:
        errors.append("unknown view")
    if mask:
        if record["field"] not in MASK_FIELDS:
            errors.append("unknown mask field")
    else:
        if record["domain"] not in SLOTS or record["slot"] not in SLOTS[record["domain"]]:
            errors.append("slot/domain mismatch")
        if record["offset_x"] != 0 or record["offset_y"] != 0:
            errors.append("asset must be full-canvas registered")
        if not isinstance(record["source_provenance"], dict) or not record["source_provenance"]:
            errors.append("missing source provenance")
        if not isinstance(record["license_provenance"], dict) or not record["license_provenance"]:
            errors.append("missing license provenance")
    if not isinstance(record["path"], str) or not record["path"]:
        errors.append("missing path")
    if not isinstance(record["sha256"], str) or SHA256.fullmatch(record["sha256"]) is None:
        errors.append("invalid SHA256")
    if (record["width"], record["height"], record["mode"]) != (1024, 1536, "RGBA8"):
        errors.append("wrong canvas or mode")
    if record["qa_status"] != "PASS":
        errors.append("production record QA is not PASS")
    return errors


def validate(target: Path) -> tuple[dict[str, object], int]:
    payload = json.loads(target.read_text(encoding="utf-8"))
    errors: list[str] = []
    kind = payload.get("manifest_kind")
    if payload.get("schema") != "mohan.poseatlas.vnext.ownership-manifest/v1":
        errors.append("wrong schema")
    if payload.get("views") != list(VIEWS):
        errors.append("views must equal the canonical 24-view list")
    if payload.get("legacy_25_layers") != list(LAYERS):
        errors.append("legacy layers must equal the canonical 25-layer z-order")
    ownership = payload.get("legacy_layer_ownership")
    if not isinstance(ownership, dict) or set(ownership) != set(LAYERS):
        errors.append("legacy ownership must map all and only 25 layers")
        ownership = {}
    elif any(value not in DOMAINS for value in ownership.values()):
        errors.append("unknown legacy ownership domain")
    if ownership.get("body") != "blocked_mixed":
        errors.append("mixed legacy body must remain blocked_mixed")
    if ownership.get("ornament") != "blocked_mixed":
        errors.append("mixed legacy ornament must remain blocked_mixed")
    if ownership.get("sleeve_left") != "garment" or ownership.get("sleeve_right") != "garment":
        errors.append("legacy sleeves must be garment-owned")
    if payload.get("ownership_domains") != list(DOMAINS):
        errors.append("ownership domains disagree")
    slots = payload.get("vnext_slots")
    if not isinstance(slots, dict) or slots != {key: list(value) for key, value in SLOTS.items()}:
        errors.append("vNext slots disagree")
    if payload.get("ownership_mask_fields") != list(MASK_FIELDS):
        errors.append("ownership mask fields disagree")
    if payload.get("canvas") != {"width": 1024, "height": 1536, "mode": "RGBA8", "offset_x": 0, "offset_y": 0}:
        errors.append("canvas contract disagrees")
    if payload.get("formal_600_complete") is not False:
        errors.append("formal_600_complete must remain false")
    if payload.get("promotion_allowed") is not False:
        errors.append("promotion_allowed must remain false")

    assets = payload.get("asset_records")
    masks = payload.get("mask_records")
    if not isinstance(assets, list) or not isinstance(masks, list):
        errors.append("asset_records and mask_records must be arrays")
        assets, masks = [], []
    if kind == "CONTRACT_FIXTURE":
        if payload.get("fixture_only") is not True:
            errors.append("contract fixture must set fixture_only=true")
        if assets or masks:
            errors.append("contract fixture must not invent asset or mask records")
    elif kind == "PRODUCTION":
        if payload.get("fixture_only") is not False:
            errors.append("production manifest must set fixture_only=false")
        expected_assets = len(VIEWS) * sum(len(values) for values in SLOTS.values())
        expected_masks = len(VIEWS) * len(MASK_FIELDS)
        if len(assets) != expected_assets:
            errors.append(f"production requires exactly {expected_assets} asset records")
        if len(masks) != expected_masks:
            errors.append(f"production requires exactly {expected_masks} mask records")
        for index, record in enumerate(assets):
            errors.extend(f"asset[{index}]: {error}" for error in _record_errors(record, mask=False))
        for index, record in enumerate(masks):
            errors.extend(f"mask[{index}]: {error}" for error in _record_errors(record, mask=True))
    else:
        errors.append("unknown manifest_kind")

    status = "PASS_CONTRACT_FIXTURE" if kind == "CONTRACT_FIXTURE" and not errors else "BLOCK"
    if kind == "PRODUCTION" and not errors:
        status = "PASS_STRUCTURE_ONLY_NOT_PROMOTED"
    report = {
        "schema": "mohan.poseatlas.vnext.ownership-validation/v1",
        "target": str(target),
        "target_sha256": _sha256(target),
        "status": status,
        "manifest_kind": kind,
        "formal_asset_write": False,
        "runtime_write": False,
        "promotion_allowed": False,
        "formal_600_complete": False,
        "facts": {
            "views": len(payload.get("views", [])) if isinstance(payload.get("views"), list) else 0,
            "legacy_layers": len(ownership),
            "vnext_asset_slots_per_view": sum(len(values) for values in SLOTS.values()),
            "ownership_masks_per_view": len(MASK_FIELDS),
            "asset_records": len(assets),
            "mask_records": len(masks),
        },
        "errors": errors,
    }
    return report, 0 if not errors else 4


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, required=True)
    args = parser.parse_args()
    target = args.target.resolve()
    report, exit_code = validate(target)
    target.with_suffix(".validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
