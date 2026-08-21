from __future__ import annotations

lazy import io
lazy import math
lazy import struct
lazy import sys
lazy import threading
lazy import time
lazy import wave
lazy from itertools import pairwise
lazy from pathlib import Path
lazy from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QCoreApplication

lazy from integrations.speech import (
    WindowsTTS,
    emit_wave_viseme_cues,
    play_wave_with_visemes,
)
lazy from lip_sync import VISEME_CUES_PER_SECOND

EXPECTED_VISEME_CUES_PER_SECOND = 50
MIN_EMITTED_CUES = 56
FIRST_CUE_MAX_SECONDS = 0.04
LAST_CUE_MIN_SECONDS = 1.05
LAST_CUE_MAX_SECONDS = 1.24
INTERVAL_TOLERANCE_SECONDS = 0.07
MEAN_INTERVAL_TOLERANCE_SECONDS = 0.003
MIN_GATED_CUES = 5


def make_test_wave(duration: float = 1.2, rate: int = 24000) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(rate)
        frames = bytearray()
        for index in range(round(duration * rate)):
            sample = round(
                math.sin(index * math.tau * 440.0 / rate) * 7200
            )
            frames.extend(struct.pack("<h", sample))
        target.writeframes(bytes(frames))
    return output.getvalue()


def measure(_tts: WindowsTTS, duration: float) -> list[float]:
    emitted_at: list[float] = []
    playback_start = threading.Event()
    timeline_ready = threading.Event()
    started_at = [0.0]
    worker = threading.Thread(
        target=emit_wave_viseme_cues,
        args=(
            make_test_wave(duration),
            lambda _level, _vowel: emitted_at.append(
                time.perf_counter() - started_at[0]
            ),
            playback_start,
            timeline_ready,
        ),
    )
    worker.start()
    assert timeline_ready.wait(timeout=2.0)
    started_at[0] = time.perf_counter()
    playback_start.set()
    worker.join(timeout=duration + 1.0)
    assert not worker.is_alive()
    return emitted_at


def run() -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    assert VISEME_CUES_PER_SECOND == EXPECTED_VISEME_CUES_PER_SECOND
    tts = WindowsTTS()
    emitted_at = measure(tts, 1.2)
    app.processEvents()
    assert len(emitted_at) >= MIN_EMITTED_CUES
    assert emitted_at[0] < FIRST_CUE_MAX_SECONDS
    assert LAST_CUE_MIN_SECONDS <= emitted_at[-1] <= LAST_CUE_MAX_SECONDS
    long_emitted_at = measure(tts, 4.0)
    app.processEvents()
    expected_last = (
        len(long_emitted_at) - 1
    ) / VISEME_CUES_PER_SECOND
    assert abs(long_emitted_at[-1] - expected_last) < INTERVAL_TOLERANCE_SECONDS
    intervals = [
        current - previous
        for previous, current in pairwise(long_emitted_at)
    ]
    assert abs(
        sum(intervals) / len(intervals)
        - 1.0 / VISEME_CUES_PER_SECOND
    ) < MEAN_INTERVAL_TOLERANCE_SECONDS

    # Only the first 20 ms WAV cue is prepared before playback, and no visual
    # cue may escape until the real playback-start gate releases it.
    playback_start = threading.Event()
    timeline_ready = threading.Event()
    gated_cues: list[tuple[float, str]] = []
    with patch(
        "domain.audio_acceleration.PythonPcmAcceleration.infer_vowel_pcm16",
        return_value=(0.5, "A"),
    ) as analyzer:
        worker = threading.Thread(
            target=emit_wave_viseme_cues,
            args=(
                make_test_wave(0.12),
                lambda level, vowel: gated_cues.append((level, vowel)),
                playback_start,
                timeline_ready,
            ),
        )
        worker.start()
        assert timeline_ready.wait(timeout=1.0)
        assert gated_cues == []
        assert analyzer.call_count == 1
        playback_start.set()
        worker.join(timeout=1.0)
    assert len(gated_cues) >= MIN_GATED_CUES

    # Volume preparation must finish before the playback gate can emit a cue.
    order: list[str] = []

    class FakeWinSound:
        SND_FILENAME = 1
        SND_MEMORY = 2

        @staticmethod
        def PlaySound(_audio, _flags) -> None:
            order.append("playback-start")
            time.sleep(0.03)
            order.append("playback-end")

    def prepared_audio(
        audio: bytes,
        _volume: int,
        _muted: bool,
        **_options: object,
    ) -> bytes:
        order.append("volume-ready")
        return audio

    with (
        patch("integrations.speech.winsound", FakeWinSound),
        patch("integrations.speech.apply_wav_volume", side_effect=prepared_audio),
    ):
        play_wave_with_visemes(
            make_test_wave(0.08),
            80,
            False,
            lambda _level, vowel: order.append(
                "closed" if vowel == "CLOSED" else "cue"
            ),
        )
    assert order[0] == "volume-ready"
    assert "cue" in order
    assert order.index("volume-ready") < order.index("cue")
    assert order.index("playback-end") < order.index("closed")
    assert order[-1] == "closed"

    # If analysis falls behind the blocking audio player, no late vowel is
    # allowed to reopen the mouth after the final closed cue.
    delayed_cues: list[str] = []

    class ShortPlayback(FakeWinSound):
        @staticmethod
        def PlaySound(_audio, _flags) -> None:
            time.sleep(0.01)

    def slow_analyzer(_pcm: bytes, _rate: int) -> tuple[float, str]:
        time.sleep(0.03)
        return 0.7, "A"

    with (
        patch("integrations.speech.winsound", ShortPlayback),
        patch(
            "domain.audio_acceleration.PythonPcmAcceleration.infer_vowel_pcm16",
            side_effect=slow_analyzer,
        ),
    ):
        play_wave_with_visemes(
            make_test_wave(0.12),
            100,
            False,
            lambda _level, vowel: delayed_cues.append(vowel),
        )
    assert delayed_cues[-1] == "CLOSED"
    completed_cues = tuple(delayed_cues)
    time.sleep(0.08)
    assert tuple(delayed_cues) == completed_cues
    print("LIPSYNC_TIMING_OK")


if __name__ == "__main__":
    run()
