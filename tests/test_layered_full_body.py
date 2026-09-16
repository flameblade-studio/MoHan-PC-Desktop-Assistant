from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path
lazy from dataclasses import replace
lazy from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from PySide6.QtCore import QPoint
lazy from PySide6.QtWidgets import QApplication
lazy from PySide6.QtGui import QColor, QPainter, QPixmap, QRegion

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
    # The +90 native profile retains visible lips; the yaw-090 profile is the
    # main-branch source again (2026-09-16) and paints no oral cavity.
    # Source/rest/A/U comparisons cover all twelve calibrated mouth views.
    "yaw-075-pitch+00",
    "yaw-060-pitch+00",
    "yaw-045-pitch+00",
    "yaw-030-pitch+00",
    "yaw-015-pitch+00",
    "yaw+000-pitch+00",
    "yaw+015-pitch+00",
    "yaw+030-pitch+00",
    "yaw+045-pitch+00",
    "yaw+060-pitch+00",
    "yaw+075-pitch+00",
    "yaw+090-pitch+00",
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


def test_renderer_applies_active_outfit_to_the_exact_yaw_view() -> None:
    _app()

    class Overlay:
        calls: list[str] = []

        def apply_appearance(self, frame: QPixmap, view_id: str) -> QPixmap:
            self.calls.append(f"appearance:{view_id}")
            return frame

        def apply_makeup(self, frame: QPixmap, view_id: str, **_kwargs) -> QPixmap:
            self.calls.append(f"makeup:{view_id}")
            return frame

    overlay = Overlay()
    manifest = load_layered_full_body_assets(FULL_BODY_DIR)
    renderer = LayeredFullBodyRenderer(manifest, outfit_overlay=overlay)
    assert not renderer.render_view("yaw+000-pitch+00", _frame()).isNull()
    assert overlay.calls == [
        "appearance:yaw+000-pitch+00",
        "makeup:yaw+000-pitch+00",
    ]


def test_renderer_blends_adjacent_views() -> None:
    _app()
    manifest = load_layered_full_body_assets(FULL_BODY_DIR)
    renderer = LayeredFullBodyRenderer(manifest)
    out = renderer.render_blended("yaw+000-pitch+00", _frame(), blend=0.5)
    assert not out.isNull()


def test_closed_eyes_suppress_only_eye_makeup_and_restore_on_reopening() -> None:
    _app()
    eye_point, cheek_point, lip_point = (500, 210), (500, 260), (500, 285)
    colors = {"eyes": QColor("red"), "cheeks": QColor("green"), "lips": QColor("blue")}

    class Overlay:
        def apply_appearance(self, frame, view_id):
            return frame

        def apply_makeup(
            self,
            frame,
            view_id,
            *,
            suppress_makeup_slots=(),
            eye_state="rest",
        ):
            result = QPixmap(frame)
            painter = QPainter(result)
            for slot, point in zip(colors, (eye_point, cheek_point, lip_point), strict=True):
                if slot not in suppress_makeup_slots:
                    painter.fillRect(*point, 1, 1, colors[slot])
            painter.end()
            return result

    manifest = load_layered_full_body_assets(FULL_BODY_DIR)
    bare = LayeredFullBodyRenderer(manifest)
    renderer = LayeredFullBodyRenderer(manifest, outfit_overlay=Overlay())
    for blink in (0.0, 1.0, 0.0):
        motion = replace(_frame(), breath=0.5, expression_shape=ExpressionShape(blink=blink))
        actual = renderer.render_view("yaw+000-pitch+00", motion).toImage()
        expected_eye = (
            bare.render_view("yaw+000-pitch+00", motion).toImage().pixelColor(*eye_point)
            if blink else colors["eyes"]
        )
        assert actual.pixelColor(*eye_point) == expected_eye
        assert actual.pixelColor(*cheek_point) == colors["cheeks"]
        assert actual.pixelColor(*lip_point) == colors["lips"]


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
    face_bounds = QRegion(QPixmap(str(view.path("base"))).mask()).united(
        QRegion(QPixmap(str(view.path("jaw"))).mask())
    ).boundingRect()
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
    # the face. Speaking preserves this lower-chin region exactly.
    chin_changes = 0
    for y in range(
        round(face_bounds.y() + face_bounds.height() * 0.76),
        face_bounds.bottom() + 12,
    ):
        for x in range(face_bounds.x(), face_bounds.right() + 1):
            chin_changes += neutral.pixel(x, y) != speaking.pixel(x, y)
    assert chin_changes == 0


def test_registered_full_body_control_cutouts_are_not_double_painted() -> None:
    """Speech/mood controls retain seamless face edges and natural feature shapes."""

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
    # Authored blink frames own their registered eye footprint, which can
    # extend beyond the neutral eyelid cutouts (for example lower lashes).
    for path in view.blink_frames.values():
        allowed_eye_region = allowed_eye_region.united(QRegion(QPixmap(str(path)).mask()))
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
        if view_id in VISIBLE_SPEECH_MOUTH_VIEWS:
            lip_region = QRegion(QPixmap(str(view.path("lip_upper"))).mask()).united(
                QRegion(QPixmap(str(view.path("lip_lower"))).mask())
            )
            assert lip_region.boundingRect().adjusted(-1, -1, 1, 1).contains(
                oral_region.boundingRect()
            ), f"{view_id} has speech pixels outside the authored lip bounds"


def test_decoded_layer_cache_stays_bounded_across_the_view_ring() -> None:
    """Rotating all 600 layers releases RGBA buffers within the cache budget."""

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



def test_authority_restoration_preserves_fractional_alpha() -> None:
    app = QApplication.instance() or QApplication([])
    authority = QPixmap(2, 1)
    edge_alpha = 64
    authority.fill(QColor(180, 120, 100, edge_alpha))
    target = QPixmap(authority)
    expected = authority.toImage()
    renderer = LayeredFullBodyRenderer()
    renderer._face_region_cache = {"edge": QRegion(0, 0, 1, 1)}
    renderer._seam_region_cache = {"edge": QRegion(0, 0, 1, 1)}
    renderer._cached_pixmap = lambda path, *, required=True: authority
    view = SimpleNamespace(view_id="edge")
    for _ in range(3):
        renderer._heal_registered_seams(target, view)
        renderer._restore_authority_face(target, view)
    assert target.toImage() == expected
    assert target.toImage().pixelColor(0, 0).alpha() == edge_alpha
    app.processEvents()

def run() -> None:
    test_authority_restoration_preserves_fractional_alpha()
    test_closed_eyes_suppress_only_eye_makeup_and_restore_on_reopening()
    test_renderer_applies_active_outfit_to_the_exact_yaw_view()
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
