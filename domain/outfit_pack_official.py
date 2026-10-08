"""Official appearance packs shipped with the app and the ``builtin`` sentinel they answer.

A fresh profile with the ``active.json`` sentinel and ``restore_builtin_outfit`` both record
``builtin/builtin/builtin`` for every selection slot.  That sentinel keeps its
built-in semantics — always restorable — but what it renders
is decided here: while the official default outfit pack ships from the
official pack root, the garment, hairstyle and headwear slots resolve to its
default ensemble and the makeup slot resolves to the built-in makeup pack.  When the official archive is outside a stripped build the slot falls back to the
bare second-generation base.

This module is a leaf: ``domain.outfit_pack`` imports it and hands it the
listings it needs, so the identity of the official packs lives in one place
without an import cycle.
"""

from __future__ import annotations

lazy import json
lazy from collections.abc import Callable, Iterable
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from typing import Protocol


_APPEARANCE_SOURCE_PATH = Path(__file__).resolve().parents[1].joinpath(
    "assets", "characters", "mohan", "pack-source.json"
)


@dataclass(frozen=True, slots=True)
class _OfficialAppearance:
    default_outfit_id: str
    makeup_pack_id: str
    makeup_item_id: str
    makeup_variants: tuple[str, ...]
    makeup_menu_variants: tuple[str, ...]
    makeup_always_visible_variants: tuple[str, ...]
    outfit_pack_id: str
    outfit_ensemble_id: str
    native_hair: tuple[str, str]
    native_headwear: tuple[str, str]


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate character appearance field: {key}")
        result[key] = value
    return result


def _appearance_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"Character appearance {name} must be non-empty text.")
    return value


def _appearance_texts(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"Character appearance {name} must be a list.")
    result = tuple(_appearance_text(item, name) for item in value)
    if not result or len(result) != len(set(result)):
        raise ValueError(f"Character appearance {name} must contain unique values.")
    return result


def _appearance_object(
    value: object,
    keys: frozenset[str],
    name: str,
) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"Character appearance {name} must contain exactly {sorted(keys)}.")
    return value


def _load_official_appearance(path: Path = _APPEARANCE_SOURCE_PATH) -> _OfficialAppearance:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_json_object,
        )
        if not isinstance(payload, dict):
            raise ValueError("Character appearance source must be an object.")
        source = payload
        if (
            source.get("schema") != "flameblade.character-pack-build-source.v1"
            or source.get("schema_version") != 1
        ):
            raise ValueError("Character appearance source uses an unsupported schema.")
        appearance = _appearance_object(
            source.get("appearance_defaults"),
            frozenset({"default_outfit_id", "makeup", "outfit"}),
            "defaults",
        )
        makeup = _appearance_object(
            appearance["makeup"],
            frozenset({"pack_id", "item_id", "variants", "menu_variants", "always_visible_variants"}),
            "makeup",
        )
        outfit = _appearance_object(
            appearance["outfit"],
            frozenset({"pack_id", "ensemble_id", "native_hair", "native_headwear"}),
            "outfit",
        )
        hair = _appearance_object(
            outfit["native_hair"], frozenset({"item_id", "variant_id"}), "native_hair"
        )
        headwear = _appearance_object(
            outfit["native_headwear"],
            frozenset({"item_id", "variant_id"}),
            "native_headwear",
        )
        variants = _appearance_texts(makeup["variants"], "makeup.variants")
        menu_variants = _appearance_texts(makeup["menu_variants"], "makeup.menu_variants")
        always_visible = _appearance_texts(
            makeup["always_visible_variants"], "makeup.always_visible_variants"
        )
        if set(menu_variants) != set(variants) or not set(always_visible) <= set(variants):
            raise ValueError("Character appearance makeup variant groups must stay consistent.")
        return _OfficialAppearance(
            default_outfit_id=_appearance_text(
                appearance["default_outfit_id"], "default_outfit_id"
            ),
            makeup_pack_id=_appearance_text(makeup["pack_id"], "makeup.pack_id"),
            makeup_item_id=_appearance_text(makeup["item_id"], "makeup.item_id"),
            makeup_variants=variants,
            makeup_menu_variants=menu_variants,
            makeup_always_visible_variants=always_visible,
            outfit_pack_id=_appearance_text(outfit["pack_id"], "outfit.pack_id"),
            outfit_ensemble_id=_appearance_text(
                outfit["ensemble_id"], "outfit.ensemble_id"
            ),
            native_hair=(
                _appearance_text(hair["item_id"], "native_hair.item_id"),
                _appearance_text(hair["variant_id"], "native_hair.variant_id"),
            ),
            native_headwear=(
                _appearance_text(headwear["item_id"], "native_headwear.item_id"),
                _appearance_text(headwear["variant_id"], "native_headwear.variant_id"),
            ),
        )
    except (OSError, UnicodeError, ValueError) as error:
        raise RuntimeError("Bundled character appearance defaults must be valid UTF-8 JSON.") from error


_APPEARANCE = _load_official_appearance()
DEFAULT_OUTFIT_SELECTION_ID = _APPEARANCE.default_outfit_id
BUILTIN_MAKEUP_PACK_ID = _APPEARANCE.makeup_pack_id
BUILTIN_MAKEUP_ITEM_ID = _APPEARANCE.makeup_item_id
BUILTIN_MAKEUP_VARIANTS = _APPEARANCE.makeup_variants
# Keep the persisted/default variant order stable while presenting the menu from
# the lightest look to the strongest look.
BUILTIN_MAKEUP_MENU_VARIANTS = _APPEARANCE.makeup_menu_variants
# Classic and light remain visible for profiles that predate the optional
# glamorous material.  Optional variants enter the menu only when the official
# archive actually declares them.
BUILTIN_MAKEUP_ALWAYS_VISIBLE_VARIANTS = _APPEARANCE.makeup_always_visible_variants
OFFICIAL_OUTFIT_PACK_ID = _APPEARANCE.outfit_pack_id
OFFICIAL_OUTFIT_ENSEMBLE_ID = _APPEARANCE.outfit_ensemble_id
# These persisted ids predate the reviewed V5 sources.  On the V5 full-body
# atlas, the named hair is already in the native layers; repainting the old
# loose-hair asset would add a second hairstyle over the accepted bun.
OFFICIAL_NATIVE_HAIR_ALIAS = (OFFICIAL_OUTFIT_PACK_ID, *_APPEARANCE.native_hair)
OFFICIAL_NATIVE_HEADWEAR_ALIAS = (OFFICIAL_OUTFIT_PACK_ID, *_APPEARANCE.native_headwear)
# The slots the official default ensemble fills; accessories stay bare by default.
OFFICIAL_OUTFIT_CATEGORIES = frozenset({"garment", "hairstyle", "headwear"})
# Ids reserved for archives under the official pack root; user imports remain separate from them.
OFFICIAL_PACK_IDS = frozenset({OFFICIAL_OUTFIT_PACK_ID, BUILTIN_MAKEUP_PACK_ID})
BARE_SELECTION = ("builtin", "none", "none")

Identity = tuple[str, str, str]
Resolution = tuple[str, Identity]


def is_official_native_alias(category: str, identity: Identity) -> bool:
    """Recognize a legacy official id without changing saved selections."""
    return (
        (category == "hairstyle" and identity == OFFICIAL_NATIVE_HAIR_ALIAS)
        or (category == "headwear" and identity == OFFICIAL_NATIVE_HEADWEAR_ALIAS)
    )


_PLUS090_FACE_SAFE_HEADWEAR_SHA256 = frozenset({
    # Retain the previously verified member for existing installs and rollback.
    "db3295c8e3138c4f4653a1470099834a48147fa82c6dc24b603dca2842fe3558",
    # Exact mirror of the verified -090 ornament for owner-approved mirror 07.
    "99adbdc74158e7e83311449fa2604b903b96e6e7784142bf74b05ec3e4fe8916",
    # New +090 headwear approved with the round13-16d appearance batch
    # (owner-final-approval-20260928.json, INSTALL-1 code_changes_authorized).
    "43491aa8bdbc9da72af123193a0cea4431cd9e1b82a2ddbf088c1e762e6c44a4",
})


def native_overlay_is_redundant(
    category: str, identity: Identity, view_id: str, *, asset_sha256: str | None = None,
) -> bool:
    """Suppress legacy V5 hair and unverified +090 headwear.

    Other headwear views retain their existing visible on/off behavior until a
    verified native ornament partition can replace that independent overlay.
    Both exact verified +090 members still pass runtime hash and face-alpha checks.
    """
    return is_official_native_alias(category, identity) and (
        category == "hairstyle"
        or (category == "headwear" and view_id == "yaw+090-pitch+00"
            and asset_sha256 not in _PLUS090_FACE_SAFE_HEADWEAR_SHA256)
    )


class SelectionLike(Protocol):
    pack_id: str
    item_id: str
    variant_id: str


class EnsembleSelectionLike(Protocol):
    category: str
    item_id: str | None
    variant_id: str | None


class EnsembleLike(Protocol):
    pack_id: str
    ensemble_id: str
    selections: tuple[EnsembleSelectionLike, ...]


def official_outfit_ensemble(ensembles: Iterable[EnsembleLike]) -> EnsembleLike | None:
    """The official default ensemble among the installed ones; the sentinel identifies a stripped build."""
    return next(
        (
            ensemble
            for ensemble in ensembles
            if (ensemble.pack_id, ensemble.ensemble_id) == (OFFICIAL_OUTFIT_PACK_ID, OFFICIAL_OUTFIT_ENSEMBLE_ID)
        ),
        None,
    )


def builtin_makeup_resolution(requested: Identity, installed_makeup: Iterable[SelectionLike]) -> Resolution:
    """``builtin`` makeup means the official built-in variant while its pack ships; a bare face until then."""
    variant = requested[2] if requested[2] in BUILTIN_MAKEUP_VARIANTS else BUILTIN_MAKEUP_VARIANTS[0]
    official = (BUILTIN_MAKEUP_PACK_ID, BUILTIN_MAKEUP_ITEM_ID, variant)
    installed = {(item.pack_id, item.item_id, item.variant_id) for item in installed_makeup}
    return ("installed", official) if official in installed else ("builtin", BARE_SELECTION)


def builtin_outfit_resolution(category: str, requested: Identity, ensembles: Iterable[EnsembleLike]) -> Resolution:
    """``builtin`` garment/hairstyle/headwear means the official default ensemble while its pack ships."""
    ensemble = official_outfit_ensemble(ensembles)
    selection = None if ensemble is None else next(
        (item for item in ensemble.selections if item.category == category), None
    )
    if selection is None or selection.item_id is None or selection.variant_id is None:
        return ("builtin", requested)
    return ("installed", (OFFICIAL_OUTFIT_PACK_ID, selection.item_id, selection.variant_id))


def resolve_builtin_sentinel(
    store: Path,
    category: str,
    requested: Identity,
    *,
    installed_makeup: Callable[[Path], Iterable[SelectionLike]],
    installed_ensembles: Callable[[Path], Iterable[EnsembleLike]],
) -> Resolution:
    """Map one ``builtin`` selection to the official pack that answers it, or keep it bare."""
    if requested[1] == "none":
        return ("builtin", requested)
    if category == "makeup":
        return builtin_makeup_resolution(requested, installed_makeup(store))
    if category in OFFICIAL_OUTFIT_CATEGORIES:
        return builtin_outfit_resolution(category, requested, installed_ensembles(store))
    return ("builtin", requested)
