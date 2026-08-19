from __future__ import annotations

"""Personality mirroring (性格鏡像), inspired by "A・I ga Tomaranai!".

A real girl is shaped by the people around her.  If the user has been serious
and work-focused lately, MoHan grows quieter and more reserved; if the user
jokes around, her tsundere tone turns lighter.  This module analyzes recent
conversation sentiment and word style, then produces a bounded "temperature"
nudge and a word-style preference so the system prompt can resonate with the
user's soul.

This is pure domain logic with no Qt dependency.  It only consumes cheap scalar
summaries (sentiment polarity and a style score), so it never blocks the UI.
"""

lazy import re

# How strongly sentiment and style each shape the mirrored temperature.
SENTIMENT_WEIGHT = 0.5
STYLE_WEIGHT = 0.5

# Word markers used to derive a cheap sentiment/style signal from raw
# conversation text.  These are deliberately lightweight so the mirror can
# consume a large conversation window (up to the full 1M-token context) without
# blocking the UI thread — it only counts substring hits, never runs a model.
_WARM_MARKERS = (
    "謝謝", "感謝", "喜歡", "開心", "太好了", "愛", "抱", "笑",
    "thank", "love", "great", "nice", "happy", "ありがとう", "好き",
)
_SERIOUS_MARKERS = (
    "問題", "錯誤", "失敗", "緊急", "嚴重", "麻煩", "擔心", "難",
    "error", "fail", "urgent", "problem", "worry", "困った", "問題",
)
_PLAYFUL_MARKERS = (
    "哈哈", "嘻嘻", "開玩笑", "笑死", "XD", "ww", "lol", "haha",
    "冗談", "遊び",
)
_FORMAL_MARKERS = (
    "請", "報告", "分析", "評估", "規劃", "正式", "會議", "文件",
    "report", "analyze", "formal", "meeting", "document",
)
_WORD_BOUNDARY = re.compile(r"[A-Za-z0-9]+")

# The mirrored temperature eases toward its target with this per-update rate.
MIRROR_EASE_RATE = 0.3

# Temperature bounds: the mirror only nudges the base temperature, never
# overrides the user's explicit setting.
TEMPERATURE_MIN = -0.3
TEMPERATURE_MAX = 0.3


class PersonalityMirrorState:
    """Track a smooth mirrored temperature from recent conversation signals."""

    def __init__(self) -> None:
        self._temperature = 0.0

    @property
    def temperature(self) -> float:
        """The current mirrored temperature nudge in [-0.3, 0.3]."""
        return self._temperature

    @property
    def style(self) -> str:
        """A word-style preference derived from the mirrored temperature."""
        if self._temperature < -0.1:
            return "reserved"
        if self._temperature > 0.1:
            return "playful"
        return "balanced"

    def update(
        self,
        *,
        sentiment_polarity: float,
        style_score: float,
    ) -> float:
        """Advance the mirrored temperature toward its target and return it.

        ``sentiment_polarity`` is in [-1, 1] (negative = serious, positive =
        warm).  ``style_score`` is in [-1, 1] (negative = formal, positive =
        playful).
        """
        sentiment_component = _clamp(sentiment_polarity, -1.0, 1.0)
        style_component = _clamp(style_score, -1.0, 1.0)
        target = _clamp(
            SENTIMENT_WEIGHT * sentiment_component
            + STYLE_WEIGHT * style_component,
            -1.0,
            1.0,
        ) * TEMPERATURE_MAX
        self._temperature += (target - self._temperature) * MIRROR_EASE_RATE
        return self._temperature

    def observe_conversation(self, text: str) -> float:
        """Derive sentiment/style from raw conversation text and advance the
        mirror, then return the new temperature.

        This is the conversation-context entry point: it accepts an arbitrary
        window of dialogue (up to the full 1M-token context) and reduces it to
        two cheap scalar signals via substring counting, so it never blocks the
        UI thread and never depends on an external model.
        """
        sentiment_polarity, style_score = derive_signals(text)
        return self.update(
            sentiment_polarity=sentiment_polarity,
            style_score=style_score,
        )

    def reset(self) -> None:
        self._temperature = 0.0


def derive_signals(text: str) -> tuple[float, float]:
    """Reduce raw conversation text to (sentiment_polarity, style_score).

    Both outputs are in [-1, 1].  Sentiment is warm-positive vs serious-negative;
    style is playful-positive vs formal-negative.  The counts are normalized by
    the number of word tokens so a long window does not saturate the signal.
    """
    raw = str(text or "")
    lowered = raw.lower()
    warm = sum(lowered.count(m) for m in _WARM_MARKERS)
    serious = sum(lowered.count(m) for m in _SERIOUS_MARKERS)
    playful = sum(lowered.count(m) for m in _PLAYFUL_MARKERS)
    formal = sum(lowered.count(m) for m in _FORMAL_MARKERS)
    tokens = max(1, len(_WORD_BOUNDARY.findall(raw)) + raw.count(" ") + 1)
    sentiment_polarity = _clamp((warm - serious) / max(1, tokens / 8.0), -1.0, 1.0)
    style_score = _clamp((playful - formal) / max(1, tokens / 8.0), -1.0, 1.0)
    return sentiment_polarity, style_score


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
