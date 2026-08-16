from __future__ import annotations

lazy import hashlib
lazy import math
lazy import re
lazy import threading
lazy from collections.abc import Iterable, Mapping
lazy from dataclasses import dataclass
lazy from datetime import datetime

lazy from domain.time_utils import local_wall_time

_WORD_PATTERN = re.compile(r"[\w]+", re.UNICODE)


def _features(text: str) -> list[str]:
    normalized = " ".join(str(text).casefold().split())
    words = _WORD_PATTERN.findall(normalized)
    compact = "".join(words)
    features = [f"w:{word}" for word in words]
    for size in (2, 3):
        features.extend(
            f"c{size}:{compact[index:index + size]}"
            for index in range(max(0, len(compact) - size + 1))
        )
    return features


def hashed_text_vector(text: str, dimensions: int = 384) -> dict[int, float]:
    """Build a deterministic, offline multilingual sparse text vector."""
    counts: dict[int, float] = {}
    for feature in _features(text):
        digest = hashlib.blake2s(
            feature.encode("utf-8"),
            digest_size=4,
            person=b"MoHanMem",
        ).digest()
        index = int.from_bytes(digest, "little") % dimensions
        counts[index] = counts.get(index, 0.0) + 1.0
    norm = math.sqrt(sum(value * value for value in counts.values()))
    if norm:
        return {index: value / norm for index, value in counts.items()}
    return {}


def cosine_similarity(
    left: Mapping[int, float],
    right: Mapping[int, float],
) -> float:
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(index, 0.0) for index, value in left.items())


@dataclass(frozen=True)
class RankedMemory:
    memory_id: int
    score: float
    semantic_score: float


class MemoryVectorIndex:
    """Thread-safe lazy index for local long-term memory retrieval."""

    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions
        self._vectors: dict[int, dict[int, float]] = {}
        self._fingerprints: dict[int, str] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _document_text(row: Mapping[str, object]) -> str:
        return " ".join(
            str(row.get(key) or "")
            for key in ("category", "title", "content")
        )

    def refresh(self, rows: Iterable[Mapping[str, object]]) -> None:
        active: set[int] = set()
        with self._lock:
            for row in rows:
                memory_id = int(row["id"])
                active.add(memory_id)
                text = self._document_text(row)
                fingerprint = hashlib.sha256(text.encode("utf-8")).hexdigest()
                if self._fingerprints.get(memory_id) == fingerprint:
                    continue
                self._vectors[memory_id] = hashed_text_vector(
                    text,
                    self.dimensions,
                )
                self._fingerprints[memory_id] = fingerprint
            for stale_id in set(self._vectors) - active:
                self._vectors.pop(stale_id, None)
                self._fingerprints.pop(stale_id, None)

    def clear(self) -> None:
        with self._lock:
            self._vectors.clear()
            self._fingerprints.clear()

    def rank(
        self,
        query: str,
        rows: list[Mapping[str, object]],
        limit: int,
        now: datetime | None = None,
    ) -> list[RankedMemory]:
        if limit <= 0 or not rows:
            return []
        self.refresh(rows)
        query_vector = hashed_text_vector(query, self.dimensions)
        reference = now or local_wall_time()
        ranked: list[RankedMemory] = []
        with self._lock:
            for row in rows:
                memory_id = int(row["id"])
                semantic = cosine_similarity(
                    query_vector,
                    self._vectors.get(memory_id, {}),
                )
                importance = max(1, min(5, int(row.get("importance") or 3))) / 5
                updated_raw = str(row.get("updated_at") or "")
                try:
                    age_days = max(
                        0.0,
                        (reference - datetime.fromisoformat(updated_raw)).total_seconds()
                        / 86400,
                    )
                except ValueError:
                    age_days = 3650.0
                freshness = 1.0 / (1.0 + age_days / 180.0)
                score = semantic * 0.72 + importance * 0.20 + freshness * 0.08
                ranked.append(RankedMemory(memory_id, score, semantic))
        ranked.sort(key=lambda item: (-item.score, item.memory_id))
        return ranked[:limit]
