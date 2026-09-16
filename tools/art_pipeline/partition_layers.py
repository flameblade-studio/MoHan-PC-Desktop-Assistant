"""Partition one approved image for visual review in a dedicated stage.

These are visible-surface layers; independently swappable outfit assets require further authoring.
Hidden surfaces and compatibility with the runtime body need separate review.
The source owns RGBA; a same-sized semantic map owns only layer membership.
"""

from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy from pathlib import Path
lazy from typing import Literal

lazy import cv2
lazy import numpy as np

lazy from .image_ops import key_file, load_image, load_rgba, save_png, transparent_rgb_zero
lazy from .constants import IMAGE_DIMENSIONS, RGBA_CHANNELS

# BGR palette: background, hair, headwear, exposed skin, garment.
OWNER_PALETTE = ((0, 0, 0), (0, 0, 255), (0, 255, 0), (255, 0, 0), (0, 255, 255))
LAYER_NAMES = ("hair", "headwear", "exposed_skin", "garment")
# Allow rasterization-scale omissions while requiring every semantic region.
MAX_EDGE_DISTANCE = 3.0
PALETTE_SEED_TOLERANCE = 24
REVIEW_BACKGROUNDS = {"gray": 140, "white": 255, "black": 0}


def ownership_map(source: np.ndarray, semantic: np.ndarray) -> tuple[np.ndarray, int]:
    """Decode membership, retaining the source silhouette at map edge omissions."""
    if source.shape != semantic.shape:
        raise ValueError("Source and semantic map must have identical RGBA dimensions.")
    palette = np.asarray(OWNER_PALETTE, dtype=np.int32)
    # Decode only pure class colors. Antialiased red/green edges can look yellow;
    # assign those mixed pixels spatially using the pure seeds as authority.
    differences = semantic[:, :, None, :3].astype(np.int32) - palette
    color_distance = np.abs(differences).max(axis=3)
    owners = color_distance.argmin(axis=2).astype(np.uint8)
    uncertain = color_distance.min(axis=2) > PALETTE_SEED_TOLERANCE
    if uncertain.all():
        raise ValueError("Semantic map requires recognizable palette seeds.")
    if uncertain.any():
        _, nearest_seed = cv2.distanceTransformWithLabels(
            uncertain.astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_5,
            labelType=cv2.DIST_LABEL_PIXEL,
        )
        seed_owners = np.zeros(int(nearest_seed.max()) + 1, dtype=np.uint8)
        seed_owners[nearest_seed[~uncertain]] = owners[~uncertain]
        owners[uncertain] = seed_owners[nearest_seed[uncertain]]
    visible = source[:, :, 3] > 0
    missing = visible & (owners == 0)
    if missing.any():
        if not (owners > 0).any():
            raise ValueError("Semantic map requires foreground owners.")
        distance, nearest = cv2.distanceTransformWithLabels(
            (owners == 0).astype(np.uint8),
            cv2.DIST_L2,
            cv2.DIST_MASK_5,
            labelType=cv2.DIST_LABEL_PIXEL,
        )
        if float(distance[missing].max()) > MAX_EDGE_DISTANCE:
            raise ValueError("Semantic map omits foreground beyond the 3-pixel edge band.")
        owner_by_label = np.zeros(int(nearest.max()) + 1, dtype=np.uint8)
        owner_by_label[nearest[owners > 0]] = owners[owners > 0]
        owners[missing] = owner_by_label[nearest[missing]]
    owners[~visible] = 0
    return owners, int(missing.sum())


def partition_rgba(source: np.ndarray, owners: np.ndarray) -> dict[str, np.ndarray]:
    """Copy each visible pixel unchanged to exactly one layer, preserving its color and alpha."""
    if source.dtype != np.uint8 or source.ndim != IMAGE_DIMENSIONS or source.shape[2] != RGBA_CHANNELS:
        raise ValueError("Source must be uint8 BGRA.")
    if owners.shape != source.shape[:2]:
        raise ValueError("Ownership dimensions must match source dimensions.")
    visible = source[:, :, 3] > 0
    if ((owners[visible] < 1) | (owners[visible] > len(LAYER_NAMES))).any():
        raise ValueError("Every visible source pixel must have exactly one valid owner.")
    layers: dict[str, np.ndarray] = {}
    for owner, name in enumerate(LAYER_NAMES, start=1):
        layer = np.zeros_like(source)
        selected = visible & (owners == owner)
        layer[selected] = source[selected]
        layers[name] = layer
    return layers


def reconstruct(layers: dict[str, np.ndarray]) -> np.ndarray:
    """Reassemble disjoint visible surfaces; reject overlap instead of blending it."""
    if not layers:
        raise ValueError("At least one layer is required.")
    result = np.zeros_like(next(iter(layers.values())))
    occupied = np.zeros(result.shape[:2], dtype=bool)
    for layer in layers.values():
        if layer.shape != result.shape:
            raise ValueError("Layer dimensions differ.")
        selected = layer[:, :, 3] > 0
        if (occupied & selected).any():
            raise ValueError("Assign each overlapping pixel to exactly one visible-surface layer.")
        result[selected] = layer[selected]
        occupied |= selected
    return result


def review_background(source: np.ndarray, brightness: int) -> np.ndarray:
    """Render the extracted stack over an opaque review background."""
    alpha = source[:, :, 3:4].astype(np.float64) / 255.0
    return np.rint(source[:, :, :3] * alpha + brightness * (1 - alpha)).astype(np.uint8)


def load_review_source(path: Path, source_mode: Literal["magenta", "native-alpha"]) -> np.ndarray:
    """Keep native matting alpha and colors intact instead of keying them again."""
    if source_mode == "magenta":
        return transparent_rgb_zero(key_file(path))
    if source_mode != "native-alpha":
        raise ValueError(f"Unknown source background mode: {source_mode}")
    source = load_image(path)
    if source.dtype != np.uint8 or source.ndim != IMAGE_DIMENSIONS or source.shape[2] != RGBA_CHANNELS:
        raise ValueError("Native-alpha source requires 8-bit BGRA with explicit transparency.")
    alpha = source[:, :, 3]
    if not np.any(alpha > 0) or not np.any(alpha == 0):
        raise ValueError("Native-alpha cutout requires both visible foreground and transparent background.")
    return transparent_rgb_zero(source)


def export_review(
    source_path: Path, semantic_path: Path, output: Path,
    *, source_mode: Literal["magenta", "native-alpha"] = "magenta",
    expected_source_sha256: str | None = None,
) -> dict[str, object]:
    """Write exclusively to a fresh isolated review directory and preserve production assets."""
    if output.exists():
        raise FileExistsError(f"Review output already exists: {output}")
    source_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
    if expected_source_sha256 is not None and source_sha256 != expected_source_sha256:
        raise ValueError("Source SHA-256 differs from the reviewed candidate.")
    source = load_review_source(source_path, source_mode)
    semantic_sha256 = hashlib.sha256(semantic_path.read_bytes()).hexdigest()
    semantic = load_rgba(semantic_path)
    owners, extended_pixels = ownership_map(source, semantic)
    layers = partition_rgba(source, owners)
    result = reconstruct(layers)
    if not np.array_equal(result, source):
        raise ValueError("Reassembled layers differ from the prepared approved source.")
    for path, expected_digest in ((source_path, source_sha256), (semantic_path, semantic_sha256)):
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected_digest:
            raise ValueError(f"Review input changed during processing: {path}")
    output.mkdir(parents=True, exist_ok=False)
    for name, layer in layers.items():
        save_png(output / f"{name}.png", layer)
    save_png(output / "reconstruction.png", result)
    save_png(output / "ownership.png", owners)
    for name, brightness in REVIEW_BACKGROUNDS.items():
        save_png(output / f"preview-{name}.png", review_background(result, brightness))
    report: dict[str, object] = {
        "schema_version": 1,
        "purpose": "visible-surface review; runtime outfit authoring is a separate stage",
        "source_mode": source_mode,
        "chroma_key_applied": source_mode == "magenta",
        "source_sha256": source_sha256,
        "semantic_sha256": semantic_sha256,
        "expected_source_sha256": expected_source_sha256,
        "width": int(source.shape[1]),
        "height": int(source.shape[0]),
        "source_edge_pixels_assigned": extended_pixels,
        "reconstruction_rgba_changed_pixels": int(np.any(result != source, axis=2).sum()),
        "layer_visible_pixels": {
            name: int((layer[:, :, 3] > 0).sum()) for name, layer in layers.items()
        },
        "limits": [
            ("Original magenta keying changes only chroma-key-affected pixels."
             if source_mode == "magenta" else
             "Native visible RGBA is preserved; only fully transparent RGB is cleared."),
            "Semantic ownership still needs visual review at internal boundaries.",
            "The export contains observed visible surfaces only; occluded surfaces await dedicated authoring.",
            "Existing runtime body, animations, and outfit packs are unchanged.",
        ],
    }
    report["output_sha256"] = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(output.glob("*.png"))
    }
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("semantic", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--source-mode", choices=("magenta", "native-alpha"), default="magenta")
    parser.add_argument("--expected-source-sha256", help="Exact SHA-256 from the candidate review record")
    arguments = parser.parse_args(argv)
    report = export_review(arguments.source, arguments.semantic, arguments.output,
                           source_mode=arguments.source_mode,
                           expected_source_sha256=arguments.expected_source_sha256)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
