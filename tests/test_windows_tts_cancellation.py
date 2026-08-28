from __future__ import annotations

lazy import io
lazy import math
lazy import struct
lazy import sys
lazy import threading
lazy import time
lazy import wave
lazy from pathlib import Path
lazy from typing import ClassVar
lazy from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QCoreApplication

lazy from domain.contracts import LocalSpeechEnginePort
lazy from integrations.speech import UnavailableSystemTTS, WindowsTTS


def _test_wave(duration: float = 0.20, rate: int = 24_000) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(rate)
        target.writeframes(
            b"".join(
                struct.pack(
                    "<h",
                    round(
                        math.sin(index * math.tau * 440.0 / rate)
                        * 7_200
                    ),
                )
                for index in range(round(duration * rate))
            )
        )
    return output.getvalue()


def _wait_until(
    app: QCoreApplication,
    condition,
    timeout: float = 2.0,
) -> None:
    deadline = time.monotonic() + timeout
    while not condition():
        app.processEvents()
        if time.monotonic() >= deadline:
            raise AssertionError("timed out waiting for Windows TTS worker")
        time.sleep(0.005)
    app.processEvents()


class BlockingPowerShell:
    instances: ClassVar[list[BlockingPowerShell]] = []

    def __init__(self, *_args, **_kwargs) -> None:
        self.returncode: int | None = None
        self.communicating = threading.Event()
        self.terminated = threading.Event()
        self.__class__.instances.append(self)

    def communicate(self, timeout: float | None = None):
        del timeout
        self.communicating.set()
        if not self.terminated.wait(timeout=2.0):
            raise AssertionError("PowerShell cancellation was not delivered")
        return b"", b"cancelled"

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.returncode = -1
        self.terminated.set()


class BlockingRawOutputStream:
    instances: ClassVar[list[BlockingRawOutputStream]] = []

    def __init__(self, **_kwargs) -> None:
        self.started = threading.Event()
        self.writing = threading.Event()
        self.aborted = threading.Event()
        self.closed = threading.Event()
        self.__class__.instances.append(self)

    def start(self) -> None:
        self.started.set()

    def write(self, _chunk: bytes) -> None:
        self.writing.set()
        if not self.aborted.wait(timeout=2.0):
            raise AssertionError("audio playback cancellation was not delivered")

    def stop(self) -> None:
        raise AssertionError("cancelled playback must not drain to completion")

    def abort(self) -> None:
        self.aborted.set()

    def close(self) -> None:
        self.closed.set()


class CompletingRawOutputStream:
    instances: ClassVar[list[CompletingRawOutputStream]] = []

    def __init__(self, **_kwargs) -> None:
        self.writes: list[bytes] = []
        self.stopped = False
        self.closed = False
        self.__class__.instances.append(self)

    def start(self) -> None:
        return

    def write(self, chunk: bytes) -> None:
        self.writes.append(chunk)

    def stop(self) -> None:
        self.stopped = True

    def abort(self) -> None:
        raise AssertionError("completed playback must not be aborted")

    def close(self) -> None:
        self.closed = True


def _signals(tts: WindowsTTS):
    events: list[tuple[str, object]] = []
    tts.viseme_cue.connect(
        lambda level, vowel: events.append(("viseme", (level, vowel)))
    )
    tts.failed.connect(lambda message: events.append(("failed", message)))
    tts.finished.connect(lambda: events.append(("finished", None)))
    return events


def _assert_contract() -> None:
    assert "stop" in LocalSpeechEnginePort.__dict__
    assert callable(WindowsTTS.stop)
    unavailable = UnavailableSystemTTS("unavailable")
    unavailable_events: list[str] = []
    unavailable.finished.connect(lambda: unavailable_events.append("finished"))
    unavailable.stop()
    assert unavailable_events == []


def _assert_synthesis_is_cancellable(app: QCoreApplication) -> None:
    BlockingPowerShell.instances.clear()
    tts = WindowsTTS()
    events = _signals(tts)
    with (
        patch("integrations.speech.windows_voices", return_value=[("Hanhan", "zh-TW")]),
        patch("subprocess.Popen", BlockingPowerShell),
    ):
        tts.speak("合成期間取消", "Hanhan")
        _wait_until(app, lambda: bool(BlockingPowerShell.instances))
        process = BlockingPowerShell.instances[0]
        _wait_until(app, process.communicating.is_set)
        tts.stop()
        _wait_until(app, process.terminated.is_set)
        time.sleep(0.03)
        app.processEvents()
    assert events == []


def _assert_playback_is_cancellable(app: QCoreApplication) -> None:
    BlockingRawOutputStream.instances.clear()
    tts = WindowsTTS()
    events = _signals(tts)
    audio = _test_wave()

    def play_synthesized(
        _text: str,
        _voice_name: str,
        _rate: int,
        generation: int,
    ) -> None:
        tts._play_wave_bytes(audio, generation)

    with (
        patch("integrations.speech.windows_voices", return_value=[("Hanhan", "zh-TW")]),
        patch.object(tts, "_run_sapi", side_effect=play_synthesized),
        patch("sounddevice.RawOutputStream", BlockingRawOutputStream),
    ):
        tts.speak("播放期間取消", "Hanhan")
        _wait_until(app, lambda: bool(BlockingRawOutputStream.instances))
        stream = BlockingRawOutputStream.instances[0]
        _wait_until(app, stream.writing.is_set)
        tts.stop()
        event_count_at_stop = len(events)
        _wait_until(app, stream.closed.is_set)
        time.sleep(0.03)
        app.processEvents()
    assert stream.aborted.is_set()
    assert len(events) == event_count_at_stop
    assert all(name not in {"failed", "finished"} for name, _ in events)


def _assert_new_speech_invalidates_old_generation(
    app: QCoreApplication,
) -> None:
    tts = WindowsTTS()
    events = _signals(tts)
    first_started = threading.Event()
    release_first = threading.Event()

    def controlled_synthesis(
        text: str,
        _voice_name: str,
        _rate: int,
        generation: int,
    ) -> None:
        if text == "第一句":
            first_started.set()
            release_first.wait(timeout=2.0)
            tts._emit_viseme(generation, 0.8, "A")

    with (
        patch("integrations.speech.windows_voices", return_value=[("Hanhan", "zh-TW")]),
        patch.object(tts, "_run_sapi", side_effect=controlled_synthesis),
    ):
        tts.speak("第一句", "Hanhan")
        _wait_until(app, first_started.is_set)
        tts.speak("第二句", "Hanhan")
        _wait_until(
            app,
            lambda: any(name == "finished" for name, _ in events),
        )
        release_first.set()
        time.sleep(0.03)
        app.processEvents()
    assert events == [("finished", None)]


def _assert_normal_speech_still_completes(app: QCoreApplication) -> None:
    CompletingRawOutputStream.instances.clear()
    tts = WindowsTTS()
    events = _signals(tts)
    audio = _test_wave(0.06)

    def play_synthesized(
        _text: str,
        _voice_name: str,
        _rate: int,
        generation: int,
    ) -> None:
        tts._play_wave_bytes(audio, generation)

    with (
        patch("integrations.speech.windows_voices", return_value=[("Hanhan", "zh-TW")]),
        patch.object(tts, "_run_sapi", side_effect=play_synthesized),
        patch("sounddevice.RawOutputStream", CompletingRawOutputStream),
    ):
        tts.speak("正常朗讀", "Hanhan")
        _wait_until(
            app,
            lambda: any(name == "finished" for name, _ in events),
        )
    stream = CompletingRawOutputStream.instances[0]
    assert stream.writes
    assert stream.stopped
    assert stream.closed
    assert events[-2:] == [
        ("viseme", (0.0, "CLOSED")),
        ("finished", None),
    ]
    assert all(name != "failed" for name, _ in events)


def run() -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    _assert_contract()
    _assert_synthesis_is_cancellable(app)
    _assert_playback_is_cancellable(app)
    _assert_new_speech_invalidates_old_generation(app)
    _assert_normal_speech_still_completes(app)
    print("WINDOWS_TTS_CANCELLATION_OK")


if __name__ == "__main__":
    run()
