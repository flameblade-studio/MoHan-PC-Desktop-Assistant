from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
EXPECTED_LAYERS = (
    "body", "hair_back", "base", "jaw", "oral_cavity", "teeth_tongue",
    "lip_lower", "lip_upper", "corner_left", "corner_right", "blush_left",
    "blush_right", "iris_left", "iris_right", "eyelid_left", "eyelid_right",
    "eyeliner_left", "eyeliner_right", "brow_left", "brow_right", "hair_left",
    "hair_right", "sleeve_left", "sleeve_right", "ornament",
)
ALLOWED_DOMAINS = {"core_anatomy", "garment", "ornament", "blocked_mixed"}
REQUIRED_POINTER_IDS = {
    "composition.overlay-factory",
    "composition.full-body-wire",
    "composition.pose-assets-wire",
    "render.legacy-z-order",
    "render.overlay-last",
    "render.body-hands-mixed",
    "schema.view-contract",
    "schema.current-slots",
    "schema.asset-contract",
    "schema.identity-deny",
    "schema.complete-views",
    "builder.seal",
    "generation.composition-root",
    "generation.audit-install",
    "runtime.fail-closed",
    "runtime.asset-gates",
    "runtime.face-only-protection",
    "test.overlay-view",
    "test.overlay-fail-closed",
    "test.pack-24-yaw",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _validate(target: Path) -> tuple[dict[str, object], int]:
    payload = json.loads(target.read_text(encoding="utf-8"))
    errors: list[str] = []
    snapshots = payload.get("source_snapshot")
    pointers = payload.get("code_pointers")
    ownership = payload.get("legacy_25_layer_ownership")
    migration = payload.get("minimum_migration_order")

    if not isinstance(snapshots, dict) or not snapshots:
        errors.append("source_snapshot must be non-empty")
        snapshots = {}
    if not isinstance(pointers, list) or not pointers:
        errors.append("code_pointers must be non-empty")
        pointers = []

    seen_pointer_ids: set[str] = set()
    for pointer in pointers:
        if not isinstance(pointer, dict):
            errors.append("every code pointer must be an object")
            continue
        pointer_id = pointer.get("id")
        path_value = pointer.get("path")
        lines = pointer.get("lines")
        token = pointer.get("token")
        if not isinstance(pointer_id, str) or pointer_id in seen_pointer_ids:
            errors.append("code pointer ids must be unique strings")
            continue
        seen_pointer_ids.add(pointer_id)
        if (
            not isinstance(path_value, str)
            or not isinstance(lines, list)
            or len(lines) != 2
            or not all(isinstance(value, int) and value > 0 for value in lines)
            or lines[0] > lines[1]
            or not isinstance(token, str)
            or not token
        ):
            errors.append(f"invalid code pointer declaration: {pointer_id}")
            continue
        source_path = PROJECT_ROOT / path_value
        if not source_path.is_file():
            errors.append(f"missing source file: {path_value}")
            continue
        expected_hash = snapshots.get(path_value)
        actual_hash = _sha256(source_path)
        if expected_hash != actual_hash:
            errors.append(f"source hash drift: {path_value}")
        source_lines = source_path.read_text(encoding="utf-8").splitlines()
        excerpt = "\n".join(source_lines[lines[0] - 1:lines[1]])
        if token not in excerpt:
            errors.append(f"code pointer token missing at declared lines: {pointer_id}")

    missing_pointers = sorted(REQUIRED_POINTER_IDS - seen_pointer_ids)
    if missing_pointers:
        errors.append("missing required code pointers: " + ", ".join(missing_pointers))

    if not isinstance(ownership, dict) or set(ownership) != set(EXPECTED_LAYERS):
        errors.append("ownership must map all and only the canonical 25 layers")
        ownership = {}
    elif any(domain not in ALLOWED_DOMAINS for domain in ownership.values()):
        errors.append("unknown ownership domain")
    if ownership.get("body") != "blocked_mixed":
        errors.append("legacy body must remain blocked_mixed")
    if ownership.get("ornament") != "blocked_mixed":
        errors.append("legacy ornament must remain blocked_mixed")
    if ownership.get("sleeve_left") != "garment" or ownership.get("sleeve_right") != "garment":
        errors.append("legacy sleeves must be garment-owned")

    if not isinstance(migration, list) or [step.get("step") for step in migration if isinstance(step, dict)] != list(range(1, 8)):
        errors.append("minimum migration order must contain exact steps 1 through 7")
    if payload.get("formal_600_complete") is not False:
        errors.append("formal_600_complete must remain false")
    if payload.get("promotion_allowed") is not False:
        errors.append("promotion_allowed must remain false")

    status = "PASS_READ_ONLY_CONTRACT" if not errors else "BLOCK"
    report = {
        "schema": "mohan.poseatlas25.yunchangge-composition-root-validation/v1",
        "target": str(target),
        "target_sha256": _sha256(target),
        "status": status,
        "formal_asset_write": False,
        "runtime_write": False,
        "promotion_allowed": False,
        "formal_600_complete": False,
        "facts": {
            "source_snapshots": len(snapshots),
            "code_pointers": len(pointers),
            "ownership_layers": len(ownership),
            "migration_steps": len(migration) if isinstance(migration, list) else 0,
        },
        "errors": errors,
    }
    return report, 0 if not errors else 4


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, required=True)
    args = parser.parse_args()
    target = args.target.resolve()
    report, exit_code = _validate(target)
    output = target.with_suffix(".validation.json")
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
