from __future__ import annotations

"""Emotional prosody and semantic-emotion mapping for companion speech.

These pure helpers translate an expressive speech state into (a) a small rate
nudge so shy/gentle lines are spoken slower and excited/proud lines faster, and
(b) a ``SemanticEmotion`` so the behavior director can pick an attentive,
gentle, or protective body pose instead of collapsing to NEUTRAL.

Kept in a separate module so ``companion_speech_runtime`` stays within the
layered-architecture line budget.
"""

lazy from application.behavior_director import SemanticEmotion
lazy from domain.expression_system import EXPRESSION_TO_EMOTION

__all__ = (
    "_emotion_rate_adjustment",
    "_semantic_emotion_for_state",
    "persist_wardrobe_mood",
    "wardrobe_mood_for_state",
)


# Emotional prosody: map an expressive speech state to a small rate nudge so a
# shy or gentle line is spoken a touch slower and an excited or proud line a
# touch faster.  The user's configured rate (-5..5) remains the baseline; this
# only adds a bounded offset that never pushes the rate outside the valid band.
_EMOTION_RATE_ADJUSTMENT = frozendict({
    "shy": -1,
    "shy_front": -1,
    "shy_cute_front": -1,
    "gentle": -1,
    "gentle_smile_front": -1,
    "worried": -1,
    "worried_front": -1,
    "reminder": -1,
    "happy": 1,
    "proud": 1,
    "proud_front": 1,
    "eureka": 1,
    "eureka_front": 1,
    "surprised": 1,
    "surprised_front": 1,
    "exasperated": 1,
    "exasperated_front": 1,
})


def _emotion_rate_adjustment(state: str) -> int:
    """Return a bounded rate nudge for an expressive speech state."""
    return _EMOTION_RATE_ADJUSTMENT.get(str(state), 0)


# Map an internal emotion name (from EXPRESSION_TO_EMOTION) to the semantic
# emotion the behavior director understands.  This covers every expressive
# state so attentive, gentle, and protective poses no longer collapse to
# NEUTRAL during speech.
_EMOTION_TO_SEMANTIC = frozendict({
    "attentive": SemanticEmotion.ATTENTIVE,
    "gentle": SemanticEmotion.GENTLE,
    "happy": SemanticEmotion.HAPPY,
    "proud": SemanticEmotion.HAPPY,
    "relieved": SemanticEmotion.GENTLE,
    "amused": SemanticEmotion.HAPPY,
    "worried": SemanticEmotion.WORRIED,
    "sad": SemanticEmotion.SAD,
    "angry": SemanticEmotion.ANGRY,
    "scold": SemanticEmotion.ANGRY,
    "mock_hit": SemanticEmotion.ANGRY,
    "exasperated": SemanticEmotion.ANGRY,
    "reminder": SemanticEmotion.REMINDER,
    "protective": SemanticEmotion.SAFETY,
})

_WARDROBE_MOOD_BY_EMOTION = frozendict({
    "attentive": "focused",
    "gentle": "affectionate",
    "happy": "cheerful",
    "proud": "cheerful",
    "relieved": "calm",
    "amused": "cheerful",
    "worried": "upset",
    "sad": "upset",
    "angry": "upset",
    "scold": "upset",
    "mock_hit": "upset",
    "exasperated": "upset",
    "reminder": "focused",
    "protective": "affectionate",
})


def _semantic_emotion_for_state(state: str) -> SemanticEmotion:
    """Resolve an expression state to a semantic emotion for body direction."""
    emotion_name = EXPRESSION_TO_EMOTION.get(str(state))
    if emotion_name is None:
        return SemanticEmotion.NEUTRAL
    return _EMOTION_TO_SEMANTIC.get(emotion_name, SemanticEmotion.NEUTRAL)


def wardrobe_mood_for_state(state: str) -> str | None:
    """Map a real expressive state into the wardrobe's stable mood vocabulary."""

    emotion_name = EXPRESSION_TO_EMOTION.get(str(state))
    return _WARDROBE_MOOD_BY_EMOTION.get(emotion_name) if emotion_name else None


def persist_wardrobe_mood(db, state: str) -> None:
    """Persist only expressive states that carry wardrobe context."""

    mood = wardrobe_mood_for_state(state)
    if mood is not None:
        db.set_setting("current_mood", mood)
