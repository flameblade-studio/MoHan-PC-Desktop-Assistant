from __future__ import annotations

# SPDX-License-Identifier: MIT
# Copyright 2026 CHOU MING HUA / Flameblade Studio

import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
POLICY_PATH = ROOT / "POLICY.json"
SHA256_RE = re.compile(r"^[0-9A-Fa-f]{64}$")
FORBIDDEN_SOURCE_NAMES = {"yaw+000-pitch+00.approved-rgba.png", "062.png", "idle.png"}
FORBIDDEN_PATH_MARKERS = ("contact-sheet", "contact_sheet", "contact sheet")
FORBIDDEN_CAPTION_TERMS = (
    "blue outer", "white inner", "blue-and-white", "blue and white", "blue robe",
    "white robe", "robe", "hanfu", "garment", "clothes", "clothing", "outfit",
    "outerwear", "bodice", "skirt", "sleeve", "藍外白內", "藍色外袍",
    "白色內衣", "白色內層", "外袍", "內袍", "漢服", "衣服", "服裝", "裙", "袖",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def fail_if(condition: bool, message: str, failures: list[str]) -> None:
    if condition:
        failures.append(message)


def resolve_path(manifest_path: Path, value: object) -> Path:
    path = Path(str(value))
    return path if path.is_absolute() else (manifest_path.parent / path).resolve()


def build_index(records: object) -> dict[str, dict[str, object]]:
    if not isinstance(records, list):
        return {}
    return {
        str(Path(str(record["path"])).resolve()).casefold(): record
        for record in records
        if isinstance(record, dict) and "path" in record
    }


def verify_file_hash(path: Path, expected: object, label: str, failures: list[str]) -> None:
    expected_text = str(expected).upper()
    fail_if(not path.is_file(), f"{label}: file missing: {path}", failures)
    fail_if(SHA256_RE.fullmatch(expected_text) is None, f"{label}: invalid SHA256 syntax", failures)
    if path.is_file() and SHA256_RE.fullmatch(expected_text):
        fail_if(sha256(path) != expected_text, f"{label}: SHA256 mismatch", failures)


def validate_entry(
    manifest_path: Path,
    entry: object,
    index_by_path: dict[str, dict[str, object]],
    allowed_authorities: set[str],
    required_fields: set[str],
    authority_only: bool,
) -> tuple[list[str], str | None]:
    failures: list[str] = []
    if not isinstance(entry, dict):
        return ["entry must be an object"], None
    entry_id = str(entry.get("id", "<missing-id>"))
    for field in required_fields:
        fail_if(field not in entry, f"{entry_id}: missing required field {field}", failures)
    source = resolve_path(manifest_path, entry.get("source_path", ""))
    crop = resolve_path(manifest_path, entry.get("crop_path", ""))
    indexed = index_by_path.get(str(source).casefold())
    source_name = source.name
    lowered_path = str(source).casefold()
    fail_if(source_name in FORBIDDEN_SOURCE_NAMES, f"{entry_id}: explicitly rejected source {source_name}", failures)
    fail_if(any(marker in lowered_path for marker in FORBIDDEN_PATH_MARKERS), f"{entry_id}: contact sheet is forbidden", failures)
    fail_if(indexed is None, f"{entry_id}: source is absent from pinned identity authority index", failures)
    if indexed is not None:
        actual_category = str(indexed.get("category", ""))
        declared_category = str(entry.get("source_category", ""))
        fail_if(declared_category != actual_category, f"{entry_id}: declared category does not match index", failures)
        admitted = (
            actual_category == "authority" and source_name in allowed_authorities
            if authority_only
            else actual_category == "support" or (
                actual_category == "authority" and source_name in allowed_authorities
            )
        )
        fail_if(not admitted, f"{entry_id}: category/name combination is not admitted ({actual_category}/{source_name})", failures)
        fail_if(
            str(indexed.get("sha256", "")).upper() != str(entry.get("source_sha256", "")).upper(),
            f"{entry_id}: source hash does not match index",
            failures,
        )
    verify_file_hash(source, entry.get("source_sha256", ""), f"{entry_id}: source", failures)
    verify_file_hash(crop, entry.get("crop_sha256", ""), f"{entry_id}: crop", failures)
    fail_if(crop.suffix.casefold() in {".jpg", ".jpeg"}, f"{entry_id}: lossy crop format is forbidden", failures)
    caption = str(entry.get("caption", "")).strip().casefold()
    fail_if(not caption, f"{entry_id}: caption is blank", failures)
    found_terms = sorted({term for term in FORBIDDEN_CAPTION_TERMS if term in caption})
    fail_if(bool(found_terms), f"{entry_id}: caption contains fixed garment terms: {found_terms}", failures)
    fail_if(entry.get("garment_excluded") is not True, f"{entry_id}: garment_excluded must be true", failures)
    fail_if(entry.get("rights_basis") != "USER_OWNED_MOHAN_REFERENCE", f"{entry_id}: rights_basis is not admitted", failures)
    fail_if(entry.get("use_scope") != "IDENTITY_TRAINING_ONLY", f"{entry_id}: use_scope must be IDENTITY_TRAINING_ONLY", failures)
    return failures, str(crop).casefold()


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed MoHan identity crop dataset admission")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--expected-count", required=True, type=int)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--authority-only", action="store_true")
    args = parser.parse_args()
    policy = load_json(POLICY_PATH)
    manifest_path = args.manifest.resolve()
    manifest = load_json(manifest_path)
    failures: list[str] = []
    index_path = Path(str(policy["identity_index_path"]))
    verify_file_hash(index_path, policy["identity_index_sha256"], "identity index", failures)
    identity_index = load_json(index_path) if index_path.is_file() else {}
    index_by_path = build_index(identity_index.get("records", []))
    fail_if(manifest.get("schema") != "mohan.identity_crop_training_manifest.v1", "wrong manifest schema", failures)
    fail_if(manifest.get("status") != "CANDIDATE_DATASET_PENDING_TRAINING", "wrong manifest status", failures)
    entries = manifest.get("entries", [])
    fail_if(not isinstance(entries, list), "entries must be a list", failures)
    if not isinstance(entries, list):
        entries = []
    fail_if(len(entries) != args.expected_count, f"expected {args.expected_count} entries, found {len(entries)}", failures)
    fail_if(manifest.get("expected_count") != args.expected_count, "manifest expected_count mismatch", failures)
    required_fields = set(policy["required_entry_fields"])
    allowed_authorities = set(policy["allowed_sources"]["authority_file_exceptions"])
    crop_paths: list[str] = []
    entry_results: list[dict[str, object]] = []
    for entry in entries:
        entry_failures, crop_path = validate_entry(
            manifest_path, entry, index_by_path, allowed_authorities, required_fields, args.authority_only
        )
        failures.extend(entry_failures)
        if crop_path is not None:
            crop_paths.append(crop_path)
        entry_results.append({
            "id": entry.get("id") if isinstance(entry, dict) else None,
            "status": "PASS" if not entry_failures else "FAIL_CLOSED",
            "failures": entry_failures,
        })
    fail_if(len(crop_paths) != len(set(crop_paths)), "duplicate crop path detected", failures)
    report = {
        "schema": "mohan.identity_crop_training_admission_report.v1",
        "status": "PASS_ADMISSION" if not failures else "FAIL_CLOSED",
        "exit_code": 0 if not failures else 4,
        "manifest": str(manifest_path),
        "expected_count": args.expected_count,
        "actual_count": len(entries),
        "failures": failures,
        "entries": entry_results,
        "training_executed": False,
    }
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    print(output, end="")
    if args.report:
        args.report.write_text(output, encoding="utf-8")
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
