"""Strict loader for character-owned default appearance selections."""

from __future__ import annotations

lazy import json
lazy from pathlib import Path

lazy from domain.character_pack.character_data_models import (
    AppearanceItemSelection,
    CharacterAppearanceDefaults,
    CharacterDataError,
)

APPEARANCE_DEFAULTS_SCHEMA = "flameblade.character-appearance-defaults.v1"


def load_character_appearance_defaults(path: Path) -> CharacterAppearanceDefaults:
    """Read one UTF-8 JSON appearance contract and reject structural drift."""

    try:
        text = Path(path).read_text(encoding="utf-8")
        value = json.loads(
            text,
            object_pairs_hook=lambda pairs: _unique_object(path, pairs),
            parse_constant=lambda constant: _raise_nonfinite(path, constant),
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise CharacterDataError(
            f"{path}: valid UTF-8 appearance data is required"
        ) from error
    return _parse_appearance_defaults(value)


def _unique_object(
    path: Path,
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise CharacterDataError(f"{path}: duplicate JSON key {key!r}")
        result[key] = value
    return result


def _raise_nonfinite(path: Path, value: str) -> None:
    raise CharacterDataError(f"{path}: non-finite number {value!r} is not allowed")


def _object(
    value: object,
    path: str,
    keys: frozenset[str],
) -> dict[str, object]:
    if type(value) is not dict:
        raise CharacterDataError(f"{path}: object required")
    actual = frozenset(value)
    if actual != keys:
        missing = sorted(keys - actual)
        extra = sorted(actual - keys)
        raise CharacterDataError(
            f"{path}: fields differ; missing={missing}, extra={extra}"
        )
    return value


def _text(value: object, path: str) -> str:
    if type(value) is not str or not value.strip():
        raise CharacterDataError(f"{path}: non-empty text required")
    return value


def _strings(value: object, path: str) -> tuple[str, ...]:
    if type(value) is not list or not value:
        raise CharacterDataError(f"{path}: string array required")
    result = tuple(
        _text(item, f"{path}[{index}]")
        for index, item in enumerate(value)
    )
    if len(set(result)) != len(result):
        raise CharacterDataError(f"{path}: duplicate values are not allowed")
    return result


def _selection(value: object, path: str) -> AppearanceItemSelection:
    source = _object(value, path, frozenset({"item_id", "variant_id"}))
    return AppearanceItemSelection(
        item_id=_text(source["item_id"], f"{path}.item_id"),
        variant_id=_text(source["variant_id"], f"{path}.variant_id"),
    )


def _optional_selection(
    value: object,
    path: str,
) -> AppearanceItemSelection | None:
    return None if value is None else _selection(value, path)


def _parse_appearance_defaults(value: object) -> CharacterAppearanceDefaults:
    path = "appearance/defaults.json"
    source = _object(
        value,
        path,
        frozenset({"schema", "schema_version", "makeup", "outfit"}),
    )
    schema_version = source["schema_version"]
    if (
        source["schema"] != APPEARANCE_DEFAULTS_SCHEMA
        or type(schema_version) is not int
        or schema_version != 1
    ):
        raise CharacterDataError(
            f"{path}: expected {APPEARANCE_DEFAULTS_SCHEMA} schema version 1"
        )
    makeup = _object(
        source["makeup"],
        f"{path}.makeup",
        frozenset(
            {
                "pack_id",
                "item_id",
                "variants",
                "menu_variants",
                "always_visible_variants",
            }
        ),
    )
    outfit = _object(
        source["outfit"],
        f"{path}.outfit",
        frozenset(
            {
                "pack_id",
                "ensemble_id",
                "native_hair",
                "native_headwear",
            }
        ),
    )
    variants = _strings(makeup["variants"], f"{path}.makeup.variants")
    menu_variants = _strings(
        makeup["menu_variants"],
        f"{path}.makeup.menu_variants",
    )
    always_visible = _strings(
        makeup["always_visible_variants"],
        f"{path}.makeup.always_visible_variants",
    )
    if set(menu_variants) != set(variants):
        raise CharacterDataError(
            f"{path}.makeup.menu_variants: must contain every variant exactly once"
        )
    if not set(always_visible) <= set(variants):
        raise CharacterDataError(
            f"{path}.makeup.always_visible_variants: unknown variant"
        )
    return CharacterAppearanceDefaults(
        makeup_pack_id=_text(makeup["pack_id"], f"{path}.makeup.pack_id"),
        makeup_item_id=_text(makeup["item_id"], f"{path}.makeup.item_id"),
        makeup_variants=variants,
        makeup_menu_variants=menu_variants,
        makeup_always_visible_variants=always_visible,
        outfit_pack_id=_text(outfit["pack_id"], f"{path}.outfit.pack_id"),
        outfit_ensemble_id=_text(
            outfit["ensemble_id"],
            f"{path}.outfit.ensemble_id",
        ),
        native_hair=_selection(
            outfit["native_hair"],
            f"{path}.outfit.native_hair",
        ),
        native_headwear=_optional_selection(
            outfit["native_headwear"],
            f"{path}.outfit.native_headwear",
        ),
    )


__all__ = (
    "APPEARANCE_DEFAULTS_SCHEMA",
    "load_character_appearance_defaults",
)
