"""Validate exact-SHA draft integrity and fail closed for formal admission.

SPDX-License-Identifier: MIT
Copyright (c) 2026 Flameblade Studio
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SIDECAR = ROOT / "CACHED-TRAINER-DERIVATION-SIDECAR-DRAFT.json"
EXPECTED_TRAINER_SHA = "41337722967D3566ED98BFB4CF421154E129AFF1A185C349230676BF432CBBE7"
EXPECTED_COMMIT = "a949d3dd906528363d2b61f7f0b38abaed4169ca"
EXPECTED_LICENSE_SHA = "E28423074EF718E6580A2C15459CDBF08D01EABAF0218754AD1B65DB0C1F4CB6"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--integrity-only", action="store_true")
    args = parser.parse_args()
    data = json.loads(SIDECAR.read_text(encoding="utf-8"))
    trainer = Path(data["trainer"]["path"])
    license_path = Path(data["upstream"]["license_path"])
    checks = {
        "schema": data.get("schema") == "mohan.trainer_derivation_sidecar.v1",
        "draft_status": data.get("status") == "DRAFT_NOT_ADOPTED",
        "trainer_hash": trainer.is_file() and sha256(trainer) == EXPECTED_TRAINER_SHA == data["trainer"]["sha256"],
        "commit": data["upstream"].get("commit") == EXPECTED_COMMIT,
        "license": license_path.is_file()
        and sha256(license_path) == EXPECTED_LICENSE_SHA == data["upstream"]["license_sha256"],
        "safe_boundary": data.get("training_authorized") is False and data.get("formal_admission") == "BLOCK",
        "unresolved_classification": data["classification"].get("whole_file") == "UNDETERMINED",
    }
    integrity_pass = all(checks.values())
    formal_pass = (
        integrity_pass
        and data.get("status") == "ADOPTED"
        and data.get("formal_admission") == "PASS"
        and data["classification"].get("whole_file") != "UNDETERMINED"
    )
    exit_code = 0 if args.integrity_only and integrity_pass else 0 if formal_pass else 4
    report = {
        "schema": "mohan.draft_derivation_validation.v1",
        "mode": "INTEGRITY_ONLY" if args.integrity_only else "FORMAL_ADMISSION",
        "integrity_status": "PASS" if integrity_pass else "FAIL",
        "formal_admission_status": "PASS" if formal_pass else "BLOCK",
        "training_authorized": False,
        "checks": checks,
        "exit_code": exit_code,
        "sidecar": str(SIDECAR),
        "sidecar_sha256": sha256(SIDECAR),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
