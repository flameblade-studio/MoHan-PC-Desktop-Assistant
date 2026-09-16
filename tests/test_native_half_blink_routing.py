"""Contract and routing gates for native ordinary half-blink portraits."""

from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy import pytest
lazy from PySide6.QtCore import QRect, Qt
lazy from PySide6.QtGui import QImage, QPainter, QPixmap
lazy from PySide6.QtWidgets import QApplication

lazy from domain.companion_animation_contract import (
    EXPRESSION_HALF_BLINK_ASSETS,
    EXPRESSION_HALF_BLINK_FRAME_SOURCES,
    EXPRESSION_HALF_BLINK_FRAMES,
    EXPRESSION_IMAGE_ASSETS,
)
lazy from presentation.companion_face_assets import CompanionFaceAssetMethods
lazy from presentation.companion_visual_physics import CompanionVisualPhysicsMethods

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HALF_BLINK_FRAMES = {
    "idle_front": "idle_front_half",
    "idle_lean": "idle_lean_half",
    "eureka_front": "eureka_front_half",
    "mock_hit_front": "mock_hit_front_half",
    "mock_scold": "mock_scold_half",
}
SAME_POSE_HALF_ALIASES = {
    "speaking_front": "idle_front_half",
    "mouth_mid_front": "idle_front_half",
    "speaking_lean": "idle_lean_half",
    "mouth_mid_lean": "idle_lean_half",
    "eureka_front_speech_mid": "eureka_front_half",
}


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def _asset(stem: str) -> QPixmap:
    return QPixmap(
        str(PROJECT_ROOT / "assets" / "expressions" / f"{stem}.png")
    ).scaled(465, 465, Qt.KeepAspectRatio, Qt.SmoothTransformation)


def _pixels(pixmap: QPixmap) -> bytes:
    image = pixmap.toImage().convertToFormat(QImage.Format_RGBA8888)
    return bytes(image.constBits())


class _Renderer:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def render_overlay(
        self,
        base: QPixmap,
        patch: QPixmap,
        **options: object,
    ) -> QPixmap:
        self.calls.append({"base": base, "patch": patch, **options})
        return QPixmap(patch)


class _CompositingRenderer(_Renderer):
    def render_overlay(
        self,
        base: QPixmap,
        patch: QPixmap,
        **options: object,
    ) -> QPixmap:
        self.calls.append({"base": base, "patch": patch, **options})
        result = QPixmap(base)
        painter = QPainter(result)
        painter.drawPixmap(0, 0, patch)
        painter.end()
        return result


class _NativeAuthority:
    def __init__(self, active: bool = True) -> None:
        self.active = active
        self.calls: list[str] = []

    def has_native_motion(self, view_id: str) -> bool:
        self.calls.append(view_id)
        return self.active


def _routing_subject() -> tuple[object, _Renderer, QPixmap, QPixmap, QPixmap]:
    subject = object.__new__(CompanionFaceAssetMethods)
    base = _asset("mock_hit_front")
    native_half = _asset("mock_hit_front_half")
    mask = CompanionFaceAssetMethods._soft_rounded_mask(
        (QRect(180, 153, 53, 34), QRect(220, 153, 56, 34)),
        ((0, 255),),
        10,
    )
    renderer = _Renderer()
    renderer._outfit_overlay = _NativeAuthority()
    subject.state = "idle"
    subject.expression_pixmaps = {
        "mock_hit_front": base,
        "mock_hit_front_half": native_half,
    }
    subject.physics_expression_poses = {"mock_hit_front": "front"}
    subject.active_physics_pose = "front"
    subject.blink_masks = {"front": mask}
    subject.face_renderer = renderer
    subject._expression_eye_offset = lambda _expression: (0, 2)
    subject._pose_suffix = lambda _pose: "_front"
    subject._masked_region = CompanionFaceAssetMethods._masked_region
    subject._translated_pixmap = CompanionFaceAssetMethods._translated_pixmap
    return subject, renderer, base, native_half, mask


def test_native_half_contract_names_and_assets(qapp: QApplication) -> None:
    assert dict(EXPRESSION_HALF_BLINK_FRAMES) == HALF_BLINK_FRAMES
    assert set(EXPRESSION_HALF_BLINK_ASSETS) == set(HALF_BLINK_FRAMES.values())
    assert set(EXPRESSION_HALF_BLINK_ASSETS) <= set(EXPRESSION_IMAGE_ASSETS)
    for stem in EXPRESSION_HALF_BLINK_ASSETS:
        image = QImage(str(PROJECT_ROOT / "assets" / "expressions" / f"{stem}.png"))
        assert image.size().toTuple() == (1254, 1254)
        assert image.hasAlphaChannel()


def test_native_half_assets_remain_transient_patch_sources(qapp: QApplication) -> None:
    subject = object.__new__(CompanionVisualPhysicsMethods)
    subject.expression_pixmaps = {
        stem: QPixmap(1, 1) for stem in EXPRESSION_HALF_BLINK_ASSETS
    }
    pose_map = subject._physics_expression_pose_map()
    assert not set(EXPRESSION_HALF_BLINK_ASSETS) & set(pose_map)


@pytest.mark.parametrize(("expression", "source"), SAME_POSE_HALF_ALIASES.items())
def test_existing_speech_aliases_resolve_native_half_sources(
    qapp: QApplication,
    expression: str,
    source: str,
) -> None:
    assert EXPRESSION_HALF_BLINK_FRAME_SOURCES[expression] == source


def test_native_half_route_ignores_old_expression_offset_and_preserves_closed_guard(
    qapp: QApplication,
) -> None:
    subject, renderer, base, native_half, mask = _routing_subject()
    result = subject._blink_composite(base, "mock_hit_front", 0.5)
    expected = CompanionFaceAssetMethods._masked_region(native_half, mask)
    assert _pixels(result) == _pixels(expected)
    assert len(renderer.calls) == 1
    assert renderer.calls[0]["eye_state"] == "half"
    assert renderer.calls[0]["view_id"] == "front-mock-hit"

    closed = subject._blink_composite(base, "mock_hit_front", 1.0)
    assert _pixels(closed) == _pixels(base)
    assert len(renderer.calls) == 1


def test_native_half_route_falls_back_when_dedicated_source_is_missing(
    qapp: QApplication,
) -> None:
    subject, renderer, base, _native_half, _mask = _routing_subject()
    subject.expression_pixmaps.pop("mock_hit_front_half")
    result = subject._blink_composite(base, "mock_hit_front", 0.5)
    assert _pixels(result) == _pixels(base)
    assert renderer.calls == []


def test_native_half_route_requires_the_matching_native_authority(
    qapp: QApplication,
) -> None:
    subject, renderer, base, _native_half, _mask = _routing_subject()
    renderer._outfit_overlay.active = False

    result = subject._blink_composite(base, "mock_hit_front", 0.5)

    assert _pixels(result) == _pixels(base)
    assert renderer.calls == []
    assert renderer._outfit_overlay.calls == ["front-mock-hit"]


def test_missing_native_authority_keeps_the_legacy_blink_source(qapp: QApplication) -> None:
    subject = object.__new__(CompanionFaceAssetMethods)
    base = _asset("idle_front")
    legacy_blink = _asset("blink_front")
    mask = CompanionFaceAssetMethods._soft_rounded_mask(
        (QRect(180, 153, 53, 34), QRect(220, 153, 56, 34)),
        ((0, 255),),
        10,
    )
    renderer = _Renderer()
    renderer._outfit_overlay = _NativeAuthority(active=False)
    subject.state = "idle"
    subject.expression_pixmaps = {
        "idle_front": base,
        "idle_front_half": _asset("idle_front_half"),
        "blink_front": legacy_blink,
    }
    subject.physics_expression_poses = {"idle_front": "front"}
    subject.active_physics_pose = "front"
    subject.blink_masks = {"front": mask}
    subject.blush_blink_masks = {"front": mask}
    subject.face_renderer = renderer
    subject._expression_eye_offset = lambda _expression: (0, 0)
    subject._pose_suffix = lambda _pose: "_front"
    subject._masked_region = CompanionFaceAssetMethods._masked_region
    subject._translated_pixmap = CompanionFaceAssetMethods._translated_pixmap

    result = subject._blink_composite(base, "idle_front", 1.0)

    expected = CompanionFaceAssetMethods._masked_region(legacy_blink, mask)
    assert _pixels(result) == _pixels(expected)
    assert len(renderer.calls) == 1
    assert renderer.calls[0]["view_id"] == "front-crossed"


def test_same_pose_speech_frames_use_native_half_eye_patch_only(qapp: QApplication) -> None:
    subject = object.__new__(CompanionFaceAssetMethods)
    base = _asset("idle_front")
    native_half = _asset("idle_front_half")
    mask = CompanionFaceAssetMethods._soft_rounded_mask(
        (QRect(180, 153, 53, 34), QRect(220, 153, 56, 34)),
        ((0, 255),),
        10,
    )
    renderer = _CompositingRenderer()
    renderer._outfit_overlay = _NativeAuthority()
    subject.state = "speaking"
    subject.expression_pixmaps = {
        "mouth_mid_front": base,
        "idle_front_half": native_half,
    }
    subject.physics_expression_poses = {"mouth_mid_front": "front"}
    subject.active_physics_pose = "front"
    subject.blink_masks = {"front": mask}
    subject.face_renderer = renderer
    subject._expression_eye_offset = lambda _expression: (0, 2)
    subject._pose_suffix = lambda _pose: "_front"
    subject._masked_region = CompanionFaceAssetMethods._masked_region
    subject._translated_pixmap = CompanionFaceAssetMethods._translated_pixmap

    result = subject._blink_composite(base, "mouth_mid_front", 0.5)

    assert EXPRESSION_HALF_BLINK_FRAME_SOURCES["mouth_mid_front"] == "idle_front_half"
    assert len(renderer.calls) == 1
    assert renderer.calls[0]["base"] is base
    assert _pixels(result) != _pixels(base)
    patch = renderer.calls[0]["patch"]
    result_image = result.toImage().convertToFormat(QImage.Format_RGBA8888)
    base_image = base.toImage().convertToFormat(QImage.Format_RGBA8888)
    patch_image = patch.toImage().convertToFormat(QImage.Format_RGBA8888)
    for y in range(result_image.height()):
        for x in range(result_image.width()):
            if patch_image.pixelColor(x, y).alpha() == 0:
                assert result_image.pixel(x, y) == base_image.pixel(x, y)
