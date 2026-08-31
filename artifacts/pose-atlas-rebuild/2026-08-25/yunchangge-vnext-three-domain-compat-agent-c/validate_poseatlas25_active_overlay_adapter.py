from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any


VIEWS = [
    *(f"yaw-{yaw:03d}-pitch+00" for yaw in range(180, 0, -15)),
    *(f"yaw+{yaw:03d}-pitch+00" for yaw in range(0, 180, 15)),
]
Z_ORDER = [
    "body", "hair_back", "base", "jaw", "oral_cavity", "teeth_tongue",
    "lip_lower", "lip_upper", "corner_left", "corner_right", "blush_left",
    "blush_right", "iris_left", "iris_right", "eyelid_left", "eyelid_right",
    "eyeliner_left", "eyeliner_right", "brow_left", "brow_right",
    "hair_left", "hair_right", "sleeve_left", "sleeve_right", "ornament",
]
IDENTITY_FACE = {
    "base", "jaw", "oral_cavity", "teeth_tongue", "lip_lower", "lip_upper",
    "corner_left", "corner_right", "blush_left", "blush_right", "iris_left",
    "iris_right", "eyelid_left", "eyelid_right", "eyeliner_left",
    "eyeliner_right", "brow_left", "brow_right",
}


def validate(record: dict[str, Any], readiness: bool = False) -> list[str]:
    errors: list[str] = []
    views = record.get("view_contract", {}).get("view_ids")
    if views != VIEWS or len(views or []) != 24 or len(set(views or [])) != 24:
        errors.append("adapter requires exact ordered 24 canonical yaw views")
    policy = record.get("view_contract", {})
    if policy.get("outfit_pack_v2_31_view_direct_binding") != "INCOMPATIBLE":
        errors.append("31-view pack cannot bind directly to 24-view layered adapter")
    if policy.get("legacy_seven_view_policy") != "REJECT_AT_THIS_ADAPTER_BOUNDARY_USE_EXISTING_FLAT_OVERLAY_PATH":
        errors.append("legacy seven views must remain outside layered adapter")
    if record.get("legacy_poseatlas_z_order") != Z_ORDER:
        errors.append("legacy 25-layer z-order mismatch")

    owners = record.get("layer_ownership", {})
    if set(owners) != set(Z_ORDER):
        errors.append("ownership map must cover exact 25 legacy layers")
    if owners.get("body") != "human-core-blocked-mixed":
        errors.append("mixed body must remain blocked human core")
    for layer in ("hair_back", "hair_left", "hair_right"):
        if owners.get(layer) != "identity-hair-fixed":
            errors.append(f"{layer} must remain fixed identity hair")
    for layer in IDENTITY_FACE:
        if owners.get(layer) != "identity-face-fixed":
            errors.append(f"{layer} must remain fixed identity face")
    for layer in ("sleeve_left", "sleeve_right"):
        if owners.get(layer) != "garment-dlc-replaceable":
            errors.append(f"{layer} must remain replaceable garment")
    if owners.get("ornament") != "legacy-ornament-blocked-unsplit":
        errors.append("legacy ornament must remain blocked until split")

    domains = record.get("vnext_domains", {})
    hairpin = domains.get("fixed_hairpin", {})
    accessories = domains.get("replaceable_accessories", {})
    garments = domains.get("garment_slots", {})
    if hairpin.get("domain") != "identity-fixed-ornament" or hairpin.get("replaceable") is not False:
        errors.append("fixed hairpin must be non-replaceable identity ornament")
    if accessories.get("domain") != "accessory-dlc" or accessories.get("replaceable") is not True:
        errors.append("replaceable accessories must remain accessory DLC")
    if garments.get("domain") != "garment-dlc":
        errors.append("garment slots must remain garment DLC")

    masks = record.get("ownership_mask_contract", {})
    if masks.get("full_canvas_registered") is not True or masks.get("offset") != [0, 0]:
        errors.append("ownership masks must be full-canvas registered at zero offset")
    if masks.get("mutually_exclusive_domains") is not True:
        errors.append("ownership domains must be mutually exclusive")
    if masks.get("complete_coverage_for_nontransparent_pixels") is not True:
        errors.append("ownership masks must cover every visible pixel")
    if masks.get("transparent_empty_mask_rejected") is not True:
        errors.append("transparent empty masks must be rejected")
    if masks.get("left_right_hash_reuse_rejected") is not True:
        errors.append("left/right mask hash reuse must be rejected")
    mask_records = masks.get("mask_records")
    if mask_records != "UNRESOLVED" and not (
        isinstance(mask_records, list) and len(mask_records) == 24
    ):
        errors.append("resolved ownership masks require exactly 24 view records")

    recomposition = record.get("recomposition_contract", {})
    if recomposition.get("pass") is True and recomposition.get("exact_diff_pixels") != 0:
        errors.append("recomposition pass cannot carry a nonzero exact diff")
    if record.get("promotion_allowed") is not False:
        errors.append("draft promotion must remain false")
    if record.get("formal_600_complete") is not False:
        errors.append("draft formal_600_complete must remain false")
    if readiness:
        if mask_records in (None, "UNRESOLVED"):
            errors.append("readiness requires real ownership mask records")
        if hairpin.get("required_mask") == "UNRESOLVED" or hairpin.get("asset") is None:
            errors.append("readiness requires split fixed-hairpin asset and mask")
        if accessories.get("required_masks") == "UNRESOLVED":
            errors.append("readiness requires replaceable accessory masks")
        if garments.get("required_masks") == "UNRESOLVED" or garments.get("assets") is None:
            errors.append("readiness requires real garment assets and masks")
        if record.get("adapter_z_order_contract", {}).get("explicit_insertion_table") == "UNRESOLVED":
            errors.append("readiness requires explicit DLC insertion z-order")
        if recomposition.get("exact_diff_pixels") != 0 or recomposition.get("pass") is not True:
            errors.append("readiness requires exact recomposition diff of zero")
    return errors


def mutate(record: dict[str, Any], name: str) -> None:
    views = record["view_contract"]["view_ids"]
    if name == "missing_yaw":
        views.pop()
    elif name == "duplicate_yaw":
        views[-1] = views[0]
    elif name == "bind_31_views":
        record["view_contract"]["outfit_pack_v2_31_view_direct_binding"] = "COMPATIBLE"
    elif name == "wrong_z_order":
        record["legacy_poseatlas_z_order"][0:2] = reversed(record["legacy_poseatlas_z_order"][0:2])
    elif name == "hair_replaceable":
        record["layer_ownership"]["hair_left"] = "garment-dlc-replaceable"
    elif name == "hairpin_replaceable":
        record["vnext_domains"]["fixed_hairpin"]["replaceable"] = True
    elif name == "accessory_fixed":
        record["vnext_domains"]["replaceable_accessories"]["replaceable"] = False
    elif name == "body_as_garment":
        record["layer_ownership"]["body"] = "garment-dlc-replaceable"
    elif name == "claim_masks_ready":
        record["ownership_mask_contract"]["mask_records"] = []
    elif name == "nonzero_diff_pass":
        record["recomposition_contract"].update({"exact_diff_pixels": 12, "pass": True})
    elif name == "false_promotion":
        record["promotion_allowed"] = True
    elif name == "false_600":
        record["formal_600_complete"] = True
    else:
        raise ValueError(f"unknown mutation: {name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("spec", type=Path)
    parser.add_argument("--readiness-gate", action="store_true")
    parser.add_argument("--fixture-suite", type=Path)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    if args.fixture_suite:
        suite = json.loads(args.fixture_suite.read_text(encoding="utf-8"))
        baseline = validate(spec)
        results = []
        for case in suite["negative_cases"]:
            changed = copy.deepcopy(spec)
            mutate(changed, case["mutation"])
            errors = validate(changed)
            code = 4 if errors else 0
            results.append({
                "name": case["name"],
                "exit_code": code,
                "expected_exit": case["expected_exit"],
                "matched": code == case["expected_exit"],
                "errors": errors,
            })
        passed = not baseline and all(item["matched"] for item in results)
        print(json.dumps({
            "status": "PASS" if passed else "FAIL",
            "exit_code": 0 if passed else 4,
            "baseline_errors": baseline,
            "negative_cases": results,
        }, indent=2))
        return 0 if passed else 4
    errors = validate(spec, readiness=args.readiness_gate)
    code = 4 if errors else 0
    print(json.dumps({
        "status": "BLOCKED" if errors else "PASS_STRUCTURAL_SPEC_ONLY",
        "readiness_gate": args.readiness_gate,
        "exit_code": code,
        "errors": errors,
    }, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
