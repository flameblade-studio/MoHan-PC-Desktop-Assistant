"""Whole half-body expressions keep mouth continuity across asynchronous blinks."""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import replace
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

from domain.face_rig import ExpressionShape, FaceMotionFrame, FacePose, MouthShape, Viseme
from infrastructure.complete_halfbody_expressions import load_complete_halfbody_frames
from infrastructure.layered_face_renderer import LayeredParametricFaceRenderer

SIZE = 1254
MOUTH = (600, 600)
EYE = (500, 400)
CLOTH = (600, 900)
COLORS = {"neutral": "gray", "small": "yellow", "a": "red", "o": "blue"}
EYE_COLORS = {"rest": "white", "half": "cyan", "closed": "black"}


@pytest.fixture(scope="module", autouse=True)
def qt_app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def sources(tmp_path):
    root = tmp_path / "complete-expressions"
    root.mkdir()
    frames = {}
    for family, color in COLORS.items():
        frames[family] = {}
        for eye, eye_color in EYE_COLORS.items():
            image = QImage(SIZE, SIZE, QImage.Format_RGBA8888)
            image.fill(QColor("gray"))
            image.setPixelColor(0, 0, QColor(0, 0, 0, 0))
            image.setPixelColor(*MOUTH, QColor(color))
            image.setPixelColor(*EYE, QColor(eye_color))
            path = root / f"{family}-{eye}.png"
            assert image.save(str(path), "PNG")
            frames[family][eye] = {
                "path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
    bindings = {"idle_front": {"pose": "front-crossed", "family": "neutral"}}
    bindings.update({
        name: {"pose": "front-crossed", "family": family}
        for name, family in (("mouth_mid_front", "small"), ("mouth_wide_front", "a"), ("mouth_o_front", "o"))
    })
    document = {
        "schema": "mohan.complete-halfbody-expressions.v1",
        "poses": {"front-crossed": {"source_lineage": {"approval": "test"}, "frames": frames}},
        "expressions": bindings,
    }
    path = root / "manifest.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return root, path, document


def _motion():
    return FaceMotionFrame(
        pose=FacePose.FRONT, expression="idle_front", viseme=Viseme.A,
        mouth=MouthShape(aperture=1.0), expression_shape=ExpressionShape(),
        gaze_x=0.0, gaze_y=0.0, breath=0.5,
    )


class Garment:
    def apply(self, frame, view_id, **_options):
        assert view_id == "front-crossed"
        painter = QPainter(frame)
        painter.fillRect(*CLOTH, 1, 1, QColor("green"))
        painter.end()
        return frame


def _renderer(root):
    return LayeredParametricFaceRenderer(
        authority_dir=root.parent, outfit_overlay=Garment(), use_detachable=False,
    )


def test_displayed_endpoint_owns_blink_even_after_next_mouth_is_rendered(sources):
    root, _, _ = sources
    renderer = _renderer(root)
    base = QPixmap(SIZE, SIZE)
    base.fill(Qt.transparent)
    old = renderer.render(base, _motion(), SimpleNamespace(mouth_expression="mouth_mid_front"))
    new = renderer.render(base, _motion(), SimpleNamespace(mouth_expression="mouth_o_front"))
    assert new.toImage().pixelColor(*MOUTH) == QColor("blue")
    # The speech transition is still displaying its old endpoint.
    archived = QPixmap(old)
    for eye in ("half", "closed"):
        blink = renderer.render_overlay(
            archived, QPixmap(), eye_state=eye, view_id="front-crossed",
        )
        assert blink.toImage().pixelColor(*MOUTH) == QColor("yellow")
        assert blink.toImage().pixelColor(*EYE) == QColor(EYE_COLORS[eye])
        assert blink.toImage().pixelColor(*CLOTH) == QColor("green")
    assert archived.toImage().pixelColor(*EYE) == QColor("white")
    assert renderer.supports_discrete_speech("idle_front")
    assert not renderer.supports_discrete_speech("unapproved-expression")


def test_zero_aperture_returns_complete_neutral_and_stable_gray_body(sources):
    root, _, _ = sources
    renderer = _renderer(root)
    motion = replace(_motion(), mouth=MouthShape(aperture=0.0))
    frame = renderer.render(QPixmap(), motion, SimpleNamespace(mouth_expression="mouth_wide_front"))
    assert frame.toImage().pixelColor(*MOUTH) == QColor("gray")
    assert frame.toImage().pixelColor(*CLOTH) == QColor("green")
    assert frame.toImage().pixelColor(0, 0).alpha() == 0


def test_scaled_display_retains_whole_expression_blink_context(sources):
    root, _, _ = sources
    renderer = _renderer(root)
    frame = renderer.render(QPixmap(465, 465), _motion(), SimpleNamespace(mouth_expression="mouth_wide_front"))
    blink = renderer.render_overlay(QPixmap(frame), QPixmap(), eye_state="closed", view_id="front-crossed")
    assert blink.size() == frame.size()
    assert renderer._complete_halfbody._contexts[blink.cacheKey()] == ("front-crossed", "a")


@pytest.mark.parametrize("defect", ["digest", "path", "missing-eye", "invalid-pose", "opaque"])
def test_installed_invalid_sources_do_not_fall_back_to_legacy(sources, defect):
    root, path, document = sources
    frames = document["poses"]["front-crossed"]["frames"]
    if defect == "digest":
        frames["a"]["rest"]["sha256"] = "0" * 64
    elif defect == "path":
        frames["a"]["rest"]["path"] = "../escape.png"
    elif defect == "missing-eye":
        del frames["a"]["half"]
    elif defect == "invalid-pose":
        document["expressions"]["idle_front"]["pose"] = "unknown"
    else:
        image = QImage(SIZE, SIZE, QImage.Format_RGBA8888)
        image.fill(QColor("blue"))
        target = root / frames["a"]["rest"]["path"]
        assert image.save(str(target), "PNG")
        frames["a"]["rest"]["sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError):
        _renderer(root).supports_discrete_speech("idle_front")


def test_missing_installation_is_optional_but_missing_manifest_is_not(tmp_path):
    root = tmp_path / "absent"
    assert load_complete_halfbody_frames(root) is None
    root.mkdir()
    with pytest.raises(FileNotFoundError):
        load_complete_halfbody_frames(root)


def test_loading_freezes_sources_before_disk_changes(sources):
    root, _, _ = sources
    renderer = _renderer(root)
    assert renderer.supports_discrete_speech("idle_front")
    (root / "a-rest.png").write_bytes(b"changed after startup")
    frame = renderer.render(QPixmap(), _motion(), SimpleNamespace(mouth_expression="mouth_wide_front"))
    assert frame.toImage().pixelColor(*MOUTH) == QColor("red")


def test_displayed_endpoint_survives_a_complete_pose_set_of_new_contexts(sources):
    root, _, _ = sources
    renderer = _renderer(root)
    frame = renderer.render(QPixmap(), _motion(), SimpleNamespace(mouth_expression="mouth_mid_front"))
    # Seven poses, four mouth families and three eye states can be queued while
    # the current speech endpoint still owns the screen.
    for _ in range(7 * 4 * 3):
        renderer.render(QPixmap(), _motion(), SimpleNamespace(mouth_expression="mouth_o_front"))
    blink = renderer.render_overlay(QPixmap(frame), QPixmap(), eye_state="closed", view_id="front-crossed")
    assert blink.toImage().pixelColor(*MOUTH) == QColor("yellow")
    assert blink.toImage().pixelColor(*EYE) == QColor("black")


def test_atomic_appearance_retains_endpoint_and_discrete_eye_context(sources):
    root, _, _ = sources
    calls = []

    class AnimatedGarment:
        def apply_animated(self, frame, view_id, paint_motion, *, eye_state, suppress_makeup_slots):
            calls.append((view_id, eye_state, suppress_makeup_slots))
            paint_motion(frame)
            return Garment().apply(frame, view_id)

    renderer = LayeredParametricFaceRenderer(authority_dir=root.parent, outfit_overlay=AnimatedGarment(), use_detachable=False)
    old = renderer.render(QPixmap(), _motion(), SimpleNamespace(mouth_expression="mouth_mid_front"))
    renderer.render(QPixmap(), _motion(), SimpleNamespace(mouth_expression="mouth_o_front"))
    blink = renderer.render_overlay(QPixmap(old), QPixmap(), eye_state="half", view_id="front-crossed")
    assert blink.toImage().pixelColor(*MOUTH) == QColor("yellow")
    assert blink.toImage().pixelColor(*EYE) == QColor("cyan")
    assert blink.toImage().pixelColor(*CLOTH) == QColor("green")
    assert calls[-1] == ("front-crossed", "half", frozenset({"eyes"}))
    assert old.toImage().pixelColor(*EYE) == QColor("white")


def test_partial_speech_bindings_do_not_advertise_complete_speech(sources):
    root, path, document = sources
    document["expressions"] = {"idle_front": document["expressions"]["idle_front"]}
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="bindings for every mouth family"):
        _renderer(root).supports_discrete_speech("idle_front")
