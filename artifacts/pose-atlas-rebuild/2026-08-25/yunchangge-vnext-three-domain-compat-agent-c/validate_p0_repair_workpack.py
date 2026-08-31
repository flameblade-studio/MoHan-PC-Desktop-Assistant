from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from PIL import Image


SHA256 = re.compile(r"^[A-F0-9]{64}$")
FACE18 = {
    "base", "jaw", "oral_cavity", "teeth_tongue", "lip_lower", "lip_upper",
    "corner_left", "corner_right", "blush_left", "blush_right", "iris_left",
    "iris_right", "eyelid_left", "eyelid_right", "eyeliner_left",
    "eyeliner_right", "brow_left", "brow_right",
}
EXPECTED = {
    ("yaw-120-pitch+00", layer) for layer in FACE18
} | {
    ("yaw-105-pitch+00", layer) for layer in FACE18
} | {
    ("yaw-045-pitch+00", "blush_left")
} | {
    ("yaw+105-pitch+00", layer) for layer in FACE18
} | {
    ("yaw+120-pitch+00", layer) for layer in FACE18
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes())
    return digest.hexdigest().upper()


def expand(index: dict[str, Any]) -> list[dict[str, Any]]:
    requirements = index["requirements_by_layer"]
    common = index["common_required_evidence"]
    records = []
    for package in index["packages"]:
        for layer_id in package["layer_ids"]:
            records.append({
                "workpack_id": package["workpack_id"],
                "view_id": package["view_id"],
                "layer_id": layer_id,
                "status": package["status"],
                "required_source": requirements[layer_id]["source"],
                "required_mask": requirements[layer_id]["mask"],
                "dynamic_asset_requirement": requirements[layer_id]["dynamic_asset"],
                **common,
            })
    return records


def validate_fixture(path: Path) -> int:
    record = json.loads(path.read_text(encoding="utf-8"))
    evidence_fields = [
        "source_asset_sha256", "geometry_or_object_id_mask_sha256",
        "dynamic_asset_sha256_or_not_applicable_evidence", "output_png_sha256",
    ]
    errors = [field for field in evidence_fields if not SHA256.fullmatch(str(record.get(field, "")))]
    if record.get("geometry_or_object_id_mask_path") == "MISSING":
        errors.append("geometry_or_object_id_mask_path")
    if record.get("dynamic_asset_path_or_not_applicable_evidence") == "MISSING":
        errors.append("dynamic_asset_path_or_not_applicable_evidence")
    if record.get("exact_recomposition_diff_pixels") != 0:
        errors.append("exact_recomposition_diff_pixels")
    if record.get("manual_qa") != "PASS":
        errors.append("manual_qa")
    if record.get("adjacent_view_continuity_qa") != "PASS":
        errors.append("adjacent_view_continuity_qa")
    passed = not errors and record.get("status") == "PASS"
    print(json.dumps({"fixture": path.as_posix(), "pass": passed, "errors": sorted(set(errors))}, indent=2))
    return 0 if passed else 4


def validate_index(index_path: Path, manifest_path: Path, asset_root: Path) -> int:
    index = json.loads(index_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = expand(index)
    pairs = {(record["view_id"], record["layer_id"]) for record in records}
    actual_empty = set()
    manifest_files = {}
    for view in manifest["views"]:
        for layer in view["layers"]:
            pair = (view["view_id"], layer["layer"])
            manifest_files[pair] = layer["file"]
            with Image.open(asset_root / layer["file"]) as image:
                if image.getchannel("A").getbbox() is None:
                    actual_empty.add(pair)
    errors = []
    if len(records) != 73 or index.get("expanded_record_count") != 73:
        errors.append("expanded_count_not_73")
    if pairs != EXPECTED:
        errors.append("p0_pair_set_mismatch")
    if not pairs.issubset(actual_empty):
        errors.append("indexed_record_not_currently_empty")
    if any(record["status"] != "MISSING" for record in records):
        errors.append("premature_status")
    missing_requirement_fields = [
        f"{record['view_id']}:{record['layer_id']}" for record in records
        if not record.get("required_source") or not record.get("required_mask") or not record.get("dynamic_asset_requirement")
    ]
    if missing_requirement_fields:
        errors.append("missing_per_record_requirements")
    result = {
        "status": "BLOCKED_EXPECTED" if not errors else "INDEX_INVALID",
        "exit_code": 4,
        "expanded_records": len(records),
        "pair_set_exact": pairs == EXPECTED,
        "all_indexed_pngs_currently_empty": pairs.issubset(actual_empty),
        "all_status_missing": all(record["status"] == "MISSING" for record in records),
        "errors": errors,
        "records_digest_sha256": hashlib.sha256(
            json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest().upper(),
        "index_sha256": sha256(index_path),
        "source_manifest_sha256": sha256(manifest_path),
        "promotion_allowed": False,
    }
    print(json.dumps(result, indent=2))
    return 4


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--index", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--asset-root", type=Path)
    args = parser.parse_args()
    if args.fixture:
        return validate_fixture(args.fixture)
    if not all((args.index, args.manifest, args.asset_root)):
        parser.error("provide --fixture or --index/--manifest/--asset-root")
    return validate_index(args.index, args.manifest, args.asset_root)


if __name__ == "__main__":
    raise SystemExit(main())
