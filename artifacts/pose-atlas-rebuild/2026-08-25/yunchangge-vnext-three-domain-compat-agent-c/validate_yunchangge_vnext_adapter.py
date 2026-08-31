"""Fail-closed validator for the isolated Yunchangge vNext adapter draft.

This artifact does not load or modify MoHan runtime assets.
Exit 0 means only that the supplied draft/fixture satisfies this draft contract.
Exit 4 means blocked. Exit 2 means invalid invocation or unreadable JSON.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

EXPECTED_VIEWS = [
    *(f"yaw-{yaw:03d}-pitch+00" for yaw in range(180, 0, -15)),
    *(f"yaw+{yaw:03d}-pitch+00" for yaw in range(0, 180, 15)),
]
ALLOWED_LICENSES = {
    "MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "CC0-1.0",
    "CC-BY-3.0", "CC-BY-4.0", "CC-BY-SA-3.0", "CC-BY-SA-4.0",
    "CC-BY-ND-3.0", "CC-BY-ND-4.0",
}
FORBIDDEN_TOKENS = ("NC", "GPL", "AGPL", "LGPL")
KINDS = {"code", "weights", "asset"}
SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError("root must be an object")
    return value


def validate(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("schema_version") != "mohan.yunchangge.vnext.adapter-license.v1-draft":
        errors.append("schema_version mismatch")
    if record.get("runtime_wired") is not False:
        errors.append("artifact draft must keep runtime_wired=false")
    if record.get("promotion_allowed") is not False:
        errors.append("draft must keep promotion_allowed=false")
    views = record.get("view_contract", {}).get("view_ids")
    if views != EXPECTED_VIEWS:
        errors.append("view_ids must be the exact canonical 24-view sequence")
    view_contract = record.get("view_contract", {})
    if view_contract.get("canvas") != {"width": 1024, "height": 1536, "mode": "RGBA"}:
        errors.append("canvas must be 1024x1536 RGBA")
    if view_contract.get("offset") != [0, 0]:
        errors.append("all assets must use full-canvas offset [0,0]")
    adapter = record.get("adapter", {})
    if adapter.get("source_format") != "mohan-outfit-pack" or adapter.get("source_version") != 2:
        errors.append("legacy source contract must be mohan-outfit-pack v2")
    unresolved = adapter.get("unresolved_slots")
    if not isinstance(unresolved, list) or unresolved:
        errors.append("unresolved_slots must be an empty list")
    ownership = record.get("ownership", {})
    if ownership.get("domains") != ["core-body", "garment-dlc", "accessory"]:
        errors.append("ownership domains mismatch")
    if ownership.get("mask_policy") != "full-canvas-mutually-exclusive-primary-with-declared-soft-overlap":
        errors.append("ownership mask policy mismatch")
    if ownership.get("exact_recomposition_required") is not True:
        errors.append("exact recomposition must be required")
    qa = record.get("qa", {})
    for gate in ("ownership_masks_pass", "exact_recomposition_pass", "license_gate_pass"):
        if qa.get(gate) is not True:
            errors.append(f"{gate} must be true")

    components = record.get("component_licenses")
    if not isinstance(components, list) or not components:
        errors.append("component_licenses must be a non-empty list")
        return errors
    identities: set[tuple[str, str]] = set()
    kinds_by_source: dict[str, set[str]] = {}
    for index, component in enumerate(components):
        prefix = f"component_licenses[{index}]"
        if not isinstance(component, dict):
            errors.append(f"{prefix} must be an object")
            continue
        kind = component.get("component_kind")
        if kind not in KINDS:
            errors.append(f"{prefix}.component_kind invalid")
        component_id = component.get("component_id")
        identity = (str(component_id), str(kind))
        if identity in identities:
            errors.append(f"{prefix} duplicates component_id+kind")
        identities.add(identity)
        source = component.get("source_path_or_url")
        if not isinstance(source, str) or not source:
            errors.append(f"{prefix}.source_path_or_url missing")
        else:
            kinds_by_source.setdefault(source, set()).add(str(kind))
        license_id = component.get("license_spdx")
        if not isinstance(license_id, str) or license_id not in ALLOWED_LICENSES:
            errors.append(f"{prefix}.license_spdx is not explicitly allowed")
        if isinstance(license_id, str) and any(token in license_id.upper() for token in FORBIDDEN_TOKENS):
            errors.append(f"{prefix}.license_spdx contains a forbidden token")
        for field in ("sha256", "license_evidence_sha256"):
            if not SHA256.fullmatch(str(component.get(field, ""))):
                errors.append(f"{prefix}.{field} must be SHA-256")
        for field in ("purpose", "revision", "license_evidence"):
            if not isinstance(component.get(field), str) or not component[field].strip():
                errors.append(f"{prefix}.{field} missing")
        if component.get("commercial_use_allowed") is not True:
            errors.append(f"{prefix}.commercial_use_allowed must be true")
        if component.get("status") != "CANDIDATE_ALLOW":
            errors.append(f"{prefix}.status must be CANDIDATE_ALLOW")
    for source, source_kinds in kinds_by_source.items():
        if "code" in source_kinds and "weights" in source_kinds:
            errors.append(f"code and weights must be separate component records and sources: {source}")
    return errors


def build_positive(draft: dict[str, Any], suite: dict[str, Any]) -> dict[str, Any]:
    record = copy.deepcopy(draft)
    overrides = suite["positive_overrides"]
    record["status"] = overrides["status"]
    record["runtime_wired"] = overrides["runtime_wired"]
    record["promotion_allowed"] = overrides["promotion_allowed"]
    record["adapter"]["unresolved_slots"] = overrides["unresolved_slots"]
    record["qa"] = overrides["qa"]
    record["component_licenses"] = overrides["component_licenses"]
    return record


def mutate(record: dict[str, Any], mutation: str) -> dict[str, Any]:
    changed = copy.deepcopy(record)
    first = changed["component_licenses"][0]
    if mutation == "unknown_license":
        first["license_spdx"] = "LicenseRef-Unknown"
    elif mutation == "nc_license":
        first["license_spdx"] = "CC-BY-NC-4.0"
    elif mutation == "gpl_license":
        first["license_spdx"] = "GPL-3.0-only"
    elif mutation == "agpl_license":
        first["license_spdx"] = "AGPL-3.0-only"
    elif mutation == "code_weights_same_source":
        changed["component_licenses"][1]["source_path_or_url"] = first["source_path_or_url"]
    elif mutation == "missing_license_evidence":
        first["license_evidence"] = ""
    elif mutation == "unresolved_slot":
        changed["adapter"]["unresolved_slots"] = ["shoe_left"]
    elif mutation == "qa_not_passed":
        changed["qa"]["ownership_masks_pass"] = False
    else:
        raise ValueError(f"unknown mutation: {mutation}")
    return changed


def result_for(record: dict[str, Any]) -> dict[str, Any]:
    errors = validate(record)
    return {
        "status": "PASS_DRAFT_CONTRACT_ONLY" if not errors else "BLOCKED",
        "exit_code": 0 if not errors else 4,
        "errors": errors,
        "record_sha256": hashlib.sha256(
            json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest().upper(),
        "truth_boundary": "PASS never means runtime wired, assets promoted, or 24/600 completed.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("contract", type=Path)
    parser.add_argument("--fixture-suite", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        draft = load_json(args.contract)
        if args.fixture_suite:
            suite = load_json(args.fixture_suite)
            positive = build_positive(draft, suite)
            positive_result = result_for(positive)
            cases = []
            suite_ok = positive_result["exit_code"] == 0
            for case in suite["negative_cases"]:
                case_result = result_for(mutate(positive, case["mutation"]))
                matched = case_result["exit_code"] == case["expected_exit"]
                suite_ok = suite_ok and matched
                cases.append({"name": case["name"], "matched": matched, **case_result})
            result = {
                "suite_status": "PASS" if suite_ok else "FAIL",
                "exit_code": 0 if suite_ok else 4,
                "positive": positive_result,
                "negative_cases": cases,
            }
        else:
            result = result_for(draft)
        rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
        print(rendered, end="")
        return int(result["exit_code"])
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "ERROR", "exit_code": 2, "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
