from __future__ import annotations

import argparse
import hashlib
import json
import struct
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def png_ihdr(path: Path) -> tuple[int, int, int, int]:
    with path.open("rb") as stream:
        signature = stream.read(8)
        length = struct.unpack(">I", stream.read(4))[0]
        kind = stream.read(4)
        data = stream.read(length)
    if signature != PNG_SIGNATURE or kind != b"IHDR" or len(data) != 13:
        raise ValueError("invalid PNG IHDR")
    width, height, bit_depth, color_type = struct.unpack(">IIBB", data[:10])
    return width, height, bit_depth, color_type


def scan(manifest_path: Path, asset_root: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []
    referenced: list[str] = []
    errors: list[dict[str, str]] = []
    for view in manifest.get("views", []):
        view_id = view.get("view_id")
        for layer in view.get("layers", []):
            relative = layer.get("file")
            referenced.append(relative)
            path = asset_root / relative
            item: dict[str, Any] = {
                "view_id": view_id,
                "yaw_degrees": view.get("yaw_degrees"),
                "layer": layer.get("layer"),
                "file": relative,
                "exists": path.is_file(),
                "manifest_present": layer.get("present"),
                "manifest_offset": [layer.get("offset_x"), layer.get("offset_y")],
            }
            if path.is_file():
                try:
                    ihdr_width, ihdr_height, bit_depth, color_type = png_ihdr(path)
                    with Image.open(path) as image:
                        image.load()
                        alpha = image.getchannel("A") if image.mode == "RGBA" else None
                        alpha_bbox = alpha.getbbox() if alpha is not None else None
                        alpha_extrema = alpha.getextrema() if alpha is not None else None
                        item.update({
                            "width": image.width,
                            "height": image.height,
                            "mode": image.mode,
                            "format": image.format,
                            "png_bit_depth": bit_depth,
                            "png_color_type": color_type,
                            "ihdr_dimensions_match": (ihdr_width, ihdr_height) == image.size,
                            "sha256": sha256(path),
                            "bytes": path.stat().st_size,
                            "alpha_bbox": list(alpha_bbox) if alpha_bbox else None,
                            "alpha_extrema": list(alpha_extrema) if alpha_extrema else None,
                            "mechanically_fillable": (
                                image.size == (1024, 1536)
                                and image.mode == "RGBA"
                                and bit_depth == 8
                                and color_type == 6
                            ),
                        })
                except (OSError, ValueError, struct.error) as exc:
                    item["read_error"] = f"{type(exc).__name__}: {exc}"
                    errors.append({"file": relative, "error": item["read_error"]})
            records.append(item)

    physical_pngs = sorted(path.name for path in asset_root.glob("yaw*.png"))
    referenced_set = set(referenced)
    missing = sorted(item["file"] for item in records if not item["exists"])
    unreadable = sorted(item["file"] for item in records if item.get("read_error"))
    wrong_dimensions = sorted(item["file"] for item in records if item.get("exists") and (item.get("width"), item.get("height")) != (1024, 1536))
    wrong_mode = sorted(item["file"] for item in records if item.get("exists") and item.get("mode") != "RGBA")
    wrong_png_encoding = sorted(item["file"] for item in records if item.get("exists") and (item.get("png_bit_depth"), item.get("png_color_type")) != (8, 6))
    mechanically_fillable = sum(1 for item in records if item.get("mechanically_fillable"))
    duplicates = sorted({name for name in referenced if referenced.count(name) > 1})
    extras = sorted(set(physical_pngs) - referenced_set)
    physical_scan_pass = not (missing or unreadable or wrong_dimensions or wrong_mode or wrong_png_encoding or duplicates)
    inventory_digest_input = [
        {
            "file": item["file"],
            "width": item.get("width"),
            "height": item.get("height"),
            "mode": item.get("mode"),
            "bit_depth": item.get("png_bit_depth"),
            "sha256": item.get("sha256"),
            "bytes": item.get("bytes"),
            "alpha_bbox": item.get("alpha_bbox"),
        }
        for item in records
    ]
    inventory_digest = hashlib.sha256(
        json.dumps(inventory_digest_input, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest().upper()
    layer_counts = dict(sorted(Counter(str(item.get("layer")) for item in records).items()))
    transparent_layer_counts = dict(sorted(Counter(
        str(item.get("layer")) for item in records if item.get("alpha_bbox") is None
    ).items()))
    unique_content_hashes = len({item.get("sha256") for item in records if item.get("sha256")})
    content_hash_counts = Counter(item.get("sha256") for item in records if item.get("sha256"))
    return {
        "schema": "mohan.pose-atlas.v4-layered.physical-asset-inventory.v1",
        "source_manifest": {
            "path": manifest_path.as_posix(),
            "sha256": sha256(manifest_path),
        },
        "asset_root": asset_root.as_posix(),
        "status": "PHYSICAL_SCAN_PASS_FORMAL_STILL_BLOCKED" if physical_scan_pass else "PHYSICAL_SCAN_FAIL_FORMAL_BLOCKED",
        "physical_scan_pass": physical_scan_pass,
        "formal_promotion_allowed": False,
        "formal_600_complete": False,
        "summary": {
            "manifest_records": len(records),
            "unique_referenced_files": len(referenced_set),
            "physical_yaw_png_files": len(physical_pngs),
            "existing_referenced_files": sum(1 for item in records if item["exists"]),
            "mechanically_fillable_dimension_mode_hash_records": mechanically_fillable,
            "missing_files": len(missing),
            "unreadable_files": len(unreadable),
            "wrong_dimensions": len(wrong_dimensions),
            "wrong_mode": len(wrong_mode),
            "wrong_png_encoding": len(wrong_png_encoding),
            "duplicate_manifest_paths": len(duplicates),
            "unreferenced_yaw_png_files": len(extras),
            "total_referenced_bytes": sum(item.get("bytes", 0) for item in records),
            "unique_content_hashes": unique_content_hashes,
            "duplicate_content_hash_groups": sum(1 for count in content_hash_counts.values() if count > 1),
            "all_transparent_layers": sum(1 for item in records if item.get("alpha_bbox") is None),
            "all_transparent_layers_by_layer": transparent_layer_counts,
            "ordered_inventory_digest_sha256": inventory_digest,
            "records_per_layer": layer_counts,
        },
        "exceptions": {
            "missing": missing,
            "unreadable": unreadable,
            "wrong_dimensions": wrong_dimensions,
            "wrong_mode": wrong_mode,
            "wrong_png_encoding": wrong_png_encoding,
            "duplicate_manifest_paths": duplicates,
            "unreferenced_yaw_png_files": extras,
            "read_errors": errors,
        },
        "mechanically_fillable_fields": [
            "views[].layers[].sha256",
            "views[].layers[].width",
            "views[].layers[].height",
            "views[].layers[].mode",
            "views[].layers[].bit_depth",
            "views[].layers[].file_size_bytes",
            "views[].pitch_degrees_from_declared_view_id",
            "top-level layer_ids and z_order from the established contract",
            "canvas mode/bit_depth/transparent-background declaration after physical verification",
        ],
        "requires_art_or_provenance_evidence": [
            "ownership_domain correctness, especially mixed body and legacy ornament",
            "ownership/rigid/soft mask files and hashes",
            "source_id, upstream/revision and license_id for every derived asset",
            "identity, forehead, nose-lip, neck, hands, shoes, hem and ornament manual QA",
            "alpha edge quality and transparent-RGB cleanup QA",
            "per-view exact recomposition against an accepted mother view",
            "adjacent-view contour and identity continuity",
            "head/neck/feet anchors with visual evidence",
            "50Hz interpolation and wraparound runtime verification",
        ],
        "records": records,
        "truth_boundary": "Physical existence, dimensions, mode and hash do not prove artistic acceptance, ownership separation, provenance or formal 600 completion.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("asset_root", type=Path)
    parser.add_argument("report", type=Path)
    parser.add_argument("--formal-gate", action="store_true")
    parser.add_argument(
        "--stdout-summary",
        action="store_true",
        help="Print the computed summary even if the artifact directory ACL blocks report writes.",
    )
    args = parser.parse_args()
    report = scan(args.manifest, args.asset_root)
    if args.stdout_summary:
        print(json.dumps({"status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))
    try:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except PermissionError as error:
        if not args.stdout_summary:
            raise
        print(f"REPORT_WRITE_BLOCKED: {error}")
    if args.formal_gate:
        print(json.dumps({
            "status": "BLOCKED",
            "exit_code": 4,
            "physical_scan_pass": report["physical_scan_pass"],
            "reason": "art, ownership-mask, provenance, recomposition, continuity and runtime evidence remain required",
        }, indent=2))
        return 4
    code = 0 if report["physical_scan_pass"] else 4
    print(json.dumps({"status": report["status"], "exit_code": code, "summary": report["summary"]}, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
