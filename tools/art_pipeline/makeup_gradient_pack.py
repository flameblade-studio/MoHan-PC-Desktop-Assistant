"""Build the approved makeup pack with a stronger four-look alpha gradient.

This tool changes only alpha values in existing eye and lip layers.  RGB,
canvas size, non-zero support, asset paths, and every unselected layer remain
unchanged.  It deliberately builds an isolated candidate; installing the
candidate as the official pack is a separate, reviewable operation.
"""

from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import zipfile
lazy from collections import Counter
lazy from io import BytesIO
lazy from pathlib import Path

lazy import numpy as np
lazy from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
if __name__ == "__main__":
    lazy from application.character_runtime_bootstrap import (
        activate_product_character_runtime,
    )

    activate_product_character_runtime(ROOT)

lazy from application.outfit_pack_builder import build_outfit_pack
lazy from domain.outfit_pack import MANIFEST, inspect_outfit_pack


SOURCE_SHA256 = "3dc76508e658f8f66d40d37af2d2d5744604f5665ffc8b9cd2871059506d6042"
SOURCE_VERSION = "1.0.2"
TARGET_VERSION = "1.0.3"
MAX_ALPHA = 255
FACTORS = {
    ("classic", "eyes"): (4, 1),
    ("classic", "lips"): (4, 1),
    ("light", "eyes"): (4, 1),
    ("light", "lips"): (4, 1),
    ("glamorous", "eyes"): (4, 1),
    ("glamorous", "lips"): (4, 1),
}


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _safe_member_path(root: Path, member: str) -> Path:
    relative = Path(*member.split("/"))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Unsafe archive member: {member}")
    output = (root / relative).resolve()
    if not output.is_relative_to(root.resolve()):
        raise ValueError(f"Archive member escapes the authoring root: {member}")
    return output


def _asset_entries(value: object) -> tuple[dict[str, object], ...]:
    found: list[dict[str, object]] = []
    if isinstance(value, dict):
        if isinstance(value.get("path"), str) and isinstance(value.get("slot"), str):
            found.append(value)
        for child in value.values():
            found.extend(_asset_entries(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_asset_entries(child))
    return tuple(found)


def _factor_by_path(manifest: dict[str, object]) -> dict[str, tuple[int, int, str, str]]:
    makeup = manifest.get("makeup")
    if not isinstance(makeup, list) or len(makeup) != 1:
        raise ValueError("Expected the single official makeup item.")
    variants = makeup[0].get("variants")
    if not isinstance(variants, list):
        raise ValueError("Official makeup variants are missing.")
    factors: dict[str, tuple[int, int, str, str]] = {}
    seen_variants: set[str] = set()
    for variant in variants:
        if not isinstance(variant, dict) or not isinstance(variant.get("id"), str):
            raise ValueError("Invalid official makeup variant.")
        variant_id = variant["id"]
        seen_variants.add(variant_id)
        for entry in _asset_entries(variant):
            slot = entry["slot"]
            factor = FACTORS.get((variant_id, slot))
            if factor is None:
                continue
            path = entry["path"]
            record = (*factor, variant_id, slot)
            previous = factors.setdefault(path, record)
            if previous != record:
                raise ValueError(f"Conflicting alpha factors for {path}.")
    if seen_variants != {"classic", "light", "glamorous"}:
        raise ValueError("Expected classic, light, and glamorous makeup variants.")
    return factors


def _scaled_png(
    payload: bytes,
    numerator: int,
    denominator: int,
) -> tuple[bytes, dict[str, int]]:
    with Image.open(BytesIO(payload)) as opened:
        if opened.format != "PNG" or opened.mode != "RGBA":
            raise ValueError("Makeup assets must be RGBA PNG files.")
        before = np.asarray(opened, dtype=np.uint8).copy()
    after = before.copy()
    alpha = before[:, :, 3].astype(np.uint16)
    scaled = np.minimum(
        MAX_ALPHA,
        (alpha * numerator + denominator // 2) // denominator,
    )
    after[:, :, 3] = scaled.astype(np.uint8)
    if not np.array_equal(before[:, :, :3], after[:, :, :3]):
        raise AssertionError("RGB changed during alpha scaling.")
    if not np.array_equal(before[:, :, 3] > 0, after[:, :, 3] > 0):
        raise AssertionError("Alpha support changed during scaling.")
    buffer = BytesIO()
    Image.fromarray(after, "RGBA").save(buffer, format="PNG", optimize=False)
    encoded = buffer.getvalue()
    with Image.open(BytesIO(encoded)) as reopened:
        verified = np.asarray(reopened, dtype=np.uint8)
    if not np.array_equal(after, verified):
        raise AssertionError("PNG round-trip changed makeup pixels.")
    changed = before[:, :, 3] != after[:, :, 3]
    return encoded, {
        "pixels_changed": int(np.count_nonzero(changed)),
        "alpha_sum_before": int(alpha.sum()),
        "alpha_sum_after": int(scaled.sum()),
        "saturated_before": int(np.count_nonzero(alpha == MAX_ALPHA)),
        "saturated_after": int(np.count_nonzero(scaled == MAX_ALPHA)),
    }


def _write_authoring_tree(
    source: Path,
    authoring_root: Path,
) -> tuple[dict[str, object], Counter[tuple[str, str]], dict[str, dict[str, int]]]:
    summary: Counter[tuple[str, str]] = Counter()
    totals: dict[str, dict[str, int]] = {}
    with zipfile.ZipFile(source) as archive:
        manifest = json.loads(archive.read(MANIFEST))
        if not isinstance(manifest, dict):
            raise ValueError("Official pack manifest must be an object.")
        factors = _factor_by_path(manifest)
        for info in archive.infolist():
            if info.is_dir() or info.filename == MANIFEST:
                continue
            destination = _safe_member_path(authoring_root, info.filename)
            destination.parent.mkdir(parents=True, exist_ok=True)
            payload = archive.read(info)
            factor = factors.get(info.filename)
            if factor is not None:
                numerator, denominator, variant, slot = factor
                payload, stats = _scaled_png(payload, numerator, denominator)
                summary[variant, slot] += 1
                totals[info.filename] = stats
            destination.write_bytes(payload)
        missing = sorted(set(factors) - set(archive.namelist()))
        if missing:
            raise ValueError(f"Declared makeup assets are missing: {missing[0]}")
    return manifest, summary, totals


def build_gradient_pack(source: Path, output: Path, receipt: Path) -> dict[str, object]:
    source = source.resolve()
    output = output.resolve()
    receipt = receipt.resolve()
    source_payload = source.read_bytes()
    if _sha256(source_payload) != SOURCE_SHA256:
        raise ValueError("The official source pack SHA-256 is not the approved 1.0.2 input.")
    inspected = inspect_outfit_pack(source)
    if inspected.pack_version != SOURCE_VERSION:
        raise ValueError("The official source pack version is not 1.0.2.")
    if output.exists() or receipt.exists():
        raise ValueError("Refusing to overwrite an existing candidate or receipt.")

    authoring_root = output.parent / f".{output.stem}-authoring"
    if authoring_root.exists():
        raise ValueError("A prior makeup-gradient authoring directory still exists.")
    authoring_root.mkdir(parents=True)
    try:
        manifest, summary, totals = _write_authoring_tree(source, authoring_root)
        manifest["pack_version"] = TARGET_VERSION
        manifest_path = authoring_root / MANIFEST
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        build_outfit_pack(manifest_path, authoring_root, output)
    finally:
        if authoring_root.exists():
            for path in sorted(authoring_root.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()
            authoring_root.rmdir()

    result = inspect_outfit_pack(output)
    if result.pack_version != TARGET_VERSION:
        output.unlink(missing_ok=True)
        raise AssertionError("Sealed candidate did not retain the target pack version.")
    report: dict[str, object] = {
        "schema": "mohan.makeup-gradient-build.v1",
        "source_pack": {
            "path": source.as_posix(),
            "pack_version": SOURCE_VERSION,
            "sha256": SOURCE_SHA256,
        },
        "output_pack": {
            "path": output.as_posix(),
            "pack_version": TARGET_VERSION,
            "sha256": _sha256(output.read_bytes()),
            "size": output.stat().st_size,
        },
        "invariants": {
            "rgb_unchanged": True,
            "alpha_support_unchanged": True,
            "canvas_and_paths_unchanged": True,
            "unselected_assets_unchanged": True,
        },
        "factors": {
            f"{variant}.{slot}": {
                "numerator": numerator,
                "denominator": denominator,
                "factor": numerator / denominator,
            }
            for (variant, slot), (numerator, denominator) in sorted(FACTORS.items())
        },
        "transformed_asset_counts": {
            f"{variant}.{slot}": count
            for (variant, slot), count in sorted(summary.items())
        },
        "transformed_assets": totals,
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--receipt", type=Path, required=True)
    arguments = parser.parse_args(argv)
    report = build_gradient_pack(arguments.source, arguments.output, arguments.receipt)
    print(report["output_pack"]["sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
