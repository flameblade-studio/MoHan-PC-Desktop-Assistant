from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.emotional_resonance import (
    BLINK_INTERVAL_REST,
    BREATH_PERIOD_AGITATED,
    BREATH_PERIOD_REST,
    EmotionalResonanceState,
)


def test_resonance_starts_at_rest() -> None:
    state = EmotionalResonanceState()
    assert state.resonance == 0.0
    assert state.breath_period() == BREATH_PERIOD_REST
    assert state.blink_interval() == BLINK_INTERVAL_REST


def test_resonance_rises_with_brow_tension_and_typing() -> None:
    state = EmotionalResonanceState()
    # A furrowed brow plus fast typing drives resonance toward 1.0.
    for step in range(20):
        state.update(brow_tension=0.9, typing_rate_kps=8.0, now=float(step))
    assert state.resonance > 0.5
    assert state.breath_period() < BREATH_PERIOD_REST
    assert state.blink_interval() < BLINK_INTERVAL_REST


def test_resonance_eases_smoothly_without_snapping() -> None:
    state = EmotionalResonanceState()
    # A single agitated sample must not snap the resonance to full.
    first = state.update(brow_tension=0.9, typing_rate_kps=8.0, now=0.0)
    assert first < 0.5, "resonance must ease in, not snap"
    # Over many samples it approaches but never exceeds 1.0.
    for step in range(100):
        level = state.update(brow_tension=0.9, typing_rate_kps=8.0, now=float(step))
    assert 0.0 <= level <= 1.0


def test_resonance_decays_back_to_rest() -> None:
    state = EmotionalResonanceState()
    for step in range(20):
        state.update(brow_tension=0.9, typing_rate_kps=8.0, now=float(step))
    assert state.resonance > 0.5
    # Calm inputs ease the resonance back down.
    for step in range(200):
        state.update(brow_tension=0.0, typing_rate_kps=0.0, now=20.0 + float(step))
    assert state.resonance < 0.1
    assert state.breath_period() > BREATH_PERIOD_AGITATED


def test_breath_period_stays_within_bounds() -> None:
    state = EmotionalResonanceState()
    for step in range(200):
        state.update(brow_tension=1.0, typing_rate_kps=100.0, now=float(step))
    period = state.breath_period()
    assert BREATH_PERIOD_AGITATED <= period <= BREATH_PERIOD_REST


def run() -> None:
    test_resonance_starts_at_rest()
    test_resonance_rises_with_brow_tension_and_typing()
    test_resonance_eases_smoothly_without_snapping()
    test_resonance_decays_back_to_rest()
    test_breath_period_stays_within_bounds()
    print("EMOTIONAL_RESONANCE_OK")


if __name__ == "__main__":
    run()
