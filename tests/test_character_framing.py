from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.character_framing import (
    CharacterFramingDirector,
    FramingContext,
    FramingMode,
    FramingReason,
    NormalizedRect,
)


class Clock:
    value = 10.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float = 2.0) -> None:
        self.value += seconds


def context(**changes: object) -> FramingContext:
    values: dict[str, object] = {
        "available_width_px": 1920,
        "available_height_px": 1080,
    }
    values.update(changes)
    return FramingContext(**values)


def assert_human_like_context_shots() -> None:
    clock = Clock()
    framing = CharacterFramingDirector(clock, style="lively")
    assert framing.decide(context()).mode is FramingMode.HALF
    clock.advance()
    assert framing.decide(context(owner_arrived=True)).mode is FramingMode.THREE_QUARTER
    clock.advance()
    assert framing.decide(context(owner_arrived=True)).mode is FramingMode.FULL_BODY
    clock.advance()
    away = framing.decide(context(turning_away=True))
    assert away.mode is FramingMode.FULL_BODY
    assert away.reason is FramingReason.TURNING_AWAY
    clock.advance()
    assert framing.decide(context()).mode is FramingMode.THREE_QUARTER
    clock.advance()
    assert framing.decide(context()).mode is FramingMode.HALF
    clock.advance()
    assert framing.decide(context(emotion_intensity=0.9)).mode is FramingMode.CLOSE


def assert_speech_holds_and_settles_before_reframing() -> None:
    clock = Clock()
    framing = CharacterFramingDirector(clock, style="lively")
    held = framing.decide(
        context(owner_arrived=True, speech_active=True, mouth_closed=False)
    )
    assert held.mode is FramingMode.HALF
    assert held.reason is FramingReason.SPEECH_HOLD
    clock.advance()
    settling = framing.decide(
        context(owner_arrived=True, speech_active=False, mouth_closed=True)
    )
    assert settling.mode is FramingMode.THREE_QUARTER
    assert not settling.held


def assert_speech_is_fixed_at_half_body() -> None:
    """Speech must stay at the half-body shot, never full-body then half-body.

    A lingering FULL_BODY from an idle full-body view must not be held across
    the start of speech.  The director should settle on HALF immediately so the
    companion does not speak a few words in full-body before snapping back.
    """
    clock = Clock()
    framing = CharacterFramingDirector(clock, style="lively")
    # Drive the director into FULL_BODY first (owner arrival).
    framing.decide(context(owner_arrived=True))
    clock.advance()
    framing.decide(context(owner_arrived=True))
    clock.advance()
    assert framing.mode is FramingMode.FULL_BODY
    # Speech begins: the director must not hold FULL_BODY.
    speaking = framing.decide(
        context(speech_active=True, mouth_closed=False)
    )
    assert speaking.mode is FramingMode.HALF, (
        "speech must settle on HALF, not hold a lingering FULL_BODY"
    )
    # High emotion during speech must still stay HALF, not CLOSE.
    clock.advance()
    emotional = framing.decide(
        context(speech_active=True, mouth_closed=False, emotion_intensity=0.95)
    )
    assert emotional.mode is FramingMode.HALF, (
        "speech must stay HALF even under high emotion"
    )


def assert_large_hands_are_never_cropped() -> None:
    clock = Clock()
    framing = CharacterFramingDirector(clock, style="lively")
    gesture = NormalizedRect(0.02, 0.20, 0.98, 0.72)
    result = framing.decide(context(gesture_bounds=gesture))
    assert result.crop.contains(gesture)
    assert result.mode in {FramingMode.THREE_QUARTER, FramingMode.FULL_BODY}


def assert_small_viewport_preserves_readable_face() -> None:
    framing = CharacterFramingDirector(Clock(), style="lively")
    result = framing.decide(
        context(
            available_width_px=400,
            available_height_px=520,
            outfit_preview=True,
        )
    )
    assert result.mode is FramingMode.HALF
    assert result.reason is FramingReason.SMALL_VIEWPORT


def assert_disabled_mode_is_stable() -> None:
    framing = CharacterFramingDirector(Clock(), style="lively")
    result = framing.decide(context(owner_arrived=True, adaptive_enabled=False))
    assert result.mode is FramingMode.HALF
    assert result.held


def assert_steady_style_holds_half_body_between_turns() -> None:
    # Owner ruling 2026-08-29: in the default "steady" style the whole
    # conversation session stays at the half-body shot — the frame must not
    # bounce back to full body the moment the mouth closes between turns.
    clock = Clock()
    framing = CharacterFramingDirector(clock, style="steady")
    framing.decide(
        context(owner_arrived=True, speech_active=True, mouth_closed=False)
    )
    clock.advance(10.0)
    between_turns = framing.decide(
        context(owner_arrived=True, speech_active=False, mouth_closed=True)
    )
    assert between_turns.mode is FramingMode.HALF
    assert between_turns.reason is FramingReason.SPEECH_HOLD
    # After the conversation cooldown the deferred full-body request resumes
    # (stepping through THREE_QUARTER as usual).
    clock.advance(120.0)
    resumed = framing.decide(
        context(owner_arrived=True, speech_active=False, mouth_closed=True)
    )
    assert resumed.mode is FramingMode.THREE_QUARTER


def assert_half_only_style_never_leaves_half_body() -> None:
    clock = Clock()
    framing = CharacterFramingDirector(clock, style="half-only")
    for changes in (
        {"owner_arrived": True},
        {"turning_away": True},
        {"emotion_intensity": 0.9},
    ):
        clock.advance(20.0)
        assert framing.decide(context(**changes)).mode is FramingMode.HALF
    # The outfit preview is the single functional exception: the garment can
    # only be judged on the full photograph.
    clock.advance(20.0)
    framing.decide(context(outfit_preview=True))
    clock.advance(20.0)
    framing.decide(context(outfit_preview=True))
    clock.advance(20.0)
    assert framing.decide(context(outfit_preview=True)).mode is FramingMode.FULL_BODY


def assert_unknown_style_falls_back_to_steady() -> None:
    framing = CharacterFramingDirector(Clock(), style="chaotic")
    assert framing.style == "steady"


def run() -> None:
    assert_human_like_context_shots()
    assert_speech_holds_and_settles_before_reframing()
    assert_speech_is_fixed_at_half_body()
    assert_large_hands_are_never_cropped()
    assert_small_viewport_preserves_readable_face()
    assert_disabled_mode_is_stable()
    assert_steady_style_holds_half_body_between_turns()
    assert_half_only_style_never_leaves_half_body()
    assert_unknown_style_falls_back_to_steady()
    print("CHARACTER_FRAMING_OK")


if __name__ == "__main__":
    run()
