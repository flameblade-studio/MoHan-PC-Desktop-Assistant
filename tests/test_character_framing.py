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
    framing = CharacterFramingDirector(clock)
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
    framing = CharacterFramingDirector(clock)
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
    framing = CharacterFramingDirector(clock)
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
    framing = CharacterFramingDirector(clock)
    gesture = NormalizedRect(0.02, 0.20, 0.98, 0.72)
    result = framing.decide(context(gesture_bounds=gesture))
    assert result.crop.contains(gesture)
    assert result.mode in {FramingMode.THREE_QUARTER, FramingMode.FULL_BODY}


def assert_small_viewport_preserves_readable_face() -> None:
    framing = CharacterFramingDirector(Clock())
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
    framing = CharacterFramingDirector(Clock())
    result = framing.decide(context(owner_arrived=True, adaptive_enabled=False))
    assert result.mode is FramingMode.HALF
    assert result.held


def run() -> None:
    assert_human_like_context_shots()
    assert_speech_holds_and_settles_before_reframing()
    assert_speech_is_fixed_at_half_body()
    assert_large_hands_are_never_cropped()
    assert_small_viewport_preserves_readable_face()
    assert_disabled_mode_is_stable()
    print("CHARACTER_FRAMING_OK")


if __name__ == "__main__":
    run()
