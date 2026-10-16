from __future__ import annotations

lazy import os
lazy import sys
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from types import SimpleNamespace

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QTimer
lazy from PySide6.QtWidgets import QApplication

lazy from application.adaptive_character_composition import AdaptiveCharacterComposition
lazy from domain.character_framing import FramingMode
lazy from presentation.companion_window import CompanionWindow


@dataclass(frozen=True, slots=True)
class FakeFrame:
    width: int
    height: int
    rgba: bytes


@dataclass(frozen=True, slots=True)
class FakeFraming:
    mode: object


@dataclass(frozen=True, slots=True)
class FakeDecision:
    should_publish: bool
    used_legacy: bool
    frame: object
    framing: object | None = None


class FakeAdaptiveRuntime:
    def __init__(self, stage_frame) -> None:
        self._stage_frame = stage_frame
        self.generation = 0
        self.cancelled: list[int] = []
        self.requests: list[object] = []
        self.publish = False
        self.framing_mode: object | None = None

    def begin_operation(self) -> int:
        self.generation += 1
        return self.generation

    def cancel(self, generation: int) -> None:
        self.cancelled.append(generation)

    def dispatch(self, request: object) -> FakeDecision:
        self.requests.append(request)
        legacy = request.atomic_frame.body
        if not self.publish or request.assets is None:
            return FakeDecision(False, True, legacy)
        frame = FakeFrame(2, 2, bytes((20, 40, 80, 255)) * 4)
        self._stage_frame(frame)
        framing = (
            FakeFraming(self.framing_mode)
            if self.framing_mode is not None
            else None
        )
        return FakeDecision(True, False, frame, framing)


@dataclass(frozen=True, slots=True)
class FakeAssets:
    enabled: bool = True


class FakeFactory:
    def __init__(self) -> None:
        self.calls = 0
        self.runtime: FakeAdaptiveRuntime | None = None
        self.assets: object | None = FakeAssets()

    def __call__(self, stage_frame) -> AdaptiveCharacterComposition:
        self.calls += 1
        self.runtime = FakeAdaptiveRuntime(stage_frame)
        return AdaptiveCharacterComposition(self.runtime, self.assets)


def atomic_frame(*, speech_generation: int = 1) -> object:
    performance = SimpleNamespace(
        speech_generation=speech_generation,
        behavior_generation=1,
        mouth_closed=False,
        body_energy=0.4,
        pose="front-crossed",
    )
    legacy = FakeFrame(2, 2, bytes((1, 1, 1, 255)) * 4)
    return SimpleNamespace(performance=performance, body=legacy)


def assert_legacy_gate_does_not_resolve_factory() -> None:
    factory = FakeFactory()
    window = CompanionWindow(
        startup_speech=False,
        defer_visual_startup=True,
        adaptive_character_factory=factory,
        adaptive_character_enabled=False,
    )
    try:
        assert factory.calls == 0
        assert window._dispatch_adaptive_character_frame(atomic_frame()) is None
        assert window.character.pixmap() is not None
    finally:
        window.close()


def assert_missing_assets_bypass_without_crash() -> None:
    factory = FakeFactory()
    factory.assets = None
    window = CompanionWindow(
        startup_speech=False,
        defer_visual_startup=True,
        adaptive_character_factory=factory,
        adaptive_character_enabled=True,
    )
    try:
        decision = window._dispatch_adaptive_character_frame(atomic_frame())
        assert decision is not None
        assert decision.used_legacy and not decision.should_publish
    finally:
        window.close()


def assert_v4_publish_and_speech_hold_preserve_geometry() -> None:
    factory = FakeFactory()
    window = CompanionWindow(
        startup_speech=False,
        defer_visual_startup=True,
        adaptive_character_factory=factory,
        adaptive_character_enabled=True,
    )
    try:
        runtime = factory.runtime
        assert runtime is not None
        assert window._performance_app_bridge is not None
        window._record_speech_performance(
            window.speech_performance.prepare("visual-only")
        )
        assert runtime.requests
        runtime.publish = True
        runtime.framing_mode = FramingMode.FULL_BODY
        before = window.character.size()
        first = window._dispatch_adaptive_character_frame(atomic_frame())
        second = window._dispatch_adaptive_character_frame(
            atomic_frame(speech_generation=2)
        )
        assert first is not None and first.should_publish
        assert second is not None and second.should_publish
        assert window.character.size() == before
        assert [
            request.atomic_frame.performance.behavior_generation
            for request in runtime.requests[-2:]
        ] == [1, 1]
    finally:
        window.close()
    assert runtime.cancelled == [1]


def assert_audio_viseme_does_not_reset_full_body_ownership() -> None:
    """A published v4 full-body frame keeps canvas ownership during speech.

    Speech-performance events drive the full-body mouth. The legacy
    _audio_viseme_cue path remains suppressed to preserve
    _adaptive_full_body_active and the single full-body composition.
    """
    factory = FakeFactory()
    window = CompanionWindow(
        startup_speech=False,
        defer_visual_startup=True,
        adaptive_character_factory=factory,
        adaptive_character_enabled=True,
    )
    try:
        runtime = factory.runtime
        assert runtime is not None
        runtime.publish = True
        runtime.framing_mode = FramingMode.FULL_BODY
        # This focused wiring test defers the full visual startup, so create
        # the mouth/viseme state explicitly before injecting an audio cue.
        window._initialize_mouth_animation_state()
        window.physics_expression_poses = {}
        window.idle_pose = "front"
        decision = window._dispatch_adaptive_character_frame(atomic_frame())
        assert decision is not None and decision.should_publish
        assert window._adaptive_full_body_active is True
        window._record_speech_performance(
            window.speech_performance.prepare("system-local")
        )
        recorded_updates = []
        real_record = window._record_speech_performance

        def record_viseme(update) -> None:
            recorded_updates.append(update)
            real_record(update)

        window._record_speech_performance = record_viseme

        # A live speech viseme reaches the adaptive renderer that owns the full-body
        # mouth, while the legacy half-body renderer remains suppressed.
        window.state = "speaking"
        window.audio_driven_mouth = True
        window.mouth_closing = False
        cue_level = 0.65
        # The production dynamics deliberately need five stable cues before a
        # fresh vowel settles from CLOSED/E to A (anti-flicker contract).
        for _ in range(5):
            window._audio_viseme_cue(cue_level, "A")
        assert window._adaptive_full_body_active is True, (
            '_audio_viseme_cue must preserve full-body ownership'
        )
        accepted_updates = [update for update in recorded_updates if update is not None]
        assert accepted_updates, recorded_updates
        viseme_event = accepted_updates[-1][0]
        assert viseme_event.viseme == "A"
        assert viseme_event.level == cue_level
    finally:
        window.close()


def assert_expression_state_does_not_reset_full_body_ownership() -> None:
    """Wave and arrival expressions preserve full-body canvas ownership.

    In full-body mode, set_state keeps _adaptive_full_body_active and the
    full-body widget in charge while the gesture animation provides a visible
    response. Legacy half-body sprites remain suppressed throughout.
    """
    factory = FakeFactory()
    window = CompanionWindow(
        startup_speech=False,
        defer_visual_startup=True,
        adaptive_character_factory=factory,
        adaptive_character_enabled=True,
    )
    try:
        runtime = factory.runtime
        assert runtime is not None
        runtime.publish = True
        runtime.framing_mode = FramingMode.FULL_BODY
        decision = window._dispatch_adaptive_character_frame(atomic_frame())
        assert decision is not None and decision.should_publish
        assert window._adaptive_full_body_active is True

        accepted = window.set_state("happy", source="visual", intensity=0.6)
        assert accepted is True
        assert window._adaptive_full_body_active is True, (
            'set_state must preserve full-body ownership'
        )
        assert window.state == "happy"
    finally:
        window.close()


def assert_blink_does_not_reset_full_body_ownership() -> None:
    """Blinking preserves the full-body photograph and its canvas ownership.

    The full-body renderer updates blink_opacity and recomposes its own eyelids.
    The ownership flag remains set and the legacy half-body blink patch stays
    suppressed, preserving a single full-body composition.
    """
    factory = FakeFactory()
    window = CompanionWindow(
        startup_speech=False,
        defer_visual_startup=True,
        adaptive_character_factory=factory,
        adaptive_character_enabled=True,
    )
    try:
        runtime = factory.runtime
        assert runtime is not None
        runtime.publish = True
        runtime.framing_mode = FramingMode.FULL_BODY
        decision = window._dispatch_adaptive_character_frame(atomic_frame())
        assert decision is not None and decision.should_publish
        assert window._adaptive_full_body_active is True

        window.state = "idle"
        # ``defer_visual_startup`` skips the blink timer wiring, so provide a
        # minimal timer for _schedule_blink in this isolated event-loop fixture.
        window.blink_timer = QTimer(window)
        window.blink_timer.setSingleShot(True)
        window._blink()
        assert window._adaptive_full_body_active is True, (
            '_blink must preserve full-body ownership'
        )
        assert window.blink_opacity > 0.0, (
            "_blink must drive blink_opacity for the full-body renderer"
        )
    finally:
        window.close()


def assert_half_body_framing_does_not_publish_full_body() -> None:
    """HALF/CLOSE framing keeps the half-body poses during idle and speech.

    Full-body photographs serve gestures, hand actions, accessory reveals,
    owner arrival, and special occasions under THREE_QUARTER/FULL_BODY.
    HALF framing retains cheek-rest, left-neutral, and front-crossed poses.
    """
    factory = FakeFactory()
    window = CompanionWindow(
        startup_speech=False,
        defer_visual_startup=True,
        adaptive_character_factory=factory,
        adaptive_character_enabled=True,
    )
    try:
        runtime = factory.runtime
        assert runtime is not None
        runtime.publish = True
        # HALF framing publishes the half-body pose exclusively.
        runtime.framing_mode = FramingMode.HALF
        decision = window._dispatch_adaptive_character_frame(atomic_frame())
        assert decision is not None and decision.should_publish
        assert window._adaptive_full_body_active is False, (
            'HALF framing must publish the half-body pose exclusively'
        )
        # FULL_BODY framing must publish the full-body photograph.
        runtime.framing_mode = FramingMode.FULL_BODY
        decision = window._dispatch_adaptive_character_frame(atomic_frame())
        assert decision is not None and decision.should_publish
        assert window._adaptive_full_body_active is True, (
            "FULL_BODY framing must publish the full-body photograph"
        )
    finally:
        window.close()


def run() -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        os.environ["LOCALAPPDATA"] = temp
        application = QApplication.instance() or QApplication([])
        assert_legacy_gate_does_not_resolve_factory()
        assert_missing_assets_bypass_without_crash()
        assert_v4_publish_and_speech_hold_preserve_geometry()
        assert_audio_viseme_does_not_reset_full_body_ownership()
        assert_expression_state_does_not_reset_full_body_ownership()
        assert_blink_does_not_reset_full_body_ownership()
        assert_half_body_framing_does_not_publish_full_body()
        application.processEvents()
    print("ADAPTIVE_CHARACTER_APP_WIRING_OK")


if __name__ == "__main__":
    run()
