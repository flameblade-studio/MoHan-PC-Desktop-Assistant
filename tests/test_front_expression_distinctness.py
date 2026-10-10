"""Front expression coverage uses actual approved assets and appearance composition."""

from __future__ import annotations

lazy import os
lazy from itertools import combinations
lazy from pathlib import Path

lazy import numpy as np
lazy import pytest
lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QPixmap, QPixmapCache
lazy from PySide6.QtWidgets import QApplication

lazy from domain.character_runtime_data import default_expression_catalog
lazy from domain.face_motion import FaceMotionController
lazy from infrastructure import layered_face_renderer
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from infrastructure.layered_face_assets import load_layered_face_assets
lazy from tools import golden_render

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

MINIMUM_CHANGED_PIXELS = 64
MINIMUM_CHANNEL_DELTA = 12
MINIMUM_VISIBLE_ALPHA = 32
OPAQUE_ALPHA = 255


def _front_expressions() -> tuple[str, ...]:
    expressions = {
        expression
        for expression, pose in default_expression_catalog().state_to_pose.items()
        if pose == "front"
    }
    expressions.add("idle_front")
    return tuple(sorted(expressions))


def _forbid_legacy_portraits(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    """Reject Python reads and renderer Qt filename loads of root-level old faces.

    The golden blink harness intentionally preloads those images for legacy
    masks. REST coverage renders directly, so no such preload is necessary.
    Complete-expression and reviewed V5 subdirectories remain available.
    """
    legacy_root = (root / "assets" / "expressions").resolve()
    original_open = Path.open
    original_pixmap = QPixmap

    def check_path(value: object) -> None:
        if not isinstance(value, (str, os.PathLike)):
            return
        path = Path(value).resolve()
        assert not (path.parent == legacy_root and path.suffix.lower() == ".png"), (
            f"Front rendering read a legacy portrait: {path}"
        )

    def checked_open(path: Path, *args, **kwargs):
        check_path(path)
        return original_open(path, *args, **kwargs)

    def checked_pixmap(*args, **kwargs):
        if args:
            check_path(args[0])
        return original_pixmap(*args, **kwargs)

    monkeypatch.setattr(Path, "open", checked_open)
    monkeypatch.setattr(layered_face_renderer, "QPixmap", checked_pixmap)


def _visible_pixels(frame: QPixmap) -> np.ndarray:
    """Premultiply colour so invisible RGB cannot satisfy distinctness."""
    rgba = np.frombuffer(golden_render._rgba_bytes(frame.toImage()), dtype=np.uint8)
    pixels = rgba.reshape(frame.height(), frame.width(), 4).astype(np.int16)
    color = pixels[:, :, :3].astype(np.int32)
    alpha = pixels[:, :, 3:4].astype(np.int32)
    pixels[:, :, :3] = (color * alpha + OPAQUE_ALPHA // 2) // OPAQUE_ALPHA
    return pixels


def test_catalog_front_expressions_are_distinct_without_legacy_faces(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every declared front state must remain visibly different at display size.

    This is intentionally an acceptance gate for installed assets. A missing
    approved expression must fail; it must not become a skip, xfail, or an
    assertion that only checks unique state names or encoded PNG hashes.
    """
    qt_app = QApplication.instance() or QApplication([])
    assert qt_app is not None
    settings = golden_render.DEFAULT_CHARACTER_SETTINGS
    root = golden_render.ROOT
    local_appdata = tmp_path / "localappdata"
    local_appdata.mkdir()
    _forbid_legacy_portraits(monkeypatch, root)
    frames: dict[str, np.ndarray] = {}
    QPixmapCache.clear()

    with (
        golden_render._render_environment(local_appdata),
        golden_render._network_disabled(),
        golden_render._official_pack_root(root, settings),
    ):
        store = tmp_path / "store"
        golden_render._prepare_store(store, "classic", settings)
        overlay = ActiveOutfitOverlay(store, root)
        renderer = layered_face_renderer.LayeredParametricFaceRenderer(
            manifest=load_layered_face_assets(settings.resolve_asset_path(
                root, settings.half_layered_root,
            )),
            outfit_overlay=overlay,
            authority_dir=settings.resolve_asset_path(root, settings.half_expression_root),
            detachable_dir=settings.resolve_asset_path(root, settings.half_detachable_root),
        )
        for expression in _front_expressions():
            base = QPixmap(*settings.half_size)
            base.fill(Qt.transparent)
            motion = FaceMotionController().close(pose="front", expression=expression)
            frame = renderer.render(base, motion, None)
            assert not frame.isNull(), expression
            assert (frame.width(), frame.height()) == settings.half_size, expression
            frames[expression] = _visible_pixels(frame)

    indistinct = []
    for left, right in combinations(frames, 2):
        first, second = frames[left], frames[right]
        visible = np.maximum(first[:, :, 3], second[:, :, 3]) >= MINIMUM_VISIBLE_ALPHA
        delta = np.max(np.abs(first[:, :, :3] - second[:, :, :3]), axis=2)
        changed = int(np.count_nonzero(visible & (delta >= MINIMUM_CHANNEL_DELTA)))
        if changed < MINIMUM_CHANGED_PIXELS:
            indistinct.append(f"{left} / {right}: {changed} changed pixels")
    assert not indistinct, (
        f"Front expressions need at least {MINIMUM_CHANGED_PIXELS} visible pixels "
        f"with channel delta >= {MINIMUM_CHANNEL_DELTA}:\n" + "\n".join(indistinct)
    )
