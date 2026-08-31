from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate candidate3 24-yaw control manifest without promoting formal assets.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    failures: list[str] = []
    expected_yaws = list(range(-180, 180, 15))
    views = manifest.get("views", [])
    if manifest.get("schema") != "mohan.candidate3_24yaw_control_manifest.v1": failures.append("schema")
    if manifest.get("formal_24_complete") is not False: failures.append("formal_24_complete_must_be_false")
    if manifest.get("body_center_contract", {}).get("value") != [512, 1292]: failures.append("body_center")
    if manifest.get("body_center_contract", {}).get("semantic") != "runtime_full_canvas_registration_anchor_not_mesh_bbox_center": failures.append("body_center_semantic")
    if len(views) != 24: failures.append(f"view_count:{len(views)}")
    if [item.get("formal_yaw_degrees") for item in views] != expected_yaws: failures.append("yaw_sequence")
    validated_controls = 0
    for view in views:
        yaw = view.get("formal_yaw_degrees")
        expected_renderer = -180 if yaw == -180 else -yaw
        if view.get("source_renderer_yaw_degrees") != expected_renderer: failures.append(f"mapping:{yaw}")
        if view.get("mirror") is not False: failures.append(f"mirror:{yaw}")
        if view.get("body_center_constant") != [512, 1292]: failures.append(f"body_center_view:{yaw}")
        for key in ("hair", "clothing", "ornament"):
            if view.get("part_id", {}).get(key) != "BLOCKED_NO_AUTHORITATIVE_PART_ID": failures.append(f"part_id:{yaw}:{key}")
        for kind, expected_mode in (("silhouette", "L"), ("depth", "L"), ("normal", "RGB")):
            control = view.get("controls", {}).get(kind, {})
            path = Path(control.get("path", ""))
            if not path.is_file(): failures.append(f"missing:{yaw}:{kind}"); continue
            if sha256(path) != control.get("sha256"): failures.append(f"hash:{yaw}:{kind}")
            with Image.open(path) as image:
                if image.size != (1024, 1536): failures.append(f"size:{yaw}:{kind}")
                if image.mode != expected_mode: failures.append(f"mode:{yaw}:{kind}")
            if control.get("bbox_touches_canvas") is not False: failures.append(f"bbox:{yaw}:{kind}")
            validated_controls += 1
        if view.get("outgoing_continuity", {}).get("status") != "PASS": failures.append(f"continuity:{yaw}")
    report = {
        "schema": "mohan.candidate3_24yaw_control_manifest_validation.v1",
        "manifest_sha256": sha256(args.manifest),
        "validated_view_count": len(views),
        "validated_control_count": validated_controls,
        "failures": failures,
        "result": "PASS_CONTROL_MANIFEST_ONLY" if not failures else "FAIL_CLOSED",
        "formal_24_complete": False,
        "promotion_performed": False
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if not failures else 4


if __name__ == "__main__":
    raise SystemExit(main())
