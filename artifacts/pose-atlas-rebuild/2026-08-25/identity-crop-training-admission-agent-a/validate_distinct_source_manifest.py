from __future__ import annotations

# SPDX-License-Identifier: MIT
# Copyright 2026 CHOU MING HUA / Flameblade Studio

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
POLICY_PATH = ROOT / "DISTINCT_SOURCE_POLICY.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def validate(manifest: dict[str, object], candidate: dict[str, object], policy: dict[str, object]) -> list[str]:
    failures: list[str] = []
    required = {int(key): str(value).upper() for key, value in dict(policy["required_source_sha256_by_sequence"]).items()}
    rejected = {int(value) for value in list(policy["rejected_hold_sequences"])}
    records = candidate.get("records", [])
    candidate_by_sha = {
        str(record.get("source_sha256", "")).upper(): record
        for record in records
        if isinstance(record, dict)
    }
    entries = manifest.get("entries", [])
    if not isinstance(entries, list) or len(entries) != 12:
        failures.append("entry_count_must_equal_12")
        return failures
    if manifest.get("training_started") is not False:
        failures.append("training_started_must_be_false")
    if manifest.get("augmentation_count") != 0:
        failures.append("augmentation_count_must_equal_0")
    if manifest.get("distinct_source_count") != 12:
        failures.append("distinct_source_count_must_equal_12")

    seen_sha: set[str] = set()
    seen_sequences: set[int] = set()
    forbidden = [str(term).casefold() for term in list(policy["caption_forbidden_terms"])]
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            failures.append(f"entry_{index}_not_object")
            continue
        source_sha = str(entry.get("source_sha256", "")).upper()
        source_record = candidate_by_sha.get(source_sha)
        if source_record is None:
            failures.append(f"entry_{index}_source_not_in_candidate_manifest")
            continue
        sequence = int(source_record.get("sequence", -1))
        declared_sequence = entry.get("source_sequence")
        if declared_sequence is not None and declared_sequence != sequence:
            failures.append(f"entry_{index}_source_sequence_mismatch")
        if sequence in rejected:
            failures.append(f"entry_{index}_hold_sequence_rejected")
        if sequence not in required or required.get(sequence) != source_sha:
            failures.append(f"entry_{index}_source_not_fixed_allowlist")
        if source_record.get("manual_gate") != "PASS" or entry.get("manual_gate") != "PASS":
            failures.append(f"entry_{index}_manual_gate_not_pass")
        if source_sha in seen_sha:
            failures.append(f"entry_{index}_duplicate_source_sha")
        seen_sha.add(source_sha)
        seen_sequences.add(sequence)
        if "variant" in entry or entry.get("augmentation") not in (None, False, 0, "NONE"):
            failures.append(f"entry_{index}_augmentation_forbidden")
        if entry.get("garment_excluded") is not True:
            failures.append(f"entry_{index}_garment_excluded_not_true")
        if entry.get("use_scope") != "IDENTITY_TRAINING_ONLY":
            failures.append(f"entry_{index}_use_scope_mismatch")
        caption = str(entry.get("caption", "")).casefold()
        if any(term in caption for term in forbidden):
            failures.append(f"entry_{index}_caption_mentions_garment")
        crop_path = Path(str(entry.get("crop_path", "")))
        crop_hash = str(entry.get("crop_sha256", "")).upper()
        if not crop_path.is_file():
            failures.append(f"entry_{index}_crop_missing")
        elif sha256(crop_path) != crop_hash:
            failures.append(f"entry_{index}_crop_hash_mismatch")
    if seen_sequences != set(required):
        failures.append("selected_sequences_do_not_match_fixed_12")
    if len(seen_sha) != 12:
        failures.append("source_sha_values_not_distinct_12")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--candidate-manifest", required=True, type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    candidate = json.loads(args.candidate_manifest.read_text(encoding="utf-8"))
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    failures = validate(manifest, candidate, policy)
    report = {
        "status": "PASS_PENDING_INDEPENDENT_QA" if not failures else "FAIL_CLOSED",
        "training_started": False,
        "exit_code": 0 if not failures else 4,
        "failures": failures,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
