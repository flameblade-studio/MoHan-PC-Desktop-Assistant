"""Registered CLOSED sources must preserve the expression's native pose."""
from __future__ import annotations

lazy import pytest
lazy from PySide6.QtGui import QImage
lazy from PySide6.QtWidgets import QApplication

lazy from domain.companion_animation_contract import (
    EXPRESSION_IMAGE_ASSETS,
    EXPRESSION_NATIVE_CLOSED_BLINK_ASSETS,
    EXPRESSION_NATIVE_CLOSED_BLINK_FRAME_SOURCES,
)
lazy from tests.test_native_half_blink_routing import (
    PROJECT_ROOT, _asset, _pixels, _routing_subject,
)


@pytest.fixture(scope='module')
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_registered_closed_sources_are_loadable(qapp: object) -> None:
    assert set(EXPRESSION_NATIVE_CLOSED_BLINK_ASSETS) <= set(EXPRESSION_IMAGE_ASSETS)
    for stem in EXPRESSION_NATIVE_CLOSED_BLINK_ASSETS:
        image = QImage(str(PROJECT_ROOT / 'assets' / 'expressions' / f'{stem}.png'))
        assert not image.isNull()
        assert image.hasAlphaChannel()


@pytest.mark.parametrize('expression', ('mock_hit_front', 'mock_hit_front_speech_mid'))
def test_registered_closed_route_uses_same_pose_endpoint(qapp: object, expression: str) -> None:
    subject, renderer, base, _half, mask = _routing_subject()
    endpoint = _asset('mock_hit_front_closed')
    subject.expression_pixmaps['mock_hit_front_closed'] = endpoint
    subject.physics_expression_poses[expression] = 'front'

    result = subject._blink_composite(base, expression, 1.0)

    assert EXPRESSION_NATIVE_CLOSED_BLINK_FRAME_SOURCES[expression] == 'mock_hit_front_closed'
    assert len(renderer.calls) == 1
    assert renderer.calls[0]['base'] is base
    assert renderer.calls[0]['eye_state'] == 'closed'
    assert _pixels(result) == _pixels(subject._masked_region(endpoint, mask))
