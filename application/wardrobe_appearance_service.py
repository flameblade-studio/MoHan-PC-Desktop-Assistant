"""Application service for independent hairstyle and headwear selection.

Archive validation, saved-state resolution, and atomic writes remain owned by
:mod:`domain.outfit_pack`.  This module only exposes the two controls used by
the wardrobe presentation layer.
"""

from __future__ import annotations

lazy from collections.abc import Callable
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from domain.language_support import canonical_ui_language

lazy from domain.outfit_pack import (
    InstalledSelection,
    OutfitPackError,
    SelectionResolution,
    apply_appearance_selection,
    clear_appearance_selection,
    list_installed_selections,
    resolve_active_selection,
)

BUILTIN_SELECTION_ID = "builtin"
DEFAULT_LANGUAGE = "zh-TW"
HAIRSTYLE_CATEGORY = "hairstyle"
HEADWEAR_CATEGORY = "headwear"
NONE_OPTION_ID = "none"
SUPPORTED_CATEGORIES = frozenset({HAIRSTYLE_CATEGORY, HEADWEAR_CATEGORY})
HEADWEAR_NONE_NAMES = frozendict({
    "zh-TW": "頭飾關閉",
    "zh-CN": "头饰关闭",
    "en": "Headwear off",
    "ja-JP": "髪飾りオフ",
})
_STATE_ERRORS = (
    OSError,
    UnicodeError,
    ValueError,
    TypeError,
    AttributeError,
    KeyError,
)


@dataclass(frozen=True, slots=True)
class AppearanceOption:
    """One selectable hairstyle or headwear variant."""

    option_id: str
    display_name: str


def _validate_category(category: str) -> None:
    if category not in SUPPORTED_CATEGORIES:
        raise OutfitPackError(
            "Only hairstyle and headwear selections are supported."
        )


def _selection_id(selection: InstalledSelection) -> str:
    return "/".join(
        (selection.pack_id, selection.item_id, selection.variant_id)
    )


def _localized_selection_name(
    selection: InstalledSelection,
    language: str,
) -> str:
    selected_language = (
        language
        if language in selection.variant_display_names
        else DEFAULT_LANGUAGE
    )
    return " · ".join(
        (
            selection.pack_display_names[selected_language],
            selection.item_display_names[selected_language],
            selection.variant_display_names[selected_language],
        )
    )


def _headwear_none_name(language: str) -> str:
    selected_language = (
        language if language in HEADWEAR_NONE_NAMES else DEFAULT_LANGUAGE
    )
    return HEADWEAR_NONE_NAMES[selected_language]


def _resolve_active(
    install_root: Path,
    category: str,
) -> SelectionResolution:
    try:
        return resolve_active_selection(install_root, category)
    except OutfitPackError:
        raise
    except _STATE_ERRORS:
        raise OutfitPackError("Provide a supported saved appearance state.") from None


def _run_state_mutation(action: Callable[[], None]) -> None:
    try:
        action()
    except OutfitPackError:
        raise
    except _STATE_ERRORS:
        raise OutfitPackError("Provide a supported saved appearance state.") from None


class WardrobeAppearanceService:
    """Select hairstyle and headwear while preserving other appearance slots."""

    def __init__(self, install_root: Path) -> None:
        self.install_root = Path(install_root)

    def options(
        self,
        category: str,
        language: str = DEFAULT_LANGUAGE,
    ) -> tuple[AppearanceOption, ...]:
        """List verified variants for one supported appearance category."""
        _validate_category(category)
        language = canonical_ui_language(language)
        installed = tuple(
            AppearanceOption(
                _selection_id(selection),
                _localized_selection_name(selection, language),
            )
            for selection in list_installed_selections(
                self.install_root,
                category,
            )
        )
        if category == HEADWEAR_CATEGORY:
            return (
                AppearanceOption(
                    NONE_OPTION_ID,
                    _headwear_none_name(language),
                ),
                *installed,
            )
        return installed

    def active_id(self, category: str) -> str:
        """Return the effective option id currently resolved by the domain."""
        _validate_category(category)
        resolution = _resolve_active(self.install_root, category)
        if (
            category == HEADWEAR_CATEGORY
            and resolution.effective_pack_id == BUILTIN_SELECTION_ID
            and resolution.effective_item_id == NONE_OPTION_ID
            and resolution.effective_variant_id == NONE_OPTION_ID
        ):
            return NONE_OPTION_ID
        return "/".join(
            (
                resolution.effective_pack_id,
                resolution.effective_item_id,
                resolution.effective_variant_id,
            )
        )

    def apply(self, category: str, option_id: str) -> None:
        """Apply one verified option, or clear the optional headwear slot."""
        _validate_category(category)
        if not isinstance(option_id, str):
            raise OutfitPackError("Appearance option id must be a string.")

        if option_id == NONE_OPTION_ID:
            if category != HEADWEAR_CATEGORY:
                raise OutfitPackError("A hairstyle selection stays active; choose another style to change it.")
            _resolve_active(self.install_root, category)
            _run_state_mutation(
                lambda: clear_appearance_selection(
                    self.install_root,
                    HEADWEAR_CATEGORY,
                )
            )
            return

        selection = next(
            (
                candidate
                for candidate in list_installed_selections(
                    self.install_root,
                    category,
                )
                if _selection_id(candidate) == option_id
            ),
            None,
        )
        if selection is None:
            raise OutfitPackError(
                "The selected appearance option is not installed."
            )

        _resolve_active(self.install_root, category)
        _run_state_mutation(
            lambda: apply_appearance_selection(self.install_root, selection)
        )


__all__ = ("AppearanceOption", "WardrobeAppearanceService")

