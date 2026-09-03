"""Hair falls naturally over the face: it is clipped only out of the feathered feature core.

The former rule cut every hairstyle layer out of the protected-face box (minus a
rectangular slice per ``face_masks`` rule), which showed as a straight cut across
the temple strands at brow height and a rectangular notch at the jaw.  Now the
assembler crops hair only inside the feature core (eye and mouth rig cut-outs
dilated by ``HAIRSTYLE_FEATURE_CORE_DILATION_PX``) and the runtime fades the
same edge over ``HAIRSTYLE_FEATURE_CORE_FEATHER_PX`` pixels; garments and headwear
keep the full protected-face rule.
"""

from __future__ import annotations

lazy import os
lazy import sys
lazy import zipfile
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy import numpy as np
lazy import pytest
lazy from PySide6.QtGui import QImage, QPixmap, QRegion
lazy from PySide6.QtWidgets import QApplication

lazy from domain.outfit_pack import OFFICIAL_PACK_ROOT, inspect_outfit_pack
lazy from domain.outfit_pack_makeup import (
    FEATURE_CORE_LAYERS,
    HAIRSTYLE_FEATURE_CORE_DILATION_PX,
    HAIRSTYLE_FEATURE_CORE_FEATHER_PX,
    HALF_BODY_RIGS,
)
lazy from domain.outfit_pack_official import OFFICIAL_OUTFIT_PACK_ID
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from tools.assemble_official_default_pack import dilate

OUTFIT_PACK_PATH = OFFICIAL_PACK_ROOT / f"{OFFICIAL_OUTFIT_PACK_ID}.mohan-outfit"
RIG_ROOT = ROOT / "assets" / "expressions" / "layered"
PORTRAITS = {
    "left-neutral": "idle_lean.png",
    "front-crossed": "idle_front.png",
    "front-eureka": "eureka_front.png",
}
STRAND_SILHOUETTE = "left-neutral"
# The retired rule for left-neutral was ``bangs-safe``: hair could touch only the top
# 48 % of the face box, so everything below that line inside the face was cropped.
OLD_BANGS_TOP_FRACTION = (48, 100)
OPAQUE = 255
STRAND_SAMPLES = 3
MIN_STRAND_CANDIDATES = 2_000
# A strand pixel must differ from the bare skin under it by at least this channel sum.
MIN_SKIN_DISTANCE = 60
MAX_STRAIGHT_EDGE_RUN = 40
ALPHA_TOLERANCE = 1


def _app() -> object:
    return QApplication.instance() or QApplication([])


def _rgba(image: QImage) -> np.ndarray:
    image = image.convertToFormat(QImage.Format_RGBA8888)
    width, height = image.width(), image.height()
    rows = np.frombuffer(bytes(image.constBits()), np.uint8).reshape(height, image.bytesPerLine())
    return rows[:, : width * 4].reshape(height, width, 4).copy()


def _pack_layer(category: str, silhouette: str, slot: str) -> np.ndarray:
    pack = inspect_outfit_pack(OUTFIT_PACK_PATH)
    item = next(item for item in pack.items if item.category == category)
    member = next(asset.path for asset in item.variants[0].poses[silhouette] if asset.slot == slot)
    with zipfile.ZipFile(OUTFIT_PACK_PATH) as archive:
        image = QImage.fromData(archive.read(member), "PNG")
    assert not image.isNull(), member
    return _rgba(image)


def _region_mask(region: QRegion, shape: tuple[int, int]) -> np.ndarray:
    mask = np.zeros(shape, dtype=bool)
    for rect in region:
        mask[rect.y() : rect.y() + rect.height(), rect.x() : rect.x() + rect.width()] = True
    return mask


def _rig_region(silhouette: str, layers: tuple[str, ...]) -> QRegion:
    region = QRegion()
    for layer in layers:
        source = QPixmap(str(RIG_ROOT / f"{HALF_BODY_RIGS[silhouette]}_{layer}.png"))
        assert not source.isNull(), layer
        region = region.united(QRegion(source.mask()))
    return region


def _longest_edge_runs(alpha: np.ndarray, box: tuple[int, int, int, int]) -> tuple[int, int]:
    """Longest horizontal / vertical run of alpha-edge pixels inside ``box``.

    An edge pixel is a painted pixel with a transparent neighbour above/below
    (horizontal edge) or left/right (vertical edge).  Straight cuts produce long
    runs; natural strands do not.
    """
    painted = alpha > 0
    up, down, left, right = (np.zeros_like(painted) for _ in range(4))
    up[1:], down[:-1], left[:, 1:], right[:, :-1] = painted[:-1], painted[1:], painted[:, :-1], painted[:, 1:]
    horizontal = painted & (~up | ~down)
    vertical = painted & (~left | ~right)
    x, y, width, height = box

    def longest(rows: np.ndarray) -> int:
        best = 0
        for row in rows:
            current = 0
            for value in row:
                current = current + 1 if value else 0
                best = max(best, current)
        return best

    return longest(horizontal[y : y + height, x : x + width]), longest(vertical[y : y + height, x : x + width].T)


def _runtime_hair_alpha(overlay: ActiveOutfitOverlay, silhouette: str, sealed: np.ndarray) -> np.ndarray:
    """Alpha of the hair layer the overlay actually paints (sealed layer times the feather)."""
    layers = overlay._layers_by_view[silhouette]
    counts = [
        (abs(int((_rgba(pixmap.toImage())[:, :, 3] > 0).sum()) - int((sealed[:, :, 3] > 0).sum())), index)
        for index, (pixmap, _x, _y, _clip, _opacity) in enumerate(layers)
    ]
    pixmap = layers[min(counts)[1]][0]
    return _rgba(pixmap.toImage())[:, :, 3]


def _strand_samples(silhouette: str, hair: np.ndarray) -> list[tuple[int, int]]:
    """Three opaque strand pixels inside the retired protected rectangle, clear of the feather and hairpiece."""
    headwear = _pack_layer("headwear", silhouette, "headwear")
    shape = hair.shape[:2]
    face = _rig_region(silhouette, ("base",))
    bounds = face.boundingRect()
    core = _region_mask(_rig_region(silhouette, FEATURE_CORE_LAYERS), shape)
    old_allowed = np.zeros(shape, dtype=bool)
    top = max(1, bounds.height() * OLD_BANGS_TOP_FRACTION[0] // OLD_BANGS_TOP_FRACTION[1])
    old_allowed[bounds.y() : bounds.y() + top, bounds.x() : bounds.x() + bounds.width()] = True
    old_forbidden = _region_mask(face, shape) & ~old_allowed
    beyond_feather = ~dilate(core, HAIRSTYLE_FEATURE_CORE_DILATION_PX + HAIRSTYLE_FEATURE_CORE_FEATHER_PX + 1)
    candidates = (hair[:, :, 3] == OPAQUE) & old_forbidden & beyond_feather & (headwear[:, :, 3] == 0)
    ys, xs = np.nonzero(candidates)
    assert len(xs) >= MIN_STRAND_CANDIDATES, len(xs)
    order = np.argsort(ys, kind="stable")
    return [(int(xs[order[index]]), int(ys[order[index]])) for index in (len(order) // 4, len(order) // 2, 3 * len(order) // 4)]


def test_left_neutral_composite_keeps_the_temple_strands_over_the_cheek(tmp_path: Path) -> None:
    _app()
    silhouette = STRAND_SILHOUETTE
    hair = _pack_layer("hairstyle", silhouette, "front")
    samples = _strand_samples(silhouette, hair)
    assert len(samples) == STRAND_SAMPLES
    base = QPixmap(str(ROOT / "assets" / "expressions" / PORTRAITS[silhouette]))
    overlay = ActiveOutfitOverlay(tmp_path / "store", ROOT)
    rendered = _rgba(overlay.apply(base, silhouette).toImage())
    bare = _rgba(base.toImage())
    for x, y in samples:
        assert tuple(rendered[y, x]) == tuple(hair[y, x]), (x, y)
        skin_distance = int(np.abs(bare[y, x, :3].astype(int) - rendered[y, x, :3].astype(int)).sum())
        assert skin_distance >= MIN_SKIN_DISTANCE, (x, y, skin_distance)


@pytest.mark.parametrize("silhouette", sorted(PORTRAITS))
def test_hair_alpha_has_no_straight_cut_inside_the_face_box(tmp_path: Path, silhouette: str) -> None:
    _app()
    hair = _pack_layer("hairstyle", silhouette, "front")
    bounds = _rig_region(silhouette, ("base",)).boundingRect()
    box = (bounds.x(), bounds.y(), bounds.width(), bounds.height())
    sealed_runs = _longest_edge_runs(hair[:, :, 3], box)
    assert max(sealed_runs) <= MAX_STRAIGHT_EDGE_RUN, sealed_runs
    overlay = ActiveOutfitOverlay(tmp_path / "store", ROOT)
    base = QPixmap(str(ROOT / "assets" / "expressions" / PORTRAITS[silhouette]))
    assert overlay.apply(base, silhouette).toImage() != base.toImage()
    runtime_runs = _longest_edge_runs(_runtime_hair_alpha(overlay, silhouette, hair), box)
    assert max(runtime_runs) <= MAX_STRAIGHT_EDGE_RUN, runtime_runs


@pytest.mark.parametrize("silhouette", sorted(HALF_BODY_RIGS))
def test_sealed_hair_stays_out_of_the_dilated_feature_core(silhouette: str) -> None:
    """The assembler's crop and the runtime's reject rule agree on the feature core."""
    _app()
    hair = _pack_layer("hairstyle", silhouette, "front")
    core = _region_mask(_rig_region(silhouette, FEATURE_CORE_LAYERS), hair.shape[:2])
    assert core.any()
    assert int(((hair[:, :, 3] > 0) & dilate(core, HAIRSTYLE_FEATURE_CORE_DILATION_PX)).sum()) == 0


def test_runtime_hair_mask_is_zero_in_the_core_and_feathers_outward(tmp_path: Path) -> None:
    _app()
    silhouette = STRAND_SILHOUETTE
    overlay = ActiveOutfitOverlay(tmp_path / "store", ROOT)
    mask = overlay._hair_core_mask(silhouette)
    assert mask is not None
    alpha_image, bounds = mask
    multiplier = _rgba(alpha_image)[:, :, 3]
    shape = (1254, 1254)
    core = _region_mask(_rig_region(silhouette, FEATURE_CORE_LAYERS), shape)
    dilation, feather = HAIRSTYLE_FEATURE_CORE_DILATION_PX, HAIRSTYLE_FEATURE_CORE_FEATHER_PX
    rings = [dilate(core, dilation)]
    for _step in range(feather):
        rings.append(dilate(rings[-1], 1))
    local = slice(bounds.y(), bounds.y() + bounds.height()), slice(bounds.x(), bounds.x() + bounds.width())
    assert multiplier[rings[0][local]].max() == 0
    for step in range(1, feather):
        band = rings[step][local] & ~rings[step - 1][local]
        assert band.any()
        expected = round(OPAQUE * step / feather)
        assert np.abs(multiplier[band].astype(int) - expected).max() <= ALPHA_TOLERANCE, step
    assert multiplier[~rings[feather][local]].min() == OPAQUE
    # Feathered means no hard step: every value of the ramp occurs at least once.
    assert len({int(value) for value in np.unique(multiplier)}) >= feather + 1
