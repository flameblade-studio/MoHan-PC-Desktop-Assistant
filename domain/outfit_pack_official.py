"""Official appearance packs shipped with the app and the ``builtin`` sentinel they answer.

A fresh profile (no ``active.json``) and ``restore_builtin_outfit`` both record
``builtin/builtin/builtin`` for every selection slot.  That sentinel keeps its
built-in semantics — never removable, always restorable — but what it renders
is decided here: while the official default outfit pack ships from the
official pack root, the garment, hairstyle and headwear slots resolve to its
default ensemble and the makeup slot resolves to the built-in makeup pack.  When
an official archive is absent (a stripped build) the slot falls back to the
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
BUILTIN_MAKEUP_VARIANTS = ("classic", "light")
OFFICIAL_OUTFIT_PACK_ID = "mohan.official.blue-white-hanfu"
OFFICIAL_OUTFIT_ENSEMBLE_ID = "blue-white-hanfu"
# Owner-accepted geometry contract: at this rear three-quarter view the head
# and bun occlude the silver hairpiece, leaving only this small visible tail.
OFFICIAL_HEADWEAR_NEAR_EMPTY_CONTRACT = (
    "yaw-105-pitch+00",
    73,
    (587, 145, 30, 13),
)
# The slots the official default ensemble fills; accessories stay bare by default.
OFFICIAL_OUTFIT_CATEGORIES = frozenset({"garment", "hairstyle", "headwear"})
# Ids reserved for archives under the official pack root; a user import may never shadow them.
OFFICIAL_PACK_IDS = frozenset({OFFICIAL_OUTFIT_PACK_ID, BUILTIN_MAKEUP_PACK_ID})
BARE_SELECTION = ("builtin", "none", "none")

Identity = tuple[str, str, str]
Resolution = tuple[str, Identity]


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
    """The official default ensemble among the installed ones; ``None`` on a stripped build."""
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
