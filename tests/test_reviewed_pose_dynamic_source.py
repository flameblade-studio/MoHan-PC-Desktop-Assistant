"""A reviewed pose that declares the complete-expression dynamic source must not raise.

Installing the approved new cheek-rest native makes the *retained* reviewed motion
root fail closed on ``native_body_sha256``.  Bound expressions never reach it
(``LayeredParametricFaceRenderer.render`` consults the complete-expression set
first), but an unbound one does, and the raise escapes ``render``.  These tests
pin the minimal contract that fixes that without weakening the gate:

* a pose that declares ``dynamic_source: complete-expressions`` (or whose installed
  complete-expression set binds it) releases the retained motion root and renders
  the approved native as a still frame;
* a pose that declares nothing keeps the original fail-closed behaviour and the
  original message;
* an unknown declaration value is rejected while loading.
"""

from __future__ import annotations

lazy import hashlib
lazy import json
lazy import os
lazy from pathlib import Path

lazy import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QColor, QImage, QPixmap
lazy from PySide6.QtWidgets import QApplication

lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from infrastructure.layered_face_renderer import LayeredParametricFaceRenderer
lazy from infrastructure.reviewed_garment_assets import load_reviewed_garment_assets

DIMENSION = 1254
VIEW = "cheek-rest"
SOURCE_SHA = "a" * 64
MOTION_ROOT_MESSAGE = "Reviewed pose motion native body SHA-256 mismatch."
COMPLETE_EXPRESSIONS_ROOT = Path("assets") / "expressions" / "complete-expressions"


def _png(image: QImage) -> bytes:
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice

    output = QByteArray()
    buffer = QBuffer(output)
    assert buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    assert image.save(buffer, "PNG")
    return bytes(output)


def _rgba(color: QColor) -> bytes:
    image = QImage(DIMENSION, DIMENSION, QImage.Format.Format_RGBA8888)
    image.fill(Qt.GlobalColor.transparent)
    image.setPixelColor(40, 30, color)
    return _png(image)


def _visibility() -> bytes:
    image = QImage(DIMENSION, DIMENSION, QImage.Format.Format_Grayscale8)
    image.fill(255)
    return _png(image)


def _write(path: Path, payload: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def _motion_root(root: Path) -> None:
    """One retained motion root bound to a *different* native body than the pose."""
    motion = root / VIEW / "motion"
    motion.mkdir(parents=True, exist_ok=True)
    (motion / "manifest.json").write_text(
        json.dumps(
            {
                "schema": "mohan.reviewed-pose-motion.v1",
                "source_sha256": SOURCE_SHA,
                "native_body_sha256": "0" * 64,
            }
        ),
        encoding="utf-8",
    )


def _build_root(
    tmp_path: Path,
    *,
    dynamic_source: str | None = None,
    complete_expressions: bool = False,
    motion_root: bool = True,
) -> Path:
    """A minimal but real reviewed-garment installation under a synthetic asset root."""
    expressions = tmp_path / "assets" / "expressions"
    root = expressions / "reviewed-garments"
    native_sha = _write(expressions / "native.rgba.png", _rgba(QColor("tan")))
    visibility_sha = _write(root / VIEW / "visibility.png", _visibility())
    layer_sha = _write(root / VIEW / "garment.rgba.png", _rgba(QColor("blue")))
    record = {
        "native_source_file": "native.rgba.png",
        "native_source_sha256": native_sha,
        "visibility": {"path": f"{VIEW}/visibility.png", "sha256": visibility_sha},
        "ordered_layers": [
            {"path": f"{VIEW}/garment.rgba.png", "sha256": layer_sha},
        ],
        "selection_exact": {
            "pack_id": "mohan.official.blue-white-hanfu",
            "item_id": "hanfu-robe",
            "variant_id": "blue-white",
        },
        "native_appearance_selections": {},
        "motion_required": True,
        "approved_source_sha256": SOURCE_SHA,
    }
    if dynamic_source is not None:
        record["dynamic_source"] = dynamic_source
    (root / "manifest.json").write_text(
        json.dumps({"schema": "mohan.reviewed-native-garments.v1",
                    "poses": {VIEW: record}}),
        encoding="utf-8",
    )
    if motion_root:
        _motion_root(root)
    if complete_expressions:
        manifest = expressions / COMPLETE_EXPRESSIONS_ROOT.name
        manifest.mkdir(parents=True, exist_ok=True)
        (manifest / "manifest.json").write_text(
            json.dumps({
                "schema": "mohan.complete-halfbody-expressions.v1",
                "poses": {VIEW: {}},
                "expressions": {},
            }),
            encoding="utf-8",
        )
    store = tmp_path / "store"
    store.mkdir(parents=True, exist_ok=True)
    (store / "active.json").write_text(
        json.dumps({
            category: {"pack_id": "builtin", "item_id": "none", "variant_id": "none"}
            for category in (
                "garment", "hairstyle", "headwear", "makeup", "weapon",
                "handheld", "jewelry", "foreground-effect",
            )
        }),
        encoding="utf-8",
    )
    return tmp_path


def _overlay(tmp_path: Path) -> ActiveOutfitOverlay:
    QApplication.instance() or QApplication([])
    return ActiveOutfitOverlay(tmp_path / "store", tmp_path, visible_hand_region=None)


def _renderer(tmp_path: Path, overlay: ActiveOutfitOverlay) -> LayeredParametricFaceRenderer:
    return LayeredParametricFaceRenderer(
        authority_dir=tmp_path / "assets" / "expressions",
        outfit_overlay=overlay,
        use_detachable=False,
    )


def _unbound_motion():
    from domain.face_rig import ExpressionShape, FaceMotionFrame, FacePose, MouthShape, Viseme

    return FaceMotionFrame(
        pose=FacePose.CHEEK,
        expression="happy",
        viseme=Viseme.CLOSED,
        mouth=MouthShape(aperture=0.0),
        expression_shape=ExpressionShape(),
        gaze_x=0.0,
        gaze_y=0.0,
        breath=0.0,
    )


def _blank() -> QPixmap:
    blank = QPixmap(DIMENSION, DIMENSION)
    blank.fill(Qt.GlobalColor.transparent)
    return blank


def test_declared_pose_returns_a_still_frame_instead_of_raising(tmp_path: Path) -> None:
    root = _build_root(tmp_path, dynamic_source="complete-expressions")
    overlay = _overlay(root)
    renderer = _renderer(root, overlay)

    pose = overlay._reviewed_assets if False else None
    del pose
    assert overlay.native_neutral(VIEW) is not None
    assert overlay._native_motion(VIEW) is None
    assert overlay.has_native_motion(VIEW) is False
    assert overlay.render_native_state(VIEW) is None
    # The declaration removes the motion root from authority; it is never loaded.
    assert not getattr(overlay, "_reviewed_motion_assets", {})

    frame = renderer.render(_blank(), _unbound_motion(), None)
    assert not frame.isNull()
    assert frame.size().toTuple() == (DIMENSION, DIMENSION)
    # ... and it is the SAME approved native, not an old character or a blank.
    assert frame.toImage() == overlay.native_neutral(VIEW).toImage()

    assets = load_reviewed_garment_assets(root / "assets/expressions/reviewed-garments")
    assert assets is not None
    assert assets.poses[VIEW].motion_required is True
    assert assets.poses[VIEW].approved_source_sha256 == SOURCE_SHA
    assert assets.poses[VIEW].dynamic_source == "complete-expressions"


def test_undeclared_pose_still_fails_closed_with_the_original_error(tmp_path: Path) -> None:
    root = _build_root(tmp_path)
    overlay = _overlay(root)
    renderer = _renderer(root, overlay)

    with pytest.raises(ValueError) as failure:
        overlay._native_motion(VIEW)
    assert str(failure.value) == MOTION_ROOT_MESSAGE

    with pytest.raises(ValueError) as capability:
        overlay.has_native_motion(VIEW)
    assert str(capability.value) == MOTION_ROOT_MESSAGE

    with pytest.raises(ValueError) as render:
        renderer.render(_blank(), _unbound_motion(), None)
    assert str(render.value) == MOTION_ROOT_MESSAGE


def test_installed_complete_expressions_declare_the_pose_without_a_manifest_field(
    tmp_path: Path,
) -> None:
    root = _build_root(tmp_path)
    overlay = _overlay(root)
    with pytest.raises(ValueError):
        overlay._native_motion(VIEW)

    _build_root(tmp_path, complete_expressions=True)
    declared = _overlay(root)
    assets = load_reviewed_garment_assets(root / "assets/expressions/reviewed-garments")
    assert assets is not None and assets.poses[VIEW].dynamic_source is None
    assert declared._native_motion(VIEW) is None
    assert declared.has_native_motion(VIEW) is False
    assert not getattr(declared, "_reviewed_motion_assets", {})


def test_unknown_dynamic_source_is_rejected_while_loading(tmp_path: Path) -> None:
    root = _build_root(tmp_path, dynamic_source="somewhere-else")
    with pytest.raises(ValueError, match="dynamic source"):
        load_reviewed_garment_assets(root / "assets/expressions/reviewed-garments")
