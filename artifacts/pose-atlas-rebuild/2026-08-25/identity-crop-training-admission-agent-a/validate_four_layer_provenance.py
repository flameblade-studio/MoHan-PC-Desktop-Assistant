from __future__ import annotations

# SPDX-License-Identifier: MIT
# Copyright 2026 CHOU MING HUA / Flameblade Studio

import argparse
import hashlib
import json
import re
from pathlib import Path


SHA256_RE = re.compile(r"^[0-9A-Fa-f]{64}$")
FLUX_ID = "black-forest-labs/FLUX.1-schnell"
FLUX_REVISION = "741f7c3ce8b383c54771c7003378a50191e9efe9"
FLUX_README_SHA256 = "66F915FF73552215A78F83852312EDA079AF1F5A08A258B6B6733350101C58AA"
DIFFUSERS_COMMIT = "a949d3dd906528363d2b61f7f0b38abaed4169ca"
GARMENT_SLOTS = ["outerwear", "bodice", "skirt", "sleeve-left", "sleeve-right"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def canonical_sha256(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def fail_if(condition: bool, message: str, failures: list[str]) -> None:
    if condition:
        failures.append(message)


def verify_binding(record: object, path_key: str, hash_key: str, label: str, failures: list[str]) -> None:
    fail_if(not isinstance(record, dict), f"{label} must be an object", failures)
    if not isinstance(record, dict):
        return
    path = Path(str(record.get(path_key, "")))
    expected = str(record.get(hash_key, "")).upper()
    fail_if(not path.is_file(), f"{label} file missing", failures)
    fail_if(SHA256_RE.fullmatch(expected) is None, f"{label} SHA256 invalid", failures)
    if path.is_file() and SHA256_RE.fullmatch(expected):
        fail_if(sha256(path) != expected, f"{label} SHA256 mismatch", failures)


def validate(manifest: dict[str, object], expected_count: int) -> list[str]:
    failures: list[str] = []
    provenance = manifest.get("provenance", {})
    fail_if(not isinstance(provenance, dict), "provenance must be an object", failures)
    if not isinstance(provenance, dict):
        return failures
    flux = provenance.get("flux_base", {})
    fail_if(not isinstance(flux, dict), "flux_base must be an object", failures)
    if isinstance(flux, dict):
        fail_if(flux.get("id") != FLUX_ID, "FLUX base id mismatch", failures)
        fail_if(flux.get("revision") != FLUX_REVISION, "FLUX base revision mismatch", failures)
        fail_if(flux.get("license") != "Apache-2.0", "FLUX base license mismatch", failures)
        snapshot = Path(str(flux.get("snapshot_path", "")))
        fail_if(not snapshot.is_dir(), "FLUX snapshot missing", failures)
        readme = snapshot / "README.md"
        fail_if(not readme.is_file(), "FLUX README missing", failures)
        if readme.is_file():
            fail_if(sha256(readme) != FLUX_README_SHA256, "FLUX README hash mismatch", failures)
        fail_if(str(flux.get("readme_sha256", "")).upper() != FLUX_README_SHA256, "declared FLUX README hash mismatch", failures)
    lora = provenance.get("lora", {})
    fail_if(not isinstance(lora, dict), "lora must be an object", failures)
    if isinstance(lora, dict):
        fail_if(lora.get("status") != "NOT_TRAINED", "pre-training LoRA status must be NOT_TRAINED", failures)
        fail_if(lora.get("expected_format") != "safetensors", "LoRA output format must be safetensors", failures)
        fail_if(lora.get("license") != "Apache-2.0", "LoRA license must be Apache-2.0", failures)
        fail_if(lora.get("upstream_diffusers_commit") != DIFFUSERS_COMMIT, "Diffusers source commit mismatch", failures)
        verify_binding(lora, "trainer_path", "trainer_sha256", "trainer", failures)
    dataset = provenance.get("dataset", {})
    fail_if(not isinstance(dataset, dict), "dataset must be an object", failures)
    entries = manifest.get("entries", [])
    if isinstance(dataset, dict):
        verify_binding(dataset, "identity_index_path", "identity_index_sha256", "identity index", failures)
        fail_if(dataset.get("expected_count") != expected_count, "dataset expected_count mismatch", failures)
        fail_if(dataset.get("use_scope") != "IDENTITY_TRAINING_ONLY", "dataset use_scope mismatch", failures)
        fail_if(dataset.get("source_selection") != "IDLE_FRONT_IDLE_LEAN_ONLY", "dataset source_selection mismatch", failures)
        fail_if(not isinstance(entries, list), "entries must be a list", failures)
        if isinstance(entries, list):
            fail_if(str(dataset.get("entries_sha256", "")).upper() != canonical_sha256(entries), "dataset entries hash mismatch", failures)
        authorization = dataset.get("user_authorization", {})
        fail_if(not isinstance(authorization, dict) or authorization.get("explicitly_granted") is not True, "explicit user authorization missing", failures)
        verify_binding(authorization, "evidence_reference", "evidence_sha256", "user authorization evidence", failures)
    isolation = provenance.get("garment_isolation", {})
    fail_if(not isinstance(isolation, dict), "garment_isolation must be an object", failures)
    if isinstance(isolation, dict):
        for key in ("garment_excluded_for_every_entry", "core_body_skin_identity_only", "fixed_core_ornament_protected"):
            fail_if(isolation.get(key) is not True, f"garment isolation false: {key}", failures)
        fail_if(isolation.get("garment_slots") != GARMENT_SLOTS, "garment slots mismatch", failures)
        verify_binding(isolation, "protected_mask_manifest_path", "protected_mask_manifest_sha256", "protected mask manifest", failures)
        protected_path = Path(str(isolation.get("protected_mask_manifest_path", "")))
        if protected_path.is_file():
            try:
                protected = json.loads(protected_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                failures.append("protected mask manifest unreadable")
            else:
                fail_if(protected.get("status") != "POLICY_ONLY_NO_MASK_IMAGES", "protected mask status mismatch", failures)
                fail_if(protected.get("mask_images_created") != 0, "protected mask manifest must not claim generated masks", failures)
                fail_if(protected.get("garment_assets_created") != 0, "protected mask manifest must not claim generated garments", failures)
                fail_if(protected.get("garment_slots") != GARMENT_SLOTS, "protected mask manifest slots mismatch", failures)
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--expected-count", required=True, type=int)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    failures = validate(manifest, args.expected_count)
    report = {"status": "PASS" if not failures else "FAIL_CLOSED", "exit_code": 0 if not failures else 4, "failures": failures}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
