"""Integrity contract for the 21 ``v120_*`` physics cutouts.

Two classes of cutout exist on the generation-2 bare base (2026-09-02):

* ``face`` / ``eyes`` (6 files) keep the full contract: more than
  ``MIN_VISIBLE_PIXELS`` visible pixels, more than ``MIN_FEATHER_PIXELS``
  feathered pixels, every visible RGB identical to the authority portrait,
  and every transparent pixel's RGB zeroed.
* ``hair_left`` / ``hair_right`` / ``sleeve_left`` / ``sleeve_right`` /
  ``ornament`` (15 files, ``LICENSED_EMPTY``) are supplied by runtime layers
  on the generation-2 bare base: the hair is tied in a bun with no swinging
  strands, the grey sleeveless top has no sleeves, and there is no hairpiece
  (robe, hair, hairpiece and makeup are separate runtime layers by owner
  decision).  These files must be FULLY TRANSPARENT: zero visible pixels and
  all-zero RGB, so ``presentation/companion_visual_physics.py`` keeps
  rotating an empty pixmap instead of inventing pixels.  A future non-empty
  file in this tuple fails the test so the contract is changed deliberately
  rather than by drift.
"""

from __future__ import annotations

lazy from pathlib import Path

lazy from PySide6.QtGui import QImage

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "expressions"
POSES = {
    "": "idle.png",
    "_lean": "idle_lean.png",
    "_front": "idle_front.png",
}
LAYERS = (
    "sleeve_left",
    "sleeve_right",
    "hair_left",
    "hair_right",
    "ornament",
    "face",
    "eyes",
)
# Cutouts that are empty by contract on the generation-2 bare base (see the
# module docstring).  Every pose of a listed layer must be fully transparent.
# Remove a layer from this tuple only when the base itself gains that art.
LICENSED_EMPTY = (
    "sleeve_left",
    "sleeve_right",
    "hair_left",
    "hair_right",
    "ornament",
)

FEATHER_ALPHA_THRESHOLD = 220
MIN_VISIBLE_PIXELS = 100
MIN_FEATHER_PIXELS = 80
EXPECTED_CHECKED_COUNT = 21
EXPECTED_FULL_CONTRACT_COUNT = 6
EXPECTED_EMPTY_COUNT = 15
RGBA_STRIDE = 4
RGB_BYTES = 3
ALPHA_INDEX = 3


def _rgba(path: Path) -> QImage:
    image = QImage(str(path)).convertToFormat(QImage.Format_RGBA8888)
    assert not image.isNull(), path
    return image


def _pixel_counts(
    layer_bytes: bytes,
    source_bytes: bytes,
    path: Path,
) -> tuple[int, int]:
    """Enforce the colour rules on every pixel; return (visible, feather)."""
    visible_count = 0
    feather_count = 0
    for offset in range(0, len(layer_bytes), RGBA_STRIDE):
        alpha = layer_bytes[offset + ALPHA_INDEX]
        rgb = layer_bytes[offset : offset + RGB_BYTES]
        if alpha == 0:
            assert rgb == bytes(RGB_BYTES), f"transparent RGB contamination: {path}"
            continue
        visible_count += 1
        assert rgb == source_bytes[offset : offset + RGB_BYTES], (
            f"non-original color introduced: {path}"
        )
        if alpha < FEATHER_ALPHA_THRESHOLD:
            feather_count += 1
    return visible_count, feather_count


def run() -> None:
    full_contract = 0
    licensed_empty = 0
    for suffix, source_name in POSES.items():
        source = _rgba(ASSETS / source_name)
        source_bytes = bytes(source.bits())
        for layer_name in LAYERS:
            path = ASSETS / f"v120_{layer_name}{suffix}.png"
            assert path.exists(), path
            layer = _rgba(path)
            assert layer.size() == source.size(), path
            visible_count, feather_count = _pixel_counts(
                bytes(layer.bits()),
                source_bytes,
                path,
            )
            if layer_name in LICENSED_EMPTY:
                # Supplied by runtime layers on the generation-2 bare base:
                # the cutout must stay fully transparent (RGB zero is already
                # enforced for every alpha == 0 pixel above).
                assert visible_count == 0, (
                    f"{path.name} is declared empty by contract "
                    f"(LICENSED_EMPTY) but has {visible_count} visible pixels; "
                    f"if the base gained real {layer_name} art, remove the "
                    "layer from LICENSED_EMPTY deliberately"
                )
                licensed_empty += 1
                continue
            assert visible_count > MIN_VISIBLE_PIXELS, path
            assert feather_count > MIN_FEATHER_PIXELS, f"hard edge lacks feather: {path}"
            full_contract += 1
    assert full_contract == EXPECTED_FULL_CONTRACT_COUNT
    assert licensed_empty == EXPECTED_EMPTY_COUNT
    assert full_contract + licensed_empty == EXPECTED_CHECKED_COUNT
    print("V120_ASSET_INTEGRITY_OK")


if __name__ == "__main__":
    run()
