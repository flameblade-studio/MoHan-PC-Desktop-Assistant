from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


PROJECT = Path(r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision")
ROOT = PROJECT / "artifacts" / "pose-atlas-rebuild" / "2026-08-25"
EVIDENCE_ROOT = ROOT / "yunchangge-vnext-three-domain-compat-agent-c"
SCHEMA_PATH = EVIDENCE_ROOT / "poseatlas25-human-garment-separation.schema.json"
FORMAL_MANIFEST = PROJECT / "assets" / "pose-atlas" / "v4-layered" / "layer_manifest.json"
FORMAL_ASSET_DIR = FORMAL_MANIFEST.parent
SHA256 = re.compile(r"[0-9A-Fa-f]{64}\Z")


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def validate(target: dict[str, object], schema: dict[str, object]) -> tuple[list[str], dict[str, object]]:
    errors: list[str] = []
    expected_views = [
        f"yaw{yaw:+04d}-pitch+00" if yaw != -180 else "yaw-180-pitch+00"
        for yaw in range(-180, 180, 15)
    ]
    required_layers = schema["required_layer_ids"]
    required_slots = schema["required_vnext_slots"]
    slot_domains = schema["slot_domains"]
    assert isinstance(required_layers, list)
    assert isinstance(required_slots, list)
    assert isinstance(slot_domains, dict)
    if target.get("schema") != "mohan.poseatlas25.human-garment-separation-contract/v1":
        errors.append("contract schema identifier mismatch")
    if target.get("views") != expected_views:
        errors.append("views must be the exact canonical 24-view list")
    if target.get("layer_ids") != required_layers:
        errors.append("layer_ids must be the exact 25-layer list")
    mapping = target.get("legacy_layer_ownership")
    if not isinstance(mapping, dict) or set(mapping) != set(required_layers):
        errors.append("legacy_layer_ownership must map all and only 25 layers")
    else:
        domains = set(schema["ownership_domains"])
        invalid = sorted(key for key, value in mapping.items() if value not in domains)
        errors.extend(f"invalid ownership domain: {key}" for key in invalid)
        if mapping.get("body") != "blocked_mixed":
            errors.append("current body must remain blocked_mixed until human and garment pixels are separated")
        if mapping.get("ornament") != "blocked_mixed":
            errors.append("current ornament must remain blocked_mixed until fixed and replaceable pixels are separated")
    if target.get("promotion_allowed") is not False:
        errors.append("promotion_allowed must be false for this migration draft")
    if target.get("formal_600_complete") is not False:
        errors.append("formal_600_complete must remain false")

    records = target.get("asset_records")
    if not isinstance(records, list):
        errors.append("asset_records must be a list")
        records = []
    required_keys = {
        (view_id, slot_id) for view_id in expected_views for slot_id in required_slots
    }
    observed: dict[tuple[str, str], dict[str, object]] = {}
    duplicate_keys: list[tuple[str, str]] = []
    for record in records:
        if not isinstance(record, dict):
            errors.append("asset record must be an object")
            continue
        key = (str(record.get("view_id")), str(record.get("slot_id")))
        if key in observed:
            duplicate_keys.append(key)
        observed[key] = record
        missing_fields = set(schema["asset_record_required_fields"]) - set(record)
        errors.extend(f"asset record {key} missing field: {field}" for field in sorted(missing_fields))
        slot_id = key[1]
        if slot_id in slot_domains and record.get("ownership_domain") != slot_domains[slot_id]:
            errors.append(f"asset record {key} ownership domain mismatch")
        if record.get("status") == "READY":
            for field in ("asset_path", "ownership_mask_path"):
                value = record.get(field)
                if not isinstance(value, str) or not value:
                    errors.append(f"READY asset record {key} has empty {field}")
            for field in ("asset_sha256", "ownership_mask_sha256"):
                value = record.get(field)
                if not isinstance(value, str) or SHA256.fullmatch(value) is None:
                    errors.append(f"READY asset record {key} has invalid {field}")
            if record.get("qa_status") != "PASS":
                errors.append(f"READY asset record {key} lacks PASS QA")
            if not record.get("source_id") or not record.get("license_id"):
                errors.append(f"READY asset record {key} lacks source/license provenance")
    errors.extend(f"duplicate view/slot record: {key}" for key in duplicate_keys)
    missing_records = sorted(required_keys - set(observed))
    if missing_records:
        errors.append(f"missing vNext ownership asset records: {len(missing_records)}")
    nonready = sorted(key for key, record in observed.items() if record.get("status") != "READY")
    if nonready:
        errors.append(f"non-READY vNext ownership asset records: {len(nonready)}")

    formal_facts: dict[str, object] = {
        "manifest_exists": FORMAL_MANIFEST.is_file(),
        "manifest_sha256": file_hash(FORMAL_MANIFEST) if FORMAL_MANIFEST.is_file() else None,
        "png_count": len(list(FORMAL_ASSET_DIR.glob("*.png"))),
    }
    if FORMAL_MANIFEST.is_file():
        formal = json.loads(FORMAL_MANIFEST.read_text(encoding="utf-8"))
        formal_views = formal.get("views", [])
        formal_facts["view_records"] = len(formal_views) if isinstance(formal_views, list) else None
        formal_facts["layer_records"] = (
            sum(len(view.get("layers", [])) for view in formal_views if isinstance(view, dict))
            if isinstance(formal_views, list)
            else None
        )
    return errors, {
        "required_asset_records": len(required_keys),
        "observed_asset_records": len(observed),
        "missing_asset_records": len(missing_records),
        "nonready_asset_records": len(nonready),
        "formal_observation_only": formal_facts,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, required=True)
    arguments = parser.parse_args()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    target = json.loads(arguments.target.read_text(encoding="utf-8"))
    errors, facts = validate(target, schema)
    report = {
        "schema": "mohan.poseatlas25.human-garment-separation-validation/v1",
        "target": str(arguments.target),
        "target_sha256": file_hash(arguments.target),
        "status": "PASS" if not errors else "BLOCK",
        "formal_asset_write": False,
        "promotion_allowed": False,
        "formal_600_complete": False,
        "facts": facts,
        "errors": errors,
    }
    output = EVIDENCE_ROOT / f"{arguments.target.stem}.validation.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 4


if __name__ == "__main__":
    raise SystemExit(main())
