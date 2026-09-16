"""Compatibility checks for the atomic animated-appearance adapter."""
from __future__ import annotations

lazy import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

lazy import pytest
lazy from PySide6.QtGui import QColor, QPainter, QPixmap
lazy from PySide6.QtWidgets import QApplication
lazy from infrastructure.animated_appearance import AnimatedAppearance

VIEW = "yaw+000-pitch+00"


@pytest.fixture(scope="module", autouse=True)
def qt_app():
    return QApplication.instance() or QApplication([])


def _frame() -> QPixmap:
    frame = QPixmap(4, 4)
    frame.fill(QColor("blue"))
    return frame


def _paint_motion(frame: QPixmap) -> None:
    painter = QPainter(frame)
    painter.fillRect(0, 0, 1, 1, QColor("green"))
    painter.end()


def test_strict_legacy_apply_receives_no_blink_keywords() -> None:
    calls: list[str] = []

    class StrictLegacy:
        def apply(self, frame: QPixmap, view_id: str) -> QPixmap:
            calls.append(view_id)
            return frame

    source = _frame()
    result = AnimatedAppearance(StrictLegacy()).compose(
        source,
        VIEW,
        _paint_motion,
        suppress_makeup_slots=frozenset({"eyes"}),
        eye_state="closed",
    )

    assert result.toImage().pixelColor(0, 0) == QColor("green")
    assert calls == [VIEW]


def test_apply_with_blink_keywords_receives_both_options() -> None:
    calls: list[tuple[frozenset[str], str]] = []

    class BlinkAware:
        def apply(
            self,
            frame: QPixmap,
            view_id: str,
            *,
            suppress_makeup_slots=frozenset(),
            eye_state="rest",
        ) -> QPixmap:
            del view_id
            calls.append((frozenset(suppress_makeup_slots), eye_state))
            return frame

    AnimatedAppearance(BlinkAware()).compose(
        _frame(),
        VIEW,
        _paint_motion,
        suppress_makeup_slots=frozenset({"eyes"}),
        eye_state="closed",
    )

    assert calls == [(frozenset({"eyes"}), "closed")]


@pytest.mark.parametrize(
    ("adapter_type", "expected"),
    [
        ("eye-state-only", {"eye_state": "half"}),
        ("suppression-only", {"suppress_makeup_slots": frozenset({"eyes"})}),
    ],
)
def test_partial_blink_keyword_support_is_respected(adapter_type: str, expected: dict[str, object]) -> None:
    calls: list[dict[str, object]] = []

    if adapter_type == "eye-state-only":
        class Partial:
            def apply(self, frame: QPixmap, view_id: str, *, eye_state="rest") -> QPixmap:
                del view_id
                calls.append({"eye_state": eye_state})
                return frame
    else:
        class Partial:
            def apply(
                self,
                frame: QPixmap,
                view_id: str,
                *,
                suppress_makeup_slots=frozenset(),
            ) -> QPixmap:
                del view_id
                calls.append({"suppress_makeup_slots": frozenset(suppress_makeup_slots)})
                return frame

    AnimatedAppearance(Partial()).compose(
        _frame(),
        VIEW,
        _paint_motion,
        suppress_makeup_slots=frozenset({"eyes"}),
        eye_state="half",
    )

    assert calls == [expected]


def test_adapter_internal_type_error_is_not_retried_or_swallowed() -> None:
    calls = 0

    class Broken:
        def apply(
            self,
            frame: QPixmap,
            view_id: str,
            *,
            suppress_makeup_slots=frozenset(),
            eye_state="rest",
        ) -> QPixmap:
            nonlocal calls
            del frame, view_id, suppress_makeup_slots, eye_state
            calls += 1
            raise TypeError("adapter-internal-typeerror")

    with pytest.raises(TypeError, match="adapter-internal-typeerror"):
        AnimatedAppearance(Broken()).compose(
            _frame(),
            VIEW,
            _paint_motion,
            suppress_makeup_slots=frozenset({"eyes"}),
            eye_state="closed",
        )

    assert calls == 1


def test_atomic_adapter_wins_over_split_and_combined_methods() -> None:
    calls: list[str] = []

    class AllContracts:
        def apply_animated(self, frame, view_id, paint_motion, **options):
            del view_id, paint_motion, options
            calls.append("atomic")
            return frame

        def apply_appearance(self, frame, view_id):
            del view_id
            calls.append("appearance")
            return frame

        def apply_makeup(self, frame, view_id, **options):
            del view_id, options
            calls.append("makeup")
            return frame

        def apply(self, frame, view_id, **options):
            del view_id, options
            calls.append("combined")
            return frame

    result = AnimatedAppearance(AllContracts()).compose(
        _frame(),
        VIEW,
        _paint_motion,
        suppress_makeup_slots=frozenset(),
        eye_state="rest",
    )

    assert not result.isNull()
    assert calls == ["atomic"]


def test_none_overlay_is_a_noop_while_motion_still_paints() -> None:
    source = _frame()
    result = AnimatedAppearance(None).compose(
        source,
        VIEW,
        _paint_motion,
        suppress_makeup_slots=frozenset(),
        eye_state="rest",
    )

    assert result is not source
    assert result.toImage().pixelColor(0, 0) == QColor("green")
    assert source.toImage().pixelColor(0, 0) == QColor("blue")


def test_legacy_atomic_adapter_can_restore_core_pixels_after_makeup() -> None:
    class LegacyAtomic:
        def apply_animated(self, frame, view_id, paint_motion, *, suppress_makeup_slots, eye_state):
            del view_id, suppress_makeup_slots, eye_state
            paint_motion(frame)
            frame.fill(QColor("red"))
            return frame

    source = _frame()
    result = AnimatedAppearance(LegacyAtomic()).compose(
        source, VIEW, _paint_motion,
        suppress_makeup_slots=frozenset(), eye_state="rest",
        paint_after_makeup=_paint_motion,
    )
    assert result.toImage().pixelColor(0, 0) == QColor("green")
    assert result.toImage().pixelColor(1, 1) == QColor("red")
    assert source.toImage().pixelColor(0, 0) == QColor("blue")
    assert source.toImage().pixelColor(1, 1) == QColor("blue")


def test_legacy_atomic_kwargs_do_not_claim_the_after_makeup_phase() -> None:
    class LegacyAtomic:
        def apply_animated(self, frame, view_id, paint_motion, **options):
            del view_id, options
            paint_motion(frame)
            frame.fill(QColor("red"))
            return frame

    source = _frame()
    adapter = AnimatedAppearance(LegacyAtomic())
    result = adapter.compose(
        source, VIEW, _paint_motion,
        suppress_makeup_slots=frozenset(), eye_state="rest",
        paint_after_makeup=_paint_motion,
    )
    assert result.toImage().pixelColor(0, 0) == QColor("green")
    assert result.toImage().pixelColor(1, 1) == QColor("red")
    assert source.toImage().pixelColor(0, 0) == QColor("blue")

    def fail_after_makeup(frame):
        del frame
        raise ValueError("oral protection failed")

    with pytest.raises(ValueError, match="oral protection failed"):
        adapter.compose(
            source, VIEW, _paint_motion,
            suppress_makeup_slots=frozenset(), eye_state="rest",
            paint_after_makeup=fail_after_makeup,
        )
