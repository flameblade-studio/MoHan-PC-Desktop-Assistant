from __future__ import annotations

lazy from functools import lru_cache

lazy from opencc import OpenCC

_S2TW = OpenCC("s2twp")


@lru_cache(maxsize=2048)
def to_taiwan_traditional(text: str) -> str:
    """Normalize model and transcription output to Taiwan Traditional Chinese."""
    if not text:
        return text
    return _S2TW.convert(str(text))
