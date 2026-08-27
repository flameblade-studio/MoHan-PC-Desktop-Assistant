from __future__ import annotations

lazy import json
lazy from pathlib import Path

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QColor, QImage, QPixmap
lazy from PySide6.QtWidgets import QApplication

lazy from infrastructure.layered_full_body_assets import (
    _load_authority_mouth_centers,
)
lazy from infrastructure.mouth_geometry import inward_lerped_u_layer

EXPECTED_YAW000_CENTER_X = 510.898681640625
OPAQUE_ALPHA = 255
_APP = QApplication.instance() or QApplication([])


def _one_pixel_layer(x: int, y: int) -> QPixmap:
    image = QImage(1024, 8, QImage.Format_RGBA8888)
    image.fill(Qt.transparent)
    image.setPixelColor(x, y, QColor(220, 60, 80, 255))
    return QPixmap.fromImage(image)


def test_authority_center_is_loaded_only_when_explicitly_trusted(tmp_path: Path) -> None:
    manifest = {
        "schema_version": 1,
        "views": {
            "yaw+000-pitch+00": {
                "trusted": True,
                "mouth_center_x": EXPECTED_YAW000_CENTER_X,
            },
            "yaw+015-pitch+00": {
                "trusted": False,
                "mouth_center_x": 500.0,
            },
        },
    }
    (tmp_path / "mouth_authority_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    centers = _load_authority_mouth_centers(tmp_path)
    assert centers == {"yaw+000-pitch+00": EXPECTED_YAW000_CENTER_X}


def test_u_layer_moves_x_only_toward_explicit_authority_center() -> None:
    source = _one_pixel_layer(700, 3)
    transformed = inward_lerped_u_layer(source, 500.0, 1.0).toImage()
    # x' = 500 + 0.95 * (700 - 500) = 690; y is unchanged.
    assert transformed.pixelColor(690, 3).alpha() > 0
    assert all(
        transformed.pixelColor(x, y).alpha() == 0
        for y in (2, 4)
        for x in range(1024)
    )
    assert transformed.pixelColor(690, 3).alpha() == OPAQUE_ALPHA


def test_missing_authority_center_fails_closed_and_is_non_cumulative() -> None:
    source = _one_pixel_layer(700, 3)
    unchanged = inward_lerped_u_layer(source, None, 1.0)
    assert unchanged.toImage() == source.toImage()
    first = inward_lerped_u_layer(source, 500.0, 1.0)
    repeated_from_authority = inward_lerped_u_layer(source, 500.0, 1.0)
    assert first.toImage() == repeated_from_authority.toImage()


def test_renderers_do_not_apply_u_to_whole_registered_mouths() -> None:
    root = Path(__file__).resolve().parents[1]
    half = (root / "infrastructure" / "layered_face_renderer.py").read_text(
        encoding="utf-8"
    )
    legacy = (root / "infrastructure" / "face_renderer.py").read_text(
        encoding="utf-8"
    )
    full = (root / "infrastructure" / "layered_full_body_renderer.py").read_text(
        encoding="utf-8"
    )
    assert "inward_lerped_u_layer" not in half
    assert "viseme_u_inward_scale" not in legacy
    assert "inward_scaled_mouth" not in half + legacy + full
    assert "inward_lerped_u_layer" in full


def test_dev_and_packaged_paths_include_trusted_authority_manifest() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = root / "assets" / "pose-atlas" / "v4-layered" / (
        "mouth_authority_manifest.json"
    )
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["views"]["yaw+000-pitch+00"]["trusted"] is True
    assert (
        payload["views"]["yaw+000-pitch+00"]["mouth_center_x"]
        == EXPECTED_YAW000_CENTER_X
    )
    renderer = (
        root / "infrastructure" / "layered_full_body_renderer.py"
    ).read_text(encoding="utf-8")
    packaging = (root / "tools" / "build_preview_package.py").read_text(
        encoding="utf-8"
    )
    assert "load_layered_full_body_assets" in renderer
    assert "LAYERED_POSE_ATLAS_ROOT" in packaging
    assert "assets/pose-atlas/v4-layered" in packaging
