from __future__ import annotations

lazy import sys
lazy from dataclasses import replace
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from adaptive_character_runtime import (
    AdaptiveCharacterDisposition,
    AdaptiveCharacterRequest,
    AdaptiveCharacterRuntime,
)
lazy from behavior_director import BreathStyle, GazeTarget, TransitionStyle
lazy from body_pose_renderer import BodyPoseFrame
lazy from character_framing import FRAMING_RECTS, FramingMode
lazy from character_framing_app_bridge import (
    AppFramingState,
    AtomicFramingCommand,
    FramingBridgeDisposition,
    FramingBridgeResult,
)
lazy from framing_context_policy import EmotionValence, FocusState, FramingPolicyContext
lazy from framing_orchestrator import FramingAuditEntry
lazy from framing_preferences import FramingPreferences
lazy from full_body_performance_bridge import (
    FullBodyBridgeDisposition,
    FullBodyBridgeResult,
)
lazy from performance_coordinator import PerformanceFrame
lazy from performance_runtime import AtomicPerformanceFrame
lazy from speech_performance import SpeechEventKind, SpeechPerformancePhase


def pixels(shade: int) -> bytes:
    return bytes((shade, shade, shade, 255)) * 4


def body(shade: int = 1, generation: int = 1) -> BodyPoseFrame:
    return BodyPoseFrame(
        2,
        2,
        pixels(shade),
        generation,
        ("yaw+000-pitch+00",),
        ("body",),
        True,
    )


def performance(
    *,
    speech_generation: int = 1,
    behavior_generation: int = 1,
    viseme: str = "A",
    mouth_closed: bool = False,
) -> AtomicPerformanceFrame:
    value = PerformanceFrame(
        speech_generation,
        behavior_generation,
        SpeechEventKind.VISEME,
        SpeechPerformancePhase.SPEAKING,
        "front-crossed",
        "yaw+000-pitch+00",
        "neutral",
        "relaxed-left",
        "relaxed-right",
        GazeTarget.USER,
        BreathStyle.SPEAKING,
        TransitionStyle.HOLD,
        20,
        viseme,
        mouth_closed,
        0.5,
        False,
        False,
    )
    return AtomicPerformanceFrame(value, body(9, behavior_generation))


def policy(**changes: object) -> FramingPolicyContext:
    value = FramingPolicyContext(
        0.0,
        False,
        0.5,
        0.2,
        EmotionValence.NEUTRAL,
        False,
        False,
        True,
        None,
        False,
        False,
        FocusState.AVAILABLE,
        False,
        True,
    )
    return replace(value, **changes)


class Assets:
    generation = 1
    enabled = True

    def resolve_static(self, *_args):
        raise AssertionError("Runtime must not read assets directly")

    def resolve_speech(self, *_args):
        raise AssertionError("Runtime must not read assets directly")


class FramingPort:
    def __init__(self) -> None:
        self.calls = 0
        self.fail = False
        self.command = AtomicFramingCommand(
            1,
            FramingMode.HALF,
            FRAMING_RECTS[FramingMode.HALF],
            480,
            (FramingAuditEntry("test", "half"),),
        )

    @property
    def last_known_good(self):
        return self.command if self.calls else None

    def dispatch(self, _value):
        self.calls += 1
        if self.fail:
            return FramingBridgeResult(FramingBridgeDisposition.FALLBACK, self.command)
        return FramingBridgeResult(FramingBridgeDisposition.EMITTED, self.command)


class FullBodyPort:
    def __init__(self) -> None:
        self.generation = 0
        self.cancelled: set[int] = set()
        self.calls = 0
        self.static_rebuilds = 0
        self.static_signature = None
        self.fail = False
        self.frame = body(3)
        self.requests = []

    @property
    def last_known_good(self):
        return self.frame if self.calls else None

    def begin_operation(self):
        self.generation += 1
        return self.generation

    def cancel(self, generation):
        self.cancelled.add(generation)

    def dispatch(self, request):
        self.calls += 1
        self.requests.append(request)
        if self.fail:
            raise RuntimeError("full-body failure")
        static = (
            request.atomic_frame.performance.behavior_generation,
            request.framing,
            request.assets.generation,
        )
        if static != self.static_signature:
            self.static_signature = static
            self.static_rebuilds += 1
        speech = request.atomic_frame.performance.speech_generation
        self.frame = replace(
            self.frame,
            rgba=pixels(speech % 255),
            generation=speech,
        )
        return FullBodyBridgeResult(
            FullBodyBridgeDisposition.PUBLISHED,
            self.frame,
            False,
        )


def runtime():
    framing = FramingPort()
    full_body = FullBodyPort()
    return AdaptiveCharacterRuntime(framing, full_body), framing, full_body


def request(
    operation: int,
    *,
    frame: AtomicPerformanceFrame | None = None,
    context: FramingPolicyContext | None = None,
    assets: Assets | None = None,
    enabled: bool = True,
) -> AdaptiveCharacterRequest:
    return AdaptiveCharacterRequest(
        operation,
        frame or performance(),
        AppFramingState(operation, context or policy(), 1280, 900, enabled),
        FramingPreferences(),
        assets if assets is not None else Assets(),
        v4_enabled=enabled,
    )


def assert_atomic_publish_uses_both_ports_once() -> None:
    engine, framing, full_body = runtime()
    operation = engine.begin_operation()
    result = engine.dispatch(request(operation))
    assert result.disposition is AdaptiveCharacterDisposition.PUBLISHED
    assert result.should_publish and not result.used_legacy
    assert result.framing is framing.command
    assert framing.calls == full_body.calls == 1
    assert full_body.requests[0].atomic_frame == performance()


def assert_generation_stale_cancel_and_dedupe_are_barriers() -> None:
    engine, framing, full_body = runtime()
    first = engine.begin_operation()
    second = engine.begin_operation()
    stale = engine.dispatch(request(first))
    assert stale.disposition is AdaptiveCharacterDisposition.STALE
    assert framing.calls == full_body.calls == 0
    engine.cancel(second)
    cancelled = engine.dispatch(request(second))
    assert cancelled.disposition is AdaptiveCharacterDisposition.CANCELLED
    assert framing.calls == full_body.calls == 0
    third = engine.begin_operation()
    current = request(third)
    assert engine.dispatch(current).should_publish
    duplicate = engine.dispatch(current)
    assert duplicate.disposition is AdaptiveCharacterDisposition.DEDUPED
    assert not duplicate.should_publish
    assert framing.calls == full_body.calls == 1


def assert_disabled_or_missing_assets_is_complete_legacy_bypass() -> None:
    cases = (
        {"enabled": False},
        {"assets": None},
    )
    for changes in cases:
        engine, framing, full_body = runtime()
        operation = engine.begin_operation()
        if "assets" in changes:
            value = replace(request(operation), assets=None)
        else:
            value = request(operation, enabled=False)
        result = engine.dispatch(value)
        assert result.disposition is AdaptiveCharacterDisposition.BYPASSED
        assert not result.should_publish and result.used_legacy
        assert result.frame == value.atomic_frame.body
        assert framing.calls == full_body.calls == 0


def assert_failure_preserves_last_known_good() -> None:
    engine, _framing, full_body = runtime()
    first = engine.begin_operation()
    published = engine.dispatch(request(first))
    full_body.fail = True
    second = engine.begin_operation()
    failed = engine.dispatch(
        request(second, frame=performance(speech_generation=2))
    )
    assert failed.disposition is AdaptiveCharacterDisposition.LKG
    assert not failed.should_publish
    assert failed.frame is published.frame
    assert engine.last_known_good is published


def assert_50hz_speech_keeps_static_full_body_and_framing_stable() -> None:
    engine, framing, full_body = runtime()
    operation = engine.begin_operation()
    for tick in range(1, 51):
        result = engine.dispatch(
            request(
                operation,
                frame=performance(speech_generation=tick, viseme=f"V{tick}"),
            )
        )
        assert result.disposition is AdaptiveCharacterDisposition.PUBLISHED
        assert result.framing is framing.command
    assert full_body.static_rebuilds == 1
    assert all(item.framing == full_body.requests[0].framing for item in full_body.requests)


def assert_speech_hold_and_settle_do_not_jump_body_height() -> None:
    engine, framing, _full_body = runtime()
    operation = engine.begin_operation()
    held = engine.dispatch(
        request(
            operation,
            context=policy(speech_active=True, mouth_closed=False, outfit_preview=True),
        )
    )
    assert held.framing is not None
    assert held.framing.mode is FramingMode.HALF
    framing.command = AtomicFramingCommand(
        2,
        FramingMode.THREE_QUARTER,
        FRAMING_RECTS[FramingMode.THREE_QUARTER],
        720,
        (FramingAuditEntry("test", "mouth-close-settle"),),
    )
    settled = engine.dispatch(
        request(
            operation,
            frame=performance(
                speech_generation=2,
                viseme="CLOSED",
                mouth_closed=True,
            ),
            context=policy(speech_active=False, mouth_closed=True, outfit_preview=True),
        )
    )
    assert settled.framing is not None
    assert settled.framing.mode is FramingMode.THREE_QUARTER
    assert settled.framing.crop.height > held.framing.crop.height
    assert settled.framing.mode is not FramingMode.FULL_BODY


def run() -> None:
    assert_atomic_publish_uses_both_ports_once()
    assert_generation_stale_cancel_and_dedupe_are_barriers()
    assert_disabled_or_missing_assets_is_complete_legacy_bypass()
    assert_failure_preserves_last_known_good()
    assert_50hz_speech_keeps_static_full_body_and_framing_stable()
    assert_speech_hold_and_settle_do_not_jump_body_height()
    print("ADAPTIVE_CHARACTER_RUNTIME_OK")


if __name__ == "__main__":
    run()
