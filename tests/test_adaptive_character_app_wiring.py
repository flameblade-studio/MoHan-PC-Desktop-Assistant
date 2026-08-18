from __future__ import annotations

lazy import os
lazy import sys
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from types import SimpleNamespace

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtWidgets import QApplication

lazy from adaptive_character_composition import AdaptiveCharacterComposition
lazy from companion_window import CompanionWindow


@dataclass(frozen=True, slots=True)
class FakeFrame:
    width: int
    height: int
    rgba: bytes


@dataclass(frozen=True, slots=True)
class FakeDecision:
    should_publish: bool
    used_legacy: bool
    frame: object


class FakeAdaptiveRuntime:
    def __init__(self, stage_frame) -> None:
        self._stage_frame = stage_frame
        self.generation = 0
        self.cancelled: list[int] = []
        self.requests: list[object] = []
        self.publish = False

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
        return FakeDecision(True, False, frame)


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
    """A published v4 full-body frame must keep owning the canvas during speech.

    The v4 full-body composition renders its own speech mouth from
    speech-performance events.  The legacy viseme path (``_audio_viseme_cue``)
    must not run in parallel: it would reset ``_adaptive_full_body_active`` and
    let the suppressed half-body overlays return, stacking a second body over
    the full-body frame (the reported startup double image).
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
        decision = window._dispatch_adaptive_character_frame(atomic_frame())
        assert decision is not None and decision.should_publish
        assert window._adaptive_full_body_active is True

        # A live viseme cue during speech must not hand the canvas back to the
        # legacy half-body renderer.
        window.state = "speaking"
        window.audio_driven_mouth = True
        window._audio_viseme_cue(0.65, "A")
        assert window._adaptive_full_body_active is True, (
            "_audio_viseme_cue must not reset full-body ownership"
        )
    finally:
        window.close()


def assert_expression_state_does_not_reset_full_body_ownership() -> None:
    """A wave/arrival expression must not hand the canvas back to legacy sprites.

    ``set_state`` switches the legacy half-body sprite for expressive states.
    In full-body mode that switch would reset ``_adaptive_full_body_active`` and
    stack the suppressed overlays back over the full-body photograph (the
    reported double image).  The full-body widget must keep owning the canvas
    while the gesture animation still provides a visible body response.
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
        decision = window._dispatch_adaptive_character_frame(atomic_frame())
        assert decision is not None and decision.should_publish
        assert window._adaptive_full_body_active is True

        accepted = window.set_state("happy", source="visual", intensity=0.6)
        assert accepted is True
        assert window._adaptive_full_body_active is True, (
            "set_state must not reset full-body ownership"
        )
        assert window.state == "happy"
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
        application.processEvents()
    print("ADAPTIVE_CHARACTER_APP_WIRING_OK")


if __name__ == "__main__":
    run()
