from __future__ import annotations

"""MoHan's thousand-year dream fragments (夢囈), inspired by "A・I ga Tomaranai!".

When the companion idles for a long stretch or enters a drowsy late-night state,
she may murmur a faint, half-remembered line from her Northern Song past.  These
lines must stay firmly inside her era: Era-appropriate vocabulary, era-appropriate greetings and titles instead of casual "hello" or "master" — only the imagery of 汴京, 赤焰劍, 蘇軾's verse,
and the quiet loneliness of a sword spirit shaped by a thousand years of waiting.

This module is pure domain logic with Qt and speech-provider details outside the domain boundary, so it
can be unit-tested and reused by the proactive runtime and the visual dynamics.
"""

lazy import random
lazy import re

lazy from domain.character_pack.character_data import load_mohan_character_data

_DIALOGUES = load_mohan_character_data().dialogues

# A modern-vocabulary blocklist used to guard against anachronistic lines.  If a
# candidate line contains one of these, it receives an out-of-era status.
# CJK markers are matched as substrings (CJK uses continuous text); Latin
# markers are matched as whole words so "hi" stays separate from "this" and "within".
_MODERN_MARKERS_CJK = frozenset({
    "哈囉",
    "哈啰",
    "主人",
    "你好",
    "嗨",
    "程式",
    "程式碼",
    "電腦",
    "螢幕",
    "滑鼠",
    "鍵盤",
    "網路",
    "下載",
    "更新",
})

_MODERN_MARKERS_LATIN = frozenset({
    "hello",
    "hi",
    "ok",
    "app",
    "bug",
})

# The canonical dream-fragment library.  Each line is a faint, grey murmur that
# evokes the Northern Song while preserving the character voice. They are written in
# Traditional Chinese first; the other three languages are provided below.
_SOMNILOQUY_ZH_TW = _DIALOGUES["zh-TW"].line_sets["somniloquy"]
_SOMNILOQUY_ZH_CN = _DIALOGUES["zh-CN"].line_sets["somniloquy"]
_SOMNILOQUY_EN = _DIALOGUES["en"].line_sets["somniloquy"]
_SOMNILOQUY_JA = _DIALOGUES["ja-JP"].line_sets["somniloquy"]
_SOMNILOQUY_BY_LANGUAGE = frozendict({
    "zh-TW": _SOMNILOQUY_ZH_TW,
    "zh-CN": _SOMNILOQUY_ZH_CN,
    "en": _SOMNILOQUY_EN,
    "ja-JP": _SOMNILOQUY_JA,
})


def somniloquy_lines(language: str) -> tuple[str, ...]:
    """Return the dream-fragment library for a language, defaulting to zh-TW."""
    return _SOMNILOQUY_BY_LANGUAGE.get(str(language), _SOMNILOQUY_ZH_TW)


def random_somniloquy(language: str, rng: random.Random | None = None) -> str:
    """Return one random dream fragment for the given language."""
    picker = rng or random
    lines = somniloquy_lines(language)
    return picker.choice(lines)


def is_anachronistic(line: str) -> bool:
    """Return True if a dream line contains out-of-era modern vocabulary."""
    lowered = line.lower()
    for marker in _MODERN_MARKERS_CJK:
        if marker.lower() in lowered:
            return True
    for marker in _MODERN_MARKERS_LATIN:
        if re.search(rf"\b{re.escape(marker)}\b", lowered):
            return True
    return False


def validate_library(language: str) -> tuple[str, ...]:
    """Return anachronistic lines in a language's library; a zero-line result confirms a clean library."""
    return tuple(
        line for line in somniloquy_lines(language) if is_anachronistic(line)
    )


# The dream murmur must be rare: a faint, half-remembered line that surfaces
# occasionally during idle or sleep, keeping conversation measured rather than constant so
# interrupt the user's work.  This is the per-check probability.
SOMNILOQUY_TRIGGER_PROBABILITY = 0.005  # 0.5%


def should_murmur(rng: random.Random | None = None) -> bool:
    """Return True with a very low probability, gating a dream murmur."""
    picker = rng or random
    return picker.random() < SOMNILOQUY_TRIGGER_PROBABILITY
