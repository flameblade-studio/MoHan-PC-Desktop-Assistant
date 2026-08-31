"""Validate compatibility boundaries without creating any image asset."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

Z_ORDER = [
    "body", "hair_back", "base", "jaw", "oral_cavity", "teeth_tongue",
    "lip_lower", "lip_upper", "corner_left", "corner_right", "blush_left",
    "blush_right", "iris_left", "iris_right", "eyelid_left", "eyelid_right",
    "eyeliner_left", "eyeliner_right", "brow_left", "brow_right", "hair_left",
    "hair_right", "sleeve_left", "sleeve_right", "ornament",
]
FACE = set(Z_ORDER[2:20])
HAIR = {"hair_back", "hair_left", "hair_right"}
SLEEVES = {"sleeve_left", "sleeve_right"}
SLOTS = ["outerwear", "innerwear", "skirt", "shoe_left", "shoe_right"]


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("root must be an object")
    return value


def validate(record: dict[str, Any], readiness_gate: bool = False) -> list[str]:
    errors: list[str] = []
    if record.get("schema") != "mohan.poseatlas25-to-yunchangge120.compatibility.v1-draft":
        errors.append("schema mismatch")
    if record.get("runtime_wired") is not False or record.get("promotion_allowed") is not False:
        errors.append("artifact draft cannot claim wiring or promotion")
    if record.get("formal_600_complete") is not False:
        errors.append("formal_600_complete must remain false")
    if record.get("canvas") != {"width": 1024, "height": 1536, "mode": "RGBA", "offset": [0, 0]}:
        errors.append("canvas contract mismatch")
    if record.get("z_order") != Z_ORDER:
        errors.append("25-layer z-order mismatch")
    layers = record.get("layer_ownership")
    if not isinstance(layers, list) or [item.get("layer") for item in layers if isinstance(item, dict)] != Z_ORDER:
        return errors + ["layer_ownership must contain exact 25 layers in z-order"]
    by_layer = {item["layer"]: item for item in layers}
    body = by_layer["body"]
    if body.get("domain") != "human-core" or body.get("replaceable") is not False or body.get("compatibility") != "BLOCKED_MIXED_SOURCE":
        errors.append("body must remain blocked mixed human core, never a garment source")
    if body.get("may_source_missing_slots") != []:
        errors.append("mixed body cannot source future garment slots")
    for name in FACE:
        layer = by_layer[name]
        if layer.get("domain") != "human-face" or layer.get("replaceable") is not False:
            errors.append(f"{name} must remain fixed human face")
    for name in HAIR:
        layer = by_layer[name]
        if layer.get("domain") != "identity-hair" or layer.get("replaceable") is not False:
            errors.append(f"{name} must remain fixed identity hair")
    for name in SLEEVES:
        layer = by_layer[name]
        if layer.get("domain") != "garment-dlc" or layer.get("replaceable") is not True:
            errors.append(f"{name} must remain replaceable garment")
    ornament = by_layer["ornament"]
    if ornament.get("domain") != "identity-fixed-ornament" or ornament.get("replaceable") is not False:
        errors.append("ornament must remain fixed identity ornament")
    future = record.get("future_missing_slots")
    if not isinstance(future, list) or [item.get("slot") for item in future if isinstance(item, dict)] != SLOTS:
        errors.append("future_missing_slots must contain exact five-slot sequence")
        future = []
    for item in future:
        slot = item.get("slot", "unknown")
        if item.get("domain") != "garment-dlc" or item.get("legacy_layer") is not None:
            errors.append(f"{slot} must be a new garment slot with no fabricated legacy source")
        if item.get("index_entries") != 24:
            errors.append(f"{slot} must have 24 missing index entries")
        if item.get("status") != "MISSING" or item.get("asset") is not None or item.get("mask") is not None:
            errors.append(f"{slot} must remain MISSING with null asset/mask")
    recomposition = record.get("recomposition_contract", {})
    for field in ("legacy_z_order_preserved", "future_garment_insertion_requires_explicit_z_order", "human_core_immutable", "identity_hair_immutable", "fixed_ornament_immutable", "missing_index_structurally_complete"):
        if recomposition.get(field) is not True:
            errors.append(f"recomposition_contract.{field} must be true")
    if readiness_gate:
        for field in ("missing_slot_assets_ready", "ownership_masks_complete", "pass"):
            if recomposition.get(field) is not True:
                errors.append(f"readiness requires recomposition_contract.{field}=true")
        if recomposition.get("exact_diff_pixels") != 0:
            errors.append("readiness requires exact_diff_pixels=0")
    return errors


def mutate(record: dict[str, Any], name: str) -> dict[str, Any]:
    changed = copy.deepcopy(record)
    by_layer = {item["layer"]: item for item in changed["layer_ownership"]}
    if name == "body_as_garment":
        by_layer["body"].update(domain="garment-dlc", replaceable=True, compatibility="DIRECT")
        by_layer["body"]["may_source_missing_slots"] = ["outerwear"]
    elif name == "hair_replaceable":
        by_layer["hair_left"]["replaceable"] = True
    elif name == "ornament_replaceable":
        by_layer["ornament"].update(domain="garment-dlc", replaceable=True)
    elif name == "sleeve_as_human":
        by_layer["sleeve_left"].update(domain="human-core", replaceable=False)
    elif name == "wrong_z_order":
        changed["z_order"][0], changed["z_order"][1] = changed["z_order"][1], changed["z_order"][0]
    elif name == "missing_future_slot":
        changed["future_missing_slots"].pop()
    elif name == "missing_slot_png":
        changed["future_missing_slots"][0]["asset"] = "fake-empty.png"
    elif name == "wrong_index_count":
        changed["future_missing_slots"][0]["index_entries"] = 23
    elif name == "claim_600_complete":
        changed["formal_600_complete"] = True
    else:
        raise ValueError(f"unknown mutation: {name}")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mapping", type=Path)
    parser.add_argument("--readiness-gate", action="store_true")
    parser.add_argument("--fixture-suite", type=Path)
    args = parser.parse_args()
    try:
        mapping = load(args.mapping)
        if args.fixture_suite:
            suite = load(args.fixture_suite)
            baseline_errors = validate(mapping)
            cases = []
            suite_ok = not baseline_errors
            for case in suite["negative_cases"]:
                errors = validate(mutate(mapping, case["mutation"]))
                exit_code = 0 if not errors else 4
                matched = exit_code == case["expected_exit"]
                suite_ok = suite_ok and matched
                cases.append({"name": case["name"], "matched": matched, "exit_code": exit_code, "errors": errors})
            payload = {"suite_status": "PASS" if suite_ok else "FAIL", "exit_code": 0 if suite_ok else 4, "baseline_exit": 0 if not baseline_errors else 4, "baseline_errors": baseline_errors, "negative_cases": cases}
        else:
            errors = validate(mapping, readiness_gate=args.readiness_gate)
            payload = {"status": "PASS_STRUCTURAL_MAPPING_ONLY" if not errors and not args.readiness_gate else "BLOCKED" if errors else "PASS", "exit_code": 0 if not errors else 4, "readiness_gate": args.readiness_gate, "asset_readiness": mapping.get("asset_readiness"), "errors": errors}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return int(payload["exit_code"])
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "ERROR", "exit_code": 2, "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
