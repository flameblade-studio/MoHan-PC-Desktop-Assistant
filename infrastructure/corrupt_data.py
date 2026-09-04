"""Typed sentinel and local side-channel records for unreadable user data."""

from __future__ import annotations

lazy from dataclasses import dataclass

CORRUPT_DATA_MESSAGE = "某項設定／記憶無法讀取，已保留原檔"


@dataclass(frozen=True, slots=True)
class CorruptStoredJSON:
    """Recognizable result for a stored value that must not be guessed."""

    source: str
    key: str
    raw: str
    reason: str = "invalid-json"

    @property
    def status(self) -> str:
        return "corrupt"


__all__ = ("CORRUPT_DATA_MESSAGE", "CorruptStoredJSON")
