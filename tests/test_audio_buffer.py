from __future__ import annotations

lazy import queue
lazy import sys
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from domain.audio_buffer import BoundedAudioQueue, PcmPacketizer
lazy from integrations.realtime_voice import RealtimeVoiceClient

EXPECTED_PEAK_DEPTH = 3
DEVICE_BLOCK_MILLISECONDS = 20
INPUT_QUEUE_CHUNKS = 32
LATENCY_BUDGET_MS = 640
PLAYBACK_LATENCY_BUDGET_MS = 1500


class _Socket:
    connected = True


class _WebSocket:
    def __init__(self) -> None:
        self.sock = _Socket()
        self.sent: list[str] = []

    def send(self, payload: str) -> None:
        self.sent.append(payload)


def test_live_input_keeps_the_newest_audio_when_delayed() -> None:
    pending: BoundedAudioQueue[bytes | None] = BoundedAudioQueue(3)
    assert pending.offer(b"old-1", keep_latest=True)
    assert pending.offer(b"old-2", keep_latest=True)
    assert pending.offer(b"old-3", keep_latest=True)
    assert pending.offer(b"newest", keep_latest=True)
    assert [pending.get_nowait() for _ in range(3)] == [
        b"old-2",
        b"old-3",
        b"newest",
    ]
    snapshot = pending.snapshot()
    assert snapshot.dropped_oldest == 1
    assert snapshot.rejected_newest == 0
    assert snapshot.peak_depth == EXPECTED_PEAK_DEPTH


def test_playback_never_silently_discards_spoken_audio() -> None:
    pending: BoundedAudioQueue[bytes | None] = BoundedAudioQueue(2)
    assert pending.offer(b"first", keep_latest=False)
    assert pending.offer(b"second", keep_latest=False)
    assert not pending.offer(b"must-not-be-silently-lost", keep_latest=False)
    assert pending.get_nowait() == b"first"
    assert pending.get_nowait() == b"second"
    assert pending.snapshot().rejected_newest == 1


def test_shutdown_sentinel_is_guaranteed_even_when_full() -> None:
    pending: BoundedAudioQueue[bytes | None] = BoundedAudioQueue(2)
    pending.offer(b"first", keep_latest=False)
    pending.offer(b"second", keep_latest=False)
    pending.force_stop(None)
    observed = []
    while True:
        try:
            observed.append(pending.get_nowait())
        except queue.Empty:
            break
    assert observed[-1] is None


def test_realtime_latency_budget_is_bounded() -> None:
    assert RealtimeVoiceClient.DEVICE_BLOCK_MILLISECONDS == DEVICE_BLOCK_MILLISECONDS
    assert RealtimeVoiceClient.INPUT_QUEUE_CHUNKS == INPUT_QUEUE_CHUNKS
    assert (
        RealtimeVoiceClient.DEVICE_BLOCK_MILLISECONDS
        * RealtimeVoiceClient.INPUT_QUEUE_CHUNKS
        <= LATENCY_BUDGET_MS
    )
    assert (
        RealtimeVoiceClient.DEVICE_BLOCK_MILLISECONDS
        * RealtimeVoiceClient.PLAYBACK_QUEUE_CHUNKS
        <= PLAYBACK_LATENCY_BUDGET_MS
    )


def test_pcm_packetizer_preserves_every_byte_and_flushes_tail() -> None:
    packetizer = PcmPacketizer(chunk_bytes=8, frame_bytes=2)
    assert packetizer.feed(b"\x01\x00\x02\x00") == []
    chunks = packetizer.feed(b"\x03\x00\x04\x00\x05\x00")
    assert chunks == [b"\x01\x00\x02\x00\x03\x00\x04\x00"]
    assert packetizer.flush() == b"\x05\x00"
    assert packetizer.flush() == b""


def test_playback_overflow_cancels_the_turn_instead_of_skipping_words() -> None:
    client = RealtimeVoiceClient()
    client.running = True
    client.ws = _WebSocket()
    failures: list[str] = []
    client.failed.connect(failures.append)
    chunk = b"\x00\x00" * (
        client.PLAYBACK_CHUNK_BYTES // 2
    )
    for _ in range(client.PLAYBACK_QUEUE_CHUNKS):
        assert client._queue_playback_chunk(chunk)
    assert not client._queue_playback_chunk(chunk)
    assert client._audio_queue.empty()
    assert client._playback_overflowed
    assert any('"type": "response.cancel"' in item for item in client.ws.sent)
    assert len(failures) == 1
    client.running = False


def main() -> None:
    test_live_input_keeps_the_newest_audio_when_delayed()
    test_playback_never_silently_discards_spoken_audio()
    test_shutdown_sentinel_is_guaranteed_even_when_full()
    test_realtime_latency_budget_is_bounded()
    test_pcm_packetizer_preserves_every_byte_and_flushes_tail()
    test_playback_overflow_cancels_the_turn_instead_of_skipping_words()
    print("LOW_LATENCY_AUDIO_BUFFER_OK")


if __name__ == "__main__":
    main()
