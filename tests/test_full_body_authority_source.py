"""Verify explicit full-body authority roots stay isolated and fail closed."""

from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy import pytest
lazy from PySide6.QtGui import QColor, QImage, QPixmap
lazy from PySide6.QtWidgets import QApplication
lazy from domain.face_rig import (
    ExpressionShape,
    FaceMotionFrame,
    FacePose,
    MouthShape,
    Viseme,
)
lazy from infrastructure import layered_full_body_renderer as renderer_module
lazy from infrastructure.layered_full_body_assets import (
    LayeredFullBodyManifest,
    LayeredFullBodyView,
)
lazy from infrastructure.layered_full_body_renderer import LayeredFullBodyRenderer

VIEW_ID = "yaw+000-pitch+00"
CANVAS_SIZE = (32, 32)
SEAM_POINT = (2, 2)
FACE_POINT = (24, 24)
TARGET_COLOR = (11, 17, 23, 255)
SOURCE_COLOR = (101, 107, 113, 255)
AUTHORITY_A_COLOR = (211, 31, 47, 255)
AUTHORITY_B_COLOR = (37, 149, 83, 255)
LEGACY_COLOR = (79, 61, 179, 255)


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _write_png(
    path: Path,
    *,
    size: tuple[int, int] = CANVAS_SIZE,
    fill: tuple[int, int, int, int] = (0, 0, 0, 0),
    pixels: tuple[tuple[tuple[int, int], tuple[int, int, int, int]], ...] = (),
) -> None:
    image = QImage(size[0], size[1], QImage.Format_RGBA8888)
    image.fill(QColor(*fill))
    for point, color in pixels:
        image.setPixelColor(*point, QColor(*color))
    assert image.save(str(path), "PNG")


def _authority(root: Path, color: tuple[int, int, int, int], *, size: tuple[int, int] = CANVAS_SIZE) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{VIEW_ID}.png"
    _write_png(path, size=size, fill=color)
    return path


def _view(root: Path, layer_name: str, point: tuple[int, int]) -> LayeredFullBodyView:
    layer = root / f"{VIEW_ID}_{layer_name}.png"
    _write_png(layer, pixels=((point, SOURCE_COLOR),))
    return LayeredFullBodyView(VIEW_ID, {layer_name: layer})


def _renderer(authority_root: Path, view: LayeredFullBodyView) -> LayeredFullBodyRenderer:
    manifest = LayeredFullBodyManifest({VIEW_ID: view})
    return LayeredFullBodyRenderer(manifest, authority_root=authority_root)


def _target() -> QPixmap:
    target = QPixmap(*CANVAS_SIZE)
    target.fill(QColor(*TARGET_COLOR))
    return target


def _pixel(target: QPixmap, point: tuple[int, int]) -> tuple[int, int, int, int]:
    color = target.toImage().pixelColor(*point)
    return color.red(), color.green(), color.blue(), color.alpha()


def _motion() -> FaceMotionFrame:
    return FaceMotionFrame(
        FacePose.FRONT,
        "authority-source-test",
        Viseme.CLOSED,
        MouthShape(),
        ExpressionShape(),
        breath=0.5,
    )


def test_explicit_authority_root_controls_registered_seam(tmp_path: Path) -> None:
    _app()
    view = _view(tmp_path, "body", SEAM_POINT)
    authority_root = tmp_path / "authority"
    _authority(authority_root, AUTHORITY_A_COLOR)

    target = _target()
    renderer = _renderer(authority_root, view)
    renderer._heal_registered_seams(target, view)

    assert _pixel(target, SEAM_POINT) == AUTHORITY_A_COLOR


def test_explicit_authority_root_controls_authority_face(tmp_path: Path) -> None:
    _app()
    view = _view(tmp_path, "base", FACE_POINT)
    authority_root = tmp_path / "authority"
    _authority(authority_root, AUTHORITY_A_COLOR)

    target = _target()
    renderer = _renderer(authority_root, view)
    renderer._restore_authority_face(target, view)

    assert _pixel(target, FACE_POINT) == AUTHORITY_A_COLOR


def test_two_explicit_authority_roots_do_not_share_cached_pixels(tmp_path: Path) -> None:
    _app()
    view = _view(tmp_path, "body", SEAM_POINT)
    base_view = _view(tmp_path, "base", FACE_POINT)
    view = LayeredFullBodyView(
        VIEW_ID,
        {**view.layers, **base_view.layers},
    )
    authority_a = tmp_path / "authority-a"
    authority_b = tmp_path / "authority-b"
    _authority(authority_a, AUTHORITY_A_COLOR)
    _authority(authority_b, AUTHORITY_B_COLOR)
    renderer_a = _renderer(authority_a, view)
    renderer_b = _renderer(authority_b, view)

    def restored(renderer: LayeredFullBodyRenderer) -> QPixmap:
        target = _target()
        renderer._heal_registered_seams(target, view)
        renderer._restore_authority_face(target, view)
        return target

    output_a = restored(renderer_a)
    output_b = restored(renderer_b)
    output_a_again = restored(renderer_a)

    assert _pixel(output_a, SEAM_POINT) == AUTHORITY_A_COLOR
    assert _pixel(output_a, FACE_POINT) == AUTHORITY_A_COLOR
    assert _pixel(output_b, SEAM_POINT) == AUTHORITY_B_COLOR
    assert _pixel(output_b, FACE_POINT) == AUTHORITY_B_COLOR
    assert _pixel(output_a_again, SEAM_POINT) == AUTHORITY_A_COLOR
    assert _pixel(output_a_again, FACE_POINT) == AUTHORITY_A_COLOR


def test_explicit_missing_authority_does_not_fall_back_to_default_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    legacy_root = tmp_path / "legacy-project"
    monkeypatch.setattr(renderer_module, "PROJECT_ROOT", legacy_root)
    monkeypatch.setattr(renderer_module, "FULL_BODY_AUTHORITY_DIR", Path("legacy-authority"))
    _authority(legacy_root / "legacy-authority", LEGACY_COLOR)
    explicit_root = tmp_path / "explicit-missing"
    view = _view(tmp_path, "body", SEAM_POINT)

    with pytest.raises(ValueError, match="Missing or invalid view authority"):
        _renderer(explicit_root, view)


def test_explicit_wrong_size_authority_does_not_fall_back_to_default_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    legacy_root = tmp_path / "legacy-project"
    monkeypatch.setattr(renderer_module, "PROJECT_ROOT", legacy_root)
    monkeypatch.setattr(renderer_module, "FULL_BODY_AUTHORITY_DIR", Path("legacy-authority"))
    _authority(legacy_root / "legacy-authority", LEGACY_COLOR)
    explicit_root = tmp_path / "explicit-wrong-size"
    _authority(explicit_root, AUTHORITY_A_COLOR, size=(8, 8))
    view = _view(tmp_path, "body", SEAM_POINT)

    renderer = _renderer(explicit_root, view)
    with pytest.raises(ValueError, match="View authority canvas mismatch"):
        renderer.render_view(VIEW_ID, _motion())


def test_default_authority_root_keeps_legacy_resolution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _app()
    legacy_root = tmp_path / "legacy-project"
    monkeypatch.setattr(renderer_module, "PROJECT_ROOT", legacy_root)
    monkeypatch.setattr(renderer_module, "FULL_BODY_AUTHORITY_DIR", Path("legacy-authority"))
    _authority(legacy_root / "legacy-authority", LEGACY_COLOR)
    view = _view(tmp_path, "body", SEAM_POINT)
    manifest = LayeredFullBodyManifest({VIEW_ID: view})

    renderer = LayeredFullBodyRenderer(manifest)
    output = renderer.render_view(VIEW_ID, _motion())

    assert _pixel(output, SEAM_POINT) == LEGACY_COLOR
    assert renderer._strict_authority is False


def test_relative_authority_root_stays_bound_to_construction_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    cwd_a = tmp_path / "cwd-a"
    cwd_b = tmp_path / "cwd-b"
    _authority(cwd_a / "authority", AUTHORITY_A_COLOR)
    _authority(cwd_b / "authority", AUTHORITY_B_COLOR)

    absolute_layer_root = tmp_path / "absolute-layers"
    absolute_layer_root.mkdir()
    view = _view(absolute_layer_root, "body", SEAM_POINT)

    monkeypatch.chdir(cwd_a)
    renderer = _renderer(Path("authority"), view)

    # The renderer must resolve a relative authority root when it is built;
    # the first authority read happens after CWD changes to a different tree.
    monkeypatch.chdir(cwd_b)
    target = _target()
    renderer._heal_registered_seams(target, view)

    assert _pixel(target, SEAM_POINT) == AUTHORITY_A_COLOR


def test_explicit_authority_without_blink_frames_freezes_source_at_construction(
    tmp_path: Path,
) -> None:
    _app()
    view = _view(tmp_path, "body", SEAM_POINT)
    authority_root = tmp_path / "authority"
    _authority(authority_root, AUTHORITY_A_COLOR)

    renderer = _renderer(authority_root, view)
    _authority(authority_root, AUTHORITY_B_COLOR)
    target = _target()
    renderer._heal_registered_seams(target, view)

    assert _pixel(target, SEAM_POINT) == AUTHORITY_A_COLOR


def test_explicit_authority_snapshot_survives_pixmap_cache_eviction(
    tmp_path: Path,
) -> None:
    _app()
    view = _view(tmp_path, "body", SEAM_POINT)
    authority_root = tmp_path / "authority"
    authority_path = _authority(authority_root, AUTHORITY_A_COLOR)
    renderer = _renderer(authority_root, view)

    assert _pixel(renderer._cached_pixmap(authority_path), SEAM_POINT) == AUTHORITY_A_COLOR
    for index in range(renderer_module.MAX_CACHED_LAYER_PIXMAPS + 1):
        dummy = tmp_path / f"dummy-authority-{index}.png"
        _write_png(dummy, fill=AUTHORITY_B_COLOR)
        renderer._cached_pixmap(dummy)
    _authority(authority_root, AUTHORITY_B_COLOR)

    assert _pixel(renderer._cached_pixmap(authority_path), SEAM_POINT) == AUTHORITY_A_COLOR


def test_lazy_manifest_freezes_authority_on_first_load(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    view = _view(tmp_path, "body", SEAM_POINT)
    manifest = LayeredFullBodyManifest({VIEW_ID: view})
    authority_root = tmp_path / "authority"
    _authority(authority_root, AUTHORITY_A_COLOR)
    renderer = LayeredFullBodyRenderer(authority_root=authority_root)
    monkeypatch.setattr(
        renderer_module,
        "load_layered_full_body_assets",
        lambda _root: manifest,
    )

    renderer._manifest_or_load()
    _authority(authority_root, AUTHORITY_B_COLOR)
    target = _target()
    renderer._heal_registered_seams(target, view)

    assert _pixel(target, SEAM_POINT) == AUTHORITY_A_COLOR


def test_explicit_corrupt_authority_is_rejected_at_construction(tmp_path: Path) -> None:
    _app()
    view = _view(tmp_path, "body", SEAM_POINT)
    authority_root = tmp_path / "authority"
    authority_root.mkdir()
    (authority_root / f"{VIEW_ID}.png").write_bytes(b"not-a-png")

    with pytest.raises(ValueError, match="Missing or invalid view authority"):
        _renderer(authority_root, view)


def main() -> None:
    result = pytest.main([__file__, "-q"])
    if result:
        raise SystemExit(result)
    print("FULL_BODY_AUTHORITY_SOURCE_OK")


if __name__ == "__main__":
    main()
