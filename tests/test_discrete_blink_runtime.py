from __future__ import annotations

lazy from types import SimpleNamespace

lazy from PySide6.QtCore import QTimer

lazy from domain.face_microtiming import (
    BLINK_CLOSE_AT_MS,
    BLINK_CLOSED_TIMES_MS,
    BLINK_CLOSED_HOLD_MS,
    BLINK_HALF_CLOSE_TIMES_MS,
    BLINK_HALF_OPEN_TIMES_MS,
    BLINK_REOPEN_AT_MS,
    BLINK_REST_AT_MS,
    FACE_TICK_MS,
)
lazy from presentation.companion_face_animation import CompanionFaceAnimationMixin


def test_full_body_blink_uses_20ms_discrete_schedule(monkeypatch) -> None:
    scheduled: list[tuple[int, object]] = []
    observed: list[float] = []
    dummy = SimpleNamespace(blink_generation=4)

    def set_blink(generation: int, value: float) -> None:
        assert generation == dummy.blink_generation
        observed.append(value)

    dummy._set_full_body_blink = set_blink
    monkeypatch.setattr(
        QTimer,
        "singleShot",
        lambda delay, callback: scheduled.append((delay, callback)),
    )

    CompanionFaceAnimationMixin._full_body_blink(dummy)

    assert observed == [0.5]
    assert [delay for delay, _ in scheduled] == [
        *BLINK_HALF_CLOSE_TIMES_MS[1:],
        *BLINK_CLOSED_TIMES_MS,
        *BLINK_HALF_OPEN_TIMES_MS,
        BLINK_REST_AT_MS,
    ]
    assert all(delay % FACE_TICK_MS == 0 for delay, _ in scheduled)
    assert BLINK_REOPEN_AT_MS - BLINK_CLOSE_AT_MS == BLINK_CLOSED_HOLD_MS

    for _, callback in scheduled:
        callback()
    assert observed == [
        0.5,
        0.5,
        1.0,
        1.0,
        1.0,
        1.0,
        0.5,
        0.5,
        0.5,
        0.0,
    ]


def test_stale_blink_generation_cannot_overwrite_rest_state() -> None:
    refreshed: list[float] = []
    dummy = SimpleNamespace(blink_generation=9, blink_opacity=0.0)
    dummy._refresh_full_body = lambda: refreshed.append(dummy.blink_opacity)

    CompanionFaceAnimationMixin._set_full_body_blink(dummy, 8, 1.0)
    assert refreshed == []
    assert dummy.blink_opacity == 0.0

    CompanionFaceAnimationMixin._set_full_body_blink(dummy, 9, 0.0)
    assert refreshed == [0.0]
