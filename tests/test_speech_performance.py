from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from speech_performance import (
    SpeechEventKind,
    SpeechPerformancePhase,
    SpeechPerformanceTimeline,
)
lazy from speech_providers import (
    AZURE_HD_SPEECH_PROVIDER,
    AZURE_SPEECH_PROVIDER,
    OPENAI_REALTIME_PROVIDER,
    OPENAI_SPEECH_PROVIDER,
    SYSTEM_LOCAL_PROVIDER,
)


class VirtualClock:
    def __init__(self) -> None:
        self.value = 100.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


def assert_every_provider_uses_one_timeline() -> None:
    providers = (
        SYSTEM_LOCAL_PROVIDER,
        OPENAI_SPEECH_PROVIDER,
        OPENAI_REALTIME_PROVIDER,
        AZURE_SPEECH_PROVIDER,
        AZURE_HD_SPEECH_PROVIDER,
    )
    for provider in providers:
        clock = VirtualClock()
        timeline = SpeechPerformanceTimeline(clock)
        prepared, preparing = timeline.prepare(provider)
        assert prepared.provider_id == provider
        assert prepared.kind is SpeechEventKind.PREPARE
        assert preparing.phase is SpeechPerformancePhase.PREPARING
        assert preparing.allow_large_turn

        started, speaking = timeline.first_audio()
        assert started.kind is SpeechEventKind.FIRST_AUDIO
        assert speaking.phase is SpeechPerformancePhase.SPEAKING
        assert not speaking.allow_large_turn
        assert speaking.hold_current_pose

        clock.advance(0.75)
        cue, directive = timeline.viseme(0.8, "A")
        assert cue.kind is SpeechEventKind.VISEME
        assert cue.provider_id == provider
        assert cue.estimated
        assert directive.gesture_beat
        assert directive.body_energy > 0.3

        final, settling = timeline.final_audio()
        assert final.kind is SpeechEventKind.FINAL_AUDIO
        assert settling.phase is SpeechPerformancePhase.SETTLING
        assert not settling.allow_large_turn
        assert timeline.final_audio() is None

        closed, idle = timeline.mouth_closed()
        assert closed.kind is SpeechEventKind.MOUTH_CLOSED
        assert idle.phase is SpeechPerformancePhase.IDLE
        assert idle.allow_large_turn
        assert timeline.snapshot.mouth_closed
        assert timeline.mouth_closed() is None


def assert_rich_boundaries_disable_estimation() -> None:
    clock = VirtualClock()
    timeline = SpeechPerformanceTimeline(clock)
    timeline.prepare(AZURE_SPEECH_PROVIDER)
    timeline.first_audio()
    boundary, directive = timeline.segment_boundary(emphasis=0.9)
    assert boundary.kind is SpeechEventKind.SEGMENT_BOUNDARY
    assert directive.gesture_beat
    clock.advance(1.5)
    cue, later = timeline.viseme(0.95, "O")
    assert not cue.estimated
    assert not later.gesture_beat


def assert_gesture_beats_are_rate_limited() -> None:
    clock = VirtualClock()
    timeline = SpeechPerformanceTimeline(clock)
    timeline.prepare(OPENAI_REALTIME_PROVIDER)
    timeline.first_audio()
    first, first_directive = timeline.segment_boundary(emphasis=0.9)
    assert first_directive.gesture_beat
    clock.advance(0.1)
    second, second_directive = timeline.segment_boundary(emphasis=1.0)
    assert second.segment_index == first.segment_index + 1
    assert not second_directive.gesture_beat
    clock.advance(0.5)
    _, third_directive = timeline.segment_boundary(emphasis=0.8)
    assert third_directive.gesture_beat


def assert_stale_events_cannot_move_the_new_speech() -> None:
    clock = VirtualClock()
    timeline = SpeechPerformanceTimeline(clock)
    old, _ = timeline.prepare(SYSTEM_LOCAL_PROVIDER)
    new, _ = timeline.prepare(OPENAI_SPEECH_PROVIDER)
    assert new.generation == old.generation + 1
    assert timeline.first_audio(old.generation) is None
    assert timeline.viseme(1.0, "A", generation=old.generation) is None
    assert timeline.final_audio(generation=old.generation) is None
    assert timeline.snapshot.provider_id == OPENAI_SPEECH_PROVIDER
    assert timeline.snapshot.phase is SpeechPerformancePhase.PREPARING


def assert_interrupt_and_failure_fail_closed() -> None:
    clock = VirtualClock()
    timeline = SpeechPerformanceTimeline(clock)
    timeline.prepare(AZURE_HD_SPEECH_PROVIDER)
    timeline.first_audio()
    event, directive = timeline.interrupt(failed=True)
    assert event.kind is SpeechEventKind.FAILURE
    assert directive.phase is SpeechPerformancePhase.INTERRUPTED
    assert directive.hold_current_pose
    assert not directive.allow_large_turn
    assert timeline.snapshot.interrupted
    assert timeline.interrupt(failed=True) is None
    closed, idle = timeline.mouth_closed()
    assert closed.kind is SpeechEventKind.MOUTH_CLOSED
    assert idle.phase is SpeechPerformancePhase.IDLE
    assert timeline.snapshot.mouth_closed


def assert_timeline_keeps_no_text_or_secret_fields() -> None:
    clock = VirtualClock()
    timeline = SpeechPerformanceTimeline(clock)
    timeline.prepare(OPENAI_SPEECH_PROVIDER)
    fields = set(timeline.snapshot.__dataclass_fields__)
    forbidden = {"text", "transcript", "api_key", "secret", "audio"}
    assert fields.isdisjoint(forbidden)


def run() -> None:
    assert_every_provider_uses_one_timeline()
    assert_rich_boundaries_disable_estimation()
    assert_gesture_beats_are_rate_limited()
    assert_stale_events_cannot_move_the_new_speech()
    assert_interrupt_and_failure_fail_closed()
    assert_timeline_keeps_no_text_or_secret_fields()
    print("SPEECH_PERFORMANCE_OK")


def test_speech_performance_contract() -> None:
    run()


if __name__ == "__main__":
    run()
