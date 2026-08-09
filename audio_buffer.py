from __future__ import annotations

lazy import queue
lazy import threading
lazy from dataclasses import dataclass


@dataclass(frozen=True)
class AudioQueueSnapshot:
    accepted: int
    dropped_oldest: int
    rejected_newest: int
    peak_depth: int
    current_depth: int


class BoundedAudioQueue[T](queue.Queue[T]):
    """A measured queue with explicit live-audio overflow behavior."""

    def __init__(self, maxsize: int) -> None:
        if maxsize <= 0:
            raise ValueError("audio queue maxsize must be positive")
        super().__init__(maxsize=maxsize)
        self._stats_lock = threading.Lock()
        self._accepted = 0
        self._dropped_oldest = 0
        self._rejected_newest = 0
        self._peak_depth = 0

    def offer(self, item: T, *, keep_latest: bool) -> bool:
        """Insert without blocking, with a caller-selected overflow policy."""
        try:
            super().put_nowait(item)
        except queue.Full:
            if not keep_latest:
                with self._stats_lock:
                    self._rejected_newest += 1
                return False
            try:
                super().get_nowait()
            except queue.Empty:
                return self.offer(item, keep_latest=keep_latest)
            with self._stats_lock:
                self._dropped_oldest += 1
            super().put_nowait(item)
        depth = self.qsize()
        with self._stats_lock:
            self._accepted += 1
            self._peak_depth = max(self._peak_depth, depth)
        return True

    def force_stop(self, sentinel: T) -> None:
        """Guarantee that a blocked consumer can observe shutdown."""
        while True:
            try:
                super().put_nowait(sentinel)
                return
            except queue.Full:
                try:
                    super().get_nowait()
                except queue.Empty:
                    continue

    def snapshot(self) -> AudioQueueSnapshot:
        with self._stats_lock:
            return AudioQueueSnapshot(
                accepted=self._accepted,
                dropped_oldest=self._dropped_oldest,
                rejected_newest=self._rejected_newest,
                peak_depth=self._peak_depth,
                current_depth=self.qsize(),
            )


class PcmPacketizer:
    """Turn arbitrary PCM network deltas into fixed low-latency chunks."""

    def __init__(self, chunk_bytes: int, frame_bytes: int = 2) -> None:
        if frame_bytes <= 0 or chunk_bytes <= 0:
            raise ValueError("PCM packet sizes must be positive")
        if chunk_bytes % frame_bytes:
            raise ValueError("chunk size must contain complete PCM frames")
        self.chunk_bytes = chunk_bytes
        self.frame_bytes = frame_bytes
        self._pending = bytearray()
        self._lock = threading.Lock()

    def feed(self, data: bytes) -> list[bytes]:
        if len(data) % self.frame_bytes:
            raise ValueError("PCM network delta contains an incomplete frame")
        with self._lock:
            self._pending.extend(data)
            chunks: list[bytes] = []
            while len(self._pending) >= self.chunk_bytes:
                chunks.append(self._pending.take_bytes(self.chunk_bytes))
            return chunks

    def flush(self) -> bytes:
        with self._lock:
            return self._pending.take_bytes()

    def reset(self) -> None:
        with self._lock:
            self._pending.clear()
