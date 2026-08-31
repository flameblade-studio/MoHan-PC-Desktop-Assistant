from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from PIL import Image

from build_ownership_mask_requirements import DOMAIN, FIELDS, VIEWS


SHA = re.compile(r"[0-9A-F]{64}\Z")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, required=True)
    args = parser.parse_args()
    target = args.target.resolve()
    payload = json.loads(target.read_text(encoding="utf-8"))
    errors: list[str] = []
    records = payload.get("records", [])
    expected = {(view, field) for view in VIEWS for field in FIELDS}
    observed: set[tuple[str, str]] = set()

    if payload.get("schema") != "mohan.poseatlas.vnext.ownership-mask-requirements/v1":
        errors.append("wrong schema")
    if payload.get("views") != list(VIEWS) or payload.get("mask_fields") != list(FIELDS):
        errors.append("canonical views or fields disagree")
    if len(records) != 192:
        errors.append(f"expected 192 records, observed {len(records)}")
    for index, record in enumerate(records):
        key = (record.get("view_id"), record.get("mask_field"))
        if key in observed:
            errors.append(f"record[{index}] duplicate view/field")
        observed.add(key)
        if record.get("domain") != DOMAIN.get(record.get("mask_field")):
            errors.append(f"record[{index}] domain mismatch")
        if record.get("authority_mask") is not False or not str(record.get("status", "")).startswith("BLOCKED"):
            errors.append(f"record[{index}] missing authority mask must stay BLOCKED")
        if record.get("qa", {}).get("promotion_allowed") is not False:
            errors.append(f"record[{index}] promotion flag invalid")
        path_text = record.get("path_if_exists")
        hash_text = record.get("sha256_if_exists")
        if path_text is None:
            if hash_text is not None:
                errors.append(f"record[{index}] hash exists without path")
        else:
            path = Path(path_text)
            if not path.is_file():
                errors.append(f"record[{index}] existing path missing")
            elif not isinstance(hash_text, str) or SHA.fullmatch(hash_text) is None or digest(path) != hash_text:
                errors.append(f"record[{index}] existing path hash mismatch")
            else:
                with Image.open(path) as image:
                    if image.size != (1024, 1536):
                        errors.append(f"record[{index}] existing control canvas mismatch")
        evidence_items = record.get("source_evidence")
        if not isinstance(evidence_items, list) or not evidence_items:
            errors.append(f"record[{index}] source evidence missing")
        else:
            for evidence_index, item in enumerate(evidence_items):
                evidence_path = Path(item.get("path", ""))
                if not evidence_path.is_file() or digest(evidence_path) != item.get("sha256"):
                    errors.append(f"record[{index}] evidence[{evidence_index}] path/hash invalid")
                if item.get("sufficient_for_authority_mask") is not False:
                    errors.append(f"record[{index}] evidence[{evidence_index}] overclaims authority")
        if not record.get("required_separation"):
            errors.append(f"record[{index}] separation requirement missing")
    if observed != expected:
        errors.append("view/field Cartesian product incomplete")
    counts = payload.get("counts", {})
    if counts != {
        "required": 192, "records": 192, "authority_masks": 0,
        "existing_control_only_paths": 6, "blocked": 192,
    }:
        errors.append("statistics disagree with fail-closed inventory")
    if payload.get("formal_600_complete") is not False or payload.get("promotion_allowed") is not False:
        errors.append("formal completion or promotion must remain false")

    report = {
        "schema": "mohan.poseatlas.vnext.ownership-mask-requirements-validation/v1",
        "target": str(target),
        "target_sha256": digest(target),
        "schema_path_statistics_validation_pass": not errors,
        "record_count": len(records),
        "existing_control_only_paths": counts.get("existing_control_only_paths"),
        "authority_masks": 0,
        "blocked_records": 192,
        "status": "VALID_REQUIREMENTS_MATRIX_ALL_AUTHORITY_MASKS_BLOCKED" if not errors else "INVALID_REQUIREMENTS_MATRIX",
        "formal_600_complete": False,
        "promotion_allowed": False,
        "errors": errors,
        "overall_exit_code": 4,
    }
    target.with_suffix(".validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 4


if __name__ == "__main__":
    raise SystemExit(main())
