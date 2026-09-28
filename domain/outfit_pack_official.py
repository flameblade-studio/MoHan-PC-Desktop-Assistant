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

lazy from collections.abc import Callable, Iterable
lazy from pathlib import Path
lazy from typing import Protocol

BUILTIN_MAKEUP_PACK_ID = "mohan.makeup.builtin"
BUILTIN_MAKEUP_ITEM_ID = "mohan-signature"
BUILTIN_MAKEUP_VARIANTS = ("classic", "light", "glamorous")
# Keep the persisted/default variant order stable while presenting the menu from
# the lightest look to the strongest look.
BUILTIN_MAKEUP_MENU_VARIANTS = ("light", "classic", "glamorous")
# Classic and light remain visible for profiles that predate the optional
# glamorous material.  Optional variants enter the menu only when the official
# archive actually declares them.
BUILTIN_MAKEUP_ALWAYS_VISIBLE_VARIANTS = ("light", "classic")
OFFICIAL_OUTFIT_PACK_ID = "mohan.official.blue-white-hanfu"
OFFICIAL_OUTFIT_ENSEMBLE_ID = "blue-white-hanfu"
# These persisted ids predate the reviewed V5 sources.  On the V5 full-body
# atlas, the named hair is already in the native layers; repainting the old
# loose-hair asset would add a second hairstyle over the accepted bun.
OFFICIAL_NATIVE_HAIR_ALIAS = (OFFICIAL_OUTFIT_PACK_ID, "loose-hair", "ink-black")
OFFICIAL_NATIVE_HEADWEAR_ALIAS = (OFFICIAL_OUTFIT_PACK_ID, "silver-hairpiece", "silver")
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
