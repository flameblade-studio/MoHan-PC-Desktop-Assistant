"""Official outfit-pack quality judges.

The thresholds in this module are the two owner-provided judges moved from the
temporary root scripts.  Keep the geometry and comparisons exact: this tool is
an acceptance gate, not a cleanup or a heuristic tuning pass.
"""

from __future__ import annotations

lazy import argparse
lazy import cv2
lazy import numpy as np
lazy import sys
lazy import zipfile
lazy from collections.abc import Mapping, Sequence
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from typing import Final


CANVAS_SIZE: Final = 1254  # Cropped pack layers previously lost their canvas registration.
CANVAS_SHAPE: Final = (CANVAS_SIZE, CANVAS_SIZE)
RGBA_CHANNELS: Final = 4
CHANNEL_DIMENSION: Final = 2
ALPHA_CHANNEL: Final = 3
CONNECTED_COMPONENTS_8: Final = 8
BACKGROUND_LABEL: Final = 0
FIRST_FOREGROUND_LABEL: Final = 1

# These three member suffixes are the front-crossed layers whose alpha defects
# previously escaped a pack-level inspection.
FRONT_LAYER_KEY: Final = "front-crossed-front.png"
BACK_LAYER_KEY: Final = "front-crossed-back.png"
HEADWEAR_LAYER_KEY: Final = "front-crossed-headwear.png"
PACK_LAYER_KEYS: Final = (FRONT_LAYER_KEY, BACK_LAYER_KEY, HEADWEAR_LAYER_KEY)

# This ROI is the owner box for isolated specks that appeared in cropped layers.
SPECK_ROI: Final = (300, 100, 1000, 520)  # x0, y0, x1, y1.
# A solid pixel is part of the historical isolated-speck judge only above alpha 30.
SOLID_ALPHA_THRESHOLD: Final = 30
# Components at or below 12 pixels are the small residuals this judge rejects.
SMALL_COMPONENT_MAX_AREA: Final = 12
# Components above 60 pixels are the nearby legitimate regions used as anchors.
LARGE_COMPONENT_MIN_AREA: Final = 60
# A 7x7 dilation means an isolated speck must be more than 3 pixels from an anchor.
SPECK_CLEARANCE_PIXELS: Final = 3
# The pack layer judge accepts no isolated specks or alpha 1--30 residue.
REQUIRED_ZERO_COUNT: Final = 0
# Alpha 1--30 was the low-alpha residue class found in earlier sealed layers.
LOW_ALPHA_MINIMUM: Final = 0
LOW_ALPHA_MAXIMUM: Final = 30

# This column is the owner box for the silver tassel body.
TASSEL_ROI: Final = (720, 180, 820, 450)  # x0, y0, x1, y1.
# A 40-pixel tassel was a known incomplete extraction; the body must reach 80.
TASSEL_MIN_HEIGHT: Final = 80

# This top box catches the detached hair-bun residue seen in the official pack.
TOP_RESIDUE_ROI: Final = (600, 90, 740, 150)  # x0, y0, x1, y1.
# Top residues from 12 through 400 pixels are suspicious rather than the main mass.
TOP_RESIDUE_MIN_AREA: Final = 12
TOP_RESIDUE_MAX_AREA: Final = 400
# A 5x5 dilation makes the top-residue distance rule exactly greater than 2 pixels.
TOP_RESIDUE_CLEARANCE_PIXELS: Final = 2
# The bare base body carries nine isolated specks; composites may not exceed it.
COMPOSITE_MAX_ISOLATED_SPECKS: Final = 9


@dataclass(frozen=True)
class TasselJudgement:
    """Numeric output for the tassel-height criterion."""

    component_count: int
    heights: tuple[int, ...]


@dataclass(frozen=True)
class TopResidue:
    """One top-residue component reported by its measured area and bbox."""

    area: int
    bbox: tuple[int, int, int, int]


def _decode_rgba(encoded: bytes, label: str) -> np.ndarray:
    image = cv2.imdecode(
        np.frombuffer(encoded, dtype=np.uint8),
        cv2.IMREAD_UNCHANGED,
    )
    if (
        image is None
        or image.ndim != RGBA_CHANNELS - 1
        or image.shape[CHANNEL_DIMENSION] != RGBA_CHANNELS
    ):
        raise ValueError(f"Expected RGBA PNG: {label}")
    return image


def _full_canvas_alpha(image: np.ndarray, key: str) -> np.ndarray:
    alpha = image[:, :, ALPHA_CHANNEL]
    if alpha.shape == CANVAS_SHAPE:
        return alpha
    height, width = alpha.shape
    if height > CANVAS_SIZE or width > CANVAS_SIZE:
        raise ValueError(
            f"Layer {key} is larger than the {CANVAS_SIZE}x{CANVAS_SIZE} canvas: "
            f"{width}x{height}"
        )
    canvas = np.zeros(CANVAS_SHAPE, dtype=np.uint8)
    canvas[:height, :width] = alpha
    print(
        f"WARNING: {key} is cropped at {width}x{height}; "
        f"pasted at top-left on the {CANVAS_SIZE}x{CANVAS_SIZE} canvas"
    )
    return canvas


def load_pack_full_canvas_alphas(pack: Path) -> dict[str, np.ndarray]:
    """Load front, back, and headwear alpha masks on one full canvas."""

    with zipfile.ZipFile(pack) as archive:
        names = tuple(archive.namelist())
        layers: dict[str, np.ndarray] = {}
        for key in PACK_LAYER_KEYS:
            member = next((name for name in names if name.endswith(key)), None)
            if member is None:
                raise ValueError(f"Missing official layer: {key}")
            layers[key] = _full_canvas_alpha(
                _decode_rgba(archive.read(member), member),
                key,
            )
    return layers


def load_composite_alpha(composite: Path) -> np.ndarray:
    """Load the alpha channel from a composed RGBA portrait."""

    return _decode_rgba(composite.read_bytes(), str(composite))[:, :, ALPHA_CHANNEL]


def _roi(alpha: np.ndarray, box: tuple[int, int, int, int]) -> np.ndarray:
    x0, y0, x1, y1 = box
    return alpha[y0:y1, x0:x1]


def _square_kernel(clearance_pixels: int) -> np.ndarray:
    kernel_size = clearance_pixels * 2 + 1
    return np.ones((kernel_size, kernel_size), dtype=np.uint8)


def count_isolated_specks(alpha: np.ndarray) -> int:
    """Count small solid components farther than the owner clearance."""

    solid = (alpha > SOLID_ALPHA_THRESHOLD).astype(np.uint8)
    if solid.size == REQUIRED_ZERO_COUNT or not solid.any():
        return REQUIRED_ZERO_COUNT
    component_count, labels, stats, _centroids = (
        cv2.connectedComponentsWithStats(
            solid,
            connectivity=CONNECTED_COMPONENTS_8,
        )
    )
    large = np.zeros_like(solid)
    for label in range(FIRST_FOREGROUND_LABEL, component_count):
        if stats[label, cv2.CC_STAT_AREA] > LARGE_COMPONENT_MIN_AREA:
            large[labels == label] = 1
    far = cv2.dilate(
        large,
        _square_kernel(SPECK_CLEARANCE_PIXELS),
    ) == BACKGROUND_LABEL
    count = REQUIRED_ZERO_COUNT
    for label in range(FIRST_FOREGROUND_LABEL, component_count):
        if stats[label, cv2.CC_STAT_AREA] <= SMALL_COMPONENT_MAX_AREA:
            ys, xs = np.nonzero(labels == label)
            if far[ys, xs].all():
                count += 1
    return count


def judge_pack_isolated_specks(
    layers: Mapping[str, np.ndarray],
) -> dict[str, int]:
    """Apply the isolated-speck criterion to each official pack layer."""

    return {
        key: count_isolated_specks(_roi(layers[key], SPECK_ROI))
        for key in PACK_LAYER_KEYS
    }


def judge_pack_low_alpha_residue(
    layers: Mapping[str, np.ndarray],
) -> dict[str, int]:
    """Count alpha 1--30 pixels in each official pack layer."""

    return {
        key: int(
            (
                (layers[key] > LOW_ALPHA_MINIMUM)
                & (layers[key] <= LOW_ALPHA_MAXIMUM)
            ).sum()
        )
        for key in PACK_LAYER_KEYS
    }


def judge_composite_isolated_specks(composite_alpha: np.ndarray) -> int:
    """Apply the isolated-speck criterion to the optional composite portrait."""

    return count_isolated_specks(_roi(composite_alpha, SPECK_ROI))


def judge_tassel_height(headwear_alpha: np.ndarray) -> TasselJudgement:
    """Require one alpha>30 component at least 80 pixels high in the tassel box."""

    column = (_roi(headwear_alpha, TASSEL_ROI) > SOLID_ALPHA_THRESHOLD).astype(
        np.uint8
    )
    component_count, _labels, stats, _centroids = (
        cv2.connectedComponentsWithStats(
            column,
            connectivity=CONNECTED_COMPONENTS_8,
        )
    )
    heights = tuple(
        sorted(
            (
                int(stats[label, cv2.CC_STAT_HEIGHT])
                for label in range(FIRST_FOREGROUND_LABEL, component_count)
            ),
            reverse=True,
        )
    )
    return TasselJudgement(component_count - FIRST_FOREGROUND_LABEL, heights)


def judge_top_residue(headwear_alpha: np.ndarray) -> tuple[TopResidue, ...]:
    """Find detached alpha>30 components in the owner top-residue box."""

    solid = (headwear_alpha > SOLID_ALPHA_THRESHOLD).astype(np.uint8)
    component_count, labels, stats, _centroids = (
        cv2.connectedComponentsWithStats(
            solid,
            connectivity=CONNECTED_COMPONENTS_8,
        )
    )
    large = np.zeros_like(solid)
    for label in range(FIRST_FOREGROUND_LABEL, component_count):
        if stats[label, cv2.CC_STAT_AREA] > TOP_RESIDUE_MAX_AREA:
            large[labels == label] = 1
    far = cv2.dilate(
        large,
        _square_kernel(TOP_RESIDUE_CLEARANCE_PIXELS),
    ) == BACKGROUND_LABEL
    x0, y0, x1, y1 = TOP_RESIDUE_ROI
    residues: list[TopResidue] = []
    for label in range(FIRST_FOREGROUND_LABEL, component_count):
        x, y, width, height, area = (
            int(value) for value in stats[label]
        )
        if not (
            TOP_RESIDUE_MIN_AREA <= area <= TOP_RESIDUE_MAX_AREA
            and x0 <= x
            and x + width <= x1
            and y0 <= y
            and y + height <= y1
        ):
            continue
        ys, xs = np.nonzero(labels == label)
        if far[ys, xs].all():
            residues.append(TopResidue(area, (x, y, width, height)))
    return tuple(residues)


def _print_pack_judgements(layers: Mapping[str, np.ndarray]) -> bool:
    ok = True
    isolated = judge_pack_isolated_specks(layers)
    low_alpha = judge_pack_low_alpha_residue(layers)
    for key in PACK_LAYER_KEYS:
        nontransparent = int((layers[key] > LOW_ALPHA_MINIMUM).sum())
        print(
            f"PACK_LAYER {key} isolated_specks={isolated[key]} "
            f"low_alpha_1_30={low_alpha[key]} "
            f"nontransparent={nontransparent}"
        )
        ok = ok and isolated[key] == REQUIRED_ZERO_COUNT
        ok = ok and low_alpha[key] == REQUIRED_ZERO_COUNT
    return ok


def _print_tassel_judgement(headwear_alpha: np.ndarray) -> bool:
    result = judge_tassel_height(headwear_alpha)
    print(
        f"TASSEL_HEIGHT component_count={result.component_count} "
        f"heights={list(result.heights[:3])} minimum={TASSEL_MIN_HEIGHT}"
    )
    return bool(result.heights) and result.heights[0] >= TASSEL_MIN_HEIGHT


def _print_top_residue_judgement(headwear_alpha: np.ndarray) -> bool:
    residues = judge_top_residue(headwear_alpha)
    for residue in residues:
        x, y, width, height = residue.bbox
        print(
            f"TOP_RESIDUE area={residue.area} "
            f"bbox=x{x}..{x + width} y{y}..{y + height}"
        )
    print(f"TOP_RESIDUE count={len(residues)}")
    return not residues


def run_qc(pack: Path, composite: Path | None = None) -> int:
    """Run every available official-pack criterion and print its numbers."""

    try:
        layers = load_pack_full_canvas_alphas(pack)
        ok = _print_pack_judgements(layers)
        if composite is None:
            print("COMPOSITE isolated_specks=SKIPPED (no --composite supplied)")
        else:
            composite_count = judge_composite_isolated_specks(
                load_composite_alpha(composite)
            )
            print(
                f"COMPOSITE isolated_specks={composite_count} "
                f"maximum={COMPOSITE_MAX_ISOLATED_SPECKS}"
            )
            ok = ok and composite_count <= COMPOSITE_MAX_ISOLATED_SPECKS
        headwear = layers[HEADWEAR_LAYER_KEY]
        tassel_ok = _print_tassel_judgement(headwear)
        top_residue_ok = _print_top_residue_judgement(headwear)
        ok = ok and tassel_ok and top_residue_ok
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(f"QC_INPUT_ERROR: {error}", file=sys.stderr)
        ok = False
    print("OFFICIAL_PACK_QC_OK" if ok else "OFFICIAL_PACK_QC_FAIL")
    return 0 if ok else 1


def _arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pack", type=Path, help="official .mohan-outfit archive")
    parser.add_argument(
        "--composite",
        type=Path,
        help="optional RGBA composite portrait to check against the base budget",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _arguments(argv)
    return run_qc(arguments.pack, arguments.composite)


if __name__ == "__main__":
    raise SystemExit(main())
