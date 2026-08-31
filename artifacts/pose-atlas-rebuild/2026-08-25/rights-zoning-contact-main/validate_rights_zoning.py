from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("contact", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    failures: list[str] = []
    records = manifest.get("records", [])
    if manifest.get("schema") != "mohan.lora.pixel_rights_zoning.v1":
        failures.append("SCHEMA_MISMATCH")
    if manifest.get("training_resume_allowed") is not False:
        failures.append("TRAINING_FLAG_NOT_FALSE")
    if manifest.get("owner_visual_approval_is_pixel_rights") is not False:
        failures.append("OWNER_VISUAL_MISUSED_AS_RIGHTS")
    if len(records) != 15:
        failures.append(f"RECORD_COUNT:{len(records)}")
    if len({record.get("source_id") for record in records}) != len(records):
        failures.append("DUPLICATE_SOURCE_ID")

    for record in records:
        source_id = record.get("source_id", "unknown")
        path = Path(record["path"])
        if not path.is_file():
            failures.append(f"{source_id}:SOURCE_MISSING")
            continue
        if sha256(path) != record.get("sha256"):
            failures.append(f"{source_id}:SOURCE_HASH_MISMATCH")
        if record.get("owner_visual_approval_used_as_pixel_rights") is not False:
            failures.append(f"{source_id}:OWNER_VISUAL_MISUSED")
        if record.get("display_class") != "TRAINABLE PIXELS" and record.get("training_pixels_allowed") is not False:
            failures.append(f"{source_id}:REFERENCE_CLASS_TRAINING_TRUE")
        if record.get("display_class") == "TRAINABLE PIXELS":
            if record.get("license_status") != "ADMIT":
                failures.append(f"{source_id}:TRAINABLE_WITHOUT_LICENSE_ADMIT")
            if record.get("training_pixels_allowed") is not True:
                failures.append(f"{source_id}:TRAINABLE_FLAG_FALSE")

    expected = {
        "trainable_pixels_rights_pass": 3,
        "identity_reference_only": 11,
        "training_prohibited": 1,
        "total": 15,
    }
    if manifest.get("counts") != expected:
        failures.append(f"COUNT_MISMATCH:{manifest.get('counts')}")
    if not args.contact.is_file() or args.contact.stat().st_size == 0:
        failures.append("CONTACT_MISSING_OR_EMPTY")

    report = {
        "decision": "PASS_RIGHTS_ZONING_ONLY" if not failures else "FAIL_CLOSED",
        "training_resume_allowed": False,
        "record_count": len(records),
        "counts": manifest.get("counts"),
        "contact_path": str(args.contact.resolve()),
        "contact_sha256": sha256(args.contact) if args.contact.is_file() else None,
        "manifest_path": str(args.manifest.resolve()),
        "manifest_sha256": sha256(args.manifest),
        "failures": failures,
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if not failures else 4


if __name__ == "__main__":
    raise SystemExit(main())
