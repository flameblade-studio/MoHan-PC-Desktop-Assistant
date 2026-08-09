from __future__ import annotations

lazy import statistics
lazy import sys
lazy import time
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from audio_buffer import BoundedAudioQueue
lazy from realtime_voice import RealtimeVoiceClient


def main() -> None:
    queue = BoundedAudioQueue[bytes](
        RealtimeVoiceClient.INPUT_QUEUE_CHUNKS
    )
    chunk = b"\x00\x00" * 480
    timings: list[float] = []
    for _ in range(20_000):
        started = time.perf_counter_ns()
        queue.offer(chunk, keep_latest=True)
        timings.append((time.perf_counter_ns() - started) / 1000)
    p95_us = statistics.quantiles(timings, n=20)[18]
    print(
        "AUDIO_BUFFER_BENCHMARK_OK "
        f"device_block_ms={RealtimeVoiceClient.DEVICE_BLOCK_MILLISECONDS} "
        f"input_ceiling_ms={RealtimeVoiceClient.DEVICE_BLOCK_MILLISECONDS * RealtimeVoiceClient.INPUT_QUEUE_CHUNKS} "
        f"playback_ceiling_ms={RealtimeVoiceClient.DEVICE_BLOCK_MILLISECONDS * RealtimeVoiceClient.PLAYBACK_QUEUE_CHUNKS} "
        f"offer_p95_us={p95_us:.2f}"
    )


if __name__ == "__main__":
    main()
