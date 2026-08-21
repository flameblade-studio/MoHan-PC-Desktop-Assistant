from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.personality_state import (
    TEMPERATURE_MAX,
    TEMPERATURE_MIN,
    PersonalityMirrorState,
)

RESERVED_TEMPERATURE_THRESHOLD = -0.1
PLAYFUL_TEMPERATURE_THRESHOLD = 0.1


def test_mirror_starts_balanced() -> None:
    state = PersonalityMirrorState()
    assert state.temperature == 0.0
    assert state.style == "balanced"


def test_serious_user_makes_reserved() -> None:
    state = PersonalityMirrorState()
    for _ in range(20):
        state.update(sentiment_polarity=-1.0, style_score=-1.0)
    assert state.temperature < RESERVED_TEMPERATURE_THRESHOLD
    assert state.style == "reserved"


def test_playful_user_makes_playful() -> None:
    state = PersonalityMirrorState()
    for _ in range(20):
        state.update(sentiment_polarity=1.0, style_score=1.0)
    assert state.temperature > PLAYFUL_TEMPERATURE_THRESHOLD
    assert state.style == "playful"


def test_temperature_stays_within_bounds() -> None:
    state = PersonalityMirrorState()
    for _ in range(100):
        state.update(sentiment_polarity=1.0, style_score=1.0)
    assert TEMPERATURE_MIN <= state.temperature <= TEMPERATURE_MAX


def test_mirror_eases_smoothly() -> None:
    state = PersonalityMirrorState()
    first = state.update(sentiment_polarity=1.0, style_score=1.0)
    assert first < TEMPERATURE_MAX, "mirror must ease in, not snap"


def run() -> None:
    test_mirror_starts_balanced()
    test_serious_user_makes_reserved()
    test_playful_user_makes_playful()
    test_temperature_stays_within_bounds()
    test_mirror_eases_smoothly()
    print("PERSONALITY_STATE_OK")


if __name__ == "__main__":
    run()
