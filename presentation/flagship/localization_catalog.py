"""Typed building blocks for immutable flagship translation catalogs."""

from __future__ import annotations

lazy from collections.abc import Mapping

TranslationRow = tuple[str, str, str]
TranslationCatalog = frozendict[str, TranslationRow]


def translations(
    simplified_chinese: str,
    english: str,
    japanese: str,
) -> TranslationRow:
    """Keep the non-default languages in the required public order."""

    return simplified_chinese, english, japanese


def merge_translation_catalogs(
    *catalogs: Mapping[str, TranslationRow],
) -> TranslationCatalog:
    """Combine disjoint catalogs and fail closed on an ambiguous source."""

    merged: dict[str, TranslationRow] = {}
    for catalog in catalogs:
        duplicates = merged.keys() & catalog.keys()
        if duplicates:
            duplicate_list = ", ".join(sorted(repr(source) for source in duplicates))
            raise ValueError(f"Duplicate flagship translation source: {duplicate_list}")
        merged.update(catalog)
    return frozendict(merged)


__all__ = (
    "TranslationCatalog",
    "TranslationRow",
    "merge_translation_catalogs",
    "translations",
)
