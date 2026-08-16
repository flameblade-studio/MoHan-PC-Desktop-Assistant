from __future__ import annotations

lazy from domain.language_support import (
    is_english,
    is_japanese,
    is_simplified_chinese,
)
lazy from domain.text_normalizer import to_taiwan_traditional

__all__ = ("normalize_for_language",)


def normalize_for_language(text: str, language: str) -> str:
    """Normalize generated text only when the selected UI uses Traditional Chinese."""

    value = str(text)
    if (
        is_english(language)
        or is_simplified_chinese(language)
        or is_japanese(language)
    ):
        return value
    return to_taiwan_traditional(value)
