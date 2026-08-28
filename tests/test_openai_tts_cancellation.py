from __future__ import annotations

lazy import io
lazy import math
lazy import struct
lazy import sys
lazy import threading
lazy import time
lazy import wave
lazy from pathlib import Path
lazy from typing import ClassVar, Self
lazy from unittest.mock import patch
lazy from urllib.error import URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QCoreApplication
lazy from shiboken6 import delete as delete_qt_object

lazy from domain.contracts import CloudSpeechEnginePort
lazy from domain.service_status_localization import ServiceStatus, service_status
lazy from integrations.speech import OpenAITTS

# Coarse non-blocking gate, not a performance benchmark (relaxed 0.10 -> 0.5
# on 2026-08-27): stop() must return promptly instead of draining playback.
# The blocked worker stubs hold their gates for 2.0 s, so 0.5 s still proves
# stop() never waited for playback while absorbing slow-runner jitter.
STOP_TIMEOUT_SECONDS = 0.5
EXPECTED_WRITE_COUNT = 6
EXPECTED_VISEME_COUNT = 7


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
            raise AssertionError("timed out waiting for OpenAI TTS worker")
        time.sleep(0.005)
    app.processEvents()


def _signals(tts: OpenAITTS) -> list[tuple[str, object]]:
    events: list[tuple[str, object]] = []
    tts.viseme_cue.connect(
        lambda level, vowel: events.append(("viseme", (level, vowel)))
    )
    tts.failed.connect(lambda message: events.append(("failed", message)))
    tts.finished.connect(lambda: events.append(("finished", None)))
    return events


class _Response:
    def __init__(self, audio: bytes) -> None:
        self.audio = audio

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, limit: int = -1) -> bytes:
        return self.audio if limit < 0 else self.audio[:limit]


class _ExitBlockedResponse(_Response):
    def __init__(self, audio: bytes) -> None:
        super().__init__(audio)
        self.response_read = threading.Event()
        self.release = threading.Event()

    def __exit__(self, *_args: object) -> None:
        self.response_read.set()
        if not self.release.wait(timeout=2.0):
            raise AssertionError("network-return gate was not released")


class _FailingBlockedResponse(_Response):
    def __init__(self) -> None:
        super().__init__(b"")
        self.read_started = threading.Event()
        self.release = threading.Event()

    def read(self, limit: int = -1) -> bytes:
        del limit
        self.read_started.set()
        if not self.release.wait(timeout=2.0):
            raise AssertionError("network-failure gate was not released")
        raise URLError("simulated network failure")


class _BlockingRawOutputStream:
    instances: ClassVar[list[_BlockingRawOutputStream]] = []

    def __init__(self, **_kwargs: object) -> None:
        self.writing = threading.Event()
        self.aborted = threading.Event()
        self.release = threading.Event()
        self.closed = threading.Event()
        self.__class__.instances.append(self)

    def start(self) -> None:
        return

    def write(self, _chunk: bytes) -> None:
        self.writing.set()
        if not self.release.wait(timeout=2.0):
            raise AssertionError("playback worker was not released")

    def stop(self) -> None:
        raise AssertionError("cancelled playback must not drain to completion")

    def abort(self) -> None:
        self.aborted.set()

    def close(self) -> None:
        self.closed.set()


class _CompletingRawOutputStream:
    instances: ClassVar[list[_CompletingRawOutputStream]] = []

    def __init__(self, **_kwargs: object) -> None:
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


def _assert_contract_and_four_language_failures() -> None:
    assert "stop" in CloudSpeechEnginePort.__dict__
    assert callable(OpenAITTS.stop)
    for language in ("zh-TW", "zh-CN", "en-US", "ja-JP"):
        tts = OpenAITTS(language=language)
        events = _signals(tts)
        tts.speak("test", "")
        assert events == [
            (
                "failed",
                service_status(
                    language,
                    ServiceStatus.SPEECH_OPENAI_KEY_MISSING,
                ),
            )
        ]


def _assert_stop_after_network_return_blocks_stale_playback(
    app: QCoreApplication,
) -> None:
    tts = OpenAITTS()
    events = _signals(tts)
    response = _ExitBlockedResponse(_test_wave())
    playback_calls: list[int] = []
    with (
        patch("integrations.speech.urlopen", return_value=response),
        patch.object(
            tts,
            "_play_wave_bytes",
            side_effect=lambda _audio, generation: playback_calls.append(
                generation
            ),
        ),
    ):
        tts.speak("網路回傳後取消", "test-key")
        _wait_until(app, response.response_read.is_set)
        started_at = time.perf_counter()
        tts.stop()
        assert time.perf_counter() - started_at < STOP_TIMEOUT_SECONDS
        response.release.set()
        time.sleep(0.03)
        app.processEvents()
    assert playback_calls == []
    assert events == []


def _assert_stop_suppresses_late_network_failure(
    app: QCoreApplication,
) -> None:
    tts = OpenAITTS()
    events = _signals(tts)
    response = _FailingBlockedResponse()
    with patch("integrations.speech.urlopen", return_value=response):
        tts.speak("網路失敗前取消", "test-key")
        _wait_until(app, response.read_started.is_set)
        tts.stop()
        response.release.set()
        time.sleep(0.03)
        app.processEvents()
    assert events == []


def _assert_new_speech_invalidates_older_network_result(
    app: QCoreApplication,
) -> None:
    tts = OpenAITTS()
    events = _signals(tts)
    old_response = _ExitBlockedResponse(_test_wave())
    new_response = _Response(_test_wave(0.06))
    responses = iter((old_response, new_response))
    played_generations: list[int] = []

    def record_playback(_audio: bytes, generation: int) -> None:
        played_generations.append(generation)

    with (
        patch("integrations.speech.urlopen", side_effect=lambda *_args, **_kwargs: next(responses)),
        patch.object(tts, "_play_wave_bytes", side_effect=record_playback),
    ):
        tts.speak("第一句", "test-key")
        _wait_until(app, old_response.response_read.is_set)
        tts.speak("第二句", "test-key")
        _wait_until(
            app,
            lambda: any(name == "finished" for name, _ in events),
        )
        old_response.release.set()
        time.sleep(0.03)
        app.processEvents()
    assert played_generations == [2]
    assert events == [("finished", None)]


def _assert_playback_stop_is_nonblocking_and_silent(
    app: QCoreApplication,
) -> None:
    _BlockingRawOutputStream.instances.clear()
    tts = OpenAITTS()
    events = _signals(tts)
    with (
        patch("integrations.speech.winsound", object()),
        patch("integrations.speech.urlopen", return_value=_Response(_test_wave(0.30))),
        patch("sounddevice.RawOutputStream", _BlockingRawOutputStream),
    ):
        tts.speak("播放期間取消", "test-key")
        _wait_until(app, lambda: bool(_BlockingRawOutputStream.instances))
        stream = _BlockingRawOutputStream.instances[0]
        _wait_until(app, stream.writing.is_set)
        event_count_at_stop = len(events)
        started_at = time.perf_counter()
        tts.stop()
        assert time.perf_counter() - started_at < STOP_TIMEOUT_SECONDS
        assert stream.aborted.is_set()
        assert not stream.closed.is_set()
        stream.release.set()
        _wait_until(app, stream.closed.is_set)
        time.sleep(0.03)
        app.processEvents()
    assert len(events) == event_count_at_stop
    assert all(name not in {"failed", "finished"} for name, _ in events)
    assert tts._active_stream is None


def _assert_queued_obsolete_signals_are_rejected(
    app: QCoreApplication,
) -> None:
    tts = OpenAITTS()
    events = _signals(tts)
    generation = tts._begin_generation()

    def enqueue_obsolete_results() -> None:
        tts._emit_viseme(generation, 0.8, "A")
        tts._emit_failed(generation, "obsolete failure")
        tts._emit_finished(generation)

    worker = threading.Thread(target=enqueue_obsolete_results)
    worker.start()
    worker.join(timeout=1.0)
    assert not worker.is_alive()
    tts.stop()
    app.processEvents()
    assert events == []


def _assert_deleted_receiver_rejects_late_provider_callbacks() -> None:
    tts = OpenAITTS()
    generation = tts._begin_generation()
    delete_qt_object(tts)

    # Closing the dashboard must not leave a provider worker crashing while it
    # tries to publish a queued failure, completion, or mouth cue.
    tts._emit_failed(generation, "private late failure")
    tts._emit_finished(generation)
    tts._emit_viseme(generation, 0.8, "A")


def _assert_normal_speech_keeps_the_50_hz_mouth_clock(
    app: QCoreApplication,
) -> None:
    _CompletingRawOutputStream.instances.clear()
    tts = OpenAITTS()
    events = _signals(tts)
    with (
        patch("integrations.speech.winsound", object()),
        patch("integrations.speech.urlopen", return_value=_Response(_test_wave(0.12))),
        patch("sounddevice.RawOutputStream", _CompletingRawOutputStream),
    ):
        tts.speak("正常 OpenAI 語音", "test-key", instructions="calm")
        _wait_until(
            app,
            lambda: any(name == "finished" for name, _ in events),
        )
    stream = _CompletingRawOutputStream.instances[0]
    mouth_events = [value for name, value in events if name == "viseme"]
    assert len(stream.writes) == EXPECTED_WRITE_COUNT
    assert len(mouth_events) == EXPECTED_VISEME_COUNT
    assert mouth_events[-1] == (0.0, "CLOSED")
    assert events[-1] == ("finished", None)
    assert all(name != "failed" for name, _ in events)
    assert stream.stopped
    assert stream.closed
    assert tts._active_stream is None


def run() -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    _assert_contract_and_four_language_failures()
    _assert_stop_after_network_return_blocks_stale_playback(app)
    _assert_stop_suppresses_late_network_failure(app)
    _assert_new_speech_invalidates_older_network_result(app)
    _assert_playback_stop_is_nonblocking_and_silent(app)
    _assert_queued_obsolete_signals_are_rejected(app)
    _assert_deleted_receiver_rejects_late_provider_callbacks()
    _assert_normal_speech_keeps_the_50_hz_mouth_clock(app)
    print("OPENAI_TTS_CANCELLATION_OK")


if __name__ == "__main__":
    run()
