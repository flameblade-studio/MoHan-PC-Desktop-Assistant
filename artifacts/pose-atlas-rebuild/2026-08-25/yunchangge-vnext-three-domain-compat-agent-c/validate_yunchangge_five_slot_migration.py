"""Fail-closed, artifact-only validator for five missing Yunchangge slots."""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path
from typing import Any

SLOTS = ["outerwear", "innerwear", "skirt", "shoe_left", "shoe_right"]
VIEWS = [
    *(f"yaw-{value:03d}-pitch+00" for value in range(180, 0, -15)),
    *(f"yaw+{value:03d}-pitch+00" for value in range(0, 180, 15)),
]
SHA = re.compile(r"^[0-9A-Fa-f]{64}$")
METHODS = {"admitted-object-id", "first-party-manual-verified", "first-party-fixture"}


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("root must be an object")
    return value


def validate_reference(ref: dict[str, Any], errors: list[str], prefix: str) -> None:
    if ref.get("view_id") not in VIEWS:
        errors.append(f"{prefix}.view_id invalid")
    slot = ref.get("slot")
    if slot not in SLOTS:
        errors.append(f"{prefix}.slot invalid")
    if ref.get("status") not in {"FIXTURE_ONLY", "CANDIDATE_HOLD", "CANDIDATE_PASS"}:
        errors.append(f"{prefix}.status unresolved")
    for field in ("mask", "asset"):
        image = ref.get(field, {})
        if not isinstance(image, dict):
            errors.append(f"{prefix}.{field} missing")
            continue
        if not SHA.fullmatch(str(image.get("sha256", ""))):
            errors.append(f"{prefix}.{field}.sha256 invalid")
        if image.get("width") != 1024 or image.get("height") != 1536 or image.get("offset") != [0, 0]:
            errors.append(f"{prefix}.{field} must be full-canvas registered")
        expected_modes = {"L", "RGBA"} if field == "mask" else {"RGBA"}
        if image.get("mode") not in expected_modes:
            errors.append(f"{prefix}.{field}.mode invalid")
    source = ref.get("source", {})
    if source.get("source_ownership") != "clean-single-owner":
        errors.append(f"{prefix}.source is mixed ownership")
    if not SHA.fullmatch(str(source.get("sha256", ""))):
        errors.append(f"{prefix}.source.sha256 invalid")
    ownership = ref.get("ownership", {})
    if ownership.get("owner") != "garment-dlc" or ownership.get("exclusive_primary") is not True:
        errors.append(f"{prefix}.ownership invalid")
    if ownership.get("overlap_with_human_core_pixels") != 0:
        errors.append(f"{prefix} overlaps human core")
    if slot in {"shoe_left", "shoe_right"} and ownership.get("left_right_separate") is not True:
        errors.append(f"{prefix} combines left/right shoes")
    if ref.get("method") not in METHODS:
        errors.append(f"{prefix}.method is not admitted")
    provenance = ref.get("provenance", {})
    for field in ("creator", "rights_basis", "license_id"):
        if not isinstance(provenance.get(field), str) or not provenance[field].strip():
            errors.append(f"{prefix}.provenance.{field} missing")
    for field in ("source_sha256", "license_evidence_sha256"):
        if not SHA.fullmatch(str(provenance.get(field, ""))):
            errors.append(f"{prefix}.provenance.{field} invalid")
    qa = ref.get("qa", {})
    for field in ("dimensions_pass", "rgba_pass", "transparent_rgb_zero", "human_core_preserved"):
        if qa.get(field) is not True:
            errors.append(f"{prefix}.qa.{field} must be true")


def validate(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("schema") != "mohan.v4-layered.yunchangge-five-slot-migration.v1-draft":
        errors.append("schema mismatch")
    if record.get("runtime_wired") is not False or record.get("promotion_allowed") is not False:
        errors.append("artifact draft cannot claim wiring or promotion")
    body = record.get("source_body_truth", {})
    if body.get("status") != "CLEAN_FIXTURE_OBJECT_ID" or body.get("ownership") != "clean-single-owner":
        errors.append("source body remains mixed or unproven")
    if body.get("allowed_as_direct_slot_source") is not True:
        errors.append("clean fixture source must explicitly allow slot derivation")
    if body.get("color_heuristic_allowed") is not False:
        errors.append("color heuristic is forbidden")
    targets = record.get("target_slots")
    if not isinstance(targets, list) or [item.get("slot") for item in targets if isinstance(item, dict)] != SLOTS:
        errors.append("target_slots must contain exact five-slot sequence")
    else:
        for item in targets:
            if item.get("status") != "FIXTURE_ONLY" or item.get("direct_copy_allowed") is not False:
                errors.append(f"{item['slot']} not ready for fixture validation")
    refs = record.get("mask_references")
    if not isinstance(refs, list):
        errors.append("mask_references must be an array")
        refs = []
    expected_pairs = {(view, slot) for view in VIEWS for slot in SLOTS}
    actual_pairs = {(ref.get("view_id"), ref.get("slot")) for ref in refs if isinstance(ref, dict)}
    if len(refs) != 120 or actual_pairs != expected_pairs:
        errors.append("mask references must cover every 24-view x five-slot pair exactly once")
    for index, ref in enumerate(refs):
        if isinstance(ref, dict):
            validate_reference(ref, errors, f"mask_references[{index}]")
        else:
            errors.append(f"mask_references[{index}] must be an object")
    recomposition = record.get("recomposition", {})
    if recomposition.get("expected_mask_reference_count") != 120 or recomposition.get("actual_mask_reference_count") != len(refs):
        errors.append("recomposition reference count mismatch")
    for field in ("human_core_preserved", "primary_masks_mutually_exclusive", "coverage_complete", "pass"):
        if recomposition.get(field) is not True:
            errors.append(f"recomposition.{field} must be true")
    if recomposition.get("exact_diff_pixels") != 0:
        errors.append("recomposition exact diff must be zero")
    return errors


def fixture_reference(view: str, slot: str) -> dict[str, Any]:
    digest = "A" * 64
    left_right = slot in {"shoe_left", "shoe_right"}
    return {
        "view_id": view,
        "slot": slot,
        "status": "FIXTURE_ONLY",
        "mask": {"path": f"fixture://{view}_{slot}.mask.png", "sha256": digest, "width": 1024, "height": 1536, "mode": "L", "offset": [0, 0]},
        "asset": {"path": f"fixture://{view}_{slot}.png", "sha256": digest, "width": 1024, "height": 1536, "mode": "RGBA", "offset": [0, 0]},
        "source": {"path": "fixture://clean-source.png", "sha256": digest, "source_layer": slot, "source_ownership": "clean-single-owner"},
        "ownership": {"owner": "garment-dlc", "exclusive_primary": True, "overlap_with_human_core_pixels": 0, "left_right_separate": left_right},
        "method": "first-party-fixture",
        "provenance": {"creator": "Flameblade Studio fixture", "rights_basis": "first-party fixture", "source_sha256": digest, "license_id": "MIT", "license_evidence_sha256": digest},
        "qa": {"dimensions_pass": True, "rgba_pass": True, "transparent_rgb_zero": True, "human_core_preserved": True, "manual_status": "FIXTURE_ONLY"}
    }


def build_positive(draft: dict[str, Any], suite: dict[str, Any]) -> dict[str, Any]:
    record = copy.deepcopy(draft)
    positive = suite["positive"]
    record["status"] = "FIXTURE_VALID"
    record["source_body_truth"].update(
        ownership="clean-single-owner", status=positive["source_body_status"],
        allowed_as_direct_slot_source=True, color_heuristic_allowed=False,
    )
    for target in record["target_slots"]:
        target["status"] = positive["target_status"]
        target["direct_copy_allowed"] = False
    record["mask_references"] = [fixture_reference(view, slot) for view in VIEWS for slot in SLOTS]
    record["recomposition"].update(positive["recomposition"], actual_mask_reference_count=120)
    return record


def mutate(record: dict[str, Any], name: str) -> dict[str, Any]:
    changed = copy.deepcopy(record)
    first = changed["mask_references"][0]
    if name == "mixed_body":
        changed["source_body_truth"].update(ownership="mixed-human-garment-shoe", status="BLOCK")
    elif name == "color_heuristic":
        first["method"] = "color-heuristic"
        changed["source_body_truth"]["color_heuristic_allowed"] = True
    elif name == "missing_mask_hash":
        first["mask"]["sha256"] = ""
    elif name == "wrong_dimensions":
        first["mask"]["width"] = 512
    elif name == "human_core_overlap":
        first["ownership"]["overlap_with_human_core_pixels"] = 1
    elif name == "combined_shoes":
        next(ref for ref in changed["mask_references"] if ref["slot"] == "shoe_left")["ownership"]["left_right_separate"] = False
    elif name == "missing_provenance":
        first["provenance"]["license_evidence_sha256"] = ""
    elif name == "missing_reference":
        changed["mask_references"].pop()
        changed["recomposition"]["actual_mask_reference_count"] = 119
    elif name == "recomposition_diff":
        changed["recomposition"]["exact_diff_pixels"] = 1
    else:
        raise ValueError(f"unknown mutation: {name}")
    return changed


def result(record: dict[str, Any]) -> dict[str, Any]:
    errors = validate(record)
    return {"status": "PASS_FIXTURE_ONLY" if not errors else "BLOCKED", "exit_code": 0 if not errors else 4, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("matrix", type=Path)
    parser.add_argument("--fixture-suite", type=Path)
    args = parser.parse_args()
    try:
        matrix = load(args.matrix)
        if args.fixture_suite is None:
            payload = result(matrix)
        else:
            suite = load(args.fixture_suite)
            clean = build_positive(matrix, suite)
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
