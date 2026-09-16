"""Small synthetic checks for reviewed native pose overlay state handling."""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

from domain.outfit_pack_official import BUILTIN_MAKEUP_PACK_ID
from infrastructure import reviewed_pose_overlay as overlay_module
from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
from infrastructure.reviewed_pose_overlay import (
    COSMETIC_SLOTS,
    ReviewedPoseOverlayMixin,
)


CANVAS = (20, 20)
SLOT_STRENGTHS = {"eyes": 0.25, "cheeks": 0.5, "lips": 0.75}
EXPECTED_RED_RANGES = {
    "eyes": (55, 75),
    "cheeks": (115, 140),
    "lips": (180, 205),
}


def _app() -> QApplication:
    app = QApplication.instance()
    return app if app is not None else QApplication([])


def _solid(color: str) -> QPixmap:
    pixmap = QPixmap(*CANVAS)
    pixmap.fill(QColor(color))
    return pixmap


def _transparent_with_point(x: int, y: int, color: QColor) -> QPixmap:
    image = QImage(*CANVAS, QImage.Format.Format_RGBA8888)
    image.fill(Qt.GlobalColor.transparent)
    image.setPixelColor(x, y, color)
    return QPixmap.fromImage(image)


def _pixel(pixmap: QPixmap, x: int, y: int) -> QColor:
    return pixmap.toImage().pixelColor(x, y)


class _StrengthProbe(ReviewedPoseOverlayMixin):
    def __init__(self, store: Path, selection: SimpleNamespace) -> None:
        self._store = store
        self._selection = selection
        self.selected_variant_calls: list[tuple[str, object]] = []

    def _selected_variant(self, category: str, selection: object) -> None:
        self.selected_variant_calls.append((category, selection))


@pytest.mark.parametrize(
    ("pack_id", "variant_id", "intensity", "expected_factor"),
    (
        ("builtin", "none", 1.0, 0.0),
        (BUILTIN_MAKEUP_PACK_ID, "light", 1.0, 0.55),
        (BUILTIN_MAKEUP_PACK_ID, "classic", 0.0, 0.0),
        (BUILTIN_MAKEUP_PACK_ID, "classic", 1.0, 1.0),
    ),
    ids=("bare", "light", "classic-zero", "classic-full"),
)
def test_native_cosmetic_strengths_keep_bare_light_and_classic_levels(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pack_id: str,
    variant_id: str,
    intensity: float,
    expected_factor: float,
) -> None:
    """Light applies the 0.55 family factor once, then preserves each slot multiplier."""

    _app()
    selection = SimpleNamespace(
        effective_pack_id=pack_id,
        effective_item_id="face",
        effective_variant_id=variant_id,
    )
    probe = _StrengthProbe(tmp_path, selection)
    monkeypatch.setattr(overlay_module, "resolve_active_selection", lambda *_: selection)
    monkeypatch.setattr(overlay_module, "read_makeup_intensity", lambda *_: intensity)
    monkeypatch.setattr(
        overlay_module,
        "read_makeup_slot_intensities",
        lambda *_args, **_kwargs: SLOT_STRENGTHS,
    )

    strengths = probe._native_cosmetic_strengths()

    assert strengths == {
        slot: pytest.approx(expected_factor * SLOT_STRENGTHS[slot])
        for slot in COSMETIC_SLOTS
    }
    if pack_id == "builtin":
        assert probe.selected_variant_calls == []
    else:
        assert probe.selected_variant_calls == [("makeup", selection)]


class _CosmeticAssets:
    cosmetic_slots = ("eyes", "cheeks", "lips")
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self._slots = {
            "eyes": _transparent_with_point(3, 3, QColor("white")),
            "cheeks": _transparent_with_point(8, 8, QColor("white")),
            "lips": _transparent_with_point(13, 13, QColor("white")),
        }

    def cosmetic(self, state: str, slot: str) -> QPixmap:
        self.calls.append((state, slot))
        return QPixmap(self._slots[slot])


class _CosmeticProbe(ReviewedPoseOverlayMixin):
    def _native_cosmetic_strengths(self, *, slots=COSMETIC_SLOTS) -> dict[str, float]:
        return dict(SLOT_STRENGTHS)


def test_native_cosmetic_paint_uses_each_slot_strength_once() -> None:
    """Synthetic slot probes distinguish the 0.25/.5/.75 opacity values."""

    _app()
    assets = _CosmeticAssets()
    result = _CosmeticProbe()._paint_native_cosmetics(
        _solid("black"), assets, "rest",
    )

    eyes_min, eyes_max = EXPECTED_RED_RANGES["eyes"]
    cheeks_min, cheeks_max = EXPECTED_RED_RANGES["cheeks"]
    lips_min, lips_max = EXPECTED_RED_RANGES["lips"]
    assert eyes_min <= _pixel(result, 3, 3).red() <= eyes_max
    assert cheeks_min <= _pixel(result, 8, 8).red() <= cheeks_max
    assert lips_min <= _pixel(result, 13, 13).red() <= lips_max
    assert assets.calls == [("rest", slot) for slot in assets.cosmetic_slots]


def test_refresh_state_clears_native_frame_and_eye_caches_for_selection_changes(
    tmp_path: Path,
) -> None:
    """Changing makeup or clothing state makes native frames eligible for recomposition."""

    _app()
    store = tmp_path / "store"
    store.mkdir()
    active = store / "active.json"
    makeup = store / "makeup.json"
    active.write_text('{"garment":"first"}', encoding="utf-8")
    makeup.write_text('{"intensity":1}', encoding="utf-8")

    overlay = ActiveOutfitOverlay(tmp_path / "store", tmp_path, visible_hand_region=None)
    overlay._refresh_state()

    def seed_native_caches() -> None:
        overlay._reviewed_native_frames = {("cheek-rest", False): _solid("blue")}
        overlay._reviewed_native_eyes = {"cheek-rest": _solid("red")}

    seed_native_caches()
    makeup.write_text('{"intensity":0.42}', encoding="utf-8")
    overlay._refresh_state()
    assert overlay._reviewed_native_frames == {}
    assert overlay._reviewed_native_eyes == {}

    seed_native_caches()
    active.write_text('{"garment":"second"}', encoding="utf-8")
    overlay._refresh_state()
    assert overlay._reviewed_native_frames == {}
    assert overlay._reviewed_native_eyes == {}


class _BlinkAssets:
    cosmetic_slots = ("eyes", "cheeks", "lips")
    def __init__(self, closed_patch: QPixmap) -> None:
        self.closed_patch = closed_patch
        # The retained endpoint set: only the authored CLOSED patch exists here.
        self.patches = {"closed": closed_patch}

    def patch(self, state: str) -> QPixmap:
        assert state == "closed"
        return QPixmap(self.closed_patch)

    def cosmetic(self, state: str, slot: str) -> QPixmap:
        del state, slot
        return _transparent_with_point(0, 0, QColor(255, 255, 255, 0))


class _BlinkProbe(ReviewedPoseOverlayMixin):
    def __init__(self, neutral: QPixmap, assets: _BlinkAssets) -> None:
        self.neutral = neutral
        self.assets = assets

    def _native_motion(self, view_id: str) -> _BlinkAssets:
        del view_id
        return self.assets

    def native_neutral(self, view_id: str) -> QPixmap:
        del view_id
        return QPixmap(self.neutral)

    def _native_cosmetic_strengths(self, *, slots=COSMETIC_SLOTS) -> dict[str, float]:
        return dict.fromkeys(slots, 0.0)


def test_closed_native_blink_preserves_the_existing_mouth_region() -> None:
    """The eye patch replaces only its registered pixels on the current frame."""

    _app()
    neutral = _solid("green")
    base = _solid("green")
    painter = QPainter(base)
    painter.fillRect(10, 10, 3, 2, QColor("red"))
    painter.end()
    closed_patch = _transparent_with_point(3, 3, QColor("blue"))
    result = _BlinkProbe(neutral, _BlinkAssets(closed_patch)).render_native_blink(
        base,
        "cheek-rest",
        eye_state="closed",
    )

    assert result is not None
    assert _pixel(result, 3, 3) == QColor("blue")
    assert _pixel(result, 10, 10) == QColor("red")
    assert _pixel(result, 0, 0) == QColor("green")
