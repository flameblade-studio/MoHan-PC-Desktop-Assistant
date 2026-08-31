from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from PIL import Image


SHA256_PATTERN = re.compile(r"^[A-F0-9]{64}$")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def validate_declaration(record: dict[str, Any], policy: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in policy["legal_empty_requires"]:
        if field not in record:
            errors.append(f"missing:{field}")
    for field in ("file_sha256", "occlusion_or_semantic_evidence_sha256"):
        if field in record and not SHA256_PATTERN.fullmatch(str(record[field])):
            errors.append(f"invalid_sha256:{field}")
    if record.get("visibility_reason") not in policy["allowed_visibility_reasons"]:
        errors.append("invalid_visibility_reason")
    if record.get("recomposition_diff_pixels") != 0:
        errors.append("recomposition_not_exact")
    if record.get("manual_qa") != "PASS":
        errors.append("manual_qa_not_pass")
    if record.get("layer_id") in policy["dynamic_asset_required_layers"]:
        if record.get("visibility_reason") == "NEUTRAL_STATE_INVISIBLE_WITH_SEPARATE_DYNAMIC_ASSET":
            if not SHA256_PATTERN.fullmatch(str(record.get("occlusion_or_semantic_evidence_sha256", ""))):
                errors.append("missing_dynamic_asset_evidence")
    return sorted(set(errors))


def validate_fixture(fixture: Path, policy_path: Path) -> int:
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    data = json.loads(fixture.read_text(encoding="utf-8"))
    results = []
    for index, record in enumerate(data.get("records", [])):
        errors = validate_declaration(record, policy)
        results.append({"index": index, "errors": errors, "pass": not errors})
    passed = bool(results) and all(item["pass"] for item in results)
    print(json.dumps({"fixture": fixture.as_posix(), "pass": passed, "results": results}, indent=2))
    return 0 if passed else 4


def classify_priority(view_id: str, layer_id: str) -> tuple[str, str]:
    yaw = int(view_id[3:7])
    absolute_yaw = abs(yaw)
    if 105 <= absolute_yaw <= 120:
        return "P0", "PARTIAL_FACE_VIEW_HAS_18_EMPTY_FACE_COMPONENTS"
    if view_id == "yaw-045-pitch+00" and layer_id == "blush_left":
        return "P0", "ONE_SIDED_ANOMALY_WHILE_COUNTERPART_IS_NONEMPTY"
    if layer_id in {"oral_cavity", "teeth_tongue"} and absolute_yaw <= 90:
        return "P1", "NEUTRAL_INVISIBILITY_POSSIBLE_BUT_DYNAMIC_ASSET_EVIDENCE_MISSING"
    return "P2", "REAR_OCCLUSION_POSSIBLE_BUT_GEOMETRY_MASK_AND_RECOMPOSITION_EVIDENCE_MISSING"


def audit_current(manifest_path: Path, asset_root: Path, policy_path: Path, declarations_path: Path) -> int:
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    declarations = json.loads(declarations_path.read_text(encoding="utf-8"))
    declared = {(item["view_id"], item["layer_id"]): item for item in declarations.get("records", [])}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    empty_records: list[dict[str, Any]] = []
    by_layer: Counter[str] = Counter()
    by_view: Counter[str] = Counter()
    by_priority: Counter[str] = Counter()
    priority_views: dict[str, set[str]] = defaultdict(set)
    legal = 0
    for view in manifest.get("views", []):
        for layer in view.get("layers", []):
            path = asset_root / layer["file"]
            with Image.open(path) as image:
                alpha_bbox = image.getchannel("A").getbbox() if image.mode == "RGBA" else None
            if alpha_bbox is not None:
                continue
            priority, reason = classify_priority(view["view_id"], layer["layer"])
            declaration = declared.get((view["view_id"], layer["layer"]))
            declaration_errors = validate_declaration(declaration, policy) if declaration else ["missing_legal_empty_declaration"]
            if declaration and declaration.get("file_sha256") != file_sha256(path):
                declaration_errors.append("file_sha256_mismatch")
            is_legal = not declaration_errors
            legal += int(is_legal)
            by_layer[layer["layer"]] += 1
            by_view[view["view_id"]] += 1
            by_priority[priority] += 1
            priority_views[priority].add(view["view_id"])
            empty_records.append({
                "view_id": view["view_id"],
                "layer_id": layer["layer"],
                "file": layer["file"],
                "manifest_present": layer.get("present"),
                "file_sha256": file_sha256(path),
                "classification": "LEGAL_EMPTY" if is_legal else "UNRESOLVED_EMPTY_BLOCKED",
                "priority": priority,
                "priority_reason": reason,
                "declaration_errors": sorted(set(declaration_errors)),
            })
    result = {
        "status": "PASS" if legal == len(empty_records) else "BLOCKED",
        "exit_code": 0 if legal == len(empty_records) else 4,
        "empty_records": len(empty_records),
        "legal_empty": legal,
        "unresolved_or_missing": len(empty_records) - legal,
        "manifest_present_true_but_empty": sum(1 for item in empty_records if item["manifest_present"] is True),
        "by_layer": dict(sorted(by_layer.items())),
        "by_view": dict(sorted(by_view.items())),
        "by_priority": dict(sorted(by_priority.items())),
        "priority_views": {key: sorted(value) for key, value in sorted(priority_views.items())},
        "records_digest_sha256": hashlib.sha256(
            json.dumps(empty_records, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest().upper(),
        "truth_boundary": "No current empty PNG is promoted. LEGAL_EMPTY requires explicit evidence and exact recomposition.",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result["exit_code"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--asset-root", type=Path)
    parser.add_argument("--declarations", type=Path)
    args = parser.parse_args()
    if args.fixture:
        return validate_fixture(args.fixture, args.policy)
    if not all((args.manifest, args.asset_root, args.declarations)):
        parser.error("current audit requires --manifest, --asset-root and --declarations")
    return audit_current(args.manifest, args.asset_root, args.policy, args.declarations)


if __name__ == "__main__":
    raise SystemExit(main())
