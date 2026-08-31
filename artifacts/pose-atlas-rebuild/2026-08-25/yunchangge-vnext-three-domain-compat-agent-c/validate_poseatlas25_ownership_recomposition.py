"""Artifact-only fail-closed validator for PoseAtlas25 ownership mapping."""

from __future__ import annotations

import argparse
import copy
import json
import re
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
REQUIRED_SLOTS = ["outerwear", "innerwear", "skirt", "sleeve_left", "sleeve_right", "shoe_left", "shoe_right"]
SHA256 = re.compile(r"^[0-9A-Fa-f]{64}$")


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("root must be an object")
    return value


def validate(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("schema") != "mohan.poseatlas25.yunchangge-ownership-recomposition.v1-draft":
        errors.append("schema mismatch")
    if record.get("runtime_wired") is not False:
        errors.append("artifact draft must keep runtime_wired=false")
    if record.get("promotion_allowed") is not False:
        errors.append("artifact draft must keep promotion_allowed=false")
    if record.get("canvas") != {"width": 1024, "height": 1536, "mode": "RGBA", "offset": [0, 0]}:
        errors.append("canvas must be full-canvas registered 1024x1536 RGBA")
    if record.get("legacy_z_order") != Z_ORDER:
        errors.append("legacy_z_order mismatch")
    layers = record.get("layers")
    if not isinstance(layers, list) or [item.get("layer") for item in layers if isinstance(item, dict)] != Z_ORDER:
        errors.append("layers must contain the exact 25 unique layers in z-order")
        return errors
    by_name = {item["layer"]: item for item in layers}
    for name in FACE:
        if by_name[name].get("owner") != "human-fixed" or by_name[name].get("replaceability") != "fixed":
            errors.append(f"{name} must be fixed human identity/animation")
    for name in HAIR:
        if by_name[name].get("owner") != "hair-fixed" or by_name[name].get("replaceability") != "fixed":
            errors.append(f"{name} must be fixed identity hair")
    for name in SLEEVES:
        if by_name[name].get("owner") != "garment-replaceable" or by_name[name].get("replaceability") != "replaceable":
            errors.append(f"{name} must be replaceable garment")
    if by_name["ornament"].get("owner") != "ornament-fixed" or by_name["ornament"].get("replaceability") != "fixed":
        errors.append("ornament must remain fixed physical-side identity ornament")
    if by_name["body"].get("owner") != "human-fixed" or by_name["body"].get("replaceability") != "fixed":
        errors.append("body must target fixed human core")
    blocked_sources = [item["layer"] for item in layers if item.get("source_status") != "CLEAN_FIXTURE"]
    if blocked_sources:
        errors.append("unclean or unresolved legacy layers: " + ",".join(blocked_sources))
    if record.get("required_replaceable_slots") != REQUIRED_SLOTS:
        errors.append("required replaceable slots mismatch")
    if record.get("missing_replaceable_slots") != []:
        errors.append("replaceable outfit slots remain missing")
    if record.get("available_legacy_replaceable_slots") != REQUIRED_SLOTS:
        errors.append("available replaceable slots must exactly cover required slots")
    masks = record.get("ownership_masks", {})
    for key in ("complete", "mutually_exclusive_primary", "soft_overlap_declared"):
        if masks.get(key) is not True:
            errors.append(f"ownership_masks.{key} must be true")
    recomposition = record.get("recomposition", {})
    if not SHA256.fullmatch(str(recomposition.get("reference_master_sha256", ""))):
        errors.append("recomposition reference master SHA is missing")
    for key in ("z_order_exact", "offsets_zero", "ownership_coverage_complete", "pass"):
        if recomposition.get(key) is not True:
            errors.append(f"recomposition.{key} must be true")
    if recomposition.get("exact_diff_pixels") != 0:
        errors.append("recomposition exact_diff_pixels must be zero")
    return errors


def positive(draft: dict[str, Any], suite: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(draft)
    overrides = suite["positive_overrides"]
    result["status"] = overrides["status"]
    for layer in result["layers"]:
        layer["source_status"] = overrides["source_status"]
    for field in ("available_legacy_replaceable_slots", "missing_replaceable_slots", "ownership_masks", "recomposition"):
        result[field] = copy.deepcopy(overrides[field])
    return result


def mutate(record: dict[str, Any], name: str) -> dict[str, Any]:
    result = copy.deepcopy(record)
    by_name = {item["layer"]: item for item in result["layers"]}
    if name == "missing_layer":
        result["layers"] = result["layers"][:-1]
    elif name == "wrong_sleeve_owner":
        by_name["sleeve_left"]["owner"] = "human-fixed"
    elif name == "replaceable_ornament":
        by_name["ornament"].update(owner="garment-replaceable", replaceability="replaceable")
    elif name == "mixed_body":
        by_name["body"]["source_status"] = "MIXED_OWNERSHIP_BLOCKED"
    elif name == "missing_shoe_slot":
        result["available_legacy_replaceable_slots"].remove("shoe_left")
        result["missing_replaceable_slots"] = ["shoe_left"]
    elif name == "mask_overlap_unverified":
        result["ownership_masks"]["mutually_exclusive_primary"] = False
    elif name == "nonzero_diff":
        result["recomposition"]["exact_diff_pixels"] = 1
    elif name == "promotion_claimed":
        result["promotion_allowed"] = True
    else:
        raise ValueError(f"unknown mutation: {name}")
    return result


def result(record: dict[str, Any]) -> dict[str, Any]:
    errors = validate(record)
    return {"status": "PASS_FIXTURE_ONLY" if not errors else "BLOCKED", "exit_code": 0 if not errors else 4, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("draft", type=Path)
    parser.add_argument("--fixture-suite", type=Path)
    args = parser.parse_args()
    try:
        draft = load(args.draft)
        if args.fixture_suite is None:
            payload = result(draft)
        else:
            suite = load(args.fixture_suite)
            clean = positive(draft, suite)
            positive_result = result(clean)
            cases = []
            suite_ok = positive_result["exit_code"] == 0
            for case in suite["negative_cases"]:
                negative = result(mutate(clean, case["mutation"]))
                matched = negative["exit_code"] == case["expected_exit"]
                suite_ok = suite_ok and matched
                cases.append({"name": case["name"], "matched": matched, **negative})
            payload = {"suite_status": "PASS" if suite_ok else "FAIL", "exit_code": 0 if suite_ok else 4, "positive": positive_result, "negative_cases": cases}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return int(payload["exit_code"])
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "ERROR", "exit_code": 2, "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
