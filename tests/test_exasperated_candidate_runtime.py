from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

from application import service_container
from application.service_container import create_presentation_ports
from domain.face_rig import ExpressionShape, FaceMotionFrame, FacePose, MouthShape, Viseme
from infrastructure.exasperated_candidate_assets import (
    APPROVED_SOURCE_SHA256,
    FORMAL_ASSET_RELATIVE_DIR,
    PART_ORDER,
    load_exasperated_candidate_assets,
    validate_formal_exasperated_install,
)
from infrastructure.layered_face_renderer import LayeredParametricFaceRenderer
from presentation.presentation_resources import FaceRenderLayers
from presentation.companion_face_animation import CompanionFaceAnimationMixin

PRODUCT_SIZE = 465
NATIVE_MOUTH_SAMPLE = 550
MIN_SKIN_RED = 180


def _app() -> None:
    _ = QApplication.instance() or QApplication([])


def _png(path: Path, color: QColor | None, rect: QRect) -> str:
    image = QImage(1254, 1254, QImage.Format.Format_RGBA8888)
    image.fill(Qt.GlobalColor.transparent)
    if color is not None:
        painter = QPainter(image)
        painter.fillRect(rect, color)
        painter.end()
    path.parent.mkdir(parents=True, exist_ok=True)
    assert image.save(str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _package(root: Path) -> None:
    parts = {}
    for role in PART_ORDER:
        relative = f"parts/{role}.rgba.png"
        color = (
            QColor("#dcaf9b") if role == "visible_head_neck_chest_skin"
            else QColor("#302a29") if role == "visible_core_hair" else None
        )
        rect = (
            QRect(500, 520, 105, 70)
            if role == "visible_head_neck_chest_skin" else QRect(100, 100, 20, 20)
        )
        digest = _png(
            root / relative,
            color,
            rect,
        )
        parts[role] = {"path": relative, "sha256": digest}
    mouths = {}
    for variant, color in (("mid", "#008000"), ("open", "#0000ff"), ("round", "#ff0000")):
        relative = f"mouths/{variant}.rgba.png"
        digest = _png(root / relative, QColor(color), QRect(530, 540, 40, 25))
        mouths[variant] = {"path": relative, "sha256": digest}
    (root / "manifest.json").write_text(json.dumps({
        "schema": "mohan.exasperated-runtime-candidate.v1",
        "approved_source_sha256": APPROVED_SOURCE_SHA256,
        "parts": parts,
        "mouths": mouths,
    }), encoding="utf-8")


def _motion(viseme: Viseme, aperture: float) -> FaceMotionFrame:
    return FaceMotionFrame(
        FacePose.FRONT,
        "exasperated_front",
        viseme,
        MouthShape(aperture=aperture),
        ExpressionShape(blink=1.0),
    )


class _CandidateAppearance:
    def __init__(self) -> None:
        self.calls: list[tuple[int, str, str | None]] = []

    def apply(self, frame: QPixmap, silhouette: str, *, mouth_expression: str | None) -> QPixmap:
        self.calls.append((frame.width(), silhouette, mouth_expression))
        return frame


class _ForbiddenOldAppearance:
    def apply(self, frame: QPixmap, silhouette: str) -> QPixmap:
        raise AssertionError(f"Old appearance reached candidate {silhouette}")


def test_candidate_renders_native_parts_and_source_bound_speech_at_product_size(tmp_path: Path) -> None:
    _app()
    _package(tmp_path)
    appearance = _CandidateAppearance()
    renderer = LayeredParametricFaceRenderer(
        exasperated_candidate_dir=tmp_path,
        candidate_appearance_overlay=appearance,
        outfit_overlay=_ForbiddenOldAppearance(),
    )
    base = QPixmap(PRODUCT_SIZE, PRODUCT_SIZE)
    base.fill(Qt.GlobalColor.transparent)
    rest = renderer.render(base, _motion(Viseme.CLOSED, 0.0), None)
    native_x = round(NATIVE_MOUTH_SAMPLE * PRODUCT_SIZE / 1254)
    native_y = round(NATIVE_MOUTH_SAMPLE * PRODUCT_SIZE / 1254)
    assert rest.size() == base.size()
    assert rest.toImage().pixelColor(native_x, native_y).red() > MIN_SKIN_RED
    old_mouth = QPixmap(PRODUCT_SIZE, PRODUCT_SIZE)
    old_mouth.fill(QColor("#ffff00"))
    mask = QPixmap(PRODUCT_SIZE, PRODUCT_SIZE)
    mask.fill(QColor("#ffffff"))
    expected = (
        ("exasperated_front_speech_mid", "#008000"),
        ("exasperated_front_speech_open", "#0000ff"),
        ("exasperated_front_speech_round", "#ff0000"),
        ("exasperated_front_speech_i", "#008000"),
        ("exasperated_front_speech_u", "#ff0000"),
    )
    for expression, color in expected:
        layers = FaceRenderLayers(
            old_mouth, mask, QRect(0, 0, PRODUCT_SIZE, PRODUCT_SIZE), mouth_expression=expression
        )
        frame = renderer.render(base, _motion(Viseme.A, 1.0), layers)
        pixel = frame.toImage().pixelColor(native_x, native_y)
        target = QColor(color)
        assert (pixel.red(), pixel.green(), pixel.blue()) == (
            target.red(), target.green(), target.blue()
        )
    open_layers = FaceRenderLayers(
        old_mouth, mask, QRect(0, 0, PRODUCT_SIZE, PRODUCT_SIZE),
        mouth_expression="exasperated_front_speech_open",
    )
    stale_closed = renderer.render(base, _motion(Viseme.A, 0.0), open_layers)
    partial = renderer.render(base, _motion(Viseme.A, 0.09), open_layers)
    full = renderer.render(base, _motion(Viseme.A, 1.0), open_layers)
    assert stale_closed.toImage() == rest.toImage()
    assert partial.toImage() == full.toImage()
    assert appearance.calls[0] == (1254, "front-exasperated", None)
    assert appearance.calls[1] == (1254, "front-exasperated", "exasperated_front_speech_mid")
    assert appearance.calls[-3] == (1254, "front-exasperated", None)


def test_candidate_hash_and_mouth_scope_fail_closed(tmp_path: Path) -> None:
    _app()
    _package(tmp_path)
    loaded = load_exasperated_candidate_assets(tmp_path)
    assert loaded.compose().toImage().pixelColor(105, 105).alpha() > 0
    assert loaded.compose(hidden=frozenset({"visible_core_hair"})).toImage().pixelColor(105, 105).alpha() == 0
    original = loaded.patch("exasperated_front_speech_open")
    path = tmp_path / "mouths/open.rgba.png"
    _png(path, QColor("red"), QRect(1, 1, 10, 10))
    assert loaded.patch("exasperated_front_speech_open").toImage() == original.toImage()
    with pytest.raises(ValueError, match="digest mismatch"):
        load_exasperated_candidate_assets(tmp_path)
    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["mouths"]["open"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="outside its source-bound ROI"):
        load_exasperated_candidate_assets(tmp_path)


def test_product_factory_requires_explicit_absolute_candidate_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    _package(tmp_path)
    monkeypatch.setenv("MOHAN_EXASPERATED_CANDIDATE_DIR", str(tmp_path))
    renderer = create_presentation_ports().face_renderer_factory()
    assert renderer._exasperated_candidate_dir == tmp_path.resolve()
    base = QPixmap(PRODUCT_SIZE, PRODUCT_SIZE)
    base.fill(Qt.GlobalColor.transparent)
    assert not renderer.render(base, _motion(Viseme.CLOSED, 0.0), None).isNull()
    (tmp_path / "appearance").mkdir()
    appearance = SimpleNamespace(store=None)
    monkeypatch.setattr(
        service_container,
        "ExasperatedCandidateAppearance",
        SimpleNamespace(load=lambda root: appearance),
    )
    create_presentation_ports().face_renderer_factory()
    assert appearance.store == service_container.presentation_contracts.default_data_dir() / "outfits"
    monkeypatch.setenv("MOHAN_EXASPERATED_CANDIDATE_DIR", "relative/candidate")
    with pytest.raises(ValueError, match="must be absolute"):
        create_presentation_ports().face_renderer_factory()


def test_default_factory_loads_formal_layers_and_preserves_other_pose(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    monkeypatch.delenv("MOHAN_EXASPERATED_CANDIDATE_DIR", raising=False)
    formal = service_container.resource_path(FORMAL_ASSET_RELATIVE_DIR).resolve()
    validate_formal_exasperated_install(formal)
    renderer = create_presentation_ports().face_renderer_factory()
    assert renderer._exasperated_candidate_dir == formal
    assert renderer.supports_discrete_speech("exasperated_front")
    assert not renderer.supports_discrete_speech("mock_scold")
    base = QPixmap(PRODUCT_SIZE, PRODUCT_SIZE)
    base.fill(Qt.GlobalColor.transparent)
    exasperated = renderer.render(base, _motion(Viseme.CLOSED, 0.0), None)
    other = FaceMotionFrame(
        FacePose.FRONT, "idle_front", Viseme.CLOSED,
        MouthShape(aperture=0.0), ExpressionShape(),
    )
    legacy = renderer.render(base, other, None)
    assert not exasperated.isNull() and not legacy.isNull()
    assert exasperated.toImage() != legacy.toImage()


def test_default_install_missing_or_drifted_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    monkeypatch.delenv("MOHAN_EXASPERATED_CANDIDATE_DIR", raising=False)
    original = service_container.resource_path
    missing = tmp_path / "missing"
    monkeypatch.setattr(
        service_container, "resource_path",
        lambda relative: missing if relative == FORMAL_ASSET_RELATIVE_DIR else original(relative),
    )
    with pytest.raises(FileNotFoundError):
        create_presentation_ports().face_renderer_factory()
    formal = original(FORMAL_ASSET_RELATIVE_DIR)
    copy = tmp_path / "copy"
    shutil.copytree(formal, copy)
    monkeypatch.setattr(
        service_container, "resource_path",
        lambda relative: copy if relative == FORMAL_ASSET_RELATIVE_DIR else original(relative),
    )
    (copy / "mouths" / "open.rgba.png").write_bytes(b"changed")
    with pytest.raises(ValueError, match="drifted"):
        create_presentation_ports().face_renderer_factory()


def test_formal_cosmetics_cannot_skip_pinned_owner_approval(tmp_path: Path) -> None:
    formal = service_container.resource_path(FORMAL_ASSET_RELATIVE_DIR)
    copied = tmp_path / "cosmetics-without-approval"
    shutil.copytree(formal, copied)
    manifest_path = copied / "appearance" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["cosmetic_status"] = "owner_palette_approved_native_integration"
    manifest.pop("cosmetic_owner_approval", None)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="owner palette approval"):
        validate_formal_exasperated_install(copied)


def test_first_speech_cue_rebinds_idle_front_motion_to_exasperated_candidate(tmp_path: Path) -> None:
    _app()
    _package(tmp_path)
    renderer = LayeredParametricFaceRenderer(exasperated_candidate_dir=tmp_path)
    window = SimpleNamespace(
        speech_gesture_expression="exasperated_front",
        speech_closed_expression="idle_front",
        physics_expression_poses={"exasperated_front": "front"},
        idle_pose="front",
    )
    stale = FaceMotionFrame(
        FacePose.FRONT, "idle_front", Viseme.A, MouthShape(aperture=1.0), ExpressionShape()
    )
    aligned = CompanionFaceAnimationMixin._speech_aligned_motion(window, stale)
    assert aligned.pose is FacePose.FRONT
    assert aligned.expression == "exasperated_front"
    base = QPixmap(PRODUCT_SIZE, PRODUCT_SIZE)
    base.fill(Qt.GlobalColor.transparent)
    blank = QPixmap(PRODUCT_SIZE, PRODUCT_SIZE)
    blank.fill(Qt.GlobalColor.transparent)
    layers = FaceRenderLayers(
        blank, blank, QRect(0, 0, PRODUCT_SIZE, PRODUCT_SIZE),
        mouth_expression="exasperated_front_speech_open",
    )
    spoken = renderer.render(base, aligned, layers)
    sample = round(NATIVE_MOUTH_SAMPLE * PRODUCT_SIZE / 1254)
    assert spoken.toImage().pixelColor(sample, sample).blue() > MIN_SKIN_RED


def test_candidate_timer_switches_complete_endpoints_while_legacy_blends(tmp_path: Path) -> None:
    _app()
    renderer = LayeredParametricFaceRenderer(exasperated_candidate_dir=tmp_path)
    before = QPixmap(20, 20)
    before.fill(QColor("red"))
    after = QPixmap(20, 20)
    after.fill(QColor("blue"))
    window = SimpleNamespace(
        state="speaking", audio_driven_mouth=True,
        mouth_transition_from=before, mouth_transition_to=after,
        mouth_transition_duration=1.0, face_renderer=renderer,
        speech_gesture_expression="exasperated_front", speech_closed_expression="idle_front",
    )
    window.mouth_transition_started = time.perf_counter() - 0.25
    early = CompanionFaceAnimationMixin._blended_mouth_transition_frame(window)
    assert early is not None and early[0].toImage() == before.toImage()
    window.mouth_transition_started = time.perf_counter() - 0.75
    late = CompanionFaceAnimationMixin._blended_mouth_transition_frame(window)
    assert late is not None and late[0].toImage() == after.toImage()
    window.speech_gesture_expression = "mock_scold"
    window.mouth_transition_started = time.perf_counter() - 0.5
    legacy = CompanionFaceAnimationMixin._blended_mouth_transition_frame(window)
    assert legacy is not None
    assert legacy[0].toImage() != before.toImage()
    assert legacy[0].toImage() != after.toImage()
