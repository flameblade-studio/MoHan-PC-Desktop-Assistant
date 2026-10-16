"""Complete front expressions retain their emotional face through speech and blinks."""

from __future__ import annotations

lazy import hashlib
lazy import json
lazy import os
lazy from dataclasses import replace
lazy from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

lazy import pytest
lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
lazy from PySide6.QtWidgets import QApplication

lazy from domain.character_runtime_data import default_expression_catalog
lazy from domain.face_motion import FaceMotionController
lazy from domain.face_rig import (
    ExpressionShape, FaceMotionFrame, FacePose, MouthShape, Viseme, blink_for_eye_state,
)
lazy from domain.outfit_pack import OPTIONAL_MAKEUP_SILHOUETTES
lazy from infrastructure.complete_halfbody_expressions import (
    COMPLETE_FRONT_POSES,
    COMPLETE_POSES,
    load_complete_halfbody_frames,
)
lazy from infrastructure.complete_halfbody_renderer import CompleteHalfbodyRenderer
lazy from infrastructure.detachable_halfbody_assets import DIMENSION
lazy from tools import golden_render

EXPRESSION = "thinking_front"
EMOTIONAL_POSE = f"front-{EXPRESSION}"
GENERIC_POSE = "front-crossed"
FACE = (100, 100)
MOUTH = (100, 110)
EYE = (100, 90)
CLOTH = (100, 150)
FAMILY_COLORS = {"neutral": "gray", "small": "yellow", "a": "red", "o": "blue"}
EYE_COLORS = {"rest": "white", "half": "cyan", "closed": "black"}
GENERIC_MOUTHS = {"small": "mouth_mid_front", "a": "mouth_wide_front", "o": "mouth_o_front"}


@pytest.fixture(scope="module", autouse=True)
def qt_app():
    return QApplication.instance() or QApplication([])


def _save_manifest(root, document):
    (root / "manifest.json").write_text(
        json.dumps(document, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n",
    )


@pytest.fixture
def front_sources(tmp_path):
    root = tmp_path / "complete-expressions"
    root.mkdir()
    poses = {}
    bindings = {}
    for pose, face_color in ((EMOTIONAL_POSE, "orange"), (GENERIC_POSE, "purple")):
        families = {}
        for family, mouth_color in FAMILY_COLORS.items():
            eyes = {}
            for eye, eye_color in EYE_COLORS.items():
                image = QImage(DIMENSION, DIMENSION, QImage.Format_RGBA8888)
                image.fill(QColor("gray"))
                image.setPixelColor(0, 0, QColor(0, 0, 0, 0))
                image.setPixelColor(*FACE, QColor(face_color))
                image.setPixelColor(*MOUTH, QColor(mouth_color))
                image.setPixelColor(*EYE, QColor(eye_color))
                path = root / f"{pose}-{family}-{eye}.png"
                assert image.save(str(path), "PNG")
                eyes[eye] = {
                    "path": path.name,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            families[family] = eyes
        poses[pose] = {
            "source_lineage": {"purpose": "test fixture"},
            "blink_composition": "whole-frame",
            "frames": families,
        }
        for family in FAMILY_COLORS:
            bindings[f"{pose}-{family}"] = {"pose": pose, "family": family}
    bindings[EXPRESSION] = {"pose": EMOTIONAL_POSE, "family": "neutral"}
    for family, expression in GENERIC_MOUTHS.items():
        bindings[expression] = {"pose": GENERIC_POSE, "family": family}
    document = {
        "schema": "mohan.complete-halfbody-expressions.v1",
        "poses": poses,
        "expressions": bindings,
    }
    _save_manifest(root, document)
    return root, document


def _motion(aperture=1.0):
    return FaceMotionFrame(
        pose=FacePose.FRONT,
        expression=EXPRESSION,
        viseme=Viseme.A,
        mouth=MouthShape(aperture=aperture),
        expression_shape=ExpressionShape(),
    )


def test_complete_front_inventory_matches_every_catalog_front_state():
    expected = set()
    for expression, pose in default_expression_catalog().state_to_pose.items():
        if pose == "front":
            expected.add(f"front-{expression}")
    assert expected
    assert expected == COMPLETE_FRONT_POSES
    assert COMPLETE_FRONT_POSES <= COMPLETE_POSES
    assert GENERIC_POSE not in COMPLETE_FRONT_POSES


def test_golden_motion_keeps_runtime_emotion_and_mouth_corners():
    runtime = FaceMotionController().close(pose="front", expression="proud_front")
    rendered = golden_render._motion("proud_front", "front", "half")
    assert rendered.expression == runtime.expression
    assert rendered.pose == runtime.pose
    assert rendered.expression_shape == replace(
        runtime.expression_shape, blink=blink_for_eye_state("half"),
    )
    assert rendered.mouth == runtime.mouth
    assert rendered.mouth.corner_smile == runtime.mouth.corner_smile
    assert 0.0 < rendered.expression_shape.blink < 1.0
    assert rendered.breath == 0.0


@pytest.mark.parametrize("pose", ("cheek", "lean"))
def test_front_golden_fix_preserves_other_pose_controls(pose):
    assert golden_render._motion("proud_front", pose, "half") == FaceMotionFrame(
        FacePose(pose), "proud_front", Viseme.CLOSED, MouthShape(),
        ExpressionShape(blink=blink_for_eye_state("half")), breath=0.0,
    )


def test_optional_front_makeup_views_cover_catalog_and_all_eye_states():
    expected = set()
    for expression, pose in default_expression_catalog().state_to_pose.items():
        if pose == "front":
            expected.update((
                f"front-{expression}",
                f"front-{expression}-half",
                f"front-{expression}-closed",
            ))
    actual = {view for view in OPTIONAL_MAKEUP_SILHOUETTES if view.startswith("front-")}
    assert actual == expected
    assert len(actual) == 3 * len(COMPLETE_FRONT_POSES)


@pytest.mark.parametrize("declares_view", (True, False))
def test_front_makeup_view_and_speech_viseme_follow_declared_support(front_sources, declares_view):
    root, _ = front_sources
    calls = []
    mouth_states = []

    class Makeup:
        def makeup_declares_view(self, view_id):
            assert view_id == EMOTIONAL_POSE
            return declares_view

        def set_active_mouth_state(self, viseme, oral_mask):
            mouth_states.append((viseme, oral_mask))

        def apply_animated(self, frame, view_id, paint_motion, *, appearance_options):
            calls.append((
                view_id,
                appearance_options.makeup_view_id,
                appearance_options.eye_state,
                mouth_states[-1],
            ))
            paint_motion(frame)
            return frame

    renderer = CompleteHalfbodyRenderer(root, Makeup())
    for family, viseme in (("small", "I"), ("a", "A"), ("o", "O")):
        frame = renderer.render(
            QPixmap(), _motion(), SimpleNamespace(mouth_expression=GENERIC_MOUTHS[family]),
        )
        assert frame is not None
        expected_view = EMOTIONAL_POSE if declares_view else None
        assert calls[-1] == (GENERIC_POSE, expected_view, "rest", (viseme, None))
        for eye in ("half", "closed"):
            blink = renderer.blink(QPixmap(frame), eye)
            assert blink is not None
            expected_view = EMOTIONAL_POSE if declares_view else None
            assert calls[-1] == (GENERIC_POSE, expected_view, eye, (viseme, None))
    neutral = renderer.render(QPixmap(), _motion(0.0), None)
    assert neutral is not None
    expected_view = EMOTIONAL_POSE if declares_view else None
    assert calls[-1] == (GENERIC_POSE, expected_view, "rest", (None, None))


@pytest.mark.parametrize("defect", ("missing", "wrong-family", "wrong-pose"))
def test_front_pose_requires_its_own_neutral_expression_binding(front_sources, defect):
    root, document = front_sources
    # Fixture aliases still cover every family, so only the canonical emotional
    # binding is broken; an unrelated completeness failure cannot pass the test.
    if defect == "missing":
        del document["expressions"][EXPRESSION]
    elif defect == "wrong-family":
        document["expressions"][EXPRESSION]["family"] = "a"
    else:
        document["expressions"][EXPRESSION]["pose"] = GENERIC_POSE
    _save_manifest(root, document)
    with pytest.raises(ValueError, match="requires its own neutral binding"):
        load_complete_halfbody_frames(root)


@pytest.mark.parametrize("composition", (None, "eye-patch"))
def test_front_pose_requires_explicit_whole_frame_blinks(front_sources, composition):
    root, document = front_sources
    record = document["poses"][EMOTIONAL_POSE]
    if composition is None:
        del record["blink_composition"]
    else:
        record["blink_composition"] = composition
    _save_manifest(root, document)
    with pytest.raises(ValueError, match="requires whole-frame blinks"):
        load_complete_halfbody_frames(root)


def test_front_expression_dresses_the_front_crossed_silhouette(front_sources):
    root, _ = front_sources
    calls = []

    class Garment:
        def apply(self, frame, view_id, **_options):
            calls.append(view_id)
            painter = QPainter(frame)
            painter.fillRect(*CLOTH, 1, 1, QColor("green"))
            painter.end()
            return frame

    renderer = CompleteHalfbodyRenderer(root, Garment())
    frame = renderer.render(QPixmap(), _motion(0.0), None)
    assert frame is not None
    assert calls == [GENERIC_POSE]
    assert frame.toImage().pixelColor(*FACE) == QColor("orange")
    assert frame.toImage().pixelColor(*CLOTH) == QColor("green")


@pytest.mark.parametrize("family", ("small", "a", "o"))
def test_generic_speech_mouth_preserves_emotion_and_closes_to_its_neutral(front_sources, family):
    root, _ = front_sources
    renderer = CompleteHalfbodyRenderer(root)
    layers = SimpleNamespace(mouth_expression=GENERIC_MOUTHS[family])
    for aperture, expected_family in ((1.0, family), (0.0, "neutral")):
        frame = renderer.render(QPixmap(), _motion(aperture), layers)
        assert frame is not None
        image = frame.toImage()
        assert image.pixelColor(*FACE) == QColor("orange")
        assert image.pixelColor(*MOUTH) == QColor(FAMILY_COLORS[expected_family])
        assert image.pixelColor(*EYE) == QColor("white")


@pytest.mark.parametrize("eye", ("half", "closed"))
def test_front_blink_keeps_displayed_emotion_and_mouth_family(front_sources, eye):
    root, _ = front_sources
    renderer = CompleteHalfbodyRenderer(root)
    displayed = renderer.render(
        QPixmap(), _motion(), SimpleNamespace(mouth_expression="mouth_mid_front"),
    )
    assert displayed is not None
    assert renderer.has_whole_frame_blink(displayed)
    queued = renderer.render(
        QPixmap(), _motion(), SimpleNamespace(mouth_expression="mouth_o_front"),
    )
    assert queued is not None
    assert queued.toImage().pixelColor(*MOUTH) == QColor("blue")
    # An empty registered eye patch must not erase the complete blink endpoint.
    patch = QPixmap(DIMENSION, DIMENSION)
    patch.fill(Qt.transparent)
    blink = renderer.blink(QPixmap(displayed), eye, patch)
    assert blink is not None
    image = blink.toImage()
    assert image.pixelColor(*FACE) == QColor("orange")
    assert image.pixelColor(*MOUTH) == QColor("yellow")
    assert image.pixelColor(*EYE) == QColor(EYE_COLORS[eye])
    assert displayed.toImage().pixelColor(*EYE) == QColor("white")
