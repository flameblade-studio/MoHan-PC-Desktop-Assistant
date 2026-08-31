from __future__ import annotations

import argparse
import copy
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


VIEWS = [
    *(f"yaw-{yaw:03d}-pitch+00" for yaw in range(180, 0, -15)),
    *(f"yaw+{yaw:03d}-pitch+00" for yaw in range(0, 180, 15)),
]
LAYERS = [
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
TOP_REQUIRED = {
    "schema_version", "status", "canvas", "view_order", "layer_ids", "z_order",
    "body_center_constant", "offset_policy", "anchors", "mask_policy",
    "transition_contract", "provenance", "views", "qa_summary",
}
VIEW_REQUIRED = {"view_id", "yaw_degrees", "pitch_degrees", "layers", "recomposition", "continuity_qa"}
LAYER_REQUIRED = {
    "layer", "file", "sha256", "width", "height", "mode", "bit_depth",
    "offset_x", "offset_y", "anchor_id", "ownership_domain", "ownership_mask",
    "rigid_mask", "soft_mask", "source_id", "license_id", "qa",
}
SHA = re.compile(r"^[A-Fa-f0-9]{64}$")


def schema_invariants(schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = set(schema.get("required", []))
    if required != TOP_REQUIRED:
        errors.append("schema top-level required set drifted")
    props = schema.get("properties", {})
    if props.get("status", {}).get("const") != "FORMAL_ACCEPTED":
        errors.append("schema must require FORMAL_ACCEPTED")
    views = props.get("view_order", {})
    if views.get("minItems") != 24 or views.get("maxItems") != 24 or views.get("uniqueItems") is not True:
        errors.append("schema must require exactly 24 unique views")
    layer_ids = props.get("layer_ids", {})
    if layer_ids.get("minItems") != 25 or layer_ids.get("maxItems") != 25 or layer_ids.get("uniqueItems") is not True:
        errors.append("schema must require exactly 25 unique layer IDs")
    if schema.get("x_layer_record_count_per_view") != 25 or schema.get("x_total_asset_record_count") != 600:
        errors.append("schema must require 25 records per view and 600 total")
    if set(schema.get("x_view_record_required", [])) != VIEW_REQUIRED:
        errors.append("schema view record requirements drifted")
    asset_required = set(schema.get("$defs", {}).get("asset_record", {}).get("required", []))
    if asset_required != LAYER_REQUIRED:
        errors.append("schema asset record requirements drifted")
    transition = props.get("transition_contract", {})
    if "runtime_verified" not in transition.get("required", []) or transition.get("properties", {}).get("runtime_verified", {}).get("const") is not True:
        errors.append("schema must require runtime-verified transition")
    return errors


def gap_report(manifest: dict[str, Any]) -> dict[str, Any]:
    missing_top = sorted(TOP_REQUIRED - set(manifest))
    invalid_top: list[str] = []
    canvas = manifest.get("canvas", {})
    for field, expected in (("width", 1024), ("height", 1536), ("mode", "RGBA"), ("bit_depth", 8), ("transparent_background", True)):
        if canvas.get(field) != expected:
            invalid_top.append(f"canvas.{field}")
    if manifest.get("schema_version") != "mohan.pose-atlas.layer-manifest.v4-formal":
        invalid_top.append("schema_version")
    if manifest.get("status") != "FORMAL_ACCEPTED":
        invalid_top.append("status")
    if manifest.get("view_order") != VIEWS:
        invalid_top.append("view_order")
    if manifest.get("layer_ids") != LAYERS:
        invalid_top.append("layer_ids")
    if manifest.get("z_order") != Z_ORDER:
        invalid_top.append("z_order")
    if manifest.get("body_center_constant") != [512, 1292]:
        invalid_top.append("body_center_constant")
    offset = manifest.get("offset_policy", {})
    if not isinstance(offset, dict) or offset.get("kind") != "full-canvas-registered" or offset.get("offset_x") != 0 or offset.get("offset_y") != 0:
        invalid_top.append("offset_policy")

    transition = manifest.get("transition_contract", {})
    transition_missing = sorted({
        "clock_hz", "frame_interval_ms", "view_step_degrees", "interpolation",
        "weight_bounds", "wraparound", "wrap_pair", "runtime_verified",
    } - set(transition)) if isinstance(transition, dict) else ["transition_contract"]
    transition_invalid = []
    if transition.get("clock_hz") != 50: transition_invalid.append("clock_hz")
    if transition.get("frame_interval_ms") != 20: transition_invalid.append("frame_interval_ms")
    if transition.get("view_step_degrees") != 15: transition_invalid.append("view_step_degrees")
    if transition.get("wraparound") is not True: transition_invalid.append("wraparound")
    if transition.get("runtime_verified") is not True: transition_invalid.append("runtime_verified")

    views = manifest.get("views", [])
    view_missing = Counter()
    layer_missing = Counter()
    invalid_layer_records = Counter()
    observed_layers = 0
    for view in views if isinstance(views, list) else []:
        for field in VIEW_REQUIRED - set(view):
            view_missing[field] += 1
        records = view.get("layers", [])
        observed_layers += len(records) if isinstance(records, list) else 0
        for layer in records if isinstance(records, list) else []:
            for field in LAYER_REQUIRED - set(layer):
                layer_missing[field] += 1
            if layer.get("sha256") is not None and not SHA.fullmatch(str(layer.get("sha256"))):
                invalid_layer_records["sha256"] += 1
            if layer.get("offset_x") != 0: invalid_layer_records["offset_x"] += 1
            if layer.get("offset_y") != 0: invalid_layer_records["offset_y"] += 1

    blockers = []
    if missing_top: blockers.append("missing formal top-level fields")
    if invalid_top: blockers.append("invalid or non-formal top-level values")
    if len(views) != 24: blockers.append("view count is not 24")
    if observed_layers != 600: blockers.append("layer record count is not 600")
    if view_missing: blockers.append("view records lack required fields")
    if layer_missing: blockers.append("layer records lack formal asset/provenance/mask/QA fields")
    if transition_missing or transition_invalid: blockers.append("transition contract is incomplete or not runtime verified")
    return {
        "status": "BLOCKED" if blockers else "PASS",
        "exit_code": 4 if blockers else 0,
        "observed_view_count": len(views) if isinstance(views, list) else 0,
        "observed_layer_record_count": observed_layers,
        "missing_top_level_fields": missing_top,
        "invalid_top_level_fields": invalid_top,
        "missing_view_fields_counts": dict(sorted(view_missing.items())),
        "missing_layer_fields_counts": dict(sorted(layer_missing.items())),
        "invalid_layer_field_counts": dict(sorted(invalid_layer_records.items())),
        "transition_missing_fields": transition_missing,
        "transition_invalid_fields": transition_invalid,
        "blockers": blockers,
    }


def mutate(schema: dict[str, Any], name: str) -> None:
    if name == "drop_provenance": schema["required"].remove("provenance")
    elif name == "drop_anchors": schema["required"].remove("anchors")
    elif name == "drop_mask_policy": schema["required"].remove("mask_policy")
    elif name == "allow_23_views": schema["properties"]["view_order"]["minItems"] = 23
    elif name == "allow_24_layers": schema["properties"]["layer_ids"]["minItems"] = 24
    elif name == "remove_asset_hash": schema["$defs"]["asset_record"]["required"].remove("sha256")
    elif name == "remove_license_id": schema["$defs"]["asset_record"]["required"].remove("license_id")
    elif name == "remove_ownership_mask": schema["$defs"]["asset_record"]["required"].remove("ownership_mask")
    elif name == "remove_qa": schema["$defs"]["asset_record"]["required"].remove("qa")
    elif name == "transition_unverified": schema["properties"]["transition_contract"]["properties"]["runtime_verified"]["const"] = False
    elif name == "allow_fewer_assets": schema["x_total_asset_record_count"] = 599
    elif name == "weaken_formal_status": schema["properties"]["status"].pop("const")
    else: raise ValueError(name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("schema", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--fixture-suite", type=Path)
    args = parser.parse_args()
    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    if args.fixture_suite:
        fixtures = json.loads(args.fixture_suite.read_text(encoding="utf-8"))
        baseline = schema_invariants(schema)
        results = []
        for case in fixtures["negative_cases"]:
            changed = copy.deepcopy(schema)
            mutate(changed, case["mutation"])
            errors = schema_invariants(changed)
            code = 4 if errors else 0
            results.append({"name": case["name"], "exit_code": code, "matched": code == case["expected_exit"], "errors": errors})
        ok = not baseline and all(item["matched"] for item in results)
        print(json.dumps({"status": "PASS" if ok else "FAIL", "exit_code": 0 if ok else 4, "negative_cases": results}, indent=2))
        return 0 if ok else 4
    schema_errors = schema_invariants(schema)
    if schema_errors:
        print(json.dumps({"status": "SCHEMA_INVALID", "exit_code": 4, "errors": schema_errors}, indent=2))
        return 4
    if args.manifest:
        report = gap_report(json.loads(args.manifest.read_text(encoding="utf-8")))
        print(json.dumps(report, indent=2))
        return report["exit_code"]
    print(json.dumps({"status": "PASS_REQUIREMENT_SCHEMA_ONLY", "exit_code": 0}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
