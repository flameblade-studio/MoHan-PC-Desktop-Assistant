"""Fail closed at product presentation boundaries for declared body packs."""
from __future__ import annotations

lazy import os
lazy from types import SimpleNamespace
lazy from unittest.mock import Mock
lazy import pytest
lazy from PySide6.QtGui import QPixmap
lazy from PySide6.QtWidgets import QApplication, QLabel
lazy from application.character_default_look import complete_fullbody_path, complete_halfbody_path
lazy from domain.body_pack import BodyPackMismatchError
lazy from infrastructure.character_fullbody_factory import create_character_fullbody_renderer
lazy from presentation.companion_core import CompanionCoreMixin
lazy from presentation.companion_blink_composite import CompanionBlinkCompositeMethods
lazy from presentation.companion_face_animation import CompanionFaceAnimationMixin
lazy from presentation.dashboard_wardrobe_preview import (
    DashboardWardrobePreviewMixin, STATE_COMPOSITED, STATE_ERROR,
)
lazy from application.appearance_ports import no_outfit_overlay_factory


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _source():
    return SimpleNamespace(
        assets=SimpleNamespace(resolve_path=Mock(side_effect=AssertionError("Legacy assets accessed"))),
        appearance=SimpleNamespace(resolved_body_pack=object()),
    )


@pytest.mark.parametrize("selector", (complete_fullbody_path, complete_halfbody_path))
def test_legacy_frame_selectors_reject_declared_body_before_path_access(selector):
    with pytest.raises(BodyPackMismatchError, match="body_pack_renderer_required"):
        selector(_source(), {})


def test_legacy_fullbody_factory_rejects_declared_body_before_asset_access():
    forbidden = Mock(side_effect=AssertionError("Legacy factory accessed"))
    with pytest.raises(BodyPackMismatchError, match="body_pack_renderer_required"):
        create_character_fullbody_renderer(
            _source(), {}, None, None, renderer_factory=forbidden,
            manifest_loader=forbidden, placement_loader=forbidden,
        )
    forbidden.assert_not_called()


class _Preview(DashboardWardrobePreviewMixin):
    def __init__(self, renderer, *, declared=True):
        self.presentation_ports = SimpleNamespace(body_pack_required=declared)
        self._wardrobe_full_body_renderer = renderer
        self._wardrobe_outfit_overlay = no_outfit_overlay_factory()
        self.wardrobe_service = SimpleNamespace(appearance_active=lambda: True)
        self._wardrobe_base_pixmap = Mock(side_effect=AssertionError("Shared base accessed"))


@pytest.mark.parametrize("error", (
    BodyPackMismatchError("file_hash_mismatch", "Changed body frame"),
    ValueError("Decode failed"),
))
def test_body_preview_failure_is_explicit_and_never_loads_shared_base(qapp, error):
    preview = _Preview(SimpleNamespace(render_view=Mock(side_effect=error)))
    frame, state = preview._composited_wardrobe_view("back")
    assert frame.isNull()
    assert state == STATE_ERROR
    assert preview._wardrobe_body_pack_error in {"file_hash_mismatch", "body_pack_render_failed"}
    preview._wardrobe_base_pixmap.assert_not_called()


def test_body_preview_with_missing_renderer_never_loads_shared_base(qapp):
    preview = _Preview(None)
    assert preview._composited_wardrobe_view("back")[1] == STATE_ERROR
    preview._wardrobe_base_pixmap.assert_not_called()


def test_body_preview_success_accepts_character_layers_with_empty_outfit_overlay(qapp):
    pixmap = QPixmap(4, 4)
    preview = _Preview(SimpleNamespace(render_view=lambda *args: pixmap))
    frame, state = preview._composited_wardrobe_view("back")
    assert not frame.isNull()
    assert state == STATE_COMPOSITED
    preview._wardrobe_base_pixmap.assert_not_called()


def test_body_preview_base_loader_returns_empty_before_resource_resolution(qapp):
    preview = _Preview(None)
    assert DashboardWardrobePreviewMixin._wardrobe_base_pixmap(preview, "back").isNull()


def test_desktop_adaptive_pose_atlas_rejects_declared_body_before_factory():
    companion = SimpleNamespace(presentation_ports=SimpleNamespace(body_pack_required=True))
    companion._stage_adaptive_character_frame = Mock()
    factory = Mock(side_effect=AssertionError("Adaptive legacy factory accessed"))
    CompanionCoreMixin._initialize_adaptive_character_composition(companion, factory, True)
    assert not companion._adaptive_character_enabled
    assert companion._adaptive_character_startup_error is not None
    assert companion._adaptive_character_composition is None
    factory.assert_not_called()


def test_body_wink_is_rejected_before_loading_legacy_patch(qapp):
    renderer = SimpleNamespace(supports_wink=False, render_overlay=Mock(
        side_effect=BodyPackMismatchError("unsupported_wink", "Body pack has no wink endpoint"),
    ))
    companion = SimpleNamespace(face_renderer=renderer)
    with pytest.raises(BodyPackMismatchError, match="unsupported_wink"):
        CompanionBlinkCompositeMethods._wink_composite(companion, QPixmap(), "neutral")
    assert renderer.render_overlay.call_args.kwargs["eye_state"] == "wink"


def test_body_wink_request_stops_before_scheduling_any_animation():
    companion = SimpleNamespace(face_renderer=SimpleNamespace(supports_wink=False))
    assert CompanionFaceAnimationMixin._wink_once(companion) is False


def test_body_preview_error_state_exposes_diagnostic_code(qapp):
    preview = _Preview(None)
    preview._t = lambda key, fallback: fallback
    preview.wardrobe_preview_state_label = QLabel()
    preview._wardrobe_body_pack_error = "file_hash_mismatch"
    preview._set_wardrobe_preview_state(STATE_ERROR)
    assert preview._wardrobe_preview_state == STATE_ERROR
    assert not preview.wardrobe_preview_state_label.isHidden()
    assert "file_hash_mismatch" in preview.wardrobe_preview_state_label.text()
