from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from PySide6.QtCore import QPoint
lazy from PySide6.QtWidgets import QApplication
lazy from PySide6.QtGui import QPixmap, QRegion

lazy from domain.constants import (
    POSE_ATLAS_LAYERED_ROOT_NAME,
    POSE_ATLAS_ROOT_NAME,
)
lazy from domain.face_rig import (
    ExpressionShape,
    FaceMotionFrame,
    FacePose,
    MouthShape,
    Viseme,
)
lazy from infrastructure.layered_full_body_assets import (
    FULL_BODY_DIMENSION_HEIGHT,
    FULL_BODY_DIMENSION_WIDTH,
    VIEW_IDS,
    load_layered_full_body_assets,
)
lazy from infrastructure.layered_full_body_renderer import (
    MAX_CACHED_LAYER_PIXMAPS,
    LayeredFullBodyRenderer,
)

FULL_BODY_DIR = ROOT / "assets" / "pose-atlas" / POSE_ATLAS_LAYERED_ROOT_NAME
FULL_BODY_AUTHORITY_DIR = ROOT / "assets" / "pose-atlas" / POSE_ATLAS_ROOT_NAME
IDENTITY_SAMPLE_STEP = 6
MAX_MEAN_CHANNEL_ERROR = 2.0
MAX_TRANSPARENT_SAMPLE_RATIO = 0.015
MIN_SPEAKING_MOUTH_CHANGED_PIXELS = 20
VISIBLE_SPEECH_MOUTH_VIEWS = {
    "yaw-060-pitch+00",
    "yaw-045-pitch+00",
    "yaw-030-pitch+00",
    "yaw-015-pitch+00",
    "yaw+000-pitch+00",
    "yaw+015-pitch+00",
    "yaw+030-pitch+00",
    "yaw+045-pitch+00",
    "yaw+060-pitch+00",
}


def _app() -> object:
    return QApplication.instance() or QApplication([])


def _frame() -> FaceMotionFrame:
    return FaceMotionFrame(
        FacePose.FRONT,
        "idle_front",
        Viseme.CLOSED,
        MouthShape(),
        ExpressionShape(),
    )


def test_manifest_loads_all_twenty_four_views() -> None:
    manifest = load_layered_full_body_assets(FULL_BODY_DIR)
    assert set(manifest.views) == set(VIEW_IDS)


def test_renderer_produces_non_null_frame() -> None:
    _app()
    manifest = load_layered_full_body_assets(FULL_BODY_DIR)
    renderer = LayeredFullBodyRenderer(manifest)
    out = renderer.render_view("yaw+000-pitch+00", _frame())
    assert not out.isNull()
    assert out.width() == FULL_BODY_DIMENSION_WIDTH
    assert out.height() == FULL_BODY_DIMENSION_HEIGHT


def test_renderer_static_preview_uses_the_runtime_compositor() -> None:
    _app()
    manifest = load_layered_full_body_assets(FULL_BODY_DIR)
    renderer = LayeredFullBodyRenderer(manifest)
    out = renderer.render_static_preview("yaw+000-pitch+00")
    assert not out.isNull()
    assert out.size().toTuple() == (FULL_BODY_DIMENSION_WIDTH, FULL_BODY_DIMENSION_HEIGHT)


def test_renderer_applies_active_outfit_to_the_exact_yaw_view() -> None:
    _app()

    class Overlay:
        calls: list[str] = []

        def apply(self, frame: QPixmap, view_id: str) -> QPixmap:
            self.calls.append(view_id)
            return frame

    overlay = Overlay()
    manifest = load_layered_full_body_assets(FULL_BODY_DIR)
    renderer = LayeredFullBodyRenderer(manifest, outfit_overlay=overlay)
    assert not renderer.render_view("yaw+000-pitch+00", _frame()).isNull()
    assert overlay.calls == ["yaw+000-pitch+00"]


def test_renderer_blends_adjacent_views() -> None:
    _app()
    manifest = load_layered_full_body_assets(FULL_BODY_DIR)
    renderer = LayeredFullBodyRenderer(manifest)
    out = renderer.render_blended("yaw+000-pitch+00", _frame(), blend=0.5)
    assert not out.isNull()


def test_renderer_wraps_view_ring() -> None:
    _app()
    manifest = load_layered_full_body_assets(FULL_BODY_DIR)
    renderer = LayeredFullBodyRenderer(manifest)
    # The last view wraps to the first.
    out = renderer.render_blended("yaw+165-pitch+00", _frame(), blend=0.5)
    assert not out.isNull()


def _sampled_identity_error(
    rendered: QPixmap,
    authority_path: Path,
) -> tuple[float, float]:
    actual = rendered.toImage()
    expected = QPixmap(str(authority_path)).toImage()
    differences: list[int] = []
    unexpected_transparent = 0
    for y in range(0, expected.height(), IDENTITY_SAMPLE_STEP):
        for x in range(0, expected.width(), IDENTITY_SAMPLE_STEP):
            expected_pixel = expected.pixelColor(x, y)
            if expected_pixel.alpha() == 0:
                continue
            actual_pixel = actual.pixelColor(x, y)
            unexpected_transparent += actual_pixel.alpha() == 0
            differences.append(
                max(
                    abs(actual_pixel.red() - expected_pixel.red()),
                    abs(actual_pixel.green() - expected_pixel.green()),
                    abs(actual_pixel.blue() - expected_pixel.blue()),
                    abs(actual_pixel.alpha() - expected_pixel.alpha()),
                )
            )
    return (
        sum(differences) / len(differences),
        unexpected_transparent / len(differences),
    )


def test_neutral_renderer_reconstructs_authority_views() -> None:
    _app()
    manifest = load_layered_full_body_assets(FULL_BODY_DIR)
    renderer = LayeredFullBodyRenderer(manifest)
    frame = FaceMotionFrame(
        FacePose.FRONT,
        "idle_front",
        Viseme.CLOSED,
        MouthShape(),
        ExpressionShape(),
        breath=0.5,
    )
    for view_id in (
        "yaw-090-pitch+00",
        "yaw+000-pitch+00",
        "yaw+090-pitch+00",
    ):
        rendered = renderer.render_view(view_id, frame)
        mean_error, transparent_ratio = _sampled_identity_error(
            rendered,
            FULL_BODY_AUTHORITY_DIR / f"{view_id}.png",
        )
        assert mean_error < MAX_MEAN_CHANNEL_ERROR
        assert transparent_ratio < MAX_TRANSPARENT_SAMPLE_RATIO


def test_speaking_moves_the_mouth_without_detaching_the_chin() -> None:
    _app()
    manifest = load_layered_full_body_assets(FULL_BODY_DIR)
    renderer = LayeredFullBodyRenderer(manifest)
    view = manifest.view("yaw+000-pitch+00")
    neutral = renderer.render_view("yaw+000-pitch+00", _frame()).toImage()
    speaking = renderer.render_view(
        "yaw+000-pitch+00",
        FaceMotionFrame(
            FacePose.FRONT,
            "speaking_front",
            Viseme.A,
            MouthShape(aperture=0.9, width=0.78, rounding=0.08, jaw=1.0),
            ExpressionShape(),
        ),
    ).toImage()
    face_bounds = QRegion(QPixmap(str(view.path("base"))).mask()).boundingRect()
    # The first regression test inferred the mouth from a fixed percentage of
    # the face bounds and accidentally sampled the nose on this asset set.
    # The rebuilt cavity layer is the authoritative per-yaw mouth location;
    # the original lip replacement exports were vertically misregistered.
    mouth_bounds = QRegion(
        QPixmap(str(view.path("oral_cavity"))).mask()
    ).boundingRect()
    mouth_center_y = mouth_bounds.center().y()
    mouth_changes = 0
    for y in range(mouth_center_y - 8, mouth_center_y + 9):
        for x in range(
            mouth_bounds.x() - 3,
            mouth_bounds.right() + 4,
        ):
            mouth_changes += neutral.pixel(x, y) != speaking.pixel(x, y)
    assert mouth_changes > MIN_SPEAKING_MOUTH_CHANGED_PIXELS

    # A moving jaw replacement used to be drawn as a second skin patch below
    # the face. Speaking must not alter this lower-chin region at all.
    chin_changes = 0
    for y in range(
        round(face_bounds.y() + face_bounds.height() * 0.76),
        face_bounds.bottom() + 12,
    ):
        for x in range(face_bounds.x(), face_bounds.right() + 1):
            chin_changes += neutral.pixel(x, y) != speaking.pixel(x, y)
    assert chin_changes == 0


def test_registered_full_body_control_cutouts_are_not_double_painted() -> None:
    """Speech/mood controls must not reveal circles or face-edge seams."""

    _app()
    manifest = load_layered_full_body_assets(FULL_BODY_DIR)
    renderer = LayeredFullBodyRenderer(manifest)
    mouth = MouthShape(aperture=0.86, width=0.74, rounding=0.1, jaw=0.8)
    neutral_controls = FaceMotionFrame(
        FacePose.FRONT,
        "speaking_front",
        Viseme.A,
        mouth,
        ExpressionShape(),
        breath=0.5,
    )
    active_controls = FaceMotionFrame(
        FacePose.FRONT,
        "speaking_front",
        Viseme.A,
        mouth,
        ExpressionShape(
            blink=0.9,
            brow_lift=0.7,
            brow_tension=0.6,
            blush=0.9,
        ),
        breath=0.5,
    )
    active_image = renderer.render_view(
        "yaw+000-pitch+00",
        active_controls,
    ).toImage()
    neutral_image = renderer.render_view(
        "yaw+000-pitch+00",
        neutral_controls,
    ).toImage()
    assert active_image != neutral_image

    view = manifest.view("yaw+000-pitch+00")
    allowed_eye_region = QRegion()
    for layer_name in (
        "eyelid_left",
        "eyelid_right",
        "eyeliner_left",
        "eyeliner_right",
    ):
        allowed_eye_region = allowed_eye_region.united(
            QRegion(QPixmap(str(view.path(layer_name))).mask())
        )
    changed_pixels = 0
    for y in range(active_image.height()):
        for x in range(active_image.width()):
            if active_image.pixel(x, y) == neutral_image.pixel(x, y):
                continue
            changed_pixels += 1
            assert allowed_eye_region.contains(QPoint(x, y))
    assert changed_pixels > 0


def test_full_body_speech_assets_never_paint_fake_teeth_or_back_view_dots() -> None:
    """Only visible authority mouths may contain a speech replacement layer."""

    _app()
    manifest = load_layered_full_body_assets(FULL_BODY_DIR)
    for view_id in VIEW_IDS:
        view = manifest.view(view_id)
        oral_region = QRegion(QPixmap(str(view.path("oral_cavity"))).mask())
        teeth_region = QRegion(QPixmap(str(view.path("teeth_tongue"))).mask())
        assert teeth_region.isEmpty(), f"{view_id} contains painted fake teeth"
        assert oral_region.isEmpty() == (view_id not in VISIBLE_SPEECH_MOUTH_VIEWS), (
            f"{view_id} has the wrong speech-mouth visibility"
        )


def test_decoded_layer_cache_stays_bounded_across_the_view_ring() -> None:
    """Rotating through all 600 layers must not retain ~3.5 GiB of RGBA."""

    _app()
    manifest = load_layered_full_body_assets(FULL_BODY_DIR)
    renderer = LayeredFullBodyRenderer(manifest)
    for view_id in VIEW_IDS:
        rendered = renderer.render_view(view_id, _frame())
        assert not rendered.isNull()
        assert len(renderer._pixmap_cache) <= MAX_CACHED_LAYER_PIXMAPS
    assert len(renderer._pixmap_cache) == MAX_CACHED_LAYER_PIXMAPS


def test_behavior_performance_changes_the_full_body_frame() -> None:
    """Authored hand/energy state must reach the full-body visual path."""

    _app()
    manifest = load_layered_full_body_assets(FULL_BODY_DIR)
    renderer = LayeredFullBodyRenderer(manifest)
    neutral = renderer.render_view(
        "yaw+000-pitch+00",
        _frame(),
        left_hand="relaxed-left",
        right_hand="relaxed-right",
    ).toImage()
    active = renderer.render_view(
        "yaw+000-pitch+00",
        _frame(),
        pose_id="greeting-wave",
        left_hand="open-left",
        right_hand="relaxed-right",
        body_energy=0.8,
        gesture_beat=True,
    ).toImage()
    assert neutral != active


def run() -> None:
    test_manifest_loads_all_twenty_four_views()
    test_renderer_produces_non_null_frame()
    test_renderer_blends_adjacent_views()
    test_renderer_wraps_view_ring()
    test_neutral_renderer_reconstructs_authority_views()
    test_speaking_moves_the_mouth_without_detaching_the_chin()
    test_registered_full_body_control_cutouts_are_not_double_painted()
    test_full_body_speech_assets_never_paint_fake_teeth_or_back_view_dots()
    test_decoded_layer_cache_stays_bounded_across_the_view_ring()
    test_behavior_performance_changes_the_full_body_frame()
    print("LAYERED_FULL_BODY_OK")


if __name__ == "__main__":
    run()
