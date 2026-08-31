#!/usr/bin/env python3
"""Fail-closed validator for the owner12 exact-selected audit."""

from __future__ import annotations

import json
from pathlib import Path


REPORT = Path(r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\artifacts\pose-atlas-rebuild\2026-08-25\owner12-exact-selected-diversity-rights-audit-main\owner12-exact-selected-identity-angle-expression-crop-rights-duplicate-matrix.json")


def main() -> int:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    counts = report["counts"]
    structural_errors: list[str] = []
    if counts["selected_records"] != 12:
        structural_errors.append("selected_records must be exactly 12")
    if counts["owner_visual_approved"] != 12:
        structural_errors.append("owner_visual_approved must be exactly 12")
    if any(not record["pixel_repeat"]["file_sha_matches_manifest"] for record in report["records"]):
        structural_errors.append("one or more selected file hashes do not match owner manifest")
    if any(record["source_rights"]["admission"] == "PASS" and record["sequence"] not in {"seq01", "seq02"} for record in report["records"]):
        structural_errors.append("unknown-rights material was improperly promoted")
    if structural_errors:
        print(json.dumps({"gate": "ERROR", "errors": structural_errors}, indent=2))
        return 3
    blockers: list[str] = []
    if counts["pixel_rights_admitted"] != 12:
        blockers.append(f"pixel rights admitted {counts['pixel_rights_admitted']}/12")
    if counts["currently_train_ready_all_gates"] != 12:
        blockers.append(f"train-ready {counts['currently_train_ready_all_gates']}/12")
    if blockers:
        print(json.dumps({"gate": "BLOCKED_DO_NOT_TRAIN", "blockers": blockers}, indent=2))
        return 4
    print(json.dumps({"gate": "PASS", "train_ready": 12}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
