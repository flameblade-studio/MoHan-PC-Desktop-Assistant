from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, required=True)
    args = parser.parse_args()
    target = args.target.resolve()
    payload = json.loads(target.read_text(encoding="utf-8"))
    project_root = Path(payload["project_root"])
    errors: list[str] = []
    keys: set[tuple[str, str]] = set()

    assets = payload.get("asset_records", [])
    for index, record in enumerate(assets):
        key = (record.get("view_id"), record.get("legacy_layer"))
        if key in keys:
            errors.append(f"asset[{index}] duplicate view/layer")
        keys.add(key)
        source = project_root / record.get("path", "")
        if not source.is_file():
            errors.append(f"asset[{index}] source missing")
            continue
        if sha256(source) != record.get("sha256"):
            errors.append(f"asset[{index}] SHA mismatch")
        with Image.open(source) as image:
            if image.mode != "RGBA" or image.size != (1024, 1536):
                errors.append(f"asset[{index}] image contract mismatch")
        if record.get("mode") != "RGBA8" or record.get("offset_x") != 0 or record.get("offset_y") != 0:
            errors.append(f"asset[{index}] registration contract mismatch")
        if not record.get("source_provenance") or not record.get("license_provenance"):
            errors.append(f"asset[{index}] provenance missing")
        qa = record.get("qa", {})
        if qa.get("status") != "TECHNICAL_PASS_NOT_PROMOTED" or qa.get("promotion_allowed") is not False:
            errors.append(f"asset[{index}] QA status invalid")
        if not qa.get("rgba") or not qa.get("corner_alpha_zero") or qa.get("transparent_rgb_contamination_pixels") != 0:
            errors.append(f"asset[{index}] technical QA invalid")

    empties = payload.get("unresolved_empty_records", [])
    empty_keys: set[tuple[str, str]] = set()
    for index, record in enumerate(empties):
        key = (record.get("view_id"), record.get("legacy_layer"))
        if key in empty_keys or key in keys:
            errors.append(f"empty[{index}] duplicate view/layer")
        empty_keys.add(key)
        source = project_root / record.get("path", "")
        if not source.is_file() or sha256(source) != record.get("sha256"):
            errors.append(f"empty[{index}] source or SHA mismatch")
        if record.get("status") != "UNRESOLVED_EMPTY" or record.get("automatic_pass_for_empty") is not False:
            errors.append(f"empty[{index}] must remain unresolved")
        if not record.get("required_evidence"):
            errors.append(f"empty[{index}] evidence requirements missing")

    if len(assets) != 336:
        errors.append(f"expected 336 reusable records, observed {len(assets)}")
    if len(empties) != 216:
        errors.append(f"expected 216 unresolved empty records, observed {len(empties)}")
    if payload.get("counts", {}).get("blocked_rebuild_records") != 48:
        errors.append("expected 48 blocked rebuild records")
    if payload.get("mask_records") != [] or payload.get("counts", {}).get("present_ownership_masks") != 0:
        errors.append("ownership masks must not be fabricated")
    if payload.get("formal_600_complete") is not False or payload.get("promotion_allowed") is not False:
        errors.append("formal completion and promotion must remain false")

    blockers = [
        "264 legacy layer records are not reusable: 216 unresolved empty plus 48 mandatory rebuild",
        "192 required ownership masks are absent",
        "asset-specific rights are candidate-only until formal provenance adjudication",
    ]
    report = {
        "schema": "mohan.poseatlas.v4-reusable-assets-validation/v1",
        "target": str(target),
        "target_sha256": sha256(target),
        "asset_record_validation_pass": not errors,
        "validated_asset_records": len(assets) if not errors else 0,
        "unresolved_empty_records": len(empties),
        "blocked_rebuild_records": payload.get("counts", {}).get("blocked_rebuild_records"),
        "present_ownership_masks": 0,
        "required_ownership_masks": 192,
        "status": "PARTIAL_RECORDS_VALID_PRODUCTION_BLOCKED" if not errors else "INVALID_RECORDS",
        "formal_600_complete": False,
        "promotion_allowed": False,
        "record_errors": errors,
        "production_blockers": blockers,
        "overall_exit_code": 4,
    }
    target.with_suffix(".validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 4


if __name__ == "__main__":
    raise SystemExit(main())
