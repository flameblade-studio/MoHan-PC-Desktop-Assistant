"""Validate yaw-105 owner-review evidence and remain blocked until answered."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
PROJECT = Path(__file__).resolve().parents[4]
WORKPACK = HERE / "yaw-105-owner-review-workpack.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def check_record(record: dict[str, Any], label: str, errors: list[str]) -> None:
    path_value = record.get("path")
    expected = record.get("sha256")
    if not path_value or not expected:
        errors.append(f"{label}: path/hash missing")
        return
    path = PROJECT / path_value
    if not path.is_file():
        errors.append(f"{label}: file missing")
    elif sha256(path) != expected:
        errors.append(f"{label}: hash drift")


def structure_errors(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("view_id") != "yaw-105-pitch+00":
        errors.append("wrong view")
    if data.get("promotion_allowed") is not False:
        errors.append("owner-review workpack cannot promote")
    if data.get("formal_layer_generation_allowed") is not False:
        errors.append("owner-review workpack cannot generate formal layers")
    candidates = data.get("candidate_inventory", [])
    if [item.get("candidate_id") for item in candidates] != [
        "v1-endpoint-bracketed", "v2-shoe-local-edit", "v3-deterministic-shoe-roi-composite"
    ]:
        errors.append("candidate inventory mismatch")
    for index, record in enumerate(candidates):
        check_record(record, f"candidate[{index}]", errors)
    for index, record in enumerate(data.get("identity_authorities", [])):
        check_record(record, f"identity_authority[{index}]", errors)
    check_record(data.get("contact_sheet", {}), "contact_sheet", errors)
    for index, record in enumerate(data.get("angle_controls", [])):
        path = PROJECT / record.get("path", "")
        if not path.is_file():
            errors.append(f"angle_control[{index}]: file missing")
    for key, record in data.get("evidence", {}).items():
        path = PROJECT / record.get("path", "")
        if not path.is_file():
            errors.append(f"evidence[{key}]: file missing")
    if len(data.get("owner_review_questions", [])) != 4:
        errors.append("owner-review question count must be four")
    return errors


def owner_gate_errors(data: dict[str, Any]) -> list[str]:
    errors = structure_errors(data)
    answers = {item["id"]: item.get("current") for item in data.get("owner_review_questions", [])}
    for key in ("identity", "angle", "art"):
        if answers.get(key) != "PASS":
            errors.append(f"owner answer {key}=PASS missing")
    if answers.get("alpha_next") != "YES_ALPHA_ONLY":
        errors.append("owner alpha-only authorization missing")
    primary = next((item for item in data.get("candidate_inventory", []) if item.get("candidate_id") == data.get("recommended_candidate_id")), None)
    if primary is None or primary.get("alpha") != "MISSING_RGB_NOT_PROCESSED":
        errors.append("primary candidate alpha truth boundary changed")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--structure-only", action="store_true")
    args = parser.parse_args()
    data = json.loads(WORKPACK.read_text(encoding="utf-8"))
    errors = structure_errors(data) if args.structure_only else owner_gate_errors(data)
    print(json.dumps({
        "mode": "STRUCTURE_ONLY" if args.structure_only else "OWNER_GATE",
        "errors": errors,
        "status": "PASS_STRUCTURE_ONLY" if args.structure_only and not errors else "BLOCK_OWNER_REVIEW",
        "promotion_allowed": False,
    }, ensure_ascii=False, indent=2))
    if args.structure_only:
        return 0 if not errors else 4
    return 4 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
