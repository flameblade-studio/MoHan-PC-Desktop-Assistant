"""Plan the fail-closed 24-view/600-layer golden asset batch.

Only explicitly approved authority masters can enter the production set.  The
planner validates the completed yaw+000 golden sample and records every other
view as blocked until an approved, non-mirrored master is registered.
"""

from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy from pathlib import Path

lazy import numpy as np
lazy from PIL import Image


SIZE = (1024, 1536)
LAYERS = (
    "body", "hair_back", "base", "jaw", "oral_cavity", "teeth_tongue",
    "lip_lower", "lip_upper", "corner_left", "corner_right", "blush_left",
    "blush_right", "iris_left", "iris_right", "eyelid_left", "eyelid_right",
    "eyeliner_left", "eyeliner_right", "brow_left", "brow_right", "hair_left",
    "hair_right", "sleeve_left", "sleeve_right", "ornament",
)


def expected_views() -> list[str]:
    return [f"yaw{yaw:+04d}-pitch+00" for yaw in range(-180, 180, 15)]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_rgba(path: Path) -> list[str]:
    failures: list[str] = []
    try:
        with Image.open(path) as image:
            if image.mode != "RGBA":
                failures.append(f"not_rgba:{path.name}:{image.mode}")
                return failures
            if image.size != SIZE:
                failures.append(f"wrong_size:{path.name}:{image.size}")
            rgba = np.asarray(image, dtype=np.uint8)
    except (OSError, ValueError) as exc:
        return [f"unreadable:{path.name}:{exc}"]
    transparent = rgba[..., 3] == 0
    if np.any(rgba[..., :3][transparent] != 0):
        failures.append(f"transparent_rgb_nonzero:{path.name}")
    return failures


def build_manifest(repo: Path, registry_path: Path) -> dict:
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    approved = registry.get("approved_views", {})
    unexpected = sorted(set(approved) - set(expected_views()))
    records: list[dict] = []
    failures = [f"unexpected_registry_view:{view}" for view in unexpected]

    for view in expected_views():
        entry = approved.get(view)
        if not entry or entry.get("status") != "approved":
            records.append({
                "view_id": view,
                "status": "blocked",
                "reason": "missing_user_approved_master",
                "ready_layers": 0,
                "blocked_layers": len(LAYERS),
            })
            continue

        view_failures: list[str] = []
        authority = repo / entry["authority_path"]
        layer_dir = repo / entry["layer_dir"]
        audit_path = repo / entry["audit_path"]
        if not authority.is_file():
            view_failures.append("authority_missing")
        else:
            view_failures.extend(_validate_rgba(authority))
            expected_hash = entry.get("authority_sha256", "")
            if expected_hash and _sha256(authority) != expected_hash:
                view_failures.append("authority_sha256_mismatch")

        expected_names = {f"{view}_{layer}.png" for layer in LAYERS}
        actual_names = {p.name for p in layer_dir.glob(f"{view}_*.png")} if layer_dir.is_dir() else set()
        if actual_names != expected_names:
            view_failures.append(
                f"layer_set_mismatch:missing={sorted(expected_names-actual_names)}:extra={sorted(actual_names-expected_names)}"
            )
        for name in sorted(expected_names & actual_names):
            view_failures.extend(_validate_rgba(layer_dir / name))

        if not audit_path.is_file():
            view_failures.append("audit_missing")
        else:
            try:
                audit = json.loads(audit_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                view_failures.append(f"audit_unreadable:{exc}")
                audit = {}
            if audit.get("passed") is not True:
                view_failures.append("audit_not_passed")
            metrics = audit.get("metrics", {})
            for key in ("recompose_diff_pixels", "recompose_max_channel_error", "lip_green_cyan_pixels"):
                if metrics.get(key) != 0:
                    view_failures.append(f"audit_metric_nonzero:{key}={metrics.get(key)!r}")
            # The foreground must retain transparent clearance below the shoes.
            # A bottom-exclusive coordinate of 1536 means the authority itself
            # touches the canvas edge and can no longer prove that the soles are
            # complete. Missing, non-integral and out-of-range values fail closed.
            bottom = metrics.get("foreground_bottom_exclusive")
            if not isinstance(bottom, int) or isinstance(bottom, bool) or not 0 < bottom < SIZE[1]:
                view_failures.append(f"shoe_bottom_clearance_invalid:{bottom!r}")

        if view_failures:
            failures.extend(f"{view}:{failure}" for failure in view_failures)
            records.append({
                "view_id": view,
                "status": "blocked_invalid_approved_master",
                "failures": view_failures,
                "ready_layers": 0,
                "blocked_layers": len(LAYERS),
            })
        else:
            records.append({
                "view_id": view,
                "status": "golden_ready",
                "authority_path": str(authority),
                "authority_sha256": _sha256(authority),
                "layer_dir": str(layer_dir),
                "audit_path": str(audit_path),
                "ready_layers": len(LAYERS),
                "blocked_layers": 0,
            })

    ready_views = sum(record["status"] == "golden_ready" for record in records)
    ready_layers = sum(record["ready_layers"] for record in records)
    summary = {
        "expected_views": 24,
        "expected_layers_per_view": 25,
        "expected_total_layers": 600,
        "ready_views": ready_views,
        "blocked_views": 24 - ready_views,
        "ready_layers": ready_layers,
        "blocked_layers": 600 - ready_layers,
        "ready_percent": round(ready_layers / 600 * 100.0, 4),
    }
    return {
        "schema": "mohan.full-body-golden-batch.v1",
        "fail_closed": True,
        "promotable": ready_views == 24 and not failures,
        "policy": {
            "mirroring": "forbidden",
            "unregistered_authority_guessing": "forbidden",
            "checkerboard_as_rgb": "forbidden",
            "transparent_rgb": [0, 0, 0],
            "neutral_teeth_tongue_may_be_empty": True,
        },
        "summary": summary,
        "failures": failures,
        "views": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=Path("work/full-body-layer-golden-batch/authority-registry.json"))
    parser.add_argument("--output", type=Path, default=Path("work/full-body-layer-golden-batch/batch-manifest.json"))
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    registry = args.registry if args.registry.is_absolute() else repo / args.registry
    output = args.output if args.output.is_absolute() else repo / args.output
    manifest = build_manifest(repo, registry)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest["summary"], ensure_ascii=False))
    print(f"promotable={str(manifest['promotable']).lower()}")
    return 0 if manifest["promotable"] or args.allow_partial else 2


if __name__ == "__main__":
    raise SystemExit(main())
