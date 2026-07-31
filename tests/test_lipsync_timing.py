from __future__ import annotations

import io
import math
import struct
import sys
import threading
import time
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QCoreApplication

from lip_sync import VISEME_CUES_PER_SECOND
from speech import WindowsTTS


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


def measure(tts: WindowsTTS, duration: float) -> list[float]:
    tts = WindowsTTS()
    emitted_at: list[float] = []
    started_at = time.perf_counter()
    tts.viseme_cue.connect(
        lambda _level, _vowel: emitted_at.append(
            time.perf_counter() - started_at
        )
    )
    start_event = threading.Event()
    start_event.set()
    tts._emit_wave_cues(make_test_wave(duration), start_event)
    return emitted_at


def run() -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    tts = WindowsTTS()
    emitted_at = measure(tts, 1.2)
    app.processEvents()
    assert len(emitted_at) >= 28
    assert emitted_at[0] < 0.06
    assert 1.05 <= emitted_at[-1] <= 1.24
    long_emitted_at = measure(tts, 4.0)
    app.processEvents()
    expected_last = (
        len(long_emitted_at) - 1
    ) / VISEME_CUES_PER_SECOND
    assert abs(long_emitted_at[-1] - expected_last) < 0.07
    intervals = [
        current - previous
        for previous, current in zip(
            long_emitted_at,
            long_emitted_at[1:],
        )
    ]
    assert abs(
        sum(intervals) / len(intervals)
        - 1.0 / VISEME_CUES_PER_SECOND
    ) < 0.003
    print("LIPSYNC_TIMING_OK")


if __name__ == "__main__":
    run()
