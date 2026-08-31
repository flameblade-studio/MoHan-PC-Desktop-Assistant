"""Validate the 120-record missing index and reject fake asset promotion."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

VIEWS = [
    *(f"yaw-{value:03d}-pitch+00" for value in range(180, 0, -15)),
    *(f"yaw+{value:03d}-pitch+00" for value in range(0, 180, 15)),
]
SLOTS = ["outerwear", "innerwear", "skirt", "shoe_left", "shoe_right"]
EXPECTED_PAIRS = [(view, slot) for view in VIEWS for slot in SLOTS]
REQUIRED_EVIDENCE = [
    "clean_source_path", "source_sha256", "source_ownership",
    "mask_method", "license_id", "license_evidence_sha256",
    "human_core_overlap_pixels", "manual_qa_status",
]
SHA256 = re.compile(r"^[0-9A-Fa-f]{64}$")
UNRESOLVED = {"MISSING", "UNRESOLVED"}


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("root must be an object")
    return value


def validate_image(image: dict[str, Any], prefix: str, errors: list[str], mask: bool) -> None:
    if not isinstance(image.get("path"), str) or not image["path"]:
        errors.append(f"{prefix}.path missing")
    if not SHA256.fullmatch(str(image.get("sha256", ""))):
        errors.append(f"{prefix}.sha256 invalid")
    if image.get("width") != 1024 or image.get("height") != 1536 or image.get("offset") != [0, 0]:
        errors.append(f"{prefix} must be full-canvas registered")
    valid_modes = {"L", "RGBA_ALPHA"} if mask else {"RGBA"}
    if image.get("mode") not in valid_modes:
        errors.append(f"{prefix}.mode invalid")
    count_field = "nonzero_pixels" if mask else "nontransparent_pixels"
    if not isinstance(image.get(count_field), int) or image[count_field] <= 0:
        errors.append(f"{prefix} is empty or fully transparent")
    if image.get("alpha_bbox") in (None, []):
        errors.append(f"{prefix}.alpha_bbox missing")


def validate(index: dict[str, Any], promotion_gate: bool = False) -> list[str]:
    errors: list[str] = []
    if index.get("schema") != "mohan.yunchangge.five-slot-mask-skeleton-index.v1":
        errors.append("schema mismatch")
    if index.get("runtime_wired") is not False or index.get("promotion_allowed") is not False:
        errors.append("index must not claim runtime wiring or promotion")
    if index.get("views") != VIEWS or index.get("slots") != SLOTS:
        errors.append("canonical views/slots mismatch")
    entries = index.get("entries")
    if not isinstance(entries, list):
        return errors + ["entries must be an array"]
    pairs = [(entry.get("view_id"), entry.get("slot")) for entry in entries if isinstance(entry, dict)]
    if len(entries) != 120 or pairs != EXPECTED_PAIRS or len(set(pairs)) != 120:
        errors.append("entries must contain exactly 120 ordered unique view-slot pairs")
    asset_hashes: list[str] = []
    mask_hashes: list[str] = []
    by_pair: dict[tuple[str, str], dict[str, Any]] = {}
    for index_number, entry in enumerate(entries):
        prefix = f"entries[{index_number}]"
        if not isinstance(entry, dict):
            errors.append(f"{prefix} must be an object")
            continue
        pair = (entry.get("view_id"), entry.get("slot"))
        by_pair[pair] = entry
        status = entry.get("status")
        evidence = entry.get("source_evidence", {})
        if evidence.get("required_fields") != REQUIRED_EVIDENCE:
            errors.append(f"{prefix}.source_evidence required fields mismatch")
        provided = evidence.get("provided", {})
        if status in UNRESOLVED:
            if entry.get("asset") is not None or entry.get("mask") is not None:
                errors.append(f"{prefix} unresolved entry must not contain asset/mask paths")
            if any(provided.get(field) is not None for field in REQUIRED_EVIDENCE):
                errors.append(f"{prefix} unresolved evidence must remain explicitly null")
        elif status in {"CANDIDATE_HOLD", "CANDIDATE_PASS"}:
            asset = entry.get("asset")
            mask = entry.get("mask")
            if not isinstance(asset, dict) or not isinstance(mask, dict):
                errors.append(f"{prefix} candidate asset/mask missing")
            else:
                validate_image(asset, f"{prefix}.asset", errors, mask=False)
                validate_image(mask, f"{prefix}.mask", errors, mask=True)
                if SHA256.fullmatch(str(asset.get("sha256", ""))):
                    asset_hashes.append(asset["sha256"].upper())
                if SHA256.fullmatch(str(mask.get("sha256", ""))):
                    mask_hashes.append(mask["sha256"].upper())
            for field in REQUIRED_EVIDENCE:
                if provided.get(field) is None:
                    errors.append(f"{prefix}.source_evidence.{field} missing")
        else:
            errors.append(f"{prefix}.status invalid")
    if len(asset_hashes) != len(set(asset_hashes)):
        errors.append("duplicate asset SHA-256 is forbidden")
    if len(mask_hashes) != len(set(mask_hashes)):
        errors.append("duplicate mask SHA-256 is forbidden")
    for view in VIEWS:
        left = by_pair.get((view, "shoe_left"), {})
        right = by_pair.get((view, "shoe_right"), {})
        for field in ("asset", "mask"):
            left_ref, right_ref = left.get(field), right.get(field)
            if isinstance(left_ref, dict) and isinstance(right_ref, dict):
                if left_ref.get("path") == right_ref.get("path") or left_ref.get("sha256") == right_ref.get("sha256"):
                    errors.append(f"{view} left/right shoes share {field}")
    if index.get("generated_image_count") != 0 and all(entry.get("status") in UNRESOLVED for entry in entries if isinstance(entry, dict)):
        errors.append("unresolved skeleton cannot claim generated images")
    if promotion_gate:
        if any(entry.get("status") != "CANDIDATE_PASS" for entry in entries if isinstance(entry, dict)):
            errors.append("promotion requires 120 CANDIDATE_PASS entries")
    return errors


def candidate_ref(view: str, slot: str, serial: int) -> dict[str, Any]:
    def digest(label: str) -> str:
        return hashlib.sha256(label.encode("utf-8")).hexdigest().upper()
    asset_sha = digest(f"asset:{serial}:{view}:{slot}")
    mask_sha = digest(f"mask:{serial}:{view}:{slot}")
    evidence_sha = digest(f"evidence:{serial}:{view}:{slot}")
    bbox = [100, 100, 900, 1400]
    side = "left" if slot == "shoe_left" else "right" if slot == "shoe_right" else "not-applicable"
    return {
        "view_id": view,
        "slot": slot,
        "status": "CANDIDATE_PASS",
        "asset": {"path": f"fixture://{view}_{slot}.png", "sha256": asset_sha, "width": 1024, "height": 1536, "mode": "RGBA", "offset": [0, 0], "nontransparent_pixels": 100, "alpha_bbox": bbox},
        "mask": {"path": f"fixture://{view}_{slot}.mask.png", "sha256": mask_sha, "width": 1024, "height": 1536, "mode": "L", "offset": [0, 0], "nonzero_pixels": 100, "alpha_bbox": bbox},
        "source_evidence": {
            "required_fields": REQUIRED_EVIDENCE,
            "provided": {"clean_source_path": "fixture://clean.png", "source_sha256": evidence_sha, "source_ownership": "clean-single-owner", "mask_method": "first-party-fixture", "license_id": "MIT", "license_evidence_sha256": evidence_sha, "human_core_overlap_pixels": 0, "manual_qa_status": "PASS", "shoe_side": side},
        },
        "blocking_reason": None,
    }


def ready_fixture(skeleton: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(skeleton)
    result["status"] = "FIXTURE_READY"
    result["asset_readiness"] = "FIXTURE_ONLY"
    result["entries"] = [candidate_ref(view, slot, serial) for serial, (view, slot) in enumerate(EXPECTED_PAIRS)]
    result["generated_image_count"] = 0
    return result


def mutate(record: dict[str, Any], name: str) -> dict[str, Any]:
    changed = copy.deepcopy(record)
    first = changed["entries"][0]
    if name == "transparent_empty":
        first["asset"]["nontransparent_pixels"] = 0
        first["asset"]["alpha_bbox"] = None
    elif name == "duplicate_hash":
        changed["entries"][1]["asset"]["sha256"] = first["asset"]["sha256"]
    elif name == "shared_shoes":
        left = next(entry for entry in changed["entries"] if entry["view_id"] == VIEWS[0] and entry["slot"] == "shoe_left")
        right = next(entry for entry in changed["entries"] if entry["view_id"] == VIEWS[0] and entry["slot"] == "shoe_right")
        right["asset"] = copy.deepcopy(left["asset"])
        right["mask"] = copy.deepcopy(left["mask"])
    elif name == "missing_pair":
        changed["entries"].pop()
    elif name == "unresolved_fake_path":
        first["status"] = "UNRESOLVED"
    elif name == "promotion_claimed":
        changed["promotion_allowed"] = True
    else:
        raise ValueError(f"unknown mutation: {name}")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("index", type=Path)
    parser.add_argument("--promotion-gate", action="store_true")
    parser.add_argument("--fixture-suite", type=Path)
    args = parser.parse_args()
    try:
        skeleton = load(args.index)
        if args.fixture_suite:
            suite = load(args.fixture_suite)
            ready = ready_fixture(skeleton)
            positive_errors = validate(ready, promotion_gate=True)
            cases = []
            suite_ok = not positive_errors
            for case in suite["negative_cases"]:
                errors = validate(mutate(ready, case["mutation"]), promotion_gate=True)
                exit_code = 0 if not errors else 4
                matched = exit_code == case["expected_exit"]
                suite_ok = suite_ok and matched
                cases.append({"name": case["name"], "matched": matched, "exit_code": exit_code, "errors": errors})
            payload = {"suite_status": "PASS" if suite_ok else "FAIL", "exit_code": 0 if suite_ok else 4, "positive_exit": 0 if not positive_errors else 4, "positive_errors": positive_errors, "negative_cases": cases}
        else:
            errors = validate(skeleton, promotion_gate=args.promotion_gate)
            structural_only = not args.promotion_gate
            payload = {"status": "PASS_MISSING_INDEX_STRUCTURE_ONLY" if not errors and structural_only else "BLOCKED" if errors else "PASS", "exit_code": 0 if not errors else 4, "promotion_gate": args.promotion_gate, "errors": errors, "asset_readiness": skeleton.get("asset_readiness")}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return int(payload["exit_code"])
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "ERROR", "exit_code": 2, "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
