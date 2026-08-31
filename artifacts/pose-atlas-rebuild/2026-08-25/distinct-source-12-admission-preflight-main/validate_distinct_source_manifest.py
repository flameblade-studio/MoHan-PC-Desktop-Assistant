from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def failure(condition: bool, message: str, failures: list[str]) -> None:
    if condition:
        failures.append(message)


def validate(manifest: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    failures: list[str] = []
    failure(manifest.get("schema") != "mohan.lora.distinct_source_admission.v1", "SCHEMA_MISMATCH", failures)
    failure(manifest.get("required_independent_source_count") != 12, "REQUIRED_COUNT_NOT_12", failures)

    policy = manifest.get("independence_policy", {})
    expected_policy = {
        "counting_unit": "verified_original_source_event",
        "derivatives_never_increase_count": True,
        "horizontal_mirror_prohibited": True,
        "unique_root_source_required": True,
        "unique_original_event_required": True,
        "rights_and_owner_approval_required": True,
    }
    failure(policy != expected_policy, "INDEPENDENCE_POLICY_MISMATCH", failures)

    slots = manifest.get("slots", [])
    failure(len(slots) != 12, f"SLOT_COUNT:{len(slots)}", failures)
    expected_slot_ids = [f"slot{index:02d}" for index in range(1, 13)]
    failure([slot.get("slot_id") for slot in slots] != expected_slot_ids, "SLOT_IDS_INVALID", failures)

    pass_slots = [slot for slot in slots if slot.get("admission") == "PASS"]
    roots: list[str] = []
    events: list[str] = []
    for slot in slots:
        slot_id = slot.get("slot_id", "unknown")
        for transform in slot.get("transform_lineage", []):
            failure(
                transform.get("changes_independent_count") is not False,
                f"{slot_id}:DERIVATIVE_COUNT_MUTATION",
                failures,
            )
            failure(
                transform.get("operation") == "horizontal_mirror",
                f"{slot_id}:HORIZONTAL_MIRROR_PROHIBITED",
                failures,
            )

        if slot.get("admission") != "PASS":
            failure(slot.get("counted_independent") is True, f"{slot_id}:BLOCKED_SLOT_COUNTED", failures)
            continue

        required_pass = {
            "rights_status": "PASS",
            "owner_status": "APPROVED",
            "identity_status": "PASS",
            "counted_independent": True,
        }
        for key, expected in required_pass.items():
            failure(slot.get(key) != expected, f"{slot_id}:{key.upper()}_NOT_{expected}", failures)

        for path_key, hash_key in [
            ("training_asset_path", "training_asset_sha256"),
            ("root_source_path", "root_source_sha256"),
        ]:
            value = slot.get(path_key)
            expected_hash = slot.get(hash_key)
            failure(not value, f"{slot_id}:{path_key.upper()}_MISSING", failures)
            if value:
                path = Path(value)
                failure(not path.is_file(), f"{slot_id}:{path_key.upper()}_NOT_FOUND", failures)
                if path.is_file():
                    failure(sha256(path) != expected_hash, f"{slot_id}:{hash_key.upper()}_MISMATCH", failures)

        root = slot.get("root_source_id")
        event = slot.get("original_event_id")
        evidence = slot.get("original_event_evidence")
        failure(not root, f"{slot_id}:ROOT_SOURCE_ID_MISSING", failures)
        failure(not event, f"{slot_id}:ORIGINAL_EVENT_ID_MISSING", failures)
        failure(not evidence or not Path(evidence).is_file(), f"{slot_id}:ORIGINAL_EVENT_EVIDENCE_MISSING", failures)
        if root:
            roots.append(root)
        if event:
            events.append(event)

    failure(len(roots) != len(set(roots)), "DUPLICATE_ROOT_SOURCE_ID", failures)
    failure(len(events) != len(set(events)), "DUPLICATE_ORIGINAL_EVENT_ID", failures)
    failure(len(pass_slots) != 12, f"DISTINCT_PASS_COUNT:{len(pass_slots)}:REQUIRED:12", failures)

    calculated_ready = not failures and len(pass_slots) == 12
    failure(manifest.get("training_resume_allowed") != calculated_ready, "TRAINING_FLAG_INCONSISTENT", failures)
    expected_status = "PASS_12_DISTINCT_SOURCES" if calculated_ready else "FAIL_CLOSED"
    failure(manifest.get("status") != expected_status, "STATUS_INCONSISTENT", failures)

    summary = {
        "decision": "PASS_12_DISTINCT_SOURCES" if not failures else "FAIL_CLOSED",
        "pass_slot_count": len(pass_slots),
        "missing_or_blocked_slot_count": 12 - len(pass_slots),
        "unique_root_source_count": len(set(roots)),
        "unique_original_event_count": len(set(events)),
        "training_resume_allowed": False if failures else True,
        "failures": failures,
    }
    return failures, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    schema = json.loads(args.schema.read_text(encoding="utf-8-sig"))
    failures, report = validate(manifest)
    schema_failures: list[str] = []
    failure(
        schema.get("$id")
        != "https://flameblade.studio/schemas/mohan/distinct-lora-source-manifest-v1.json",
        "SCHEMA_ID_MISMATCH",
        schema_failures,
    )
    failure(
        schema.get("properties", {}).get("schema", {}).get("const")
        != "mohan.lora.distinct_source_admission.v1",
        "SCHEMA_CONST_MISMATCH",
        schema_failures,
    )
    failure(
        schema.get("properties", {}).get("required_independent_source_count", {}).get("const")
        != 12,
        "SCHEMA_REQUIRED_COUNT_NOT_12",
        schema_failures,
    )
    if schema_failures:
        failures.extend(schema_failures)
        report["failures"] = failures
        report["decision"] = "FAIL_CLOSED"
        report["training_resume_allowed"] = False
    report["schema_path"] = str(args.schema.resolve())
    report["schema_sha256"] = sha256(args.schema)
    report["manifest_path"] = str(args.manifest.resolve())
    report["manifest_sha256"] = sha256(args.manifest)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 4 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
