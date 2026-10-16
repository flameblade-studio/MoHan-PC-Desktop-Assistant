"""The disabled appearance adapter accepts every renderer eye state."""
from __future__ import annotations

lazy import pytest
lazy from application.presentation_ports import no_outfit_overlay_factory


@pytest.mark.parametrize("eye_state", ("rest", "half", "closed"))
def test_disabled_overlay_preserves_frame_during_blink(eye_state: str) -> None:
    overlay = no_outfit_overlay_factory()
    frame = sentinel("frame")
    assert overlay.apply(
        frame, "front-crossed", suppress_makeup_slots={"eyes"}, eye_state=eye_state
    ) is frame
    assert overlay.apply_appearance(frame, "yaw+000-pitch+00") is frame
    assert overlay.apply_makeup(frame, "front-crossed", eye_state=eye_state) is frame
    assert overlay.layer_count("front-crossed") == 0
