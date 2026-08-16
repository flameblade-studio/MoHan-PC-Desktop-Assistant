from __future__ import annotations

lazy import os
lazy import sys
lazy import threading
lazy from collections import deque
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy import pytest
lazy from PySide6.QtWidgets import QApplication

lazy from companion_window import CompanionWindow
lazy from integrations.speech import OpenAITTS


class _StoppingEngine:
    def __init__(self, name: str) -> None:
        self.name = name
        self.stop_calls = 0

    def stop(self) -> None:
        self.stop_calls += 1


class _EngineWithoutStop:
    pass


class _RealtimeEngine:
    def __init__(self, barrier: int = 73) -> None:
        self.barrier = barrier
        self.stop_calls = 0

    def stop(self) -> int:
        self.stop_calls += 1
        return self.barrier


class _RealtimeOutput:
    def __init__(self) -> None:
        self.cancelled_generations: list[int] = []

    def cancel(self, generation: int) -> None:
        self.cancelled_generations.append(generation)


class _GestureStopHarness:
    _stop_current_speech_from_gesture = (
        CompanionWindow._stop_current_speech_from_gesture
    )
    _stop_realtime_output = CompanionWindow._stop_realtime_output
    _complete_proactive_companion_speech = (
        CompanionWindow._complete_proactive_companion_speech
    )

    def __init__(
        self,
        *,
        windows_tts: object,
        openai_tts: object,
        azure_tts: object,
        dragon_hd_tts: object,
        realtime_output: _RealtimeOutput | None,
    ) -> None:
        self.tts = windows_tts
        self.cloud_tts = openai_tts
        self.azure_tts = azure_tts
        self.azure_hd_tts = dragon_hd_tts
        self.realtime = _RealtimeEngine()
        self.realtime_speech_output = realtime_output
        self.speech_queue = deque(("queued one", "queued two"))
        self.speech_playing = True
        self.active_speech_text = "active speech"
        self.active_speech_engine = "openai"
        self.active_speech_delivery_token = "delivery-token"
        self.proactive_results: list[bool] = []
        self._proactive_speech_completions = {
            self.active_speech_delivery_token: self.proactive_results.append
        }
        self.state = "speaking"
        self.mouth_open = True
        self.audio_driven_mouth = True
        self.mouth_stop_calls = 0
        self.state_changes: list[tuple[str, str, bool]] = []
        self.stale_openai_signals: list[str] = []

    def _stop_mouth_animation(self) -> None:
        self.mouth_stop_calls += 1
        self.mouth_open = False
        self.audio_driven_mouth = False

    def set_state(
        self,
        state: str,
        *,
        source: str,
        force: bool,
    ) -> None:
        self.state = state
        self.state_changes.append((state, source, force))

    def observe_stale_viseme(self, _level: float, _vowel: str) -> None:
        self._reopen_from_stale_signal("viseme")

    def observe_stale_finished(self) -> None:
        self._reopen_from_stale_signal("finished")

    def observe_stale_failure(self, _message: str) -> None:
        self._reopen_from_stale_signal("failed")

    def _reopen_from_stale_signal(self, signal_name: str) -> None:
        self.stale_openai_signals.append(signal_name)
        self.mouth_open = True
        self.audio_driven_mouth = True
        self.state = "speaking"


def _application() -> QApplication:
    instance = QApplication.instance()
    return instance if instance is not None else QApplication([])


def _assert_stopped_presentation(harness: _GestureStopHarness) -> None:
    assert not harness.speech_queue
    assert not harness.speech_playing
    assert harness.active_speech_text == ""
    assert harness.active_speech_engine == ""
    assert harness.active_speech_delivery_token == ""
    assert harness.proactive_results == [False]
    assert harness.mouth_stop_calls == 1
    assert not harness.mouth_open
    assert not harness.audio_driven_mouth
    assert harness.state == "idle"
    assert harness.state_changes == [("idle", "conversation", True)]


def test_gesture_stop_uses_every_existing_speech_stop_path() -> None:
    windows_tts = _StoppingEngine("windows")
    openai_tts = OpenAITTS()
    azure_tts = _StoppingEngine("azure")
    dragon_hd_tts = _StoppingEngine("dragon-hd")
    realtime_output = _RealtimeOutput()
    harness = _GestureStopHarness(
        windows_tts=windows_tts,
        openai_tts=openai_tts,
        azure_tts=azure_tts,
        dragon_hd_tts=dragon_hd_tts,
        realtime_output=realtime_output,
    )
    openai_generation = openai_tts._generation

    harness._stop_current_speech_from_gesture()

    assert windows_tts.stop_calls == 1
    assert openai_tts._generation == openai_generation + 1
    assert azure_tts.stop_calls == 1
    assert dragon_hd_tts.stop_calls == 1
    assert harness.realtime.stop_calls == 1
    assert realtime_output.cancelled_generations == [harness.realtime.barrier]
    _assert_stopped_presentation(harness)


@pytest.mark.parametrize(
    "optional_name",
    ("cloud_tts", "azure_tts", "azure_hd_tts"),
)
@pytest.mark.parametrize("replacement_kind", ("none", "without-stop"))
def test_optional_engine_absence_does_not_block_other_providers(
    optional_name: str,
    replacement_kind: str,
) -> None:
    windows_tts = _StoppingEngine("windows")
    openai_tts = _StoppingEngine("openai")
    azure_tts = _StoppingEngine("azure")
    dragon_hd_tts = _StoppingEngine("dragon-hd")
    realtime_output = _RealtimeOutput()
    harness = _GestureStopHarness(
        windows_tts=windows_tts,
        openai_tts=openai_tts,
        azure_tts=azure_tts,
        dragon_hd_tts=dragon_hd_tts,
        realtime_output=realtime_output,
    )
    replacement = (
        None if replacement_kind == "none" else _EngineWithoutStop()
    )
    setattr(harness, optional_name, replacement)

    harness._stop_current_speech_from_gesture()

    assert windows_tts.stop_calls == 1
    expected_openai_calls = 0 if optional_name == "cloud_tts" else 1
    assert openai_tts.stop_calls == expected_openai_calls
    expected_azure_calls = 0 if optional_name == "azure_tts" else 1
    expected_dragon_calls = 0 if optional_name == "azure_hd_tts" else 1
    assert azure_tts.stop_calls == expected_azure_calls
    assert dragon_hd_tts.stop_calls == expected_dragon_calls
    assert harness.realtime.stop_calls == 1
    assert realtime_output.cancelled_generations == [harness.realtime.barrier]
    _assert_stopped_presentation(harness)


def test_missing_realtime_output_still_stops_all_speech_engines() -> None:
    engines = tuple(
        _StoppingEngine(name)
        for name in ("windows", "openai", "azure", "dragon-hd")
    )
    harness = _GestureStopHarness(
        windows_tts=engines[0],
        openai_tts=engines[1],
        azure_tts=engines[2],
        dragon_hd_tts=engines[3],
        realtime_output=None,
    )

    harness._stop_current_speech_from_gesture()

    assert [engine.stop_calls for engine in engines] == [1, 1, 1, 1]
    assert harness.realtime.stop_calls == 1
    _assert_stopped_presentation(harness)


def test_openai_signals_late_at_gesture_stop_cannot_restore_speech() -> None:
    application = _application()
    openai_tts = OpenAITTS()
    harness = _GestureStopHarness(
        windows_tts=_StoppingEngine("windows"),
        openai_tts=openai_tts,
        azure_tts=_StoppingEngine("azure"),
        dragon_hd_tts=_StoppingEngine("dragon-hd"),
        realtime_output=_RealtimeOutput(),
    )
    openai_tts.viseme_cue.connect(harness.observe_stale_viseme)
    openai_tts.finished.connect(harness.observe_stale_finished)
    openai_tts.failed.connect(harness.observe_stale_failure)
    obsolete_generation = openai_tts._begin_generation()

    def enqueue_obsolete_signals() -> None:
        openai_tts._emit_viseme(obsolete_generation, 0.9, "A")
        openai_tts._emit_failed(obsolete_generation, "obsolete failure")
        openai_tts._emit_finished(obsolete_generation)

    worker = threading.Thread(target=enqueue_obsolete_signals)
    worker.start()
    worker.join(timeout=1.0)
    assert not worker.is_alive()

    harness._stop_current_speech_from_gesture()
    late_worker = threading.Thread(target=enqueue_obsolete_signals)
    late_worker.start()
    late_worker.join(timeout=1.0)
    assert not late_worker.is_alive()
    application.processEvents()

    assert harness.stale_openai_signals == []
    _assert_stopped_presentation(harness)
