#!/usr/bin/env python3
"""Fail-closed structural validator for an owner exact-SHA declaration."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
DEFAULT_FORM = HERE / "owner-exact-sha-declaration.blank.json"
ALLOWED_RIGHTS_BASES = {
    "SOLE_COPYRIGHT_OWNER",
    "AUTHORIZED_BY_RIGHTSHOLDER",
    "WORK_MADE_FOR_HIRE_OR_COMMISSION_WITH_TRANSFER",
    "OTHER_WITH_ATTACHED_EVIDENCE",
}


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def valid_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789ABCDEFabcdef" for char in value)


def validate_row(row: dict[str, Any]) -> list[str]:
    seq = row.get("sequence", "UNKNOWN")
    errors: list[str] = []
    selected = Path(str(row.get("selected_asset_path", "")))
    upstream = Path(str(row.get("upstream_source_path", "")))
    if sha256(selected) != str(row.get("selected_asset_sha256", "")).upper():
        errors.append(f"{seq}:SELECTED_SHA_MISMATCH_OR_MISSING")
    if sha256(upstream) != str(row.get("upstream_source_sha256", "")).upper():
        errors.append(f"{seq}:UPSTREAM_SHA_MISMATCH_OR_MISSING")
    if not row.get("declaration_required_for_current_rights_gap"):
        return errors
    declaration = row.get("owner_declaration", {})
    for field in [
        "declarant_legal_name",
        "declarant_role",
        "generation_or_creation_method",
        "signature_name",
        "signed_at_iso8601_with_timezone",
    ]:
        if not nonempty(declaration.get(field)):
            errors.append(f"{seq}:{field.upper()}_MISSING")
    if declaration.get("rights_basis") not in ALLOWED_RIGHTS_BASES:
        errors.append(f"{seq}:RIGHTS_BASIS_INVALID")
    for field in [
        "generation_account_owned_or_controlled_by_declarant",
        "all_input_assets_disclosed",
        "no_nc_or_noncommercial_restriction",
        "no_copyleft_or_share_alike_obligation_incompatible_with_mohan",
        "commercial_machine_learning_training_authorized",
        "commercial_derivatives_authorized",
        "redistribution_of_resulting_lora_or_generated_outputs_authorized",
        "third_party_personality_or_privacy_clearance_confirmed_if_applicable",
    ]:
        if declaration.get(field) is not True:
            errors.append(f"{seq}:{field.upper()}_MUST_BE_TRUE")
    required_text = declaration.get("required_declaration_text")
    if declaration.get("declaration_text") != required_text or not nonempty(required_text):
        errors.append(f"{seq}:DECLARATION_TEXT_NOT_EXACT")
    try:
        stamp = datetime.fromisoformat(str(declaration.get("signed_at_iso8601_with_timezone", "")))
        if stamp.tzinfo is None:
            errors.append(f"{seq}:SIGNED_AT_TIMEZONE_MISSING")
    except ValueError:
        errors.append(f"{seq}:SIGNED_AT_INVALID")
    receipt_path = declaration.get("generation_receipt_path")
    receipt_sha = declaration.get("generation_receipt_sha256")
    if receipt_path or receipt_sha:
        if not valid_sha(receipt_sha) or sha256(Path(str(receipt_path))) != str(receipt_sha).upper():
            errors.append(f"{seq}:GENERATION_RECEIPT_SHA_MISMATCH")
    prompt_path = declaration.get("prompt_and_settings_record_path")
    prompt_sha = declaration.get("prompt_and_settings_record_sha256")
    if not nonempty(prompt_path) or not valid_sha(prompt_sha):
        errors.append(f"{seq}:PROMPT_RECORD_AND_SHA_REQUIRED")
    elif sha256(Path(str(prompt_path))) != str(prompt_sha).upper():
        errors.append(f"{seq}:PROMPT_RECORD_SHA_MISMATCH")
    inputs = declaration.get("input_assets")
    if not isinstance(inputs, list):
        errors.append(f"{seq}:INPUT_ASSETS_MUST_BE_LIST")
    else:
        for index, item in enumerate(inputs):
            if not isinstance(item, dict):
                errors.append(f"{seq}:INPUT_{index}_INVALID")
                continue
            path = item.get("path")
            expected = item.get("sha256")
            basis = item.get("rights_basis")
            if not nonempty(path) or not valid_sha(expected) or sha256(Path(str(path))) != str(expected).upper():
                errors.append(f"{seq}:INPUT_{index}_SHA_MISMATCH")
            if not nonempty(basis):
                errors.append(f"{seq}:INPUT_{index}_RIGHTS_BASIS_MISSING")
    supporting = declaration.get("supporting_evidence_paths")
    if not isinstance(supporting, list) or not supporting:
        errors.append(f"{seq}:SUPPORTING_EVIDENCE_REQUIRED")
    else:
        for index, item in enumerate(supporting):
            if not isinstance(item, dict):
                errors.append(f"{seq}:SUPPORTING_{index}_INVALID")
                continue
            path = item.get("path")
            expected = item.get("sha256")
            if not nonempty(path) or not valid_sha(expected) or sha256(Path(str(path))) != str(expected).upper():
                errors.append(f"{seq}:SUPPORTING_{index}_SHA_MISMATCH")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--declaration", type=Path, default=DEFAULT_FORM)
    args = parser.parse_args()
    if not args.declaration.is_file():
        print("HOLD: declaration file missing")
        return 4
    data = json.loads(args.declaration.read_text(encoding="utf-8"))
    rows = data.get("rows")
    if not isinstance(rows, list) or len(rows) != 12:
        print("HOLD: declaration must contain exactly 12 rows")
        return 4
    errors = [error for row in rows for error in validate_row(row)]
    if errors:
        print(f"HOLD: declaration is unsigned, incomplete, or hash-unbound ({len(errors)} errors)")
        for error in errors:
            print(f"- {error}")
        return 4
    print("STRUCTURAL_PASS_PENDING_SEPARATE_RIGHTS_REVIEW")
    print("This does not admit pixels, authorize training, or provide legal advice.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
