from __future__ import annotations

from collections.abc import Mapping
lazy from dataclasses import dataclass
lazy from typing import Protocol

lazy from application.companion_phrasebook import (
    WARDROBE_REVEAL_ORIGIN,
    WARDROBE_REVEAL_QUESTION,
    CompanionPhrasebook,
    public_companion_line,
)

PENDING_OUTFIT_KEY = "wardrobe_reveal_pending_outfit_id"
LAST_REVEALED_OUTFIT_KEY = "wardrobe_last_revealed_outfit_id"


class OutfitRevealSettingsPort(Protocol):
    def read(self, keys: tuple[str, ...]) -> Mapping[str, object]:
        raise NotImplementedError

    def write(self, values: Mapping[str, object]) -> None:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class OutfitRevealContext:
    outfit_id: str
    first_reveal_pending: bool
    user_present: bool
    user_looking: bool
    speech_busy: bool
    do_not_disturb: bool


@dataclass(frozen=True, slots=True)
class OutfitRevealCue:
    outfit_id: str
    phrase_key: str
    expression: str
    gesture: str
    framing: str


class OutfitRevealStateStore:
    """Persist only reveal lifecycle identifiers, never generated imagery."""

    def __init__(self, settings: OutfitRevealSettingsPort) -> None:
        self._settings = settings

    def pending_outfit_id(self) -> str:
        value = self._settings.read((PENDING_OUTFIT_KEY,)).get(
            PENDING_OUTFIT_KEY,
            "",
        )
        return str(value or "").strip()

    def mark_pending(self, outfit_id: str) -> None:
        normalized = str(outfit_id).strip()
        if not normalized:
            raise ValueError("A pending outfit reveal requires an outfit id.")
        self._settings.write({PENDING_OUTFIT_KEY: normalized})

    def record_reveal(self, outfit_id: str, *, succeeded: bool) -> bool:
        normalized = str(outfit_id).strip()
        if not normalized or type(succeeded) is not bool:
            raise ValueError("Outfit reveal result is invalid.")
        if self.pending_outfit_id() != normalized:
            return False
        if not succeeded:
            return False
        self._settings.write(
            {
                PENDING_OUTFIT_KEY: "",
                LAST_REVEALED_OUTFIT_KEY: normalized,
            }
        )
        return True


def decide_outfit_reveal(
    context: OutfitRevealContext,
) -> OutfitRevealCue | None:
    if (
        not context.first_reveal_pending
        or not context.user_present
        or not context.user_looking
        or context.speech_busy
        or context.do_not_disturb
    ):
        return None
    return OutfitRevealCue(
        context.outfit_id,
        WARDROBE_REVEAL_QUESTION,
        "shy_cute_front",
        "show-outfit",
        "full-body",
    )


_ORIGIN_QUESTION_MARKERS = {
    "zh-TW": ("哪來的", "哪裡買", "什麼時候有", "何時有", "新衣服"),
    "zh-CN": ("哪来的", "哪里买", "什么时候有", "何时有", "新衣服"),
    "en": ("where did you get", "when did you get", "new outfit"),
    "ja-JP": ("どこで買", "いつ買", "どこから", "新しい衣装"),
}


def is_outfit_origin_question(text: str, language: str) -> bool:
    normalized = " ".join(str(text).casefold().split())
    markers = _ORIGIN_QUESTION_MARKERS.get(
        language,
        _ORIGIN_QUESTION_MARKERS["zh-TW"],
    )
    return bool(normalized and any(marker.casefold() in normalized for marker in markers))


def outfit_origin_reply(
    language: str,
    *,
    variation_index: int = 0,
    phrasebook: CompanionPhrasebook | None = None,
) -> str:
    return public_companion_line(
        language,
        WARDROBE_REVEAL_ORIGIN,
        variation_index=variation_index,
        phrasebook=phrasebook,
    )
