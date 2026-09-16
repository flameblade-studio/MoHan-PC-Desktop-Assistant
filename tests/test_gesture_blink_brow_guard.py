"""Regression for neutral blink donors overwriting expressive native brows."""
lazy from pathlib import Path

lazy import numpy as np
lazy import pytest
lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QPainter, QPixmap
lazy from PySide6.QtWidgets import QApplication

lazy from presentation.companion_blink_brow_guard import _cached_guard, _rgba, preserve_gesture_brows

ROOT = Path(__file__).resolve().parents[1]
NATIVE_SIZE = 1254
OPAQUE_ALPHA = 255
EYE_TOP = 445
BROW_BOTTOM = 434
BROW_TOP = 370
BROW_LEFT = 490
BROW_RIGHT = 725


@pytest.mark.parametrize("expression", ["eureka_front", "mock_hit_front", "mock_scold"])
def test_native_brow_guard_retains_eye_patch_and_reduces_brow_overwrite(expression):
    app = QApplication.instance() or QApplication([])
    assert app is not None
    base = QPixmap(str(ROOT / "assets/expressions" / f"{expression}.png"))
    donor = QPixmap(str(ROOT / "assets/expressions/blink_front.png"))
    mask = QPixmap(NATIVE_SIZE, NATIVE_SIZE)
    mask.fill(Qt.white)
    guarded = _rgba(preserve_gesture_brows(base, donor, mask, expression=expression))
    assert np.any(guarded[BROW_TOP:BROW_BOTTOM, BROW_LEFT:BROW_RIGHT, 3] == 0)
    assert np.all(guarded[EYE_TOP:, :, 3] == OPAQUE_ALPHA)
    # No pigment or geometry is added: only the input alpha can be reduced.
    assert np.all(guarded[:, :, 3] <= _rgba(mask)[:, :, 3])


def test_mismatched_brow_guard_canvas_rejected():
    app = QApplication.instance() or QApplication([])
    assert app is not None
    base = QPixmap(20, 20)
    with pytest.raises(ValueError, match="matching native"):
        preserve_gesture_brows(base, QPixmap(21, 20), base)



def test_mouth_changes_reuse_bounded_brow_guard_cache():
    app = QApplication.instance() or QApplication([])
    assert app is not None
    base = QPixmap(str(ROOT / "assets/expressions/eureka_front.png"))
    donor = QPixmap(str(ROOT / "assets/expressions/blink_front.png"))
    mask = QPixmap(NATIVE_SIZE, NATIVE_SIZE)
    mask.fill(Qt.white)
    _cached_guard.cache_clear()
    preserve_gesture_brows(base, donor, mask, expression="eureka_front")
    changed = base.copy()
    painter = QPainter(changed)
    painter.fillRect(550, 550, 30, 20, Qt.red)
    painter.end()
    preserve_gesture_brows(changed, donor, mask, expression="eureka_front")
    cache = _cached_guard.cache_info()
    assert cache.misses == 1
    assert cache.hits == 1
    assert cache.currsize == 1
    assert cache.maxsize is not None

