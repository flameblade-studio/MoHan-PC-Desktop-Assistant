"""Integrate reviewed native masks into exact, partial visible partitions.

This production-tooling entry point exports reviewed partitions only; body and outfit installation remain separate stages.
The unclassified remainder remains explicit until hidden surfaces are authored.
"""

from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import re
lazy from io import BytesIO
lazy from pathlib import Path

lazy import numpy as np
lazy from PIL import Image

SCHEMA = "mohan.reviewed-visible-partitions.v1"
ROLES = frozenset({
    "visible_core_hair", "visible_upper_garment", "visible_shorts",
    "visible_left_hand", "visible_right_hand",
})
MASK_FOREGROUND = 255
PNG_BIT_DEPTH_OFFSET = 24
NATIVE_BIT_DEPTH = 8


def _snapshot(record: dict, base: Path, snapshots: dict[Path, bytes]) -> bytes:
    path = (base / record["path"]).resolve()
    payload = path.read_bytes()
    digest = record["sha256"]
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("Expected a lowercase SHA-256")
    if hashlib.sha256(payload).hexdigest() != digest:
        raise ValueError(f"Source or mask changed: {path}")
    if path in snapshots and snapshots[path] != payload:
        raise ValueError(f"Input changed during preparation: {path}")
    snapshots[path] = payload
    return payload


def _decode(payload: bytes, mode: str) -> np.ndarray:
    with Image.open(BytesIO(payload)) as image:
        if image.format != "PNG" or image.mode != mode:
            raise ValueError(f"Expected native PNG {mode}")
        # PNG IHDR stores bit depth at byte 24; Pillow's RGBA mode hides 16-bit input.
        if payload[PNG_BIT_DEPTH_OFFSET] != NATIVE_BIT_DEPTH:
            raise ValueError("Expected native 8-bit PNG; implicit downconversion is forbidden")
        image.load()
        return np.array(image)


def _png(array: np.ndarray) -> bytes:
    stream = BytesIO()
    Image.fromarray(array).save(stream, format="PNG")
    return stream.getvalue()


def _snapshot_review_artifacts(review: dict, base: Path, snapshots: dict[Path, bytes]) -> None:
    """Pin explicitly hashed review files; legacy prose remains descriptive only."""
    for name in ("evidence", "trace"):
        hash_key = f"{name}_sha256"
        if hash_key not in review:
            continue
        path = review.get(name)
        if not isinstance(path, str) or not path.strip():
            raise ValueError(f"Hashed review {name} requires a nonempty file path")
        _snapshot({"path": path, "sha256": review[hash_key]}, base, snapshots)


def _partition(entry: dict, base: Path, snapshots: dict[Path, bytes]) -> tuple[dict, dict]:
    source = _decode(_snapshot(entry["source"], base, snapshots), "RGBA")
    parts = entry["parts"]
    if not isinstance(parts, list) or not parts:
        raise ValueError("At least one reviewed component is required")
    owners = np.zeros(source.shape[:2], dtype=bool)
    outputs: dict[str, bytes] = {}
    arrays = []
    counts = {}
    for part in parts:
        role = part["role"]
        if role not in ROLES or role in counts:
            raise ValueError("Unknown or duplicate component role")
        review = part["review"]
        if (
            review.get("decision") != "accept_visible_partition"
            or not isinstance(review.get("reviewer"), str)
            or not review["reviewer"].strip()
            or review.get("source_sha256") != entry["source"]["sha256"]
            or review.get("mask_sha256") != part["mask"]["sha256"]
        ):
            raise ValueError("A source-bound visual review is required")
        _snapshot_review_artifacts(review, base, snapshots)
        mask = _decode(_snapshot(part["mask"], base, snapshots), "L")
        if mask.shape != source.shape[:2] or not np.isin(mask, [0, 255]).all():
            raise ValueError("Mask must be binary and match the native canvas")
        selected = mask == MASK_FOREGROUND
        if np.any(selected & owners):
            raise ValueError("Reviewed components overlap; resolve ownership first")
        if not np.any(selected) or np.any(selected & (source[:, :, 3] == 0)):
            raise ValueError("Mask is empty or selects transparent background")
        layer = np.zeros_like(source)
        layer[selected] = source[selected]
        arrays.append(layer)
        outputs[f"{role}.png"] = _png(layer)
        counts[role] = int(selected.sum())
        owners |= selected
    remainder = source.copy()
    remainder[owners] = 0
    outputs["remaining_foreground.png"] = _png(remainder)
    arrays.append(remainder)
    # Disjoint ownership also preserves RGB stored under transparent pixels.
    reconstructed = np.sum(arrays, axis=0, dtype=np.uint16)
    if not np.array_equal(reconstructed, source):
        raise ValueError("Native RGBA reconstruction requires exact equality with the source")
    outputs["reconstruction.png"] = _png(source)
    for name, payload in outputs.items():
        actual = _decode(payload, "RGBA")
        if name == "reconstruction.png" and not np.array_equal(actual, source):
            raise ValueError("Encoded reconstruction changed pixels")
    return outputs, {
        "id": entry["id"], "source": entry["source"], "parts": parts,
        "dimensions": [source.shape[1], source.shape[0]],
        "visible_component_pixels": counts,
        "remainder_role": "unclassified complement; body-layer classification awaits semantic evidence",
        "rgba_reconstruction_exact": True, "overlap_pixels": 0,
        "outputs": {name: hashlib.sha256(data).hexdigest() for name, data in outputs.items()},
    }


def verify_completed_entry(
    entry: dict, report: dict, payloads: dict[str, bytes],
    base: Path, snapshots: dict[Path, bytes],
) -> None:
    """Cross-check recorded metadata and decoded exports against native inputs.

    Reuse canonical partition ownership; PNG compression differences are allowed,
    but every RGBA channel, including transparent RGB, must match its partition.
    """
    expected_files, expected_report = _partition(entry, base, snapshots)
    expected_metadata = {key: value for key, value in expected_report.items() if key != "outputs"}
    actual_metadata = {key: report.get(key) for key in expected_metadata}
    if json.dumps(actual_metadata, sort_keys=True) != json.dumps(expected_metadata, sort_keys=True):
        raise ValueError("Completed entry metadata contradicts its native inputs")
    if set(payloads) != set(expected_files):
        raise ValueError("Completed entry output inventory is incomplete")
    for name, expected in expected_files.items():
        if not np.array_equal(_decode(payloads[name], "RGBA"), _decode(expected, "RGBA")):
            raise ValueError(f"Completed entry pixels contradict its native inputs: {name}")


def integrate_batch(manifest: Path, output: Path) -> dict:
    """Validate the entire batch before writing to a fresh export directory.

    A receipt is written last. Treat a directory as an integrated batch only
    after receipt.json confirms completion; interrupted directories remain pending.
    """
    manifest = manifest.resolve()
    payload = manifest.read_bytes()
    spec = json.loads(payload)
    if spec.get("schema") != SCHEMA or not isinstance(spec.get("entries"), list):
        raise ValueError("The reviewed-partition batch requires the supported schema")
    if not spec["entries"] or output.exists():
        raise ValueError("Empty batch or output already exists")
    snapshots = {manifest: payload}
    prepared = {}
    reports = []
    for entry in spec["entries"]:
        identifier = entry["id"]
        if (
            not isinstance(identifier, str)
            or re.fullmatch(r"[a-z0-9][a-z0-9_+-]{0,79}", identifier) is None
            or identifier in prepared
        ):
            raise ValueError("View identifiers must be valid and unique")
        files, report = _partition(entry, manifest.parent, snapshots)
        prepared[identifier] = files
        reports.append(report)
    for path, original in snapshots.items():
        if path.read_bytes() != original:
            raise ValueError(f"Input changed before batch publication: {path}")
    receipt = {
        "schema": SCHEMA, "manifest_sha256": hashlib.sha256(payload).hexdigest(),
        "status": "integrated_partial_visible_partitions",
        "entries": reports, "production_runtime_ready": False,
        "complete_24_600": False,
    }
    output.mkdir(parents=True, exist_ok=False)
    for identifier, files in prepared.items():
        directory = output / identifier
        directory.mkdir()
        for name, data in files.items():
            target = directory / name
            target.write_bytes(data)
            if target.read_bytes() != data:
                raise OSError(f"Export readback failed: {target}")
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(integrate_batch(args.manifest, args.output), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
